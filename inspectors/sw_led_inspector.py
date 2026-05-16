"""
프로그램명: 전수 시각화 지원 SW/LED 인스펙터 (sw_led_inspector.py)
버전: v2.4.0 (2026-01-06)
변경 사항: 
- [Feature] 타겟 필터링 없이 모델이 탐지한 모든(All) 객체를 반환하는 기능 추가
"""
import cv2
from loguru import logger

class SW_LED_Inspector:
    def __init__(self):
        # 상태 정규화 매핑
        self.status_map = {
            "opend": "opened", "opened": "opened", "closed": "closed",
            "on": "on", "off": "off", "right": "right", "left": "left", "center": "center"
        }

    def check_status_compliance(self, matched_label, excel_type):
        """AI 라벨과 엑셀 타입 간의 상태 일치 여부 판정"""
        m_label = matched_label.lower()
        e_type = excel_type.lower()
        if e_type in m_label: return True, "Match"
        for key, val in self.status_map.items():
            if key in e_type:
                if val in m_label: return True, f"Status Match ({val})"
                else: return False, f"Status Mismatch (Exp: {val})"
        return False, "Type Mismatch"

    def get_all_detections(self, system_setup, img_path):
        """이미지 내 모든 탐지 객체를 수집하고 타겟 여부를 표시함"""
        raw_res = system_setup.detector(img_path, verbose=False)[0]
        all_items = []
        for box in raw_res.boxes:
            label = raw_res.names[int(box.cls[0])]
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            # SW/LED로 시작하면 타겟(True), 아니면 일반 객체(False)
            is_target = label.startswith("Sw") or label.startswith("LED")
            all_items.append({
                'label': label,
                'box': [x1, y1, x2, y2],
                'area': (x2 - x1) * (y2 - y1),
                'center_x': (x1 + x2) / 2,
                'is_target': is_target,
                'used': False
            })
        return all_items