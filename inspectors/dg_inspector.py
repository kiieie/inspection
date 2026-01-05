import cv2
import numpy as np
import math
import re
from paddleocr import PaddleOCR
from loguru import logger

class DGInspector:
    def __init__(self):
        self.ocr = None
        try:
            logger.info("PaddleOCR 초기화 시도 (CPU 모드)...")
            self.ocr = PaddleOCR(use_angle_cls=True, lang='en', 
                                 use_gpu=False, enable_mkldnn=False, show_log=False)
            logger.info("✅ PaddleOCR 초기화 성공")
        except Exception as e:
            logger.error(f"🔥 PaddleOCR 초기화 실패: {e}")
            self.ocr = None

    def analyze_crop(self, crop_img):
        """
        [수정됨] 회전된 이미지(rotated_img)를 포함하여 4가지를 반환합니다.
        Return: (numeric_val, full_text, raw_results, rotated_img)
        """
        if self.ocr is None:
            return None, "OCR Init Failed", [], crop_img

        if crop_img is None or crop_img.size == 0:
            return None, "Empty Crop", [], crop_img

        # 1. 회전 보정 (시각화 끔, Matrix 불필요)
        rotated_img, angle, _ = self._correct_skew(crop_img, visualize=False)

        # 2. OCR 수행 (회전된 이미지 기준 좌표 그대로 사용)
        full_text, raw_results = self._run_ocr(rotated_img)
        
        # 3. 숫자 추출
        numeric_val = self._extract_number(full_text)

        return numeric_val, full_text, raw_results, rotated_img

    # =========================================================
    # [Internal] 회전 보정 및 OCR 로직
    # =========================================================
    def _correct_skew(self, img, visualize=False):
        h, w = img.shape[:2]
        try:
            rough_angle = self._estimate_angle_hough(img)
            img_with_line = self._draw_blue_line(img, rough_angle)
            blue_angle = self._detect_blue_line_angle_strict(img_with_line)
            
            if blue_angle is None: 
                return img, 0.0, None
            
            M = cv2.getRotationMatrix2D((w//2, h//2), blue_angle, 1.0)
            rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR)
            
            return rotated, blue_angle, M
        except Exception:
            return img, 0.0, None

    def _estimate_angle_hough(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        h, w = img.shape[:2]
        roi = edges[int(h*0.2):int(h*0.8), int(w*0.2):int(w*0.8)]
        if roi.size == 0: return 0.0
        lines = cv2.HoughLinesP(roi, 1, np.pi/180, threshold=40, minLineLength=80, maxLineGap=60)
        if lines is None: return 0.0
        angles = []
        for l in lines:
            x1, y1, x2, y2 = l[0]
            if x2 == x1: continue
            ang = math.degrees(math.atan2(y2-y1, x2-x1))
            if -45 < ang < 45: angles.append(ang)
        return float(np.median(angles)) if angles else 0.0

    def _draw_blue_line(self, img, angle):
        h, w = img.shape[:2]
        cx, cy = w // 2, int(h * 0.1)
        rad = math.radians(angle)
        dx, dy = math.cos(rad), math.sin(rad)
        length = int(w * 0.9)
        x1, y1 = int(cx - dx*length*0.5), int(cy - dy*length*0.5)
        x2, y2 = int(cx + dx*length*0.5), int(cy + dy*length*0.5)
        img2 = img.copy()
        cv2.line(img2, (x1,y1), (x2,y2), (255,0,0), 8)
        return img2

    def _detect_blue_line_angle_strict(self, img):
        mask = (img[:,:,0] == 255) & (img[:,:,1] == 0) & (img[:,:,2] == 0)
        ys, xs = np.where(mask)
        if len(xs) < 20: return None
        pts = np.vstack([xs, ys]).T.astype(np.float32)
        mean = np.mean(pts, axis=0)
        cov = np.cov((pts - mean).T)
        eigvals, eigvecs = np.linalg.eig(cov)
        vec = eigvecs[:, np.argmax(eigvals)]
        angle = math.degrees(math.atan2(vec[1], vec[0]))
        if angle > 90: angle -= 180
        if angle < -90: angle += 180
        return angle

    def _run_ocr(self, img):
        if self.ocr is None: return "OCR Init Failed", []
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        try:
            result = self.ocr.ocr(rgb, cls=True)
            if not result or result[0] is None: return "", []
            
            full_text_list = []
            raw_results = []
            
            for line in result[0]:
                box = line[0]
                text = line[1][0]
                conf = line[1][1]
                
                full_text_list.append(text)
                raw_results.append({
                    'text': text,
                    'conf': conf,
                    'box': box # Rotated Image 기준 좌표
                })
                
            return " ".join(full_text_list), raw_results
        except Exception as e:
            logger.error(f"OCR Run Error: {e}")
            return "OCR Error", []

    def _extract_number(self, text):
        if not text: return None
        match = re.search(r"[-+]?\d*\.\d+|\d+", text.replace(" ", ""))
        if match:
            try: return float(match.group())
            except: return None
        return None

    # =========================================================================
    # [Visualization] 회전된 이미지 위에 결과 보여주기
    # =========================================================================
    def show_combined_result(self, img_path, labeled_dets, highlight_count=0, title="DG Result"):
        """
        [수정] 각 Detection에 대해 '회전 보정된 이미지'를 카드 형태로 보여줍니다.
        """
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        for i, det in enumerate(labeled_dets):
            # 1. 회전된 이미지 가져오기
            rotated_img = det.get('rotated_img')
            if rotated_img is None: continue # 없으면 스킵
            
            # 사본 생성 (그리기용)
            canvas = rotated_img.copy()
            
            # 정보 추출
            val = det.get('final_value', 'N/A')
            status = det.get('status', '')
            fac_info = det.get('facility_info', 'Unknown')
            ocr_details = det.get('ocr_details', [])
            
            # 색상 설정
            if status == "Abnormal" or val == "Read Fail":
                color = (0, 0, 255) # Red
            elif status == "Type Mismatch":
                color = (255, 0, 255)
            else:
                color = (0, 255, 0) # Green

            # -----------------------------------------------------------------
            # 2. OCR 박스 및 텍스트 그리기 (이미지 내부)
            # -----------------------------------------------------------------
            for item in ocr_details:
                text = item['text']
                box_pts = np.array(item['box'], dtype=np.int32) # Rotated 기준 좌표
                
                # 박스 그리기 (노랑)
                cv2.polylines(canvas, [box_pts], isClosed=True, color=(0, 255, 255), thickness=2)
                
                # 텍스트 그리기 (박스 위쪽)
                text_org = tuple(box_pts[0]) # 좌상단
                cv2.putText(canvas, text, (text_org[0], text_org[1] - 5), font, 0.6, (0, 0, 0), 3)
                cv2.putText(canvas, text, (text_org[0], text_org[1] - 5), font, 0.6, (0, 255, 255), 1)

            # -----------------------------------------------------------------
            # 3. 상단 헤더 붙이기 (설비명, 결과)
            # -----------------------------------------------------------------
            h, w = canvas.shape[:2]
            header_h = 60
            
            # 헤더 배경 생성
            header = np.zeros((header_h, w, 3), dtype=np.uint8)
            header[:] = color # 상태 색상으로 채우기
            
            # 텍스트 작성
            info_str = f"{fac_info}"
            res_str = f"Result: {val} ({status})"
            
            cv2.putText(header, info_str, (10, 25), font, 0.7, (0,0,0), 2)
            cv2.putText(header, res_str, (10, 50), font, 0.6, (255,255,255), 1)
            
            # 이미지 합치기 (헤더 + 회전된 이미지)
            final_view = np.vstack([header, canvas])
            
            # -----------------------------------------------------------------
            # 4. 출력 및 대기
            # -----------------------------------------------------------------
            # 너무 크면 리사이즈
            fh, fw = final_view.shape[:2]
            if fh > 800:
                scale = 800 / fh
                final_view = cv2.resize(final_view, (int(fw*scale), 800))
                
            cv2.imshow(f"{title} - {i+1}/{len(labeled_dets)}", final_view)
            
            # 스페이스바 누르면 다음 게이지로 넘어감
            key = cv2.waitKey(0)
            cv2.destroyAllWindows()
            if key == 27: # ESC 누르면 전체 종료
                return