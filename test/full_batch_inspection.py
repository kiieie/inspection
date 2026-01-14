
import cv2
import os
import sys
import json
import uuid
import re
import pandas as pd
import numpy as np
from datetime import datetime
from loguru import logger
from pathlib import Path
import importlib.util

# 프로젝트 경로 추가
sys.path.insert(0, os.getcwd())

import config
from database import SessionLocal, engine, Base
from inspectors.vlm_inspector import VLMInspector
from inspectors.ag_inspector import AGInspector 
from utils.matching import evaluate_gauge_reading, is_type_compatible
from utils.visualizer import (
    draw_diagnosis_box, 
    draw_summary_table, 
    draw_outline_text,
    draw_text_with_bg
)

# [DB Setup]
spec = importlib.util.spec_from_file_location("models", str(Path(config.DB_CONFIG['models_dir']) / config.DB_CONFIG['models_file']))
models = importlib.util.module_from_spec(spec)
sys.modules["models"] = models
spec.loader.exec_module(models)

def get_friendly_spatial_desc(depth, index):
    """사람이 이해하기 쉬운 위치 설명 생성 (2026-01-13)"""
    prefix = "전면" if depth == "Front" else "후면"
    return f"{prefix} {index + 1}번"

def run_full_batch_inspection():
    logger.info("🚀 [전수 자동 점검] 최종 리포트 정규화 및 전수(930개) 반영 시작 (2026-01-13)")
    
    db = SessionLocal()
    vlm_inspector = VLMInspector()
    ag_inspector = AGInspector()
    
    # 1. 인스펙션 그룹 로드
    points = db.query(models.InspectionPoint).all()
    if not points:
        logger.error("❌ DB에 인스펙션 데이터가 없습니다.")
        return

    df_points = pd.DataFrame([p.__dict__ for p in points])
    if '_sa_instance_state' in df_points.columns:
        df_points = df_points.drop(columns=['_sa_instance_state'])
    
    grouped = df_points.groupby(['mission_name', 'inspection_name'])
    
    from main import DiagnosisSystem
    ds = DiagnosisSystem()
    
    results_dir = os.path.join(os.getcwd(), "test_results")
    os.makedirs(results_dir, exist_ok=True)
    
    excel_report_rows = []
    total_json_data = {
        "report_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_items_in_db": len(df_points), 
        "total_groups": len(grouped),
        "inspections": []
    }

    for idx, ((mission, insp_name), group) in enumerate(grouped):
        logger.info(f"🔄 [{idx+1}/{len(grouped)}] 처리 중: {mission} / {insp_name}")
        
        img_path = ds.get_latest_image(config.BASE_DIR, mission, insp_name)
        img = None
        final_img = None
        all_dets = []
        ag_dets = []
        
        if img_path and os.path.exists(img_path):
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
                            "center_x": (x1+x2)/2, "center_y": (y1+y2)/2,
                            "area": (x2-x1)*(y2-y1), "used": False
                        })
                ag_dets = ag_inspector.inspect_all(img_path)
        
        # [Step 3] 엑셀 기준 공간 매칭
        excel_rear = group[group['facility_2'].str.contains('(rear)', na=False, regex=False)]
        excel_front = group[~group['facility_2'].str.contains('(rear)', na=False, regex=False)]
        
        results_map = {}
        
        for depth, ex_bucket in [("Front", excel_front), ("Rear", excel_rear)]:
            type_groups = ex_bucket.groupby('inspection_point_type')
            for target_type, type_df in type_groups:
                compatible_dets = [d for d in all_dets if not d['used'] and is_type_compatible(target_type, d['label'])]
                if depth == "Rear":
                    compatible_dets.sort(key=lambda d: d['area'], reverse=True)
                else:
                    compatible_dets.sort(key=lambda d: d['center_x'])
                
                type_df_indexed = type_df.reset_index()
                for sub_idx, row in type_df_indexed.iterrows():
                    r_idx = row['index']
                    target = str(row['inspection_point_type'])
                    friendly_pos = get_friendly_spatial_desc(depth, sub_idx)
                    
                    # [2026-01-13] 초기 상태 정규화 (사용자 요청: 미탐지)
                    res = {
                        "type": target, "found": False, "val": "미탐지", "status": "FAIL", 
                        "spatial_desc": friendly_pos
                    }
                    if not img_path or not os.path.exists(img_path):
                        res["val"] = "미탐지 (이미지 없음)"
                    
                    matched = compatible_dets[sub_idx] if sub_idx < len(compatible_dets) else None
                    if matched:
                        matched['used'] = True
                        x1, y1, x2, y2 = matched['box']
                        val_display = "탐지"
                        is_ok = True
                        v_res = ""
                        
                        if target.startswith("DG") or target.startswith("Class"):
                            pad = 10
                            crop = img[max(0,y1-pad):min(img.shape[0],y2+pad), max(0,x1-pad):min(img.shape[1],x2+pad)]
                            tmp_crop = f"temp_batch_{uuid.uuid4().hex}.jpg"
                            cv2.imwrite(tmp_crop, crop)
                            q_text = config.VLM_PROMPTS.get(target) or next((v for k, v in config.VLM_PROMPTS.items() if target.startswith(k)), row.get('query', "Read precisely."))
                            v_res = vlm_inspector.analyze(tmp_crop, str(q_text))
                            if target.startswith("DG"):
                                nums = re.findall(r"[-+]?\d*\.\d+|\d+", v_res)
                                ex_val = float(nums[0]) if nums else None
                                val_display_gau, _, is_ok = evaluate_gauge_reading({'value': ex_val, 'label': matched['label']}, row)
                                val_display = str(val_display_gau)
                            else:
                                val_display = v_res.replace("\n", " ")
                                is_ok = True
                            if os.path.exists(tmp_crop): os.remove(tmp_crop)
                        elif target.startswith("AG"):
                            best_ag = None
                            max_iou = 0
                            for ad in ag_dets:
                                ax1, ay1, ax2, ay2 = ad['box']
                                iou_x1, iou_y1 = max(x1, ax1), max(y1, ay1)
                                iou_x2, iou_y2 = min(x2, ax2), min(y2, ay2)
                                inter = max(0, iou_x2-iou_x1) * max(0, iou_y2-iou_y1)
                                if inter > max_iou: 
                                    max_iou = inter; best_ag = ad
                            if best_ag:
                                val_num, _, is_ok = evaluate_gauge_reading(best_ag, row)
                                val_display = str(val_num)
                            else: val_display = "탐지 (AG 판독 실패)"; is_ok = False
                        elif target.startswith("LED") or target.startswith("Sw"):
                            if hasattr(ds.sw_led_inspector, 'check_status_compliance'):
                                is_ok, reason = ds.sw_led_inspector.check_status_compliance(matched['label'], target)
                                # [2026-01-13] 'Match' 등의 영문 결과를 한국어로 치환
                                if is_ok: val_display = "탐지"
                                else: val_display = "미탐지"
                            else: val_display = "탐지"
                        
                        if final_img is not None:
                            draw_diagnosis_box(final_img, matched['box'], row, matched['label'], "PASS", val_display, is_ok)
                        
                        res.update({"found": True, "val": val_display, "status": "PASS" if is_ok else "FAIL"})
                    
                    results_map[r_idx] = res

        # [리포트 생성 및 이미지 저장]
        res_img_path = "이미지 없음"
        if final_img is not None:
            save_dir = os.path.join(results_dir, mission)
            os.makedirs(save_dir, exist_ok=True)
            # 2026-01-13 [Fix]: 중복 확장자 방지
            out_name = insp_name if insp_name.lower().endswith(".jpg") else f"{insp_name}.jpg"
            res_img_path = os.path.abspath(os.path.join(save_dir, out_name))
            cv2.imwrite(res_img_path, final_img)

        group_data = []
        for i, row in group.iterrows():
            r = results_map.get(i)
            if not r:
                r = {"type": str(row['inspection_point_type']), "found": False, "val": "미탐지", "status": "FAIL", "spatial_desc": "분류불가"}
                if not img_path: r["val"] = "미탐지 (이미지 없음)"
            
            row_dict = {
                "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Mission": mission,
                "Source Image Path": os.path.abspath(img_path) if img_path else "이미지 없음",
                "Result Image Path": res_img_path,
                "Type": str(row['inspection_point_type']),
                "Spatial Position": r['spatial_desc'],
                "Result Value": r['val'],
                "Judgement": r['status']
            }
            excel_report_rows.append(row_dict)
            group_data.append(row_dict)
            
        total_json_data["inspections"].append({
            "mission": mission, "name": insp_name, "results": group_data
        })

    logger.info(f"📊 최종 보고서 행 수: {len(excel_report_rows)} / DB 포인트 수: {len(df_points)}")

    # 최종 저장 (v5 정규화 완료)
    final_excel = os.path.join(results_dir, "batch_inspection_final_normalized.xlsx")
    final_json = os.path.join(results_dir, "batch_inspection_final_normalized.json")
    
    pd.DataFrame(excel_report_rows).to_excel(final_excel, index=False)
    with open(final_json, "w", encoding="utf-8") as f:
        json.dump(total_json_data, f, indent=4, ensure_ascii=False)
    
    logger.success(f"✅ 정규화된 930개 전수 리포트 생성 완료: {results_dir}")

if __name__ == "__main__":
    run_full_batch_inspection()
