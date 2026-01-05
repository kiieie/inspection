import pytest
import pandas as pd
import os
import cv2
import re
from collections import defaultdict
from main import DiagnosisSystem

# =============================================================================
# [Configuration] 사용자 환경 설정
# =============================================================================
BASE_DIR = "/home/kiie/synology/Projects/R25IA04/Inspection_and_Diagnosis"
EXCEL_FILE = "/home/kiie/synology/Projects/R25IA04/Inspection_point, Labeling_251230.xlsx"
# DG 테스트 및 Mixed 테스트를 위해 Detection 모델 경로 필수
CLASSIFIER_PATH = "models/classifier/weights/best.pt" 

# =============================================================================
# [Helper Functions] AG 진단용 로직
# =============================================================================

def get_type_group_id(label_str):
    """
    라벨을 분석하여 '매칭 그룹 ID'를 반환 (압력계, 온도계 등 통합)
    """
    s = str(label_str).lower()
    if "pressure" in s: return "SHARED_PRESSURE"
    if "temperature" in s: return "SHARED_TEMPERATURE"
    if "thermo-hygro" in s: return "SHARED_THERMO_HYGRO"
    if "ammeter" in s: return "SHARED_AMMETER"
    return s

def sort_by_grid_position(detections):
    """ 같은 타입 내에서 '좌상 -> 우하' 순서로 정렬 (Y축 우선, 후 X축) """
    if not detections: return []
    
    # 1. Y축(Center Y) 기준으로 정렬
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
        
        # Y축 차이가 크지 않으면 같은 행으로 간주
        if abs(det['center_y'] - prev['center_y']) < threshold:
            current_row.append(det)
        else:
            rows.append(current_row)
            current_row = [det]
            # 새 행의 기준으로 임계값 갱신
            h = det['box'][3] - det['box'][1]
            threshold = h * 0.5
            
    if current_row: rows.append(current_row)
    
    final_sorted = []
    for row in rows:
        row.sort(key=lambda x: x['center_x']) # 같은 행 내에서는 X축(좌->우) 정렬
        final_sorted.extend(row)
        
    return final_sorted

def evaluate_gauge_reading(det, excel_row):
    """ 모델 예측값과 엑셀 기준값을 비교하여 상태 판정 """
    try:
        min_val = float(excel_row.get('min_value', 0))
        max_val = float(excel_row.get('max_value', 100))
        norm_min = float(excel_row.get('normal_min', 0))
        norm_max = float(excel_row.get('normal_max', 100))
    except: 
        return 0.0, "Config Error", False

    if not det.get('is_valid', True):
        return 0.0, f"Shape Error ({det.get('status_msg')})", False

    # 비율(ratio)을 실제 값으로 변환
    ratio = det.get('value_ratio', 0.0)
    current_val = min_val + (ratio * (max_val - min_val))
    current_val = round(current_val, 2)
    
    is_normal = norm_min <= current_val <= norm_max
    status = "Normal" if is_normal else "Abnormal"
    return current_val, status, is_normal

# =============================================================================
# [Pytest Fixture] 시스템 초기화
# =============================================================================
@pytest.fixture
def system_setup():
    # DiagnosisSystem 인스턴스 생성
    # classifier_model_path가 있어야 DG/Mixed 테스트 시 self.detector가 로드됨
    system = DiagnosisSystem(BASE_DIR, EXCEL_FILE, classifier_model_path=CLASSIFIER_PATH)
    return system

