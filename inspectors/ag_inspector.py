import cv2
import numpy as np
import math
from ultralytics import YOLO
from loguru import logger

class AGInspector:
    def __init__(self, model_path="models/ag_inspector/weights/best.pt"):
        self.model = YOLO(model_path)
        # 키포인트 인덱스 정의
        self.KP_IDX = { "Start": 0, "Mid": 1, "Center": 2, "End": 3, "ND_HEAD": 4 }
        self.FINAL_LEN = 400  # 변환(Warping) 후 이미지 크기

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
                # 4. 바늘 머리 확인
                has_head = p_h is not None and np.linalg.norm(p_h - p_c) > avg_r * 0.1
                
                # 5. Aspect Ratio (AR) 체크 및 Warping 결정
                p_s_opp = 2 * p_c - p_s
                p_e_opp = 2 * p_c - p_e
                side_1 = np.linalg.norm(p_s - p_e)
                side_2 = np.linalg.norm(p_e - p_s_opp)
                ar = max(side_1, side_2) / (min(side_1, side_2) + 1e-6)

                # AR이 너무 크면(심한 측면) Warping이 역효과를 낼 수 있음 -> Raw 사용
                skip_warp = (ar > 1.5)

                if has_head and not skip_warp:
                    # --- Homography Warping ---
                    src_pts = np.float32([p_s, p_e, p_s_opp, p_e_opp])
                    cx_f, cy_f = self.FINAL_LEN // 2, self.FINAL_LEN // 2
                    dst_r = int(self.FINAL_LEN * 0.35)

                    v_s, v_e = p_s - p_c, p_e - p_c
                    cos_theta = np.dot(v_s, v_e) / (np.linalg.norm(v_s) * np.linalg.norm(v_e) + 1e-6)
                    half_span = math.acos(np.clip(cos_theta, -1.0, 1.0)) / 2.0

                    # 방향 판단
                    mid_y = (p_s[1] + p_e[1]) / 2.0
                    is_rainbow = mid_y < p_c[1]
                    
                    base_angle = -math.pi/2.0 if is_rainbow else math.pi/2.0
                    t_s_rad = base_angle - half_span if is_rainbow else base_angle + half_span
                    t_e_rad = base_angle + half_span if is_rainbow else base_angle - half_span
                    
                    def get_dst_pt(rad):
                        return (cx_f + dst_r * math.cos(rad), cy_f + dst_r * math.sin(rad))

                    dst_s = get_dst_pt(t_s_rad)
                    dst_e = get_dst_pt(t_e_rad)
                    dst_pts = np.float32([dst_s, dst_e, (2*cx_f-dst_s[0], 2*cy_f-dst_s[1]), (2*cx_f-dst_e[0], 2*cy_f-dst_e[1])])

                    try:
                        M_homo, _ = cv2.findHomography(src_pts, dst_pts)
                        def transform_pt(pt, m):
                            v = m @ np.array([pt[0], pt[1], 1])
                            return np.array([v[0]/v[2], v[1]/v[2]])

                        ratio = self._calculate_ratio(transform_pt(p_c, M_homo), 
                                                     transform_pt(p_s, M_homo), 
                                                     transform_pt(p_e, M_homo), 
                                                     transform_pt(p_h, M_homo))
                    except:
                        ratio = self._calculate_ratio(p_c, p_s, p_e, p_h)
                elif has_head:
                    # Raw Ratio
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