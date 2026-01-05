import logging
import cv2
import numpy as np
import pandas as pd
from .base import BaseInspector

class SW_LED_Inspector(BaseInspector):
    def __init__(self, model):
        super().__init__()
        self.model = model
        self.status_mapping = {
            "opend": "opened", "opened": "opened", "closed": "closed",
            "on": "on", "off": "off", "right": "right", "left": "left", "center": "center"
        }

    def _normalize(self, text):
        if not isinstance(text, str): return ""
        return text.lower().strip()

    def check_compliance(self, excel_target_str, model_labels, mission_name):
        """
        Compliance 체크 함수 (대소문자 무시, 특정 미션 예외 처리, 매칭 상세 정보 반환)
        """
        if pd.isna(excel_target_str) or not isinstance(excel_target_str, str) or excel_target_str.strip() == "":
            return False, "Invalid Target", []

        # 1. 엑셀 타겟 정규화 (소문자 변환 및 공백 제거)
        # 쉼표로 구분된 타겟들을 리스트로 변환
        raw_targets = [t.strip() for t in excel_target_str.split(',')]
        
        # 2. 미션별 예외 처리 (SW_LED_inspection인 경우 AG, DG, ETC 제외)
        active_targets = []
        if mission_name == "SW_LED_inspection":
            for t in raw_targets:
                # 대소문자 무시하고 접두어 체크
                t_lower = t.lower()
                if not (t_lower.startswith("ag") or t_lower.startswith("dg") or t_lower.startswith("etc")):
                    active_targets.append(t)
        else:
            active_targets = raw_targets

        # 필터링 후 타겟이 없으면 Pass로 처리할지, 검사 대상 없음으로 할지 결정 (여기선 Pass로 가정)
        if not active_targets:
            return True, "No Target (Filtered)", []

        # 3. 모델 검출 라벨 정규화 (소문자 변환)
        # model_labels는 [{'label': 'name', 'bbox': ...}, ...] 형태라고 가정하거나 문자열 리스트라면 아래와 같이 처리
        # (여기서는 문자열 리스트로 들어온다고 가정하고 처리합니다. 만약 객체라면 객체 내부의 label을 꺼내야 함)
        detected_labels_norm = [self._normalize(l) for l in model_labels]
        
        if not detected_labels_norm: 
            return False, "No object detected", []

        matched_count = 0
        fail_details = []
        match_details = [] # 시각화를 위해 (Target, Detected_Label) 쌍을 저장

        # 4. 매칭 로직 (대소문자 무시 비교)
        for target in active_targets:
            if not target: continue
            target_norm = self._normalize(target) # 소문자화 된 타겟
            
            is_target_matched = False
            best_match_label = "None"

            # 매핑 로직 (기존 로직 유지하되 대소문자 완화)
            target_keyword = None
            for key, val in self.status_mapping.items():
                if key in target_norm:
                    target_keyword = val
                    break
            
            for label in detected_labels_norm:
                # valve 관련 로직
                if "valve" in label:
                    if target_keyword and target_keyword in label:
                        is_target_matched = True
                        best_match_label = label
                        break
                    elif "valve" in target_norm:
                        # 밸브는 찾았으나 상태가 다름
                        pass 
                else:
                    # 일반 매칭 (target 이름이 label에 포함되는지)
                    if target_norm in label:
                        if "nok" in label: 
                            pass # NOK 검출됨
                        else: 
                            is_target_matched = True
                            best_match_label = label
                            break
            
            if is_target_matched:
                matched_count += 1
                match_details.append({"target": target, "found": best_match_label, "status": "OK"})
            else:
                fail_details.append(f"Missing: {target}")
                match_details.append({"target": target, "found": "Not Found/Mismatch", "status": "Fail"})

        # 모든 Active Target이 매칭되었는지 확인
        if matched_count == len(active_targets):
            return True, "Pass", match_details
        
        return False, f"{', '.join(fail_details)}" if fail_details else "Mismatch", match_details

    def _normalize(self, text):
        # 대소문자 무시 및 공백 제거 헬퍼
        return str(text).lower().strip().replace(" ", "_")

    def inspect(self, image_path, spec):
        try:
            results = self.model(image_path, verbose=False)
            if not results or len(results[0].boxes) == 0:
                 return {"status": "Fail", "reason": "No object", "detected_labels": []}

            detected_labels = []
            for r in results:
                for c in r.boxes.cls:
                    detected_labels.append(r.names[int(c)])

            target_type = spec.get('inspection_point_type', '')
            if pd.isna(target_type): target_type = ""
            
            is_pass, message = self.check_compliance(str(target_type), detected_labels)

            return {
                "status": "Pass" if is_pass else "Fail",
                "reason": message,
                "detected_labels": detected_labels,
                "target_spec": target_type
            }
        except Exception as e:
            return {"status": "Error", "reason": str(e)}

    # ▼▼▼ [텍스트 투명 배경 + 아웃라인 적용된 시각화 함수] ▼▼▼
    def show_result(self, image_path, annotated_data, title="Result"):
        img = cv2.imread(image_path)
        if img is None:
            print(f"❌ Error: Image not found: {image_path}")
            return

        # 이전 창 닫기
        cv2.destroyAllWindows()

        font = cv2.FONT_HERSHEY_SIMPLEX
        # 폰트 설정
        font_scale_top = 0.5
        font_scale_bot1 = 0.6
        font_scale_bot2 = 0.5
        thickness = 2
        outline_thickness = thickness + 3 # 아웃라인은 더 두껍게

        # 박스 및 텍스트 그리기
        if annotated_data:
            for item in annotated_data:
                x1, y1, x2, y2 = map(int, item['box'])
                yolo_label = item.get('label', '')
                excel_target = item.get('target', '')
                facility_info = item.get('facility', '')
                status = item.get('status', 'Info')

                if status == "Pass": color = (0, 255, 0)      # Green
                elif status == "Fail": color = (0, 0, 255)    # Red
                else: color = (0, 255, 255)                   # Yellow

                # 1. 메인 박스
                cv2.rectangle(img, (x1, y1), (x2, y2), color, thickness)

                # 2. 상단 라벨 (YOLO) - 아웃라인 텍스트
                top_text = f"Det: {yolo_label}"
                # 텍스트 높이 계산
                (_, th), _ = cv2.getTextSize(top_text, font, font_scale_top, thickness)
                text_x = x1
                # 박스 위에 공간이 없으면 박스 안쪽에 그림
                text_y = y1 - 7 if y1 - 7 > th else y1 + th + 5 

                # 검정색 아웃라인 그리기
                cv2.putText(img, top_text, (text_x, text_y), font, font_scale_top, (0, 0, 0), outline_thickness)
                # 메인 색상 텍스트 그리기
                cv2.putText(img, top_text, (text_x, text_y), font, font_scale_top, color, thickness)


                # 3. 하단 라벨 (Excel Info 2줄) - 아웃라인 텍스트
                if excel_target:
                    line1 = f"[{status}] {excel_target}"
                    line2 = f"{facility_info}" if facility_info else ""

                    (_, h1), _ = cv2.getTextSize(line1, font, font_scale_bot1, thickness)
                    (_, h2), _ = cv2.getTextSize(line2, font, font_scale_bot2, thickness)
                    
                    # 위치 계산
                    line1_x = x1 + 5
                    line1_y = y2 + h1 + 5
                    
                    line2_x = x1 + 5
                    line2_y = y2 + h1 + h2 + 15

                    # Line 1: Target (상태 색상 + 아웃라인)
                    cv2.putText(img, line1, (line1_x, line1_y), font, font_scale_bot1, (0, 0, 0), outline_thickness)
                    cv2.putText(img, line1, (line1_x, line1_y), font, font_scale_bot1, color, thickness)

                    # Line 2: Facility (흰색 + 아웃라인)
                    if line2:
                        cv2.putText(img, line2, (line2_x, line2_y), font, font_scale_bot2, (0, 0, 0), outline_thickness)
                        cv2.putText(img, line2, (line2_x, line2_y), font, font_scale_bot2, (255, 255, 255), thickness)

        # 윈도우 생성 및 표시
        cv2.namedWindow(title, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(title, 1920, 1080)
        cv2.imshow(title, img)
        
        print(f"   👀 Window Title: {title}")
        print("   ⌨️  [SPACE] Next, [ESC] Exit")

        while True:
            key = cv2.waitKey(0) & 0xFF
            if key == 32: break
            elif key == 27:
                cv2.destroyAllWindows()
                raise KeyboardInterrupt("⛔ User aborted.")
        
        cv2.destroyWindow(title) 