# =============================================================================
# [Test 1] AG (Analog Gauge) 그룹핑 정밀 진단 (New Code)
# =============================================================================
def test_ag_gauge_inference_grouped(system_setup):
    """
    AG 타입에 대해 엑셀 데이터와 YOLO 검출 결과를 그룹핑 및 정렬하여 매칭 테스트
    """
    df = system_setup.df
    # AG 데이터만 필터링
    ag_df = df[df['inspection_point_type'].str.contains('AG', na=False)].copy()
    if ag_df.empty: 
        pytest.skip("⚠️ 엑셀에 AG 데이터가 없습니다.")

    # 미션_점검명 기준으로 그룹핑
    ag_df['unique_key'] = ag_df['mission_name'].astype(str) + "_" + ag_df['inspection_name'].astype(str)
    grouped = ag_df.groupby('unique_key')

    print(f"\n🚀 [AG Grouped] 총 {len(grouped)}개의 사진 그룹 점검 시작")

    # 위치 표시용 내부 함수
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
        
        # [수정됨] 인자 개수 오류 수정 (base_path 추가)
        img_path = system_setup.get_latest_image(system_setup.base_path, mission, insp_name)
        
        if img_path is None or not os.path.exists(img_path):
            print(f"❌ Image Not Found: {mission}/{insp_name}")
            continue

        # 1. AG Inspector를 통해 이미지 내 모든 게이지 검출
        # (주의: system_setup.ag_inspector가 초기화되어 있어야 함)
        all_detections = system_setup.ag_inspector.inspect_all(img_path)
        
        # 2. YOLO 결과 버킷 분류 (압력계끼리, 온도계끼리)
        yolo_buckets = defaultdict(list)
        for det in all_detections:
            yolo_buckets[get_type_group_id(det['label'])].append(det)

        # 3. 엑셀 데이터 버킷 분류
        excel_buckets = defaultdict(list)
        for idx, row in group.iterrows():
            excel_buckets[get_type_group_id(row['inspection_point_type'])].append((idx, row))

        processed_detections = []
        
        # 4. 그룹별 매칭 및 판정
        for group_id in excel_buckets.keys():
            excel_items = excel_buckets[group_id]
            yolo_items = yolo_buckets[group_id]
            
            # YOLO 검출 결과를 격자(좌상->우하) 순으로 정렬
            sorted_yolo = sort_by_grid_position(yolo_items)
            
            print(f"   🔹 Type Group [{group_id}]: Excel({len(excel_items)}) vs YOLO({len(sorted_yolo)})")

            # 엑셀 순서(보통 입력 순서)와 정렬된 YOLO 순서를 매칭
            for i, (idx, row) in enumerate(excel_items):
                excel_type = row['inspection_point_type']
                fac_2 = str(row.get('facility_2', ''))
                
                if i < len(sorted_yolo):
                    det = sorted_yolo[i]
                    
                    # 값 계산 및 판정
                    val, status, is_normal = evaluate_gauge_reading(det, row)
                    
                    # 시각화를 위한 정보 삽입
                    det['final_value'] = val
                    det['status'] = status
                    det['label_vis'] = excel_type
                    det['facility_info'] = fac_2
                    det['pos_info'] = get_pos_label(i, len(sorted_yolo))
                    
                    icon = "✅" if is_normal else "⚠️"
                    print(f"      [Matched] {fac_2}({det['pos_info']}) : {val} {icon}")
                    
                    processed_detections.append(det)
                else:
                    print(f"      [Missing] {excel_type} ({fac_2}): ❌ Not Detected")

        # 5. 엑셀에 없는데 검출된 잉여 객체 처리
        for g_id, dets in yolo_buckets.items():
            for d in dets:
                if d not in processed_detections:
                    d['final_value'] = "N/A"
                    d['status'] = "Extra"
                    d['facility_info'] = "Unknown"
                    d['pos_info'] = "?"
                    processed_detections.append(d)

        # 6. 결과 시각화 (창 띄우기)
        # 스페이스바를 누르면 다음 사진으로 넘어갑니다.
        system_setup.ag_inspector.show_combined_result(
            img_path, 
            processed_detections, 
            highlight_count=len(group), 
            title=f"AG Result: {insp_name}"
        )

