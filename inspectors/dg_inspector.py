"""
프로그램명: 디지털 게이지 정밀 인스펙터 (dg_inspector.py)
버전: v2.1.0 (2026-01-06)
변경 사항:
- [Integration] PaddleOCR 기반 회전 보정 및 수치 추출 로직 통합
- [Logic Fix] 뎁스 매칭을 위한 'area' 및 'center_x' 데이터 반환 추가
- [Efficiency] inspect_all 메서드를 통해 이미지 내 전수 조사 지원
"""
import cv2
import numpy as np
import math
import re
from paddleocr import PaddleOCR
from loguru import logger
import config

class DGInspector:
    def __init__(self):
        self.ocr = None
        try:
            self.ocr = PaddleOCR(use_angle_cls=True, lang='en', 
                                 use_gpu=False, enable_mkldnn=False, show_log=False)
            logger.info("✅ PaddleOCR 초기화 성공")
        except Exception as e:
            logger.error(f"🔥 PaddleOCR 초기화 실패: {e}")

    def analyze_crop(self, crop_img):
        """
        [수정] M(회전 행렬)을 포함하여 5가지를 반환합니다.
        Return: (numeric_val, full_text, raw_results, rotated_img, M)
        """
        if self.ocr is None or crop_img is None or crop_img.size == 0:
            return None, "Error", [], crop_img, None

        # 1. 회전 보정 (M 행렬 획득)
        rotated_img, angle, M = self._correct_skew(crop_img) 
        
        # 2. OCR 수행
        full_text, raw_results = self._run_ocr(rotated_img)
        
        # 3. 숫자 추출
        numeric_val = self._extract_number(full_text)

        # [핵심] M을 포함하여 5개 데이터 반환
        return numeric_val, full_text, raw_results, rotated_img, M

    def _correct_skew(self, img):
        """회전 보정 및 행렬 M 반환"""
        h, w = img.shape[:2]
        try:
            rough_angle = self._estimate_angle_hough(img)
            # (중략: 기존 기울기 감지 로직)
            blue_angle = self._detect_blue_line_angle_strict(self._draw_blue_line(img, rough_angle))
            
            if blue_angle is None: return img, 0.0, np.eye(2, 3, dtype=np.float32)
            
            M = cv2.getRotationMatrix2D((w//2, h//2), blue_angle, 1.0)
            rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR)
            return rotated, blue_angle, M
        except:
            return img, 0.0, np.eye(2, 3, dtype=np.float32)

    def inspect_all(self, img_path):
        """
        이미지 내의 모든 디지털 게이지를 탐지하고 OCR 분석을 수행합니다.
        (Main Detector의 결과를 기반으로 크롭하여 분석하거나 자체 검출 수행)
        """
        full_img = cv2.imread(img_path)
        if full_img is None: return []

        # [참고] 여기서는 system_setup.detector(Main YOLO)의 결과를 인자로 받거나 
        # 직접 predict를 수행하는 구조로 확장 가능합니다. 
        # 본 코드에서는 구조적 일관성을 위해 탐지 및 분석 통합 과정을 기술합니다.
        
        # 임시: DG 전용 탐지 모델이 있다면 호출 (없다면 config의 classifier 사용)
        from ultralytics import YOLO
        detector = YOLO(config.MODEL_CONFIG["classifier"])
        results = detector.predict(full_img, conf=0.25, verbose=False)
        
        final_results = []
        if not results: return []

        for box in results[0].boxes:
            label = results[0].names[int(box.cls[0])]
            # DG 관련 라벨인 경우에만 OCR 수행
            if 'DG' in label or 'digital' in label.lower():
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                crop = full_img[y1:y2, x1:x2]
                
                # [기존 로직 호출] 회전 보정 및 OCR 분석
                numeric_val, full_text, raw_results, rotated_img, M = self.analyze_crop(crop)
                
                final_results.append({
                    'label': label,
                    'value': numeric_val if numeric_val is not None else "Read Fail",
                    'full_text': full_text,
                    'box': [x1, y1, x2, y2],
                    'area': (x2 - x1) * (y2 - y1),
                    'center_x': (x1 + x2) / 2,
                    'center_y': (y1 + y2) / 2,
                    'rotated_img': rotated_img,
                    'ocr_details': raw_results,
                    'M': M  # [중요] M 행렬을 딕셔너리에 저장하여 외부에서 쓸 수 있게 함
                })
        return final_results
    # def analyze_crop(self, crop_img):
    #     """[기존 로직] 단일 크롭 이미지 분석"""
    #     if self.ocr is None or crop_img is None or crop_img.size == 0:
    #         return None, "Error", [], crop_img

    #     # 1. 회전 보정
    #     rotated_img, angle, _ = self._correct_skew(crop_img)
    #     # 2. OCR 수행
    #     full_text, raw_results = self._run_ocr(rotated_img)
    #     # 3. 숫자 추출
    #     numeric_val = self._extract_number(full_text)

    #     return numeric_val, full_text, raw_results, rotated_img

    # =========================================================
    # [Internal Logic] _correct_skew, _run_ocr, _extract_number 
    # (사용자님이 제공해주신 내부 로직을 그대로 유지합니다)
    # =========================================================
    # def _correct_skew(self, img, visualize=False):
        h, w = img.shape[:2]
        try:
            rough_angle = self._estimate_angle_hough(img)
            img_with_line = self._draw_blue_line(img, rough_angle)
            blue_angle = self._detect_blue_line_angle_strict(img_with_line)
            if blue_angle is None: return img, 0.0, None
            M = cv2.getRotationMatrix2D((w//2, h//2), blue_angle, 1.0)
            return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR), blue_angle, M
        except: return img, 0.0, None

    def _estimate_angle_hough(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        h, w = img.shape[:2]
        roi = edges[int(h*0.2):int(h*0.8), int(w*0.2):int(w*0.8)]
        lines = cv2.HoughLinesP(roi, 1, np.pi/180, 40, minLineLength=80, maxLineGap=60)
        if lines is None: return 0.0
        angles = [math.degrees(math.atan2(l[0][3]-l[0][1], l[0][2]-l[0][0])) for l in lines if l[0][2] != l[0][1]]
        return float(np.median([a for a in angles if -45 < a < 45])) if angles else 0.0

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
        vec = np.linalg.eig(np.cov((pts - np.mean(pts, axis=0)).T))[1][:, np.argmax(np.linalg.eig(np.cov((pts - np.mean(pts, axis=0)).T))[0])]
        angle = math.degrees(math.atan2(vec[1], vec[0]))
        return angle - 180 if angle > 90 else (angle + 180 if angle < -90 else angle)

    def _run_ocr(self, img):
        if self.ocr is None: return "OCR Init Failed", []
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        try:
            result = self.ocr.ocr(rgb, cls=True)
            if not result or result[0] is None: return "", []
            full_text = " ".join([line[1][0] for line in result[0]])
            raw_res = [{'text': l[1][0], 'conf': l[1][1], 'box': l[0]} for l in result[0]]
            return full_text, raw_res
        except: return "OCR Error", []

    def _extract_number(self, text):
        if not text: return None
        match = re.search(r"[-+]?\d*\.\d+|\d+", text.replace(" ", ""))
        return float(match.group()) if match else None