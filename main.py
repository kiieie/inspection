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
    def __init__(self):
        self.base_path = config.BASE_DIR
        self.excel_path = config.EXCEL_FILE
        
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

            insp_name = task.data_result_dir
            mission_name = task.mission_name

            task.state = DiagnosisState.RUNNING
            db.commit()

            points = db.query(InspectionPoint).filter(
                InspectionPoint.mission_name == mission_name,
                InspectionPoint.inspection_name == insp_name
            ).all()

            if not points:
                logger.warning(f"⚠️ 마스터 정보 없음: {mission_name} / {insp_name}")
                task.state = DiagnosisState.FAILED
                db.commit()
                return

            # 2. 이미지 로드
            img_path = self.get_latest_image(self.base_path, mission_name, insp_name)
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
            results = self.detector.predict(img_path, conf=0.1, verbose=False)
            
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
            expected_types = list(set([p.inspection_point_type for p in points]))
            for det in all_detections:
                # 오타 수정 (전처리기)
                if "extingisher" in det['label']: det['label'] = det['label'].replace("extingisher", "extinguisher")
                
                if det['label'] in expected_types:
                    # 정확히 일치하면 skip
                    continue

                # config.LABEL_MAP을 이용한 통합 매칭 시도
                matched_target = None
                for target_type in expected_types:
                    # 1. LABEL_MAP 확인
                    candidates = config.LABEL_MAP.get(target_type, [])
                    if not isinstance(candidates, list): candidates = [candidates]
                    for cand in candidates:
                        if cand == det['label'] or (cand in det['label']):
                            matched_target = target_type; break
                    if matched_target: break

                    # 2. is_type_compatible 이용한 유연한 매칭
                    if is_type_compatible(target_type, det['label']):
                        matched_target = target_type
                        break
                
                if matched_target: det['label'] = matched_target
                det['used'] = False

            # 5. 적응형 정렬 및 매칭 (Adaptive Sorting)
            excel_rear = [p for p in points if p.facility_2 and '(rear)' in p.facility_2]
            excel_front = [p for p in points if p not in excel_rear]
            
            front_reqs = Counter([p.inspection_point_type for p in excel_front])
            rear_reqs = Counter([p.inspection_point_type for p in excel_rear])
            
            candidates_by_label = {}
            for d in all_detections:
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
                for point in ex_bucket:
                    target = point.inspection_point_type
                    matched = next((d for i, d in enumerate(available_dets) if is_type_compatible(target, d['label'])), None)
                    
                    # [Debug] 매칭 상세 로그
                    if matched:
                        logger.info(f"🎯 Match Found: Target='{target}' <--> Label='{matched['label']}'")
                    else:
                        logger.debug(f"⚠️ Match Failed: Target='{target}' vs Available={[d['label'] for d in available_dets]}")

                    final_val, final_status = "N/A", "UNKNOWN"
                    is_norm = False
                    box_info = [0, 0, 0, 0]
                    
                    if matched:
                        matched['used'] = True
                        available_dets = [d for d in available_dets if d is not matched]
                        box_info = matched['box']
                        
                        if target.upper().startswith("AG"):
                            final_val, _, is_norm = evaluate_gauge_reading(matched, vars(point))
                            final_val = str(round(final_val, 2))
                            if matched.get('source') == 'Pose' and 'keypoints' in matched:
                                for i, kp in enumerate(matched['keypoints']):
                                    if len(kp) >= 3 and kp[2] > 0.25:
                                        cv2.circle(final_img, (int(kp[0]), int(kp[1])), 4, (0,0,255) if i in [2,4] else (255,0,0), -1)
                        
                        elif target.upper().startswith("DG"):
                            # [VLM Logic] VLM을 이용해 디지털 숫자 직접 판독
                            x1, y1, x2, y2 = map(int, box_info)
                            h, w = img.shape[:2]
                            x1, y1 = max(0, x1), max(0, y1)
                            x2, y2 = min(w, x2), min(h, y2_in := y2)
                            
                            if x2 > x1 and y2 > y1:
                                # [Fix] 테스트 코드와 동일하게 Padding 추가 (인식률 향상)
                                pad = 10
                                crop = img[max(0, y1-pad):min(h, y2+pad), max(0, x1-pad):min(w, x2+pad)]
                                
                                # VLM 질의 수행
                                vlm_resp = self.vlm_inspector.analyze_crop(crop)
                                
                                # [Logic] 응답에서 실제 숫자만 추출 (테스트 코드 로직 이식)
                                import re
                                try:
                                    if vlm_resp and str(vlm_resp).strip():
                                        # 실수 또는 정수 패턴 찾기
                                        numbers = re.findall(r"[-+]?\d*\.\d+|\d+", str(vlm_resp))
                                        if numbers:
                                            matched['value'] = numbers[0] # 첫 번째 발견된 숫자 사용
                                        else:
                                            matched['value'] = vlm_resp # 숫자가 없으면 원본 텍스트 유지
                                    else:
                                        matched['value'] = "No Read"
                                except:
                                    matched['value'] = "Parse Error"
                            else:
                                matched['value'] = "Crop Fail"
                            
                            # 값 평가
                            val_raw, _, is_norm = evaluate_gauge_reading({'value': matched.get('value'), 'label': matched['label']}, vars(point))
                            
                            final_val = str(val_raw) if val_raw is not None else "Reading Fail"
                            
                            # 값이 "No Read"나 기타 에러면 FAIL 처리
                            if final_val in ["No Read", "Crop Fail", "Reading Fail", "Parse Error"]:
                                is_norm = False
                                final_status = "FAIL"

                        else:
                            is_norm, reason = self.sw_led_inspector.check_status_compliance(matched['label'], target)
                            final_val = matched['label']

                        final_status = "PASS" if is_norm else "FAIL"
                        draw_diagnosis_box(final_img, box_info, vars(point), matched['label'], final_status, value=final_val)
                    
                    # [Fix] 결과 DB 저장 (생성해둔 절대 경로 res_abs_path 전달)
                    self._save_result(db, task.id, point, final_val, final_status, img_path, box_info, res_abs_path)
                    summary_list.append({"type": target, "found": matched is not None})

            # 7. 통합 결과 이미지 저장
            draw_summary_table(final_img, summary_list)
            # 이미 경로는 생성했으므로 저장만 수행
            cv2.imwrite(str(res_path), final_img)

            task.data_result_dir = res_abs_path
            task.state = DiagnosisState.COMPLETED
            db.commit()
            logger.info(f"✅ 태스크 {task_id} 처리 완료 (총 {len(points)}개 지점)")

        except Exception as e:
            logger.error(f"❌ 분석 엔진 오류: {e}")
            db.rollback()
            if task: task.state = DiagnosisState.FAILED; db.commit()
        finally:
            db.close()

    def _save_result(self, db, data_id, point, val, status, raw_path, box, res_path_str):
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
            inspection_datetime=datetime.now()
        )
        db.add(res)
        db.commit()

    def _save_error_result(self, db, task, reason):
        task.state = DiagnosisState.FAILED
        db.commit()

    @staticmethod
    def get_latest_image(base_dir, mission, insp_name):
        import glob
        path = os.path.join(base_dir, f"{mission}.walk", f"{mission}.walk_{insp_name}")
        files = glob.glob(os.path.join(path, "*.[jJ][pP][gG]"))
        return max(files, key=os.path.getmtime) if files else None

    def run(self):
        logger.info("🚀 [Advanced Engine] DB Polling 시작...")
        while True:
            db = SessionLocal()
            try:
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
    try:
        DiagnosisSystem().run()
    except KeyboardInterrupt:
        logger.info("👋 종료합니다.")