# =============================================================================
# [Test 2] DG (Digital Gauge) 단독 테스트 (Old Code)
# =============================================================================
def test_dg_only_execution(system_setup):
    """
    엑셀에서 DG 타입만 있는 그룹을 찾아 로직(Detect->Crop->OCR)을 수행
    """
    df = system_setup.df
    dg_df = df[df['inspection_point_type'].str.contains('DG', na=False)].copy()
    
    if dg_df.empty:
        pytest.skip("⚠️ 엑셀에 DG 데이터가 없습니다.")

    dg_df['unique_key'] = dg_df['mission_name'].astype(str) + "_" + dg_df['inspection_name'].astype(str)
    grouped = dg_df.groupby('unique_key')

    print(f"\n🚀 [DG Only] 총 {len(grouped)}개의 DG 그룹을 점검합니다.")

    for key, group in grouped:
        first = group.iloc[0]
        mission = first['mission_name']
        insp_name = first['inspection_name']
        
        img_path = system_setup.get_latest_image(system_setup.base_path, mission, insp_name)
        if not img_path:
            print(f"❌ Image Not Found: {mission}/{insp_name}")
            continue

        print(f"\n📸 Checking DG: {os.path.basename(img_path)}")
        
        results_map = {}
        system_setup._process_dg_group(img_path, group, results_map)
        
        print("   ✅ DG Check Complete.")

# =============================================================================
# [Test 3] Mixed (AG + DG) 복합 테스트 (Old Code)
# =============================================================================
def test_mixed_ag_dg_execution(system_setup):
    """
    하나의 사진(그룹) 안에 AG와 DG 타입이 섞여 있는 경우 테스트
    """
    df = system_setup.df
    df['unique_key'] = df['mission_name'].astype(str) + "_" + df['inspection_name'].astype(str)
    grouped = df.groupby('unique_key')
    
    mixed_groups = []
    for key, group in grouped:
        types = group['inspection_point_type'].astype(str).tolist()
        has_ag = any(t.startswith('AG') for t in types)
        has_dg = any(t.startswith('DG') for t in types)
        
        if has_ag and has_dg:
            mixed_groups.append((key, group))

    if not mixed_groups:
        pytest.skip("⚠️ AG와 DG가 섞여 있는(Mixed) 사진 그룹을 찾을 수 없습니다.")

    print(f"\n🚀 [Mixed AG+DG] 총 {len(mixed_groups)}개의 복합 그룹을 점검합니다.")

    for key, group in mixed_groups:
        first = group.iloc[0]
        mission = first['mission_name']
        insp_name = first['inspection_name']
        
        img_path = system_setup.get_latest_image(system_setup.base_path, mission, insp_name)
        if not img_path: 
            print(f"❌ Image Not Found: {mission}/{insp_name}")
            continue

        print(f"\n📸 Checking Mixed: {os.path.basename(img_path)}")
        results_map = {}

        # 1. AG 처리
        ag_subset = group[group['inspection_point_type'].str.startswith('AG')]
        if not ag_subset.empty:
            print(f"   👉 [Step 1] AG Processing ({len(ag_subset)} items)...")
            system_setup._process_ag_group(img_path, ag_subset, results_map)
        
        # 2. DG 처리
        dg_subset = group[group['inspection_point_type'].str.startswith('DG')]
        if not dg_subset.empty:
            print(f"   👉 [Step 2] DG Processing ({len(dg_subset)} items)...")
            system_setup._process_dg_group(img_path, dg_subset, results_map)
        
        print("   ✅ Mixed Check Complete.")

# =============================================================================
# [Helper] 위치 정렬 함수 (기존 유지)
# =============================================================================
def sort_by_grid_position(detections):
    """
    박스 좌표를 기준으로 '위->아래', 같은 줄이면 '좌->우' 순서로 정렬합니다.
    """
    if not detections: return []
    
    detections.sort(key=lambda x: (x['box'][1] + x['box'][3]) / 2)
    
    rows = []
    current_row = []
    
    if detections:
        current_row.append(detections[0])
        h = detections[0]['box'][3] - detections[0]['box'][1]
        threshold = h * 0.5

    for i in range(1, len(detections)):
        det = detections[i]
        prev = current_row[-1]
        
        prev_cy = (prev['box'][1] + prev['box'][3]) / 2
        curr_cy = (det['box'][1] + det['box'][3]) / 2
        
        if abs(curr_cy - prev_cy) < threshold:
            current_row.append(det)
        else:
            rows.append(current_row)
            current_row = [det]
            h = det['box'][3] - det['box'][1]
            threshold = h * 0.5
            
    if current_row: rows.append(current_row)
    
    final_sorted = []
    for row in rows:
        row.sort(key=lambda x: (x['box'][0] + x['box'][2]) / 2) 
        final_sorted.extend(row)
        
    return final_sorted

