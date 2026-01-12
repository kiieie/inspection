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

        for i, box in enumerate(main_res.boxes):
            # 1. 기본 정보 추출
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            label_name = main_res.names[int(box.cls[0])]
            kpts = main_res.keypoints[i].data[0].cpu().numpy() # [5, 3]

            if kpts.shape[0] < 5: continue

            p_s, p_m, p_c, p_e, p_h = kpts[0][:2], kpts[1][:2], kpts[2][:2], kpts[3][:2], kpts[4][:2]

            # 2. [검증 로직] ag_core의 기하학적 유효성 검사 반영
            d_s = np.linalg.norm(p_s - p_c)
            d_e = np.linalg.norm(p_e - p_c)
            d_m = np.linalg.norm(p_m - p_c)
            avg_r = (d_s + d_e + d_m) / 3.0
            max_r = max(d_s, d_e, d_m)
            min_r = min(d_s, d_e, d_m)

            is_valid = True
            status_msg = "OK"

            # 너무 작거나 심하게 찌그러진 경우 필터링
            if max_r < 15.0: 
                is_valid, status_msg = False, "Too Small"
            elif max_r > 0 and (min_r / max_r) < 0.4: 
                is_valid, status_msg = False, "Distorted"
            
            ratio = 0.0
            if is_valid:
                # 3. [Warping 로직] 정면 보정 후 비율 계산
                # 대칭점 계산
                p_s_opp = 2 * p_c - p_s
                p_e_opp = 2 * p_c - p_e
                
                # 종횡비(AR) 체크
                side_1 = np.linalg.norm(p_s - p_e)
                side_2 = np.linalg.norm(p_e - p_s_opp)
                ar = max(side_1, side_2) / (min(side_1, side_2) + 1e-6)

                # 바늘 탐지 여부 확인
                head_len = np.linalg.norm(p_h - p_c)
                if head_len > avg_r * 0.1:
                    # 원본 이미지에서의 Raw Ratio (백업용)
                    # raw_ratio = self._calculate_ratio(p_c, p_s, p_e, p_h)

                    # --- Homography 변환 시작 ---
                    src_pts = np.float32([p_s, p_e, p_s_opp, p_e_opp])
                    cx, cy = self.FINAL_LEN // 2, self.FINAL_LEN // 2
                    dst_r = int(self.FINAL_LEN * 0.35)

                    v_s, v_e = p_s - p_c, p_e - p_c
                    cos_theta = np.dot(v_s, v_e) / (np.linalg.norm(v_s) * np.linalg.norm(v_e) + 1e-6)
                    half_span = math.acos(np.clip(cos_theta, -1.0, 1.0)) / 2.0

                    # 게이지 방향 판단 (무지개 형태 여부)
                    is_rainbow = ((p_s[1] + p_e[1]) / 2.0) < p_c[1]
                    base_angle = -math.pi/2.0 if is_rainbow else math.pi/2.0
                    
                    # 목적지 좌표 생성
                    def get_dst_pt(rad):
                        return (cx + dst_r * math.cos(rad), cy + dst_r * math.sin(rad))

                    t_s_rad = base_angle - half_span if is_rainbow else base_angle + half_span
                    t_e_rad = base_angle + half_span if is_rainbow else base_angle - half_span
                    
                    dst_s = get_dst_pt(t_s_rad)
                    dst_e = get_dst_pt(t_e_rad)
                    dst_pts = np.float32([dst_s, dst_e, (2*cx-dst_s[0], 2*cy-dst_s[1]), (2*cx-dst_e[0], 2*cy-dst_e[1])])

                    try:
                        M_homo, _ = cv2.findHomography(src_pts, dst_pts)
                        # 바늘 포인트 변환
                        def transform_pt(pt, m):
                            v = m @ np.array([pt[0], pt[1], 1])
                            return np.array([v[0]/v[2], v[1]/v[2]])

                        t_c = transform_pt(p_c, M_homo)
                        t_s = transform_pt(p_s, M_homo)
                        t_e = transform_pt(p_e, M_homo)
                        t_h = transform_pt(p_h, M_homo)

                        # 보정된 이미지 기준 비율 계산
                        ratio = self._calculate_ratio(t_c, t_s, t_e, t_h)
                    except Exception as e:
                        logger.error(f"Warping failed: {e}")
                        ratio = self._calculate_ratio(p_c, p_s, p_e, p_h) # 실패 시 원본 기준 계산
                else:
                    status_msg = "No Needle"

            # 4. 결과 저장
            final_results.append({
                'label': label_name,
                'value_ratio': ratio,
                'status_msg': status_msg,
                'is_valid': is_valid,
                'box': [x1, y1, x2, y2],
                'area': (x2 - x1) * (y2 - y1), # 면적 데이터 산출 추가
                'center_x': (x1 + x2) / 2,
                'center_y': (y1 + y2) / 2,
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