"""2단계 레이블 매칭 로직"""
from config.domain import LABEL_MAP


def normalize_text(text):
    return str(text).lower().strip().replace(" ", "_")


def get_type_group_id(label_str):
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

    norm_e = e_str.replace("-", "").replace("_", "")
    norm_d = d_str.replace("-", "").replace("_", "")

    if norm_e == norm_d: return True

    suffixes = ["ok", "nok", "na"]
    for s in suffixes:
        if norm_d == norm_e + s: return True

    # LABEL_MAP 확인
    if excel_target in LABEL_MAP:
        mapping = LABEL_MAP[excel_target]
        items = mapping if isinstance(mapping, list) else [mapping]
        for m in items:
            m_norm = m.lower().replace("-", "").replace("_", "")
            if norm_d == m_norm: return True
            for s in suffixes:
                if norm_d == m_norm + s: return True

    # Fuzzy: 접두어 제거 후 핵심 키워드 포함 여부
    prefixes = ["dg_", "ag_", "sw_", "led_", "etc_"]
    target_core = norm_e
    for p in prefixes:
        if target_core.startswith(p):
            target_core = target_core[len(p):]
            break

    if len(target_core) > 3 and target_core in d_str:
        return True

    return False


def evaluate_gauge_reading(det, excel_row):
    """AG ratio → 물리값 변환, DG value → 직접 평가"""
    try:
        min_v = float(excel_row.get('min_value', 0))
        max_v = float(excel_row.get('max_value', 100))
        norm_min = float(excel_row.get('normal_min_value', 0))
        norm_max = float(excel_row.get('normal_max_value', 100))

        if 'value' in det and det['value'] is not None:
            try:
                current_val = float(det['value'])
            except ValueError:
                return det['value'], "Unknown", True
        else:
            if 'value_ratio' not in det:
                return None, "No Value", False
            ratio = det.get('value_ratio', 0.0)
            current_val = min_v + (ratio * (max_v - min_v))

        current_val = round(current_val, 2)
        is_normal = norm_min <= current_val <= norm_max
        return current_val, "PASS" if is_normal else "FAIL", is_normal
    except Exception:
        return getattr(det, 'get', lambda k: None)('value'), "Error", False


def sort_by_x_priority(detections):
    """X축(가로) 좌표 기준 정렬, 동일 X는 Y로 보조 정렬"""
    if not detections:
        return []
    detections.sort(key=lambda d: (
        (d['box'][0] + d['box'][2]) / 2,
        (d['box'][1] + d['box'][3]) / 2,
    ))
    return detections


def sort_by_grid_position(detections):
    """Y축 우선, 행 단위 X 정렬 (좌상→우하)"""
    if not detections:
        return []
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
            if abs(curr_y - prev_y) < threshold:
                current_row.append(det)
            else:
                rows.append(current_row)
                current_row = [det]
    if current_row:
        rows.append(current_row)
    final_sorted = []
    for row in rows:
        row.sort(key=lambda x: (x['box'][0] + x['box'][2]) / 2)
        final_sorted.extend(row)
    return final_sorted
