import cv2
import numpy as np
from ultralytics import YOLO
from utils.geometry import calculate_gauge_ratio, validate_gauge_geometry

class AGInspector:
    def __init__(self, model_path="models/ag_inspector/weights/best.pt"):
        self.model = YOLO(model_path)
        # 참조 코드 기준 인덱스 매핑
        self.KP_IDX = { "Start": 0, "Mid": 1, "Center": 2, "End": 3, "ND_HEAD": 4 }

    def inspect_all(self, img_path, classifier_result=None):
        # 이미지 로드
        full_img = cv2.imread(img_path)
        if full_img is None: return []
        h, w = full_img.shape[:2]

        # 추론
        results = self.model.predict(full_img, conf=0.25, verbose=False)
        if not results: return []
        
        main_res = results[0]
        final_results = []

        # Boxes와 Keypoints 순회
        if main_res.boxes is None or main_res.keypoints is None:
            return []

        for i, box in enumerate(main_res.boxes):
            # 1. 기본 정보 추출
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            cls_id = int(box.cls[0])
            label_name = main_res.names[cls_id]
            
            # 2. 키포인트 데이터 추출 (x, y, conf)
            kpts = main_res.keypoints[i].data[0].cpu().numpy() # shape: [5, 3]
            
            # 키포인트 개수 확인 (5개 미만이면 계산 불가)
            if kpts.shape[0] < 5:
                continue

            # 좌표 분리 (가독성을 위해 변수 할당)
            p_s = kpts[self.KP_IDX["Start"]][:2]
            p_m = kpts[self.KP_IDX["Mid"]][:2]
            p_c = kpts[self.KP_IDX["Center"]][:2]
            p_e = kpts[self.KP_IDX["End"]][:2]
            p_h = kpts[self.KP_IDX["ND_HEAD"]][:2]

            # 3. [검증 단계] 기하학적 유효성 검사 (참조 코드 로직 반영)
            is_valid, msg = validate_gauge_geometry(p_c, p_s, p_m, p_e, w, h)
            
            ratio = 0.0
            status_msg = msg
            
            # 유효하고, 바늘(Head)이 존재할 때만 값 계산
            if is_valid:
                # 바늘이 중심점에 너무 붙어있으면(길이가 0에 가까우면) 미검출로 간주
                head_len = np.linalg.norm(p_h - p_c)
                avg_radius = (np.linalg.norm(p_s-p_c) + np.linalg.norm(p_e-p_c)) / 2
                
                if head_len > avg_radius * 0.1: # 반지름의 10% 이상 길어야 바늘로 인정
                    ratio = calculate_gauge_ratio(p_c, p_s, p_e, p_h)
                    status_msg = "OK"
                else:
                    status_msg = "No Needle"
            else:
                # 유효하지 않은 경우(찌그러짐 등) 비율은 0.0 처리하되, 메시지로 필터링 가능하게 함
                ratio = 0.0

            # 4. 결과 저장
            final_results.append({
                'label': label_name,
                'value_ratio': ratio,  # 0.0 ~ 1.0
                'status_msg': status_msg, # "OK", "Distorted", "Too Small" 등
                'is_valid': is_valid,     # True/False
                'box': [x1, y1, x2, y2],
                'area': (x2 - x1) * (y2 - y1),
                'center_x': (x1 + x2) / 2,
                'center_y': (y1 + y2) / 2,
                'keypoints': kpts, # 시각화용 원본 키포인트
                'spatial_label': '' # 나중에 위치 라벨링에서 채워짐
            })

        return final_results
    
    def show_combined_result(self, img_path, labeled_dets, highlight_count=0, title="Inspection Result"):
        img = cv2.imread(img_path)
        if img is None: return

        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 0.5
        thickness = 1

        for i, det in enumerate(labeled_dets):
            x1, y1, x2, y2 = map(int, det['box'])
            
            # 정보 가져오기
            val = det.get('final_value', 'N/A')
            status = det.get('status', '')
            
            # 위치 및 설비 정보
            fac_info = det.get('facility_info', 'NA')
            pos_info = det.get('pos_info', 'NA')
            
            # [추가] YOLO 검출 라벨 가져오기
            yolo_label = det.get('label', 'Unknown')

            # 색상 설정
            is_target = i < highlight_count
            if status == "Abnormal": color = (0, 0, 255)      # Red
            elif status == "Type Mismatch": color = (255, 0, 255) # Magenta
            elif is_target: color = (0, 255, 0)               # Green
            else: color = (0, 165, 255)                       # Orange

            # 박스 그리기
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
            
            # -------------------------------------------------------
            # [수정] 텍스트 3줄 출력 로직
            # -------------------------------------------------------
            line1 = f"[{pos_info}] {fac_info}"
            line2 = f"[{yolo_label}]"         # <--- 추가된 YOLO 라벨
            line3 = f"{val} ({status})"
            
            # 텍스트 크기 계산 (배경 박스용)
            (w1, h1), _ = cv2.getTextSize(line1, font, scale, thickness)
            (w2, h2), _ = cv2.getTextSize(line2, font, scale, thickness)
            (w3, h3), _ = cv2.getTextSize(line3, font, scale, thickness)
            
            max_w = max(w1, w2, w3)
            # 줄간격(6) * 2 + 여백(10)
            total_h = h1 + h2 + h3 + 22 
            
            # 텍스트 배경 (박스 상단에 부착)
            # 좌표: 박스 좌상단(x1, y1) 기준 위쪽으로
            bg_pt1 = (x1, y1 - total_h - 4)
            bg_pt2 = (x1 + max_w + 10, y1)
            
            # 배경 그리기
            cv2.rectangle(img, bg_pt1, bg_pt2, color, -1)
            
            # 텍스트 쓰기 (검은색) - 좌표 계산 주의 (위에서부터 아래로)
            # Line 1 (위치/설비)
            cv2.putText(img, line1, (x1 + 5, y1 - h2 - h3 - 18), font, scale, (0, 0, 0), thickness)
            # Line 2 (YOLO 라벨)
            cv2.putText(img, line2, (x1 + 5, y1 - h3 - 10), font, scale, (0, 0, 0), thickness)
            # Line 3 (값/상태)
            cv2.putText(img, line3, (x1 + 5, y1 - 4), font, scale, (0, 0, 0), thickness)

            # Keypoints 표시
            if det.get('keypoints') is not None:
                for kp in det['keypoints']:
                    kx, ky, conf = kp
                    if conf > 0.5:
                        cv2.circle(img, (int(kx), int(ky)), 3, (0, 0, 255), -1)

        cv2.imshow(title, img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()