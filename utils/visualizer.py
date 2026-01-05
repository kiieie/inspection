# utils/visualizer.py
import cv2

def draw_outline_text(img, text, pos, color, font_scale=0.5, thickness=1):
    """설계서 4.2절: 가독성을 위한 검은색 아웃라인이 적용된 텍스트 작성"""
    x, y = pos
    # 1. 아웃라인 (검은색)
    cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), thickness + 2)
    # 2. 본문 텍스트
    cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)

def draw_diagnosis_box(img, box, title, sub_info, status="PASS"):
    """상태별 색상이 적용된 바운딩 박스와 텍스트 오버레이"""
    import config
    color = config.COLORS.get(status, config.COLORS["UNKNOWN"])
    x1, y1, x2, y2 = map(int, box)
    
    cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
    draw_outline_text(img, title, (x1, y1 - 10), color)
    draw_outline_text(img, sub_info, (x1, y2 + 20), (255, 255, 255), font_scale=0.4)