# =============================================================================
# [Helper] 타입 호환성 체크 함수 (엄격한 접두어 매칭)
# =============================================================================
def is_type_compatible(excel_target, detected_label):
    """
    사용자 요청 룰:
    1. 대소문자 무시
    2. Excel 이름으로 시작해야 함 (startswith)
    3. 단, 파생형(예: -dot)과는 구분되어야 함
       -> LED_red는 LED_red_on과 매칭 (O)
       -> LED_red는 LED_red-dot_on과 매칭 (X)
    """
    e_str = str(excel_target).lower().strip()
    d_str = str(detected_label).lower().strip()
    
    # 1. 길이 체크 (엑셀 타겟이 더 길면 접두어가 될 수 없음)
    if len(e_str) > len(d_str):
        return False
        
    # 2. 접두어 체크 (Starts with)
    if not d_str.startswith(e_str):
        return False
        
    # 3. 경계(Boundary) 체크 - 중요!
    # 정확히 일치하거나, 그 뒤에 상태값(_on, _off 등)이 와야 함.
    # 만약 뒤에 '-'가 오면 그건 다른 타입(예: -dot)이므로 False.
    
    if len(d_str) == len(e_str):
        return True # 완전 일치 (예: Sw_valve == Sw_valve)
        
    # 접두어 바로 뒷글자 확인
    next_char = d_str[len(e_str)]
    
    # 허용하는 구분자: 언더바(_), 공백( ) -> 상태값으로 이어지는 경우
    if next_char in ['_', ' ']:
        return True
        
    # 허용하지 않는 구분자: 하이픈(-), 문자 등 -> 파생 타입인 경우
    # 예: e="led_green", d="led_green-dot" -> next_char는 '-' -> False
    return False

# =============================================================================
# [Test] SW/LED Visual Check (Grouped by Image)
# =============================================================================
def test_sw_led_inference_grouped(system_setup):
    cv2.startWindowThread()

    df = system_setup.df
    
    # 1. SW/LED 관련 데이터만 필터링
    mask = df['inspection_point_type'].str.contains('sw|led', case=False, na=False) | \
           df['model_type'].str.contains('switch|led', case=False, na=False)
    target_df = df[mask].copy()
    
    if target_df.empty:
        pytest.skip("⚠️ No SW/LED data found.")
    
    # 2. 이미지 기준 그룹핑
    target_df['unique_key'] = target_df['mission_name'].astype(str) + "_" + target_df['inspection_name'].astype(str)
    grouped = target_df.groupby('unique_key')
    
    print(f"\n🚀 [SW/LED Visual Check] Total {len(grouped)} groups found.")
    
    display_count = 0

    for key, group in grouped:
        first_row = group.iloc[0]
        mission = first_row['mission_name']
        insp_name = first_row['inspection_name']
        
        img_path = system_setup.get_latest_image(system_setup.base_path, mission, insp_name)
        
        if img_path is None or not os.path.exists(str(img_path)):
            continue
        
        img = cv2.imread(img_path)
        if img is None: continue

        inspector = system_setup 

        # 3. 모델 추론
        results = system_setup.detector(img_path, verbose=False)
        
        yolo_items = []
        
        if results and len(results[0].boxes) > 0:
            for r in results:
                for box in r.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    label_name = r.names[int(box.cls[0])]
                    conf = float(box.conf[0])
                    
                    # [필터] 게이지(AG/DG)는 제외
                    if mission == "SW_LED_inspection":
                        l_lower = label_name.lower()
                        if l_lower.startswith("ag") or l_lower.startswith("dg") or "meter" in l_lower:
                            continue

                    yolo_items.append({
                        "box": [x1, y1, x2, y2],
                        "label": label_name,
                        "conf": conf,
                        "matched_info": None,
                        "is_used": False 
                    })
        
        # 4. 위치 정렬
        sorted_yolo_items = sort_by_grid_position(yolo_items)
        
        # 5. 엑셀 데이터 매칭 (엄격한 타입 체크 + 순서 매칭)
        excel_rows = list(group.iterrows())
        group_fail_count = 0
        
        for idx, row in excel_rows:
            target_spec = str(row['inspection_point_type'])
            model_type = str(row.get('model_type', '')).lower()

            if pd.isna(target_spec): target_spec = "Unknown"
            
            # [필터] 엑셀에서도 게이지 행은 무시
            t_lower = target_spec.lower()
            if mission == "SW_LED_inspection":
                if t_lower.startswith("ag") or t_lower.startswith("dg") or "analog" in model_type:
                    continue

            fac_1 = str(row.get('facility_1', ''))
            fac_2 = str(row.get('facility_2', ''))
            if fac_1.lower() == 'nan': fac_1 = ""
            if fac_2.lower() == 'nan': fac_2 = ""
            
            # [매칭 로직] 정렬된 박스 중, "아직 안 썼고" & "엄격히 호환되는" 첫 번째 박스 찾기
            matched_item = None
            
            for item in sorted_yolo_items:
                if item['is_used']: continue 
                
                # 여기서 개선된 엄격한 비교 함수 사용
                if is_type_compatible(target_spec, item['label']):
                    matched_item = item
                    item['is_used'] = True
                    break
            
            if matched_item:
                detected_label = matched_item['label']
                
                try:
                    is_pass, reason, match_details = inspector.check_compliance(target_spec, [detected_label], mission)
                except ValueError:
                    is_pass, reason = inspector.check_compliance(target_spec, [detected_label], mission)

                if not is_pass: group_fail_count += 1
                
                matched_item['matched_info'] = {
                    'excel_target': target_spec,
                    'facility_1': fac_1,
                    'facility_2': fac_2,
                    'status': "OK" if is_pass else "FAIL",
                    'reason': reason
                }
            else:
                group_fail_count += 1
                # print(f"❌ Missing: {target_spec} ({fac_2})")

        # 6. 시각화
        final_img = img.copy()

        # (1) 타이틀
        title_text = f"[{mission}] {os.path.basename(img_path)}"
        cv2.putText(final_img, title_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        res_str = "ALL PASS" if group_fail_count == 0 else f"FAIL ({group_fail_count})"
        color_res = (0, 255, 0) if group_fail_count == 0 else (0, 0, 255)
        info_text = f"Result: {res_str}"
        cv2.putText(final_img, info_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color_res, 2)

        # (3) 박스 그리기
        for item in sorted_yolo_items:
            x1, y1, x2, y2 = item['box']
            label = item['label']
            info = item['matched_info']
            
            box_color = (0, 255, 255) 
            top_text = f"Det: {label}"
            fac1_txt, fac2_txt = "", ""
            
            if info:
                top_text = f"Exp: {info['excel_target']} / Fnd: {label}"
                fac1_txt = info['facility_1']
                fac2_txt = info['facility_2']
                
                if info['status'] == "OK":
                    box_color = (0, 255, 0)
                else:
                    box_color = (0, 0, 255)
            
            if "nok" in label.lower():
                box_color = (0, 0, 255)
                top_text += " (NOK)"

            cv2.rectangle(final_img, (x1, y1), (x2, y2), box_color, 2)
            
            text_y_top = y1 - 10 if y1 - 10 > 10 else y1 + 20
            cv2.putText(final_img, top_text, (x1, text_y_top), cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 2)
            
            text_y_bottom = y2 + 20
            line_spacing = 18
            
            if fac1_txt:
                cv2.putText(final_img, fac1_txt, (x1, text_y_bottom), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (220, 220, 220), 1)
                text_y_bottom += line_spacing
            
            if fac2_txt:
                cv2.putText(final_img, fac2_txt, (x1, text_y_bottom), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (220, 220, 220), 1)

        window_name = f"Test Result"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 960, 540)
        cv2.imshow(window_name, final_img)
        
        print(f"👉 Displaying: {title_text}")
        display_count += 1
        
        key = cv2.waitKey(0)
        cv2.destroyAllWindows()
        
        if key == 27:
            print("🛑 Test aborted by user.")
            break

    if display_count == 0:
        print("\n⚠️ 경고: 표시된 이미지가 0개입니다.")