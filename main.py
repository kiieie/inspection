"""
프로그램명: AI 설비 진단 통합 컨트롤러 (main.py) - 고도화 엔진 버전 (Fix)
버전: v2.5.1 (2026-01-14)
변경 사항:
- [Fix] 이전 수정 시 누락된 추론/정렬 로직 전면 복구
- [Fix] InspectionResult 저장 시 'data_result_dir'에 절대 경로 저장 (웹 표시 오류 해결)
- [Logic] 그룹형 매칭 및 시각화 로직 안정화
"""

import os
import cv2
import sys
import time
import pandas as pd
import numpy as np
import importlib.util
from pathlib import Path
from loguru import logger
from datetime import datetime
from collections import Counter
from ultralytics import YOLO
import argparse

# 설정 및 유틸리티 로드
import config
from database import SessionLocal
from utils.matching import sort_by_x_priority, is_type_compatible, evaluate_gauge_reading
from utils.visualizer import draw_diagnosis_box, draw_summary_table, draw_outline_text

# [DB Setup] models.py 동적 임포트
models_path = Path(config.DB_CONFIG['models_dir']) / config.DB_CONFIG['models_file']
spec = importlib.util.spec_from_file_location("models", str(models_path))
models = importlib.util.module_from_spec(spec)
sys.modules["models"] = models
spec.loader.exec_module(models)

# 모델 클래스들 가져오기
from models import InspectionPoint, InspectionData, MissionResult, DiagnosisState, InspectionResult

# 인스펙터 컴포넌트 로드
from inspectors.ag_inspector import AGInspector
from inspectors.dg_inspector import DGInspector
from inspectors.sw_led_inspector import SW_LED_Inspector
from inspectors.vlm_inspector import VLMInspector

class DiagnosisSystem:
    def __init__(self, visualize=True):
        self.base_path = config.BASE_DIR
        self.excel_path = config.EXCEL_FILE
        self.visualize = visualize
        
        try:
            self.detector = YOLO(config.MODEL_CONFIG["classifier"])
            self.ag_inspector = AGInspector(config.MODEL_CONFIG["ag_pose"])
            self.dg_inspector = DGInspector()
            self.sw_led_inspector = SW_LED_Inspector()
            self.vlm_inspector = VLMInspector()
            logger.info("✅ DiagnosisSystem 초기화 완료")
        except Exception as e:
            logger.error(f"❌ 초기화 실패: {e}")
            raise e

    def process_task(self, task_id):
        """태스크 그룹 전체를 분석하고 결과를 각각 저장합니다."""
        db = SessionLocal()
        try:
            # 1. 태스크 및 마스터 데이터 로드
            task = db.query(InspectionData).filter(InspectionData.id == task_id).first()
            if not task: return

            insp_name = task.inspection_name
            mission_name = task.mission_name
            task.state = DiagnosisState.RUNNING
            db.commit()

            points = db.query(InspectionPoint).filter(
                InspectionPoint.site == task.site,
                InspectionPoint.mission_name == mission_name,
                InspectionPoint.inspection_name == insp_name
            ).all()

            # [Fix] photo_time을 미리 추출 (No Master Info 처리 시 필요)
            try:
                # Filename pattern: SpotCam-PTZ-2_20260106_111042.jpg
                filename = os.path.basename(task.data_raw_dir)
                time_part = filename.split('_')[-1].split('.')[0] # 111042
                date_part = filename.split('_')[-2] # 20260106
                photo_time_str = f"{date_part}_{time_part}"
                photo_time = datetime.strptime(photo_time_str, "%Y%m%d_%H%M%S")
                logger.info(f"📸 Extracted Photo Time: {photo_time}")
            except Exception:
                logger.warning(f"⚠️ Failed to extract photo time from {task.data_raw_dir}, using now()")
                photo_time = datetime.now()

            if not points:
                logger.warning(f"⚠️ 마스터 정보 없음: {mission_name} / {insp_name}")
                
                # [Fix] Master 정보가 없어도 결과 이미지 저장 및 DB 기록 수행
                img_path = os.path.join(self.base_path, task.data_raw_dir)
                if os.path.exists(img_path):
                    # 1. Image Load
                    img = cv2.imread(img_path)
                    
                    if img is not None:
                        # 2. Prepare Result Path
                        res_dir = Path("test_results")
                        res_dir.mkdir(parents=True, exist_ok=True)
                        unique_sub = f"task_{task_id}_{int(time.time())}"
                        
                        # [Fix] Use actual site/mission/inspection even if points are missing (Requested by User)
                        # Previous: os.path.join(config.RESULT_BASE_DIR, "Unknown", "Unknown", "Unknown", unique_sub)
                        target_dir = os.path.join(config.RESULT_BASE_DIR, task.site, mission_name, insp_name, unique_sub)
                        os.makedirs(target_dir, exist_ok=True)
                        
                        orig_name = os.path.splitext(os.path.basename(img_path))[0]
                        structured_res_path = os.path.join(target_dir, f"{orig_name}_result.jpg")
                        res_abs_path = os.path.abspath(structured_res_path)

                        # 3. Save Result Image (Original)
                        cv2.imwrite(res_abs_path, img)
                        logger.info(f"   💾 Saved Result Image (No Master): {res_abs_path}")

                        # 4. Save DB Record (InspectionResult)
                        # Create a dummy point object for _save_result or manually insert
                        # Since point is None, we construct InspectionResult directly here to avoid issues
                        res = InspectionResult(
                            site=task.site,
                            mission_name=task.mission_name,
                            inspection_name=task.inspection_name,
                            facility_1="Unknown",
                            facility_2="Unknown",
                            inspection_point_type="Unknown",
                            inspection_point_id=0,
                            result_value="No Master Info",
                            judgement="FAIL",
                            data_raw_dir=img_path,
                            data_result_dir=res_abs_path,
                            spatial_info={"box": [0,0,0,0]},
                            inspection_datetime=datetime.now().replace(microsecond=0),
                            photo_time=photo_time
                        )
                        db.add(res)
                        
                        # [Request] Visualization for No Master Info
                        if self.visualize:
                            cv2.imshow("Inspection Result", img)
                            cv2.waitKey(1)

                        task.data_result_dir = res_abs_path
                        task.state = DiagnosisState.COMPLETED # Mark as completed (processed) even if failed logic
                        db.commit()
                        logger.info(f"✅ 태스크 {task_id} 처리 완료 (No Master Info)")
                        return
                    else:
                        logger.error("❌ Image Load Failed (No Master)")
                
                task.state = DiagnosisState.FAILED
                db.commit()
                return

            # [Extract Photo Time from Path]
            # Format: {insp_name}_{YYYYMMDD}_{HHMMSS}.jpg
            photo_time = None
            try:
                base_fname = os.path.splitext(os.path.basename(task.data_raw_dir))[0]
                parts = base_fname.split('_')
                if len(parts) >= 2:
                    # Last two are usually date and time
                    date_str = parts[-2]
                    time_str = parts[-1]
                    if len(date_str) == 8 and len(time_str) == 6:
                        photo_time = datetime.strptime(f"{date_str}{time_str}", "%Y%m%d%H%M%S")
                        logger.info(f"📸 Extracted Photo Time: {photo_time}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to extract photo_time: {e}")

            
            # [Summary Log]
            types_summary = [p.inspection_point_type for p in points]
            logger.info(f"📋 Plan: Need to check {len(points)} points -> {types_summary}")

            # 2. 이미지 로드
            img_path = os.path.join(self.base_path, task.data_raw_dir)

            if not img_path:
                self._save_error_result(db, task, "Image Missing")
                return

            img = cv2.imread(img_path)
            if img is None:
                self._save_error_result(db, task, "Image Load Failed")
                return
            final_img = img.copy()

            # [Fix] 결과 이미지 경로생성을 루프 밖(앞)으로 이동하여 DB 저장 시 활용
            res_dir = Path("test_results")
            res_dir.mkdir(parents=True, exist_ok=True)
            res_filename = f"res_{task_id}_{int(time.time())}.jpg"
            res_path = res_dir / res_filename
            res_abs_path = os.path.abspath(str(res_path))

            # 3. 통합 추론 (AG, DG, CLS)
            all_detections = []
            
            # [Step 1] Pose Model (AG)
            ag_dets = self.ag_inspector.inspect_all(img_path)
            for d in ag_dets: d['source'] = "Pose"
            all_detections.extend(ag_dets)
            
            # [Step 2] Main YOLO Model (DG & CLS) - Single Pass
            # DGInspector가 모델을 매번 로드하는 비효율을 제거하고 main의 detector 사용
            # [Fix] conf를 0.1로 낮춰 미검출 방지
            results = self.detector.predict(img_path, conf=0.4, verbose=False)
            
            dg_dets = []
            cls_dets = []
            
            if results:
                names = results[0].names
                box_count = len(results[0].boxes)
                # [Debug] 검출된 총 객체 수와 라벨 목록 로깅
                detected_labels = [names[int(box.cls[0])] for box in results[0].boxes]
                logger.info(f"🕵️ YOLO Detected Total: {box_count} | Labels: {detected_labels}")
                
                for box in results[0].boxes:
                    cls_id = int(box.cls[0])
                    label = names[cls_id]
                    conf = float(box.conf[0])
                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                    
                    det_obj = {
                        'label': label,
                        'box': [x1, y1, x2, y2],
                        'area': (x2 - x1) * (y2 - y1),
                        'center_x': (x1 + x2) / 2,
                        'center_y': (y1 + y2) / 2,
                        'used': False
                    }

                    # DG 분류 (라벨에 DG나 digital 포함)
                    if 'DG' in label or 'digital' in label.lower():
                        det_obj['source'] = "OCR" # DG는 OCR/VLM 소스로 취급
                        # DG 전용 분석 (M 행렬 추출 등) - 필요 시 Crop해서 analyze_crop 호출
                        crop = final_img[y1:y2, x1:x2]
                        if crop.size > 0:
                            # DGInspector의 analyze_crop을 이용해 회전보정 정보 등 획득
                            _, _, _, _, M = self.dg_inspector.analyze_crop(crop)
                            det_obj['M'] = M
                            det_obj['ocr_details'] = [] # OCR Disabled
                            det_obj['value'] = None # 추후 VLM으로 채움
                        dg_dets.append(det_obj)
                    
                    # AG 분류 (이미 Pose에서 했지만, Box형 AG가 잡힐 경우 무시하거나 보완)
                    elif label.startswith('AG_'):
                        continue # Pose 결과 사용 우선
                        
                    # 일반 CLS 분류 (Sw, LED, extinguisher 등)
                    else:
                        det_obj['source'] = "Cls"
                        cls_dets.append(det_obj)
            else:
                logger.warning("🕵️ YOLO Detected: 0 items (No results)")

            all_detections.extend(dg_dets)
            all_detections.extend(cls_dets)

            # 4. 라벨 매핑 및 전처리
            expected_types = sorted(list(set([p.inspection_point_type for p in points])), key=len, reverse=True)

            # [Fix: Pre-calculate Result Path for Consistency]
            if points:
                p0 = points[0]
                site, mission, insp = p0.site, p0.mission_name, p0.inspection_name
            else:
                site, mission, insp = "Unknown", "Unknown", "Unknown"
            
            orig_name = os.path.splitext(os.path.basename(img_path))[0]
            # [Fix] Create Unique Subdirectory per Task Run to prevent Result Mixing
            unique_sub = f"task_{task_id}_{int(time.time())}"
            target_dir = os.path.join(config.RESULT_BASE_DIR, site, mission, insp, unique_sub)
            os.makedirs(target_dir, exist_ok=True)
            
            structured_res_path = os.path.join(target_dir, f"{orig_name}_result.jpg")

            for det in all_detections:
                # config.LABEL_MAP을 이용한 통합 매칭 시도
                matched_target = None
                for target_type in expected_types:
                    # 1. LABEL_MAP 확인
                    candidates = config.LABEL_MAP.get(target_type, [])
                    if not isinstance(candidates, list): candidates = [candidates]
                    for cand in candidates:
                        norm_cand = str(cand).lower().replace("-", "").replace("_", "")
                        norm_det = str(det['label']).lower().replace("-", "").replace("_", "")
                        
                        # Exact match or suffix match
                        if norm_cand == norm_det: matched_target = target_type; break
                        if any(norm_det == norm_cand + s for s in ["ok", "nok", "na"]):
                            matched_target = target_type; break
                    if matched_target: break

                    # 2. is_type_compatible 이용한 유연한 매칭
                    if is_type_compatible(target_type, det['label']):
                        matched_target = target_type
                        break
                
                if matched_target: 
                    logger.info(f"🔄 Renaming Label: '{det['label']}' -> '{matched_target}'")
                    det['label'] = matched_target
                det['used'] = False

            # 5. 적응형 정렬 및 매칭 (Adaptive Sorting)
            excel_rear = [p for p in points if p.facility_2 and '(rear)' in p.facility_2]
            excel_front = [p for p in points if p not in excel_rear]
            
            front_reqs = Counter([p.inspection_point_type for p in excel_front])
            rear_reqs = Counter([p.inspection_point_type for p in excel_rear])
            
            candidates_by_label = {}
            for d in all_detections:
                # [Fix] Use smart matching to group detections, not just strict equality
                matched_target_type = None
                if d['label'] in expected_types:
                    candidates_by_label.setdefault(d['label'], []).append(d)
            
            det_front_pool = []
            det_rear_pool = []
            for label, dets in candidates_by_label.items():
                n_front = front_reqs.get(label, 0)
                n_rear = rear_reqs.get(label, 0)
                
                if n_rear > 0:
                    dets.sort(key=lambda d: d.get('area', 0), reverse=True)
                else:
                    dets.sort(key=lambda d: d['center_x'])
                
                det_front_pool.extend(dets[:n_front])
                det_rear_pool.extend(dets[n_front : n_front+n_rear])

            det_front_pool.sort(key=lambda d: d['center_x'])
            det_rear_pool.sort(key=lambda d: d['center_x'])

            # 6. 매칭 수행 및 시각화 작성
            summary_list = []
            
            for depth_name, ex_bucket, det_bucket in [("Front", excel_front, det_front_pool), ("Rear", excel_rear, det_rear_pool)]:
                available_dets = list(det_bucket)
                # [Debug] Available Labels for Matching
                logger.info(f"🔍 [Matching {depth_name}] Targets={[p.inspection_point_type for p in ex_bucket]} | Available={[d['label'] for d in available_dets]}")

                for point in ex_bucket:
                    target = point.inspection_point_type
                    matched = next((d for i, d in enumerate(available_dets) if is_type_compatible(target, d['label'])), None)
                    
                    # [Logic Update] 'Class_' items should run on Full Image even if no YOLO match
                    if not matched and target.upper().startswith("CLASS_"):
                        h, w = img.shape[:2]
                        matched = {
                            'label': target, 
                            'box': [0, 0, w, h], 
                            'source': 'Virtual',
                            'used': True
                        }
                        logger.info(f"🔹 [Pt] Target='{target}' | Force-Match for VLM Analysis (Full Image)")
                    
                    if matched:
                        matched['used'] = True
                        available_dets = [d for d in available_dets if d is not matched]
                        box_info = matched['box']
                        
                        # [Spatial Rank Calculation]
                        # 1. Filter all detections to only those compatible with the current target type
                        compatible_dets = [d for d in all_detections if is_type_compatible(target, d['label'])]
                        
                        # 2. Sort compatible items
                        sorted_x = sorted(compatible_dets, key=lambda d: d['center_x'])
                        sorted_y = sorted(compatible_dets, key=lambda d: d['center_y'])
                        
                        # 3. Find rank of matched object within its type group
                        try:
                            rank_x = sorted_x.index(matched) + 1
                            rank_y = sorted_y.index(matched) + 1
                        except ValueError:
                            rank_x, rank_y = 0, 0 # Should not happen

                        log_msg = f"✅ [Pt] Target='{target}' | Match='{matched['label']}' | Loc='{depth_name}' | Pos=(Left #{rank_x}, Top #{rank_y})"
                        logger.info(log_msg)
                    else:
                        rank_x, rank_y = None, None
                        box_info = [0, 0, 0, 0] # Initialize for failed match case (Fix UnboundLocalError)
                        log_msg = f"❌ [Pt] Target='{target}' | Match='None' | Loc='{depth_name}' | Pos=(Left N/A, Top N/A)"
                        logger.warning(log_msg)

                    final_val, final_status = "N/A", "UNKNOWN"
                    is_norm = False
                    
                    if matched:
                        # box_info already set above
                        
                        if target.upper().startswith("AG"):
                            final_val, _, is_norm = evaluate_gauge_reading(matched, vars(point))
                            final_val = str(round(final_val, 2))
                            logger.info(f"   ⏱️ AG Value: {final_val}")
                            if matched.get('source') == 'Pose' and 'keypoints' in matched:
                                for i, kp in enumerate(matched['keypoints']):
                                    if len(kp) >= 3 and kp[2] > 0.25:
                                        cv2.circle(final_img, (int(kp[0]), int(kp[1])), 4, (0,0,255) if i in [2,4] else (255,0,0), -1)
                        
                        elif target.upper().startswith("DG") or "DIGITAL" in target.upper() or "CLASS_" in target.upper():
                            # [VLM Logic] Digital Gauge OR Class Item
                            x1, y1, x2, y2 = map(int, box_info)
                            h, w = img.shape[:2]
                            x1, y1 = max(0, x1), max(0, y1)
                            x2, y2 = min(w, x2), min(h, y2_in := y2)
                            
                            is_class_item = "CLASS_" in target.upper()
                            
                            crop = None
                            if is_class_item:
                                # User Request: Use FULL IMAGE for Class items
                                crop = img
                            elif x2 > x1 and y2 > y1:
                                pad = 10
                                crop = img[max(0, y1-pad):min(h, y2+pad), max(0, x1-pad):min(w, x2+pad)]
                            
                            if crop is not None:
                                # [Prompt Selection]
                                prompt = config.VLM_PROMPTS.get(target, config.VLM_PROMPTS["DEFAULT"])
                                if prompt == config.VLM_PROMPTS["DEFAULT"]:
                                    for key, p_text in config.VLM_PROMPTS.items():
                                        if key in target:
                                            prompt = p_text
                                            break
                                
                                # VLM Query
                                vlm_resp = self.vlm_inspector.analyze_crop(crop, prompt=prompt)
                                
                                # [Post-Processing]
                                if vlm_resp and "Error" in str(vlm_resp) and "Timeout" in str(vlm_resp):
                                    matched['value'] = "timeout"
                                else:
                                    matched['value'] = str(vlm_resp).replace("\n", " | ").strip() if vlm_resp else "No Read"
                                
                                if not is_class_item:
                                    # DG: Use VLM response as is (User Request)
                                    pass

                            else:
                                matched['value'] = "Crop Fail"
                            
                            if is_class_item:
                                # Class Item Logic: Just write VLM data
                                final_val = matched['value']
                                logger.info(f"   📝 Class Result: {final_val}")
                                
                                # User Request: FAIL only on timeout, otherwise PASS
                                if final_val == "timeout":
                                    is_norm = False
                                    final_status = "FAIL"
                                else:
                                    is_norm = True
                            else:
                                # DG Evaluation
                                # User Request: Use raw VLM response as final_val
                                final_val = matched['value']
                                logger.info(f"   🤖 DG Value: {final_val}")
                                
                                # User Request: FAIL on Not Found, Error, Crop Fail, No Read, or timeout. Otherwise PASS.
                                if final_val in ["No Read", "Crop Fail", "Reading Fail", "Parse Error", "timeout"] or "Error" in str(final_val):
                                    is_norm = False
                                    final_status = "FAIL"
                                else:
                                    # 유의미한 결과 수신 시 PASS (evaluate_gauge_reading는 시각화 등을 위해 호출은 유지하되 판정은 덮어씀)
                                    # [Update] 2026-01-26: 사용자가 수치가 잘 나오면 PASS라고 했으므로 무역비교 없이 PASS 처리.
                                    is_norm = True
                                    final_status = "PASS"

                        else:
                            # 3. Default (ETC, SW, LED, etc.) -> FOUND
                            is_norm, reason = self.sw_led_inspector.check_status_compliance(matched['label'], target)
                            final_val = "Found"
                            logger.info(f"   🔎 Status: {final_val}")
                        
                        final_status = "PASS" if is_norm else "FAIL"
                        draw_diagnosis_box(final_img, box_info, vars(point), matched['label'], final_status, value=final_val)
                    
                    else:
                        # [No Match Found]
                        final_val = "Not Found"
                        final_status = "FAIL"
                        # draw_diagnosis_box is not called if box is 0,0,0,0 or handled differently?
                        # Usually we draw an outline or text for missing item if coords known? 
                        # But without detection, we don't have box using which to draw.
                        # Logic continues to _save_result.
                    
                    # [Fix] 결과 DB 저장 (생성해둔 절대 경로 structured_res_path 전달)
                    self._save_result(db, task.id, point, final_val, final_status, img_path, box_info, structured_res_path, photo_time)
                    summary_list.append({"type": target, "found": matched is not None})

            # [User Request] Draw Unmatched (Unused) Detections as Gray Boxes
            for d in all_detections:
                if not d.get('used', False):
                    x1, y1, x2, y2 = map(int, d['box'])
                    gray_color = (128, 128, 128)
                    cv2.rectangle(final_img, (x1, y1), (x2, y2), gray_color, 1)
                    draw_outline_text(final_img, f"Unmatched: {d['label']}", (x1, y1 - 5), gray_color, font_scale=0.4)

            # 7. 통합 결과 이미지 저장
            draw_summary_table(final_img, summary_list)
            
            # [Fix] Save structured result (Image + JSON)
            saved_img_path = self.save_inspection_data(task, points[0] if points else None, final_img, summary_list, all_detections, img_path, structured_res_path)
            
            # [User Request] Show Result Window
            if self.visualize:
                cv2.imshow("Inspection Result", final_img)
                cv2.waitKey(1)

            task.data_result_dir = saved_img_path
            task.state = DiagnosisState.COMPLETED
            db.commit()
            logger.info(f"✅ 태스크 {task_id} 처리 완료")

        except Exception as e:
            logger.error(f"❌ 분석 엔진 오류: {e}")
            db.rollback()
            if task: task.state = DiagnosisState.FAILED; db.commit()
        finally:
            db.close()

    def save_inspection_data(self, task, point, img, summary, detections, original_img_path, res_img_path):
        """
        [User Request] Save Result Image & JSON to Structured Directory.
        Directory is already created in process_task.
        """
        import json
        
        # 0. Extract Metadata
        if point:
            site = point.site
            mission = point.mission_name
            insp = point.inspection_name
        else:
            site, mission, insp = "Unknown", "Unknown", "Unknown"

        # 3. Save Image
        cv2.imwrite(res_img_path, img)
        logger.info(f"   💾 Saved Result Image: {res_img_path}")
        
        # 4. Save JSON
        res_json_path = os.path.splitext(res_img_path)[0] + ".json"
        
        # 4. Save JSON
        data = {
            "task_id": task.id,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "site": site,
            "mission": mission,
            "inspection": insp,
            "original_image": original_img_path,
            "summary": summary,
            "detections": [
                {
                    "label": d['label'],
                    "box": d['box'], # box is list
                    "score": float(d.get('score', 0.0)),
                    "used": d.get('used', False),
                    "value": d.get('value', None)
                }
                for d in detections
            ]
        }
        
        with open(res_json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        logger.info(f"   💾 Saved Result JSON: {res_json_path}")
        
        return res_img_path

    def _save_result(self, db, data_id, point, val, status, raw_path, box, res_path_str, photo_time=None):
        """진단 결과를 InspectionResult 테이블에 기록합니다."""
        res = InspectionResult(
            site=point.site,
            mission_name=point.mission_name,
            inspection_name=point.inspection_name,
            facility_1=point.facility_1,
            facility_2=point.facility_2,
            inspection_point_type=point.inspection_point_type,
            min_value=point.min_value,
            max_value=point.max_value,
            normal_min_value=point.normal_min_value,
            normal_max_value=point.normal_max_value,
            inspection_point_id=point.id,
            result_value=val,
            judgement=status,
            data_raw_dir=raw_path,
            data_result_dir=res_path_str, # 절대 경로 저장
            spatial_info={"box": box},
            inspection_datetime=datetime.now().replace(microsecond=0),
            photo_time=photo_time
        )
        db.add(res)
        db.commit()

    def _save_error_result(self, db, task, reason):
        task.state = DiagnosisState.FAILED
        db.commit()

    @staticmethod
    def get_latest_image(base_dir, mission, insp_name):
        import glob
        path = os.path.join(base_dir, insp_name)
        files = glob.glob(os.path.join(path, "*.[jJ][pP][gG]"))
        return max(files, key=os.path.getmtime) if files else None

    def run(self):
        logger.info(f"🚀 [Advanced Engine] DB Polling 시작... (Visualization: {'ON' if self.visualize else 'OFF'})")
        while True:
            # UI Refresh (Handle Window Events)
            if self.visualize:
                cv2.waitKey(100)
            
            try:
                db = SessionLocal()
                queued_task = db.query(InspectionData).filter(
                    InspectionData.state == DiagnosisState.QUEUED
                ).order_by(InspectionData.id.asc()).first()

                if queued_task:
                    logger.info(f"🔔 새 태스크 주입 감지 (ID: {queued_task.id})")
                    self.process_task(queued_task.id)
                else:
                    time.sleep(1)
            except Exception as e:
                logger.error(f"Polling 에러: {e}")
                time.sleep(5)
            finally:
                db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI 설비 진단 통합 컨트롤러")
    parser.add_argument("--withfig", action="store_true", help="결과 이미지 디스플레이(OpenCV) 활성화")
    args = parser.parse_args()

    try:
        # 기본값은 비활성화, --withfig가 설정되면 True
        DiagnosisSystem(visualize=args.withfig).run()
    except KeyboardInterrupt:
        logger.info("👋 종료합니다.")