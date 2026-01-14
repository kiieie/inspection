
import cv2
import os
import sys
import time
import json
import uuid
import re
import pandas as pd
from datetime import datetime
from loguru import logger
from pathlib import Path
import importlib.util
import argparse

# 프로젝트 경로 추가
sys.path.insert(0, os.getcwd())

import config
from database import SessionLocal
from inspectors.vlm_inspector import VLMInspector
from inspectors.ag_inspector import AGInspector 
from utils.matching import evaluate_gauge_reading, is_type_compatible
import models
# [DB Setup]
spec = importlib.util.spec_from_file_location("models", str(Path(config.DB_CONFIG['models_dir']) / config.DB_CONFIG['models_file']))
models = importlib.util.module_from_spec(spec)
sys.modules["models"] = models
spec.loader.exec_module(models)

from models import InspectionPoint, InspectionData, MissionResult, DiagnosisState, InspectionResult

def extract_insp_name_from_path(file_path):
    """파일명에서 타임스탬프를 제거하고 원본 inspection_name을 추출함"""
    fname = os.path.basename(file_path)
    base, ext = os.path.splitext(fname)
    parts = base.split('_')
    if len(parts) > 1:
        return "_".join(parts[:-2]) + ext
    return fname

def run_diagnosis_watcher(visualize=False):
    """2초마다 InspectionData를 폴링하여 진단 수행 (2026-01-14) 
    - [Update]: 시각화 플래그 추가 및 조건부 전시
    """
    logger.info("🚀 [Watcher] Polling & Manual Interaction Process Started")
    
    db = SessionLocal()
    vlm_inspector = VLMInspector()
    ag_inspector = AGInspector()
    
    from main import DiagnosisSystem
    ds = DiagnosisSystem()
    
    results_dir = os.path.join(os.getcwd(), "test_results")
    if not os.path.exists(results_dir):
        os.makedirs(results_dir, exist_ok=True)
        
    report_path = os.path.join(results_dir, "realtime_batch_report_final.xlsx")
    excel_rows = []
    window_name = "Diagnosis Monitor (Press Any Key to Continue)"
    
    try:
        while True:
            task = db.query(models.InspectionData).filter(
                models.InspectionData.state == models.DiagnosisState.QUEUED
            ).order_by(models.InspectionData.id.asc()).first()
            
            if not task:
                time.sleep(2)
                continue
            
            task.state = models.DiagnosisState.RUNNING
            db.commit()
            
            logger.info(f"🔄 [Watcher] Task ID: {task.id} | Analyzing...")
            
            match_key = task.data_result_dir if task.data_result_dir else extract_insp_name_from_path(task.data_raw_dir)
            points = db.query(models.InspectionPoint).filter(
                models.InspectionPoint.mission_name == task.mission_name,
                models.InspectionPoint.inspection_name == match_key
            ).all()
            
            img_path = task.data_raw_dir
            img = None; final_img = None; all_dets = []; ag_dets = []
            
            image_exists = os.path.exists(img_path) and img_path not in ["No Image", "이미지 없음"]
            
            if image_exists:
                img = cv2.imread(img_path)
                if img is not None:
                    final_img = img.copy()
                    yolo_res = ds.detector.predict(img, conf=0.1, verbose=False)
                    if yolo_res and len(yolo_res[0].boxes) > 0:
                        for box in yolo_res[0].boxes:
                            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                            all_dets.append({
                                "box": [x1, y1, x2, y2],
                                "label": yolo_res[0].names[int(box.cls[0])],
                                "center_x": (x1+x2)/2, "center_y": (y1+y2)/2, "used": False
                            })
                    ag_dets = ag_inspector.inspect_all(img_path)
            
            results_to_save = []
            summary_list = []
            
            excel_Rear = [p for p in points if '(rear)' in (p.facility_2 or "").lower()]
            excel_Front = [p for p in points if '(rear)' not in (p.facility_2 or "").lower()]
            
            for depth, bucket in [("Front", excel_Front), ("Rear", excel_Rear)]:
                types = list(set([p.inspection_point_type for p in bucket]))
                for t in types:
                    t_points = [p for p in bucket if p.inspection_point_type == t]
                    comp_dets = [d for d in all_dets if not d['used'] and is_type_compatible(t, d['label'])]
                    
                    if depth == "Rear": comp_dets.sort(key=lambda d: (d['box'][2]-d['box'][0])*(d['box'][3]-d['box'][1]), reverse=True)
                    else: comp_dets.sort(key=lambda d: d['center_x'])
                    
                    for sub_idx, p in enumerate(t_points):
                        friendly_pos = f"{depth} No.{sub_idx+1}"
                        res_val = "Not Detected"; is_ok = False
                        
                        matched = comp_dets[sub_idx] if sub_idx < len(comp_dets) else None
                        if matched:
                            matched['used'] = True; res_val = "Detected"; is_ok = True
                            
                            matched_kpts = None
                            if t.startswith("DG") or t.startswith("Class"):
                                x1,y1,x2,y2 = matched['box']
                                crop = img[max(0,y1-10):min(img.shape[0],y2+10), max(0,x1-10):min(img.shape[1],x2+10)]
                                tmp = f"temp_watcher_{uuid.uuid4().hex}.jpg"
                                cv2.imwrite(tmp, crop)
                                q = config.VLM_PROMPTS.get(t) or p.query or "Read state."
                                v_res = vlm_inspector.analyze(tmp, str(q))
                                
                                if t.startswith("DG"):
                                    nums = re.findall(r"[-+]?\d*\.\d+|\d+", v_res)
                                    val_num = float(nums[0]) if nums else None
                                    val_result, _, ok_flag = evaluate_gauge_reading({'value': val_num}, p.__dict__)
                                    res_val = str(val_result) if val_result is not None else v_res.replace("\n", " ")
                                    is_ok = ok_flag if val_result is not None else True
                                else:
                                    res_val = v_res.replace("\n", " "); is_ok = True
                                if os.path.exists(tmp): os.remove(tmp)
                            elif t.startswith("AG"):
                                x1,y1,x2,y2 = matched['box']
                                best_ag = None; max_iou = 0
                                for ad in ag_dets:
                                    ax1,ay1,ax2,ay2 = ad['box']
                                    inter = max(0, min(x2,ax2)-max(x1,ax1)) * max(0, min(y2,ay2)-max(y1,ay1))
                                    if inter > max_iou: max_iou = inter; best_ag = ad
                                if best_ag:
                                    v_num, _, ok_flag = evaluate_gauge_reading(best_ag, p.__dict__)
                                    res_val = str(v_num) if v_num is not None else "Detected"; is_ok = ok_flag
                                    matched_kpts = best_ag.get('keypoints')
                                else:
                                    res_val = "Detected (AG Failed)"; is_ok = False
                            
                            if final_img is not None:
                                draw_diagnosis_box(final_img, matched['box'], p.__dict__, matched['label'], "PASS", res_val, is_ok, keypoints=matched_kpts)
                        
                        elif not image_exists: res_val = "No_Image"
                        
                        summary_list.append({
                            "type": t, 
                            "found": matched is not None,
                            "fac1": p.facility_1,
                            "fac2": p.facility_2
                        })
                        res_obj = {
                            "site": p.site, "mission_name": p.mission_name, "inspection_name": p.inspection_name,
                            "facility_1": p.facility_1, "facility_2": p.facility_2, "inspection_point_type": p.inspection_point_type,
                            "model_type": p.model_type, "model_ver": p.model_ver, "hyperparameter": p.hyperparameter,
                            "min_value": p.min_value, "max_value": p.max_value, "normal_min_value": p.normal_min_value,
                            "normal_max_value": p.normal_max_value, "comment_master": p.comment, "report_name": p.report_name,
                            "inspection_details": p.inspection_details, "inspection_period": p.inspection_period,
                            "insepction_cell_number": p.insepction_cell_number, "query": p.query, "sort_key": p.sort_key,
                            "inspection_point_id": p.id, "inspection_datetime": datetime.now(),
                            "result_value": res_val, "judgement": "PASS" if is_ok else "FAIL", "data_raw_dir": img_path,
                            "spatial_info": matched['box'] if matched else None
                        }
                        results_to_save.append(res_obj)

            if final_img is not None:
                draw_right_summary_table(final_img, summary_list)

            res_img_path = "No Image"
            if final_img is not None:
                os.makedirs(os.path.join(results_dir, task.mission_name), exist_ok=True)
                raw_fname = os.path.basename(task.data_raw_dir)
                out_name = f"res_{raw_fname}"
                res_img_path = os.path.abspath(os.path.join(results_dir, task.mission_name, out_name))
                cv2.imwrite(res_img_path, final_img)
                
                if visualize:
                    disp_img = cv2.resize(final_img, (1920, 1080))
                    cv2.imshow(window_name, disp_img)
                    logger.info("⏸ [Watcher] Waiting for user key input to close window...")
                    cv2.waitKey(0) 
                    cv2.destroyWindow(window_name)
                    cv2.waitKey(1) 
                else:
                    logger.debug(f"🖼 [Watcher] Result image saved: {res_img_path}")
            
            for r in results_to_save:
                r["data_result_dir"] = res_img_path
                new_res = models.InspectionResult(**{k: v for k, v in r.items() if hasattr(models.InspectionResult, k)})
                db.add(new_res)
                excel_rows.append({
                    "Time": r["inspection_datetime"].strftime("%Y-%m-%d %H:%M:%S"),
                    "Mission": r["mission_name"], "Facility": f"{r['facility_1']} | {r['facility_2']}",
                    "Type": r["inspection_point_type"], "Value": r["result_value"], "Judge": r["judgement"]
                })
            
            pd.DataFrame(excel_rows).to_excel(report_path, index=False)
            task.state = models.DiagnosisState.COMPLETED
            db.commit()
            status_msg = f" (Window Closed by User)" if visualize else ""
            logger.success(f"✅ [Watcher] Task ID {task.id} Processed{status_msg}")
            
    except KeyboardInterrupt:
        logger.info("🛑 [Watcher] Interrupted.")
    finally:
        cv2.destroyAllWindows()
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Diagnosis Watcher with Optional Visualization")
    parser.add_argument("--visualize", action="store_true", help="Display result windows and wait for key input")
    args = parser.parse_args()
    
    run_diagnosis_watcher(visualize=args.visualize)
