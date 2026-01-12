"""
프로그램명: 정밀 매칭 및 진단 로직 유틸리티 (utils/matching.py)
버전: v1.4 (2026-01-05)
주요 변경 사항:
- [Error Fix] get_type_group_id, evaluate_gauge_reading 함수 추가
- [요구사항 4] config.LABEL_MAP을 참조하여 모델 라벨과 엑셀 타입 매칭
"""

import config
from loguru import logger

def normalize_text(text):
    """텍스트 소문자화 및 공백 제거"""
    return str(text).lower().strip().replace(" ", "_")

def get_type_group_id(label_str):
    """라벨을 분석하여 '매칭 그룹 ID'를 반환 (압력계, 온도계 등 통합)"""
    s = normalize_text(label_str)
    if any(k in s for k in ["dg", "digital", "meter"]): return "SHARED_DIGITAL"
    if "pressure" in s: return "SHARED_PRESSURE"
    if "temperature" in s: return "SHARED_TEMPERATURE"
    if "thermo-hygro" in s: return "SHARED_THERMO_HYGRO"
    if "ammeter" in s: return "SHARED_AMMETER"
    return s

def is_type_compatible(excel_target, detected_label):
    e_str = str(excel_target).lower().strip()
    d_str = str(detected_label).lower().strip()
    
    # 1. LABEL_MAP 확인
    if excel_target in config.LABEL_MAP:
        mapping = config.LABEL_MAP[excel_target]
        # 리스트일 경우와 단일 문자열일 경우 모두 대응
        if isinstance(mapping, list):
            if any(d_str.startswith(m.lower()) for m in mapping): return True
        else:
            if d_str.startswith(mapping.lower()): return True

    # 2. 기본 매칭
    return d_str.startswith(e_str.replace(" ", "_"))

def sort_by_grid_position(detections):
    """Y축 우선 정렬 후 행 단위 X축 정렬 (좌상->우하)"""
    if not detections: return []
    # Center Y 기준 정렬
    detections.sort(key=lambda x: (x['box'][1] + x['box'][3]) / 2)
    rows, current_row = [], []
    if detections:
        current_row.append(detections[0])
        h = detections[0]['box'][3] - detections[0]['box'][1]
        threshold = h * 0.5
        for i in range(1, len(detections)):
            det = detections[i]
            prev_y = (current_row[-1]['box'][1] + current_row[-1]['box'][3]) / 2
            curr_y = (det['box'][1] + det['box'][3]) / 2
            if abs(curr_y - prev_y) < threshold: current_row.append(det)
            else:
                rows.append(current_row); current_row = [det]
    if current_row: rows.append(current_row)
    final_sorted = []
    for row in rows:
        row.sort(key=lambda x: (x['box'][0] + x['box'][2]) / 2)
        final_sorted.extend(row)
    return final_sorted

# [utils/matching.py]
def evaluate_gauge_reading(det, excel_row):
    """
    AG 게이지의 ratio(0~1)를 실제 물리 수치로 변환
    """
    try:
        # 엑셀의 컬럼명 확인 (파일에 따라 normal_min_value 또는 normal_min 일 수 있음)
        min_v = float(excel_row.get('min_value', 0))
        max_v = float(excel_row.get('max_value', 100))
        norm_min = float(excel_row.get('normal_min_value', 0))
        norm_max = float(excel_row.get('normal_max_value', 100))
        
        # AGInspector가 계산한 바늘 위치 비율 (0.0 ~ 1.0)
        ratio = det.get('value_ratio', 0.0)
        
        # 실제 값 계산: Min + (Ratio * 범위)
        current_val = min_v + (ratio * (max_v - min_v))
        current_val = round(current_val, 2)
        
        is_normal = norm_min <= current_val <= norm_max
        status = "PASS" if is_normal else "FAIL"
        
        return current_val, status, is_normal
    except Exception as e:
        return 0.0, f"Error: {e}", False
    
"""
프로그램명: 정밀 공간 매칭 유틸리티 (utils/matching.py)
버전: v2.0 (2026-01-06)
주요 변경 사항:
- [핵심 변경] Y축 우선 정렬에서 X축(가로) 최우선 정렬로 변경
- [로직] 엑셀의 '위쪽 항목 = 이미지의 왼쪽 객체' 원칙을 준수함
"""

def sort_by_x_priority(detections):
    """
    탐지된 객체들을 X축(가로) 좌표 기준으로 정렬합니다.
    X좌표가 동일하거나 매우 유사할 경우에만 Y좌표를 보조 지표로 사용합니다.
    """
    if not detections:
        return []

    # 1. 중심점 계산 및 X축 기준 오름차순 정렬 (좌 -> 우)
    # detections 리스트의 각 항목은 'box' [x1, y1, x2, y2]를 가지고 있어야 합니다.
    detections.sort(key=lambda d: (
        (d['box'][0] + d['box'][2]) / 2, # Primary: Center X
        (d['box'][1] + d['box'][3]) / 2  # Secondary: Center Y
    ))
    
    # 2. 정렬된 결과 반환
    # 이제 리스트의 0번 인덱스가 이미지의 가장 왼쪽 객체가 됩니다.
    return detections