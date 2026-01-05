import pytest
import pandas as pd
import cv2
import re
from main import DiagnosisSystem
from collections import defaultdict

POS_MAP = {
    "좌": "Left", "중": "Center", "우": "Right",
    "좌상": "Top-Left", "우상": "Top-Right",
    "좌하": "Bot-Left", "우하": "Bot-Right"
}

# ---------------------------------------------------------------------
# [Helper] 타입 그룹 ID 반환 (통합 매칭용)
# ---------------------------------------------------------------------
def get_type_group_id(label_str):
    """
    라벨을 분석하여 '매칭 그룹 ID'를 반환
    예: AG_pressure02_... -> 'SHARED_PRESSURE'
    예: AG_temperature... -> 'SHARED_TEMPERATURE'
    """
    s = str(label_str).lower()
    
    # 1. 압력계 통합 (Pressure 01~99 모두 같은 타입으로 간주)
    if "pressure" in s:
        # 필요하다면 pressure01과 pressure02를 나눌 수도 있지만,
        # 사용자님 요청(레인지 같음)에 따라 통일합니다.
        # 혹시 스펙이 다른 압력계가 있다면 여기서 elif로 분기하면 됩니다.
        return "SHARED_PRESSURE"
    
    # 2. 온도계 통합
    if "temperature" in s:
        return "SHARED_TEMPERATURE"
        
    # 3. 온습도계
    if "thermo-hygro" in s:
        return "SHARED_THERMO_HYGRO"
    
    # 4. 전류계
    if "ammeter" in s:
        return "SHARED_AMMETER"

    # 매핑되지 않은 경우 자기 자신 반환
    return s

# ---------------------------------------------------------------------
# [Helper] 정렬 로직 (Grid Sort)
# ---------------------------------------------------------------------
def sort_by_grid_position(detections):
    """ 같은 타입 내에서 '좌상 -> 우하' 순서로 정렬 """
    if not detections: return []
    
    # 1. Y축 정렬
    detections.sort(key=lambda x: x['center_y'])
    
    rows = []
    current_row = []
    
    if detections:
        current_row.append(detections[0])
        # 동적 임계값: 첫 객체 높이의 50%
        h = detections[0]['box'][3] - detections[0]['box'][1]
        threshold = h * 0.5

    for i in range(1, len(detections)):
        det = detections[i]
        prev = current_row[-1]
        
        if abs(det['center_y'] - prev['center_y']) < threshold:
            current_row.append(det)
        else:
            rows.append(current_row)
            current_row = [det]
            h = det['box'][3] - det['box'][1]
            threshold = h * 0.5
            
    if current_row: rows.append(current_row)
    
    final_sorted = []
    for row in rows:
        row.sort(key=lambda x: x['center_x']) # X축 정렬
        final_sorted.extend(row)
        
    return final_sorted

# ---------------------------------------------------------------------
# [Helper] 값 계산 함수
# ---------------------------------------------------------------------
def evaluate_gauge_reading(det, excel_row):
    try:
        min_val = float(excel_row.get('min_value', 0))
        max_val = float(excel_row.get('max_value', 100))
        norm_min = float(excel_row.get('normal_min', 0))
        norm_max = float(excel_row.get('normal_max', 100))
    except: return None, "Config Error", False

    if not det.get('is_valid', True):
        return 0.0, f"Shape Error ({det.get('status_msg')})", False

    ratio = det.get('value_ratio', 0.0)
    current_val = min_val + (ratio * (max_val - min_val))
    current_val = round(current_val, 2)
    
    is_normal = norm_min <= current_val <= norm_max
    status = "Normal" if is_normal else "Abnormal"
    return current_val, status, is_normal

# ---------------------------------------------------------------------
# 메인 테스트 로직
# ---------------------------------------------------------------------
@pytest.fixture
def system_setup():
    BASE_DIR = "/home/kiie/synology/Projects/R25IA04/Inspection_and_Diagonosis"
    EXCEL_FILE = "Inspection_point, Labeling_251215.xlsx"
    return DiagnosisSystem(BASE_DIR, EXCEL_FILE)

def test_ag_gauge_inference_grouped(system_setup):
    df = system_setup.df
    ag_df = df[df['inspection_point_type'].str.contains('AG', na=False)].copy()
    if ag_df.empty: pytest.skip("No AG Data")

    ag_df['unique_key'] = ag_df['mission_name'].astype(str) + "_" + ag_df['inspection_name'].astype(str)
    grouped = ag_df.groupby('unique_key')

    print(f"\n총 {len(grouped)}개의 사진 그룹 점검 시작")

    # [Helper] 위치 라벨 생성 함수 (내부 정의)
    def get_pos_label(idx, total):
        if total == 1: return "mi"
        if total == 2: return ["le", "ri"][idx]
        if total == 3: return ["le", "mi", "ri"][idx]
        return f"pos-{idx+1}"

    for key, group in grouped:
        first_row = group.iloc[0]
        mission = first_row['mission_name']
        insp_name = first_row['inspection_name']
        
        print(f"\n" + "="*80)
        print(f"📸 Group: {mission} | {insp_name} ({len(group)} items)")
        
        img_path = system_setup.get_latest_image(mission, insp_name)
        if img_path is None:
            print("❌ Image Not Found")
            continue

        # 1. 전체 검출 및 버킷 분류
        all_detections = system_setup.ag_inspector.inspect_all(img_path)
        yolo_buckets = defaultdict(list)
        for det in all_detections:
            yolo_buckets[get_type_group_id(det['label'])].append(det)

        excel_buckets = defaultdict(list)
        for idx, row in group.iterrows():
            excel_buckets[get_type_group_id(row['inspection_point_type'])].append((idx, row))

        processed_detections = []
        
        # 2. 그룹별 매칭
        for group_id in excel_buckets.keys():
            excel_items = excel_buckets[group_id]
            yolo_items = yolo_buckets[group_id]
            
            # 격자 정렬 (Row -> Col)
            sorted_yolo = sort_by_grid_position(yolo_items)
            
            print(f"   🔹 Type Group [{group_id}]: Excel {len(excel_items)} vs YOLO {len(sorted_yolo)}")

            for i, (idx, row) in enumerate(excel_items):
                excel_type = row['inspection_point_type']
                
                # [추가] facility_2 정보 가져오기
                fac_2 = str(row.get('facility_2', ''))
                
                if i < len(sorted_yolo):
                    det = sorted_yolo[i]
                    
                    val, status, is_normal = evaluate_gauge_reading(det, row)
                    
                    # [추가] 정보 저장
                    det['final_value'] = val
                    det['status'] = status
                    det['label_vis'] = excel_type
                    det['facility_info'] = fac_2
                    det['pos_info'] = get_pos_label(i, len(sorted_yolo)) # le, mi, ri 생성
                    
                    icon = "✅" if is_normal else "⚠️"
                    print(f"      [Target] {fac_2}({det['pos_info']}) : {val} {icon}")
                    
                    processed_detections.append(det)
                else:
                    print(f"      [Target] {excel_type} ({fac_2}): ❌ Missing")

        # 3. 잉여 객체 처리 (Optional)
        for g_id, dets in yolo_buckets.items():
            for d in dets:
                if d not in processed_detections:
                    d['final_value'] = "N/A"
                    d['status'] = "Extra"
                    d['facility_info'] = "Unknown"
                    d['pos_info'] = "?"
                    processed_detections.append(d)

        system_setup.ag_inspector.show_combined_result(
            img_path, 
            processed_detections, 
            highlight_count=len(group), 
            title=f"Result: {insp_name}"
        )