import cv2
import numpy as np
import math
from ultralytics import YOLO
from loguru import logger
from config.model import MODEL_CONFIG

class AGInspector:
    def __init__(self, model_path=None):
        if model_path is None:
            model_path = MODEL_CONFIG["ag_pose"]
        self.model = YOLO(str(model_path))
        self.KP_IDX = {"Start": 0, "Mid": 1, "Center": 2, "End": 3, "ND_HEAD": 4}

    def _get_deg(self, pt, center):
        """중심점 기준 특정 포인트의 각도(Degree) 계산"""
        return (math.degrees(math.atan2(-(pt[1] - center[1]), pt[0] - center[0])) + 360) % 360

    def _calculate_ratio(self, c, s, e, h):
        """각도를 기반으로 0.0 ~ 1.0 사이의 비율 계산 (ag_core 로직)"""
        ang_s = self._get_deg(s, c)
        ang_e = self._get_deg(e, c)
        ang_h = self._get_deg(h, c)

        def clockwise_dist(a_start, a_end):
            return (a_start - a_end) % 360

        span = clockwise_dist(ang_s, ang_e)
        prog = clockwise_dist(ang_s, ang_h)
        
        if span < 1e-6: span = 360.0
        buffer = 20.0 # 허용 오차
        
        if prog > span + buffer: return 0.0
        elif prog > span: return 1.0
        else: return prog / span

    def inspect_all(self, img_path):
        full_img = cv2.imread(img_path)
        if full_img is None: return []
        img_h, img_w = full_img.shape[:2]

        results = self.model.predict(full_img, conf=0.25, verbose=False)
        if not results: return []
        
        main_res = results[0]
        final_results = []

        if main_res.boxes is None or main_res.keypoints is None:
            return []

        # YOLOv8 keypoints data: [N, 5, 3] (x, y, conf)
        kps_all = main_res.keypoints.data.cpu().numpy()
        boxes_all = main_res.boxes.data.cpu().numpy() # [N, 6] (x1, y1, x2, y2, conf, cls)

        for i in range(len(boxes_all)):
            # 1. 기본 정보 추출
            box = boxes_all[i]
            x1, y1, x2, y2 = map(int, box[:4])
            label_name = main_res.names[int(box[5])]
            kpts = kps_all[i] # [5, 3]

            # 2. 키포인트 유효성 검사 (Confidence filtering)
            # KP: Start(0), Mid(1), Center(2), End(3), Head(4)
            def get_valid_pt(idx):
                if kpts[idx][2] < 0.5: return None
                return kpts[idx][:2]

            p_s, p_m, p_c, p_e, p_h = get_valid_pt(0), get_valid_pt(1), get_valid_pt(2), get_valid_pt(3), get_valid_pt(4)

            # 필수 포인트(Center, Start, End)가 없으면 불가능
            if p_c is None or p_s is None or p_e is None:
                final_results.append({
                    'label': label_name, 
                    'value_ratio': 0.0, 
                    'status_msg': "Missing Keypoints",
                    'is_valid': False, 
                    'box': [x1, y1, x2, y2], 
                    'area': (x2 - x1) * (y2 - y1),
                    'center_x': (x1 + x2) / 2,
                    'center_y': (y1 + y2) / 2,
                    'keypoints': kpts
                })
                continue

            # 3. 기하학적 유효성 검사 (Radius check)
            d_s = np.linalg.norm(p_s - p_c)
            d_e = np.linalg.norm(p_e - p_c)
            d_m = np.linalg.norm(p_m - p_c) if p_m is not None else (d_s + d_e) / 2.0
            
            radii = [d_s, d_e, d_m]
            avg_r = sum(radii) / 3.0
            max_r, min_r = max(radii), min(radii)

            # 너무 작거나 경계선에 걸친 경우 필터링
            margin = 5
            cx, cy = p_c
            is_valid = True
            status_msg = "OK"

            if max_r < 15.0:
                is_valid, status_msg = False, "Too Small"
            elif max_r > 0 and (min_r / max_r) < 0.4:
                is_valid, status_msg = False, "Distorted"
            elif cx < margin or cx > img_w-margin or cy < margin or cy > img_h-margin:
                is_valid, status_msg = False, "Edge"

            ratio = 0.0
            if is_valid:
                has_head = p_h is not None and np.linalg.norm(p_h - p_c) > avg_r * 0.1

                if has_head:
                    ratio = self._calculate_ratio(p_c, p_s, p_e, p_h)
                else:
                    status_msg = "No Needle"

            # 6. 결과 저장
            final_results.append({
                'label': label_name,
                'value_ratio': ratio,
                'status_msg': status_msg,
                'is_valid': is_valid,
                'box': [x1, y1, x2, y2],
                'area': (x2 - x1) * (y2 - y1),
                'center_x': cx,
                'center_y': cy,
                'keypoints': kpts
            })

        return final_results

    def show_combined_result(self, img_path, labeled_dets, title="Inspection Result"):
        # ... (기존 시각화 로직과 동일하되, status_msg 등을 활용하여 표시)
        img = cv2.imread(img_path)
        if img is None: return

        for det in labeled_dets:
            x1, y1, x2, y2 = map(int, det['box'])
            ratio = det.get('value_ratio', 0.0)
            status = det.get('status_msg', 'Unknown')
            label = det.get('label', 'AG')

            color = (0, 255, 0) if status == "OK" else (0, 0, 255)
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
            
            # 텍스트 출력
            txt = f"{label}: {ratio:.2f} ({status})"
            cv2.putText(img, txt, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            # Keypoints 시각화
            for kp in det['keypoints']:
                kx, ky, conf = kp
                if conf > 0.5:
                    cv2.circle(img, (int(kx), int(ky)), 3, (0, 0, 255), -1)

        cv2.imshow(title, img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()