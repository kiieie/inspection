"""
프로그램명: 디지털 게이지 인스펙터 (dg_inspector.py) - PaddleOCR 제거 버전
버전: v2.2.0 (2026-01-14)
변경 사항:
- [Optimization] 사용하지 않는 PaddleOCR 라이브러리 및 초기화 로직 전면 제거
- [Logic Fix] OCR 없이 회전 보정(Correct Skew) 결과만 반환하도록 구조 변경
- [Refactoring] .antigravityrules에 따라 상세한 한국어 주석 추가
"""
import cv2
import numpy as np
import math
import re
from loguru import logger
import config

class DGInspector:
    """
    디지털 게이지(Digital Gauge)의 이미지를 분석하는 클래스입니다.
    현재 버전에서는 OCR을 사용하지 않으며, 이미지의 기울기 보정 및 객체 정보 반환에 집중합니다.
    """
    def __init__(self):
        # PaddleOCR 제거로 인해 초기화 로직 생략
        logger.info("✅ DGInspector 초기화 완료 (OCR 미사용 모드)")

    def analyze_crop(self, crop_img):
        """
        추출된 게이지 영역(Crop)을 분석하여 회전 보정된 이미지와 변환 행렬을 반환합니다.
        OCR이 제거되었으므로 텍스트 관련 정보는 기본값(N/A)으로 반환합니다.
        
        Args:
            crop_img (np.ndarray): 분석할 게이지 크롭 이미지
            
        Returns:
            tuple: (numeric_val, full_text, raw_results, rotated_img, M)
                   - numeric_val: 추출된 숫자 (OCR 제거로 None)
                   - full_text: 전체 텍스트 (OCR 제거로 "N/A")
                   - raw_results: 상세 OCR 결과 (OCR 제거로 빈 리스트)
                   - rotated_img: 회전 보정된 이미지
                   - M: 회전 변환 행렬 (원본 좌표 복원용)
        """
        if crop_img is None or crop_img.size == 0:
            return None, "Error", [], crop_img, None

        # 1. 기하학적 회전 보정 수행 (M 행렬 획득)
        # PaddleOCR의 내부 회전 분류 대신 허프 변환 기반의 자체 기울기 보정 사용
        rotated_img, angle, M = self._correct_skew(crop_img) 
        
        # 2. OCR이 제거되었으므로 텍스트 분석 과정 생략
        full_text = "N/A (OCR Disabled)"
        raw_results = []
        numeric_val = None

        return numeric_val, full_text, raw_results, rotated_img, M

    def _correct_skew(self, img):
        """
        이미지의 수평을 맞추기 위해 기울기를 계산하고 회전 변환을 수행합니다.
        
        Args:
            img (np.ndarray): 입력 이미지
            
        Returns:
            tuple: (rotated_img, angle, M)
        """
        h, w = img.shape[:2]
        try:
            # 허프 변환을 이용한 대략적인 각도 추정
            rough_angle = self._estimate_angle_hough(img)
            
            # 파란색 가이드라인(시뮬레이션용) 등을 이용한 정밀 각도 계산 로직
            # 기존 로직을 유지하여 호환성 보장
            blue_angle = self._detect_blue_line_angle_strict(self._draw_blue_line(img, rough_angle))
            
            if blue_angle is None: 
                return img, 0.0, np.eye(2, 3, dtype=np.float32)
            
            # 회전 행렬 생성 (이미지 중심 기준)
            M = cv2.getRotationMatrix2D((w//2, h//2), blue_angle, 1.0)
            # 아핀 변환 적용
            rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR)
            return rotated, blue_angle, M
        except Exception as e:
            logger.debug(f"Skew correction failed: {e}")
            return img, 0.0, np.eye(2, 3, dtype=np.float32)

    def _estimate_angle_hough(self, img):
        """허프 변환(Hough Transform)을 사용하여 이미지 내 직선의 각도를 추정합니다."""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        h, w = img.shape[:2]
        # 중앙 영역(ROI) 추출하여 외곽 노이즈 제거
        roi = edges[int(h*0.2):int(h*0.8), int(w*0.2):int(w*0.8)]
        lines = cv2.HoughLinesP(roi, 1, np.pi/180, 40, minLineLength=80, maxLineGap=60)
        if lines is None: return 0.0
        
        angles = []
        for l in lines:
            x1, y1, x2, y2 = l[0]
            if x2 != x1:
                angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
                if -45 < angle < 45: # 유효 범위 내 각도만 수집
                    angles.append(angle)
        
        return float(np.median(angles)) if angles else 0.0

    def _draw_blue_line(self, img, angle):
        """기운 각도에 맞춰 가상의 파란색 라인을 그립니다 (디버깅 및 정밀 보정용)."""
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
        """그려진 파란색 라인의 좌표를 역추적하여 정밀한 회전 각도를 산출합니다."""
        # 파란색(255, 0, 0) 픽셀 추출
        mask = (img[:,:,0] == 255) & (img[:,:,1] == 0) & (img[:,:,2] == 0)
        ys, xs = np.where(mask)
        if len(xs) < 20: return None
        
        # 주성분 분석(PCA)과 유사한 방식으로 최적의 직선 각도 계산
        pts = np.vstack([xs, ys]).T.astype(np.float32)
        mu = np.mean(pts, axis=0)
        cov = np.cov((pts - mu).T)
        evals, evecs = np.linalg.eig(cov)
        vec = evecs[:, np.argmax(evals)]
        
        angle = math.degrees(math.atan2(vec[1], vec[0]))
        # 각도 정규화 (-90 ~ 90 범위)
        if angle > 90: angle -= 180
        elif angle < -90: angle += 180
        return angle

    def inspect_all(self, img_path):
        """
        주어진 이미지에서 모든 디지털 게이지를 찾아 분석 결과를 리스트로 반환합니다.
        기존 main 진단 시스템과의 호환성을 위해 유지합니다.
        """
        full_img = cv2.imread(img_path)
        if full_img is None: return []

        # YOLO 모델 로딩 (내부 임포트로 종속성 최소화)
        from ultralytics import YOLO
        detector = YOLO(config.MODEL_CONFIG["classifier"])
        results = detector.predict(full_img, conf=0.25, verbose=False)
        
        final_results = []
        if not results: return []

        for box in results[0].boxes:
            label = results[0].names[int(box.cls[0])]
            # DG(Digital Gauge) 관련 라벨만 처리
            if 'DG' in label or 'digital' in label.lower():
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                # 이미지 크롭 (안전 마진 고려 가능)
                crop = full_img[y1:y2, x1:x2]
                
                # 분석 수행
                _, full_text, _, rotated_img, M = self.analyze_crop(crop)
                
                final_results.append({
                    'label': label,
                    'value': "OCR Disabled",
                    'full_text': full_text,
                    'box': [x1, y1, x2, y2],
                    'area': (x2 - x1) * (y2 - y1),
                    'center_x': (x1 + x2) / 2,
                    'center_y': (y1 + y2) / 2,
                    'rotated_img': rotated_img,
                    'ocr_details': [],
                    'M': M 
                })
        return final_results