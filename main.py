import os
import cv2
import pandas as pd
import numpy as np
from collections import defaultdict
from ultralytics import YOLO
from loguru import logger

# Inspector들 임포트
from inspectors.ag_inspector import AGInspector
from inspectors.dg_inspector import DGInspector

class DiagnosisSystem:
    def __init__(self, base_path, excel_name, classifier_model_path="models/classifier/weights/best.pt"):
        self.base_path = base_path
        self.excel_full_path = excel_name
        self.df = pd.DataFrame()
        
        # [NEW] 상태 매핑용 키워드 (Compliance Check에서 사용)
        self.status_mapping = {
            "on": "on", "off": "off", "open": "open", "close": "close", 
            "run": "run", "stop": "stop", "trip": "trip", "fault": "fault"
        }
        
        # 초기화 메서드 호출
        self._init_system(classifier_model_path)

    def _init_system(self, classifier_path):
        self.ag_inspector = None
        self.dg_inspector = None
        try:
            # 1. 엑셀 로드
            if os.path.exists(self.excel_full_path):
                self.df = pd.read_excel(self.excel_full_path, sheet_name='inspection_point')
                logger.info(f"엑셀 로드 완료: {len(self.df)} rows")
            
            # 2. 메인 디텍터(Classifier) 모델 로드 [핵심]
            logger.info(f"Detector 모델 로드 중: {classifier_path}")
            self.detector = YOLO(classifier_path) 
            
            # 3. 개별 인스펙터 로드
            self.ag_inspector = AGInspector()
            self.dg_inspector = DGInspector() 
            
        except Exception as e:
            logger.error(f"초기화 오류: {e}")

    # =========================================================================
    # [NEW] Compliance Check 로직 (대소문자 무시, 매칭 상세 정보 반환)
    # =========================================================================
    def check_compliance(self, excel_target_str, model_labels, mission_name):
        if pd.isna(excel_target_str) or not isinstance(excel_target_str, str) or excel_target_str.strip() == "":
            return False, "Invalid Target", []

        # 1. 엑셀 타겟 정규화
        raw_targets = [t.strip() for t in excel_target_str.split(',')]
        
        # 2. 미션별 예외 처리 (SW_LED_inspection인 경우 AG, DG, ETC 제외)
        active_targets = []
        if mission_name == "SW_LED_inspection":
            for t in raw_targets:
                t_lower = t.lower()
                if not (t_lower.startswith("ag") or t_lower.startswith("dg") or t_lower.startswith("etc")):
                    active_targets.append(t)
        else:
            active_targets = raw_targets

        if not active_targets:
            return True, "Pass (No Target)", []

        # 3. 모델 검출 라벨 정규화
        detected_labels_norm = [self._normalize(l) for l in model_labels]
        if not detected_labels_norm: 
            return False, "No object detected", []

        matched_count = 0
        fail_details = []
        match_details = [] 

        # 4. 매칭 로직
        for target in active_targets:
            if not target: continue
            target_norm = self._normalize(target)
            
            is_target_matched = False
            best_match_label = "None"

            target_keyword = None
            for key, val in self.status_mapping.items():
                if key in target_norm:
                    target_keyword = val
                    break
            
            for label in detected_labels_norm:
                if "valve" in label:
                    if target_keyword and target_keyword in label:
                        is_target_matched = True; best_match_label = label; break
                else:
                    if target_norm in label:
                        if "nok" in label: pass 
                        else: is_target_matched = True; best_match_label = label; break
            
            if is_target_matched:
                matched_count += 1
                match_details.append({"target": target, "found": best_match_label, "status": "OK"})
            else:
                fail_details.append(f"Missing: {target}")
                match_details.append({"target": target, "found": "Mismatch/None", "status": "Fail"})

        if matched_count == len(active_targets):
            return True, "Pass", match_details
        
        return False, f"{', '.join(fail_details)}" if fail_details else "Mismatch", match_details

    def _normalize(self, text):
        return str(text).lower().strip().replace(" ", "_")

    # =========================================================================
    # [NEW] Compliance Group 처리 (LED, Switch 등 일반 검사 시각화)
    # =========================================================================
    def _process_compliance_group(self, img_path, group_df, results_map):
        logger.info(f"📸 Compliance 분석 수행 중... [{os.path.basename(img_path)}]")
        
        img = cv2.imread(img_path)
        if img is None: return

        # 1. 디텍팅
        results = self.detector.predict(img, conf=0.1, verbose=False)
        detected_objs = [] 
        detected_labels_list = [] 

        if results:
            for box in results[0].boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                cls_id = int(box.cls[0])
                label = results[0].names[cls_id]
                conf = float(box.conf[0])
                
                detected_labels_list.append(label)
                detected_objs.append({
                    "label": label, "bbox": (x1, y1, x2, y2), "conf": conf
                })

        # 2. 엑셀 행별로 Compliance Check 진행 & 시각화 준비
        final_img = img.copy()
        
        # 2-1. 화면 상단 타이틀 (요청사항: [Mission] Filename)
        mission_name = group_df.iloc[0]['mission_name']
        file_name = os.path.basename(img_path)
        title_text = f"[{mission_name}] {file_name}"
        cv2.putText(final_img, title_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        y_offset_info = 60

        # 한 이미지에 여러 Inspection Point가 있을 수 있으므로 Loop
        for idx, row in group_df.iterrows():
            target_str = row['inspection_point_type']
            facility_info = f"{row.get('facility_1', '')} / {row.get('facility_2', '')}"
            
            # Compliance Check 수행
            is_pass, msg, match_details = self.check_compliance(
                target_str, detected_labels_list, mission_name
            )
            
            results_map[idx] = msg # 결과 저장

            # 3. 박스 그리기 (매칭 정보를 바탕으로)
            for obj in detected_objs:
                label = obj['label']
                x1, y1, x2, y2 = obj['bbox']
                
                # 기본값 (매칭 안됨/Unknown)
                display_text = f"Det: {label}"
                box_color = (0, 255, 255) # 노란색

                # 이 객체가 match_details의 'found'와 일치하는지 확인
                for m in match_details:
                    if self._normalize(m['found']) == self._normalize(label):
                        # 요청사항: Exp: [엑셀타겟] / Fnd: [검출라벨]
                        display_text = f"Exp: {m['target']} / Fnd: {label}"
                        if m['status'] == "OK":
                            box_color = (0, 255, 0) # 초록
                        else:
                            box_color = (0, 0, 255) # 빨강
                        break
                
                if "nok" in label.lower():
                    box_color = (0, 0, 255)
                    display_text += " (NOK)"

                cv2.rectangle(final_img, (x1, y1), (x2, y2), box_color, 2)
                # 텍스트 위치 조정 (박스 위쪽)
                text_y = y1 - 10 if y1 - 10 > 10 else y1 + 20
                cv2.putText(final_img, display_text, (x1, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 2)

            # 4. 좌측 상단 텍스트 추가
            info_text = f"Loc: {facility_info} | Result: {msg}"
            cv2.putText(final_img, info_text, (10, y_offset_info), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)
            y_offset_info += 30

        # 5. 창 띄우기 (화면 절반 크기)
        window_name = f"Compliance: {file_name}"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        screen_width = 1920 
        cv2.resizeWindow(window_name, int(screen_width / 2), 600)
        cv2.imshow(window_name, final_img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    # =========================================================================
    # [Process] DG 그룹 처리 (사용자 코드 원본 유지)
    # =========================================================================
    def _process_dg_group(self, img_path, group_df, results_map):
        logger.info(f"📸 DG 분석 수행 중... [{os.path.basename(img_path)}]")
        
        img = cv2.imread(img_path)
        if img is None: return

        # 1. 메인 디텍터 실행
        results = self.detector.predict(img, conf=0.1, verbose=False)
        
        # [디버깅용 시각화 유지]
        debug_img = img.copy()
        if results:
            for box in results[0].boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                cls_id = int(box.cls[0])
                label = results[0].names[cls_id]
                conf = float(box.conf[0])
                
                cv2.rectangle(debug_img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                label_text = f"{label} ({conf:.2f})"
                (w, h), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                cv2.rectangle(debug_img, (x1, y1 - 20), (x1 + w, y1), (0, 255, 0), -1)
                cv2.putText(debug_img, label_text, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

        cv2.imshow(f"Raw Classifier: {os.path.basename(img_path)}", debug_img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

        detected_objects = []
        if results:
            for box in results[0].boxes:
                cls_id = int(box.cls[0])
                label = results[0].names[cls_id]
                if not label.startswith("DG_"): continue

                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                conf = float(box.conf[0])
                logger.info(f"   👉 Found DG: '{label}' (conf: {conf:.2f})")
                detected_objects.append({
                    'label': label, 'box': [x1, y1, x2, y2],
                    'center_x': (x1+x2)/2, 'center_y': (y1+y2)/2,
                    'area': (x2-x1)*(y2-y1)
                })
        
        if not detected_objects:
            logger.warning("⚠️ DG 타겟(DG_*)을 찾지 못했습니다!")

        yolo_buckets = defaultdict(list)
        for det in detected_objects:
            gid = self.get_type_group_id(det['label'])
            yolo_buckets[gid].append(det)

        excel_buckets = defaultdict(list)
        for idx, row in group_df.iterrows():
            gid = self.get_type_group_id(row['inspection_point_type'])
            excel_buckets[gid].append((idx, row))

        processed_detections = []
        for gid in excel_buckets.keys():
            excel_items = excel_buckets[gid]
            yolo_items = yolo_buckets.get(gid, [])
            sorted_yolo = self.sort_by_grid_position(yolo_items)
            
            total_yolo = len(sorted_yolo)
            get_pos = lambda i: ["le", "mi", "ri"][i] if total_yolo==3 and i<3 else (
                                ["le", "ri"][i] if total_yolo==2 and i<2 else "mi" if total_yolo==1 else f"p{i+1}")

            for i, (idx, row) in enumerate(excel_items):
                fac_2 = str(row.get('facility_2', ''))
                if i < len(sorted_yolo):
                    det = sorted_yolo[i]
                    x1, y1, x2, y2 = det['box']
                    h, w, _ = img.shape
                    cx1, cy1 = max(0, x1-5), max(0, y1-5)
                    cx2, cy2 = min(w, x2+5), min(h, y2+5)
                    crop_img = img[cy1:cy2, cx1:cx2].copy()
                    
                    val, ocr_text, ocr_details, rotated_img = self.dg_inspector.analyze_crop(crop_img)
                    det['read_value'] = val
                    det['ocr_text'] = ocr_text
                    det['ocr_details'] = ocr_details
                    det['rotated_img'] = rotated_img
                    
                    _, status, is_normal = self.evaluate_digital_reading(det, row)
                    det['final_value'] = val
                    det['status'] = status
                    det['facility_info'] = fac_2
                    det['pos_info'] = get_pos(i)
                    processed_detections.append(det)
                    results_map[idx] = f"[{fac_2}] {val} ({status})"
                else:
                    results_map[idx] = "미검출"

        self.dg_inspector.show_combined_result(
            img_path, processed_detections, highlight_count=len(group_df), 
            title=f"DG Result: {os.path.basename(img_path)}"
        )

    # =========================================================================
    # [Helper Methods] 사용자 코드 원본 유지
    # =========================================================================
    @staticmethod
    def get_latest_image(base_dir, mission, insp_name):
        import glob
        folder_name = f"{mission}.walk/{mission}.walk_{insp_name}"
        target_dir = os.path.join(base_dir, "Inspection_Raw_DATA_Dockerd/robot-control-system_inspection_data(docker X)", folder_name)
        if not os.path.exists(target_dir): return None
        files = glob.glob(os.path.join(target_dir, "*.[jJ][pP][gG]")) + \
                glob.glob(os.path.join(target_dir, "*.[pP][nN][gG]"))
        if not files: return None
        return max(files, key=os.path.getmtime)

    @staticmethod
    def get_type_group_id(label_str):
        s = str(label_str).lower()
        if "dg" in s or "digital" in s or "meter" in s: return "SHARED_DIGITAL"
        if "pressure" in s: return "SHARED_PRESSURE"
        if "temperature" in s: return "SHARED_TEMPERATURE"
        if "thermo-hygro" in s: return "SHARED_THERMO_HYGRO"
        if "ammeter" in s: return "SHARED_AMMETER"
        return s

    @staticmethod
    def sort_by_grid_position(detections):
        if not detections: return []
        detections.sort(key=lambda x: x['center_y'])
        rows = []
        current_row = []
        if detections:
            current_row.append(detections[0])
            h = detections[0]['box'][3] - detections[0]['box'][1]
            threshold = h * 0.5

        for i in range(1, len(detections)):
            det = detections[i]
            prev = current_row[-1]
            if abs(det['center_y'] - prev['center_y']) < threshold:
                current_row.append(det)
            else:
                rows.append(current_row)
                current_row = [det]
                h = det['box'][3] - det['box'][1]
                threshold = h * 0.5
        if current_row: rows.append(current_row)
        final_sorted = []
        for row in rows:
            row.sort(key=lambda x: x['center_x'])
            final_sorted.extend(row)
        return final_sorted

    @staticmethod
    def evaluate_gauge_reading(det, excel_row):
        try:
            min_val = float(excel_row.get('min_value', 0))
            max_val = float(excel_row.get('max_value', 100))
            norm_min = float(excel_row.get('normal_min', 0))
            norm_max = float(excel_row.get('normal_max', 100))
        except: return None, "Config Error", False
        if not det.get('is_valid', True):
            return 0.0, f"Shape Error ({det.get('status_msg')})", False
        ratio = det.get('value_ratio', 0.0)
        current_val = min_val + (ratio * (max_val - min_val))
        current_val = round(current_val, 2)
        is_normal = norm_min <= current_val <= norm_max
        status = "Normal" if is_normal else "Abnormal"
        return current_val, status, is_normal
    
    @staticmethod
    def evaluate_digital_reading(det, excel_row):
        try:
            norm_min = float(excel_row.get('normal_min', 0))
            norm_max = float(excel_row.get('normal_max', 100))
        except: return None, "Config Error", False
        current_val = det.get('read_value')
        if current_val is None: return "Read Fail", "OCR Error", False
        is_normal = norm_min <= current_val <= norm_max
        status = "Normal" if is_normal else "Abnormal"
        return current_val, status, is_normal

    def _process_ag_group(self, img_path, group_df, results_map):
        """AG 타입 그룹 처리 (사용자 코드 원본 유지)"""
        logger.info(f"📸 분석 수행 중... [{os.path.basename(img_path)}]")
        all_detections = self.ag_inspector.inspect_all(img_path)
        yolo_buckets = defaultdict(list)
        for det in all_detections:
            gid = self.get_type_group_id(det['label'])
            yolo_buckets[gid].append(det)

        excel_buckets = defaultdict(list)
        for idx, row in group_df.iterrows():
            gid = self.get_type_group_id(row['inspection_point_type'])
            excel_buckets[gid].append((idx, row))

        processed_detections = []
        for gid in excel_buckets.keys():
            excel_items = excel_buckets[gid]
            yolo_items = yolo_buckets[gid]
            sorted_yolo = self.sort_by_grid_position(yolo_items)
            total_yolo = len(sorted_yolo)
            get_pos = lambda i: ["le", "mi", "ri"][i] if total_yolo==3 and i<3 else (
                                ["le", "ri"][i] if total_yolo==2 and i<2 else "mi" if total_yolo==1 else f"p{i+1}")

            for i, (idx, row) in enumerate(excel_items):
                fac_2 = str(row.get('facility_2', ''))
                if i < len(sorted_yolo):
                    det = sorted_yolo[i]
                    val, status, is_normal = self.evaluate_gauge_reading(det, row)
                    det['final_value'] = val
                    det['status'] = status
                    det['facility_info'] = fac_2
                    det['pos_info'] = get_pos(i)
                    processed_detections.append(det)
                    results_map[idx] = f"[{fac_2}] {val} ({status})"
                else:
                    results_map[idx] = "미검출"

        for gid, dets in yolo_buckets.items():
            for d in dets:
                if d not in processed_detections:
                    d['final_value'] = "N/A"
                    d['status'] = "Extra"
                    d['facility_info'] = "Unknown"
                    d['pos_info'] = "?"
                    processed_detections.append(d)

        self.ag_inspector.show_combined_result(
            img_path, processed_detections, highlight_count=len(group_df), 
            title=f"Result: {os.path.basename(img_path)}"
        )

    # =========================================================================
    # [Main Logic] 실행부 (수정됨)
    # =========================================================================
    def run(self):
        """전체 진단 프로세스 실행"""
        self.df['unique_key'] = self.df['mission_name'].astype(str) + "_" + self.df['inspection_name'].astype(str)
        grouped = self.df.groupby('unique_key')
        
        logger.info(f"총 {len(grouped)}개의 포인트 그룹 진단 시작")
        diagnosis_results = {}

        for key, group in grouped:
            first = group.iloc[0]
            mission = first['mission_name']
            insp_name = first['inspection_name']
            
            img_path = self.get_latest_image(self.base_path, mission, insp_name)
            if not img_path:
                logger.warning(f"이미지 없음: {mission}/{insp_name}")
                continue

            # 타입 확인
            insp_types = [str(t) for t in group['inspection_point_type']]
            
            # 1. AG 로직 (기존 유지)
            if any(t.startswith('AG') for t in insp_types):
                self._process_ag_group(img_path, group, diagnosis_results)

            # 2. DG 로직 (기존 유지)
            elif any(t.startswith('DG') for t in insp_types):
                self._process_dg_group(img_path, group, diagnosis_results)
            
            # 3. [NEW] 그 외 (LED, Switch 등) -> 개선된 시각화 로직 사용
            else:
                self._process_compliance_group(img_path, group, diagnosis_results)

        self.df['diagnosis_result'] = self.df.index.map(diagnosis_results)
        return self.df

if __name__ == "__main__":
    BASE_DIR = "/home/kiie/synology/Projects/R25IA04/Inspection_and_Diagnosis"
    EXCEL_FILE = "/home/kiie/synology/Projects/R25IA04/Inspection_point, Labeling_251215.xlsx"
    
    print("🚀 진단 시스템 시작...")
    system = DiagnosisSystem(BASE_DIR, EXCEL_FILE)
    
    if not system.df.empty:
        result_df = system.run()
        print("\n📊 진단 결과 미리보기:")
        if 'diagnosis_result' in result_df.columns:
            print(result_df[['mission_name', 'inspection_name', 'diagnosis_result']].head(10).to_string())
    else:
        print("❌ 엑셀 데이터를 로드하지 못했습니다. 경로를 확인해주세요.")