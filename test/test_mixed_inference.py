"""
프로그램명: 산업용 설비 복합 진단 테스트 (Mixed Inference Test)
버전: v1.9.9 (2026-01-06)
변경 사항:
- [Depth Logic] 엑셀의 (rear) 태그와 객체 면적(Area)을 결합한 전후방 자동 매칭
- [X-Priority] 각 Depth 그룹 내에서 X축 좌표 기준 좌->우 매칭 (엑셀 위쪽=이미지 왼쪽)
- [Logic Reuse] AGInspector의 보정 로직 및 DiagnosisSystem 이미지 로더 재사용
- [UI Policy] 매칭 시 PASS(초록 박스) 고정, 수치 이상 시 텍스트 적색 강조
"""

import pytest
import cv2
import os
import config
import numpy as np
from main import DiagnosisSystem
from utils.matching import evaluate_gauge_reading, is_type_compatible
from utils.visualizer import (
    draw_diagnosis_box, 
    draw_summary_table, 
    draw_outline_text, 
    show_navigation_window,
    draw_text_with_bg, # 새로 추가됨
    draw_stack_text    # 새로 추가됨
)
import concurrent.futures
from loguru import logger

@pytest.fixture
def system_setup():
    """시스템 인스턴스를 단 한 번 생성하여 테스트 간 재사용"""
    return DiagnosisSystem()

# =============================================================================
# [Test 1] AG (Analog Gauge) 그룹핑 정밀 진단
# =============================================================================
"""
프로그램명: 아날로그 게이지 통합 진단 테스트 (test_ag_gauge_inference_grouped)
버전: v2.0.1 (2026-01-06)
변경 사항:
- [Depth Logic] 엑셀의 (rear) 태그와 객체 면적(Area)을 이용한 전후방 매칭
- [Logic Fix] 뎁스 풀(Pool) 내에서 라벨 호환성(is_type_compatible) 체크로 Expected 값 일치
- [X-Priority] 각 그룹 내 X축 좌표 우선 정렬 (엑셀 위쪽 = 이미지 왼쪽)
- [UI Policy] 매칭 시 PASS(초록 박스) 고정, 수치 이상 시 텍스트 적색, 바늘 포인트 표시
"""

def test_ag_gauge_inference_grouped(system_setup):
    import cv2
    import os
    import config
    from loguru import logger
    from utils.matching import is_type_compatible, evaluate_gauge_reading
    from utils.visualizer import draw_diagnosis_box, draw_summary_table, draw_outline_text

    # 1. AG 타입 데이터 필터링 및 그룹화
    df = system_setup.df
    ag_df = df[df['inspection_point_type'].str.contains('AG', na=False)].copy()
    if ag_df.empty:
        logger.warning("⚠️ 엑셀에 AG 데이터가 없습니다.")
        return

    # 미션_점검명 기준으로 그룹핑하여 리스트화 (양방향 이동용)
    ag_df['unique_key'] = ag_df['mission_name'].astype(str) + "_" + ag_df['inspection_name'].astype(str)
    grouped_list = list(ag_df.groupby('unique_key'))
    
    idx = 0
    while 0 <= idx < len(grouped_list):
        key, group = grouped_list[idx]
        first = group.iloc[0]
        
        # 이미지 경로 획득 (시스템 클래스 로더 재사용)
        img_path = system_setup.get_latest_image(system_setup.base_path, first['mission_name'], first['inspection_name'])
        if not img_path: 
            logger.error(f"❌ 이미지를 찾을 수 없습니다: {key}")
            idx += 1; continue

        img = cv2.imread(img_path)
        final_img = img.copy()

        # [Step 1] Inference: AGInspector 통합 추론 (Warping 및 Ratio 포함)
        all_detections = system_setup.ag_inspector.inspect_all(img_path)
        
        # [Step 2] Label Conversion (현재 그룹 대상 최적화 필터링)
        expected_types = group['inspection_point_type'].unique()
        for det in all_detections:
            for target_type in expected_types:
                ai_labels = config.LABEL_MAP.get(target_type, [])
                if det['label'] in (ai_labels if isinstance(ai_labels, list) else [ai_labels]):
                    det['label'] = target_type
                    det['used'] = False
                    break

        # ---------------------------------------------------------------------
        # [Step 3] Depth & X-Priority Matching Logic [사용자 요청 반영]
        # ---------------------------------------------------------------------
        # 3.1 엑셀 분류 (Front vs Rear)
        excel_rear = group[group['facility_2'].str.contains('(rear)', na=False, regex=False)]
        excel_front = group[~group['facility_2'].str.contains('(rear)', na=False, regex=False)]
        
        # 3.2 탐지 객체 면적($Area$) 기준 정렬 및 분리 (KeyError 방지 포함)
        all_detections.sort(key=lambda d: d.get('area', (d['box'][2]-d['box'][0])*(d['box'][3]-d['box'][1])), reverse=True)
        
        num_front = len(excel_front)
        det_front_pool = all_detections[:num_front]
        det_rear_pool = all_detections[num_front:]

        # 3.3 각 풀 내에서 X축(좌->우) 정렬
        det_front_pool.sort(key=lambda d: d['center_x'])
        det_rear_pool.sort(key=lambda d: d['center_x'])
        
        summary_list = []

        # 3.4 뎁스(Front/Rear) 내에서 라벨 호환성을 확인하며 매칭 수행
        for depth_name, ex_bucket, det_bucket in [("Front", excel_front, det_front_pool), ("Rear", excel_rear, det_rear_pool)]:
            available_dets = list(det_bucket)
            
            for _, row in ex_bucket.iterrows():
                target = str(row['inspection_point_type'])
                matched = None
                
                # 라벨이 호환되는 객체를 X축 순서대로 탐색하여 매칭
                for i, det in enumerate(available_dets):
                    if not det.get('used', False) and is_type_compatible(target, det['label']):
                        matched = det
                        det['used'] = True
                        available_dets.pop(i) # 중복 매칭 방지
                        break
                
                summary_list.append({"type": target, "found": matched is not None})
                
                if matched:
                    # 수치 계산 및 시각화
                    val, _, is_norm = evaluate_gauge_reading(matched, row)
                    draw_diagnosis_box(final_img, matched['box'], row, matched['label'], status="PASS", value=val, is_normal=is_norm)
                    
                    # 바늘 포인트(Keypoints) 표시
                    if 'keypoints' in matched:
                        for kp in matched['keypoints']:
                            if kp[2] > 0.5: cv2.circle(final_img, (int(kp[0]), int(kp[1])), 4, (0, 0, 255), -1)

        # [Step 4] Unmatched: 매칭 안 된 객체 노란색 표시
        for det in all_detections:
            if not det.get('used'):
                x1, y1, x2, y2 = map(int, det['box'])
                cv2.rectangle(final_img, (x1, y1), (x2, y2), config.COLORS["UNKNOWN"], 2)
                draw_outline_text(final_img, f"Unk: {det['label']}", (x1, y1 - 10), config.COLORS["UNKNOWN"], 0.45)

        # [Step 5] 결과 출력 및 키 네비게이션 (A:이전, D:다음, Q:종료)
        draw_summary_table(final_img, summary_list)
        win_name = f"{first.get('site','Unk')}/{first['mission_name']}/{first['inspection_name']}"
        
        cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
        h, w = final_img.shape[:2]
        target_width = 1920
        target_height = int(h * (target_width / w))
        cv2.resizeWindow(win_name, target_width, target_height)
        cv2.imshow(win_name, final_img)
        
        key = cv2.waitKey(0) & 0xFF
        if key == ord('q') or key == ord('Q'): break
        elif key == ord('a') or key == ord('A'): idx = max(0, idx - 1)
        else: idx += 1
        cv2.destroyWindow(win_name)

"""
프로그램명: 디지털 게이지 통합 진단 테스트 (v2.3.0)
변경 사항:
- [UI] 창 제목을 AG와 동일하게 "사이트/미션/점검명" 형식으로 통일 [사용자 요청]
- [Visualization] OCR 인식된 텍스트를 원본 이미지의 실제 위치에 오버랩 [사용자 요청]
- [Logic] 회전 역행렬을 이용한 OCR 좌표 복원 로직 추가
"""

"""
프로그램명: 디지털 게이지 통합 진단 테스트 (test_dg_gauge_inference_grouped)
버전: v2.3.1 (2026-01-06)
수정 사항: 
- [ValueError 해결] analyze_crop의 5개 반환값(M 포함) 정상 수신
- [UI] 창 제목 AG 형식으로 통일 및 OCR 텍스트 원본 위치 오버랩
"""

def test_dg_gauge_inference_grouped(system_setup):
    import cv2
    import numpy as np
    import config
    from utils.matching import is_type_compatible, evaluate_gauge_reading
    from utils.visualizer import draw_diagnosis_box, draw_summary_table, draw_outline_text

    df = system_setup.df
    dg_df = df[df['inspection_point_type'].str.contains('DG', na=False)].copy()
    if dg_df.empty: return

    dg_df['unique_key'] = dg_df['mission_name'].astype(str) + "_" + dg_df['inspection_name'].astype(str)
    grouped_list = list(dg_df.groupby('unique_key'))
    
    idx = 0
    while 0 <= idx < len(grouped_list):
        key, group = grouped_list[idx]
        first = group.iloc[0]
        img_path = system_setup.get_latest_image(system_setup.base_path, first['mission_name'], first['inspection_name'])
        if not img_path: idx += 1; continue

        img = cv2.imread(img_path)
        final_img = img.copy()

        # [Step 1] DG 탐지 및 필터링 ("DG" 시작 라벨)
        raw_detections = system_setup.detector(img_path, verbose=False)[0]
        dg_candidates = []
        for box in raw_detections.boxes:
            label = raw_detections.names[int(box.cls[0])]
            if label.startswith("DG"):
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                dg_candidates.append({
                    'label': label, 'box': [x1, y1, x2, y2],
                    'area': (x2 - x1) * (y2 - y1), 'center_x': (x1 + x2) / 2, 'used': False
                })

        # [Step 2] Depth & X-Priority Sorting
        excel_rear = group[group['facility_2'].str.contains('(rear)', na=False, regex=False)]
        excel_front = group[~group['facility_2'].str.contains('(rear)', na=False, regex=False)]
        dg_candidates.sort(key=lambda d: d['area'], reverse=True)
        det_front_pool = sorted(dg_candidates[:len(excel_front)], key=lambda d: d['center_x'])
        det_rear_pool = sorted(dg_candidates[len(excel_front):], key=lambda d: d['center_x'])
        
        summary_list = []

        # [Step 3] Matching & Overlap Visualization
        for depth_name, ex_bucket, det_bucket in [("Front", excel_front, det_front_pool), ("Rear", excel_rear, det_rear_pool)]:
            available_dets = list(det_bucket)
            for _, row in ex_bucket.iterrows():
                target = str(row['inspection_point_type'])
                matched = None
                for i, det in enumerate(available_dets):
                    if is_type_compatible(target, det['label']):
                        matched = det; det['used'] = True; available_dets.pop(i); break
                
                if matched:
                    # [Fix] 5개의 반환값을 모두 명시적으로 받음
                    x1, y1, x2, y2 = matched['box']
                    crop = img[y1:y2, x1:x2]
                    val, _, ocr_details, rotated_img, M = system_setup.dg_inspector.analyze_crop(crop)
                    
                    val_out, _, is_norm = evaluate_gauge_reading({'value': val, 'label': matched['label']}, row)
                    draw_diagnosis_box(final_img, matched['box'], row, matched['label'], status="PASS", value=val_out, is_normal=is_norm)
                    
                    # [사용자 요청] OCR 결과 원본 위치 오버랩 로직
                    if ocr_details and M is not None:
                        M_inv = cv2.invertAffineTransform(M)
                        for item in ocr_details:
                            pts = np.array(item['box'], dtype=np.float32)
                            center_ocr = np.mean(pts, axis=0)
                            # 회전 역행렬을 이용해 원본 크롭 좌표로 복원
                            orig_crop_pt = cv2.transform(np.array([[center_ocr]]), M_inv)[0][0]
                            global_x, global_y = int(orig_crop_pt[0] + x1), int(orig_crop_pt[1] + y1)
                            cv2.putText(final_img, item['text'], (global_x, global_y), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
                    
                    summary_list.append({"type": target, "found": True})
                else:
                    summary_list.append({"type": target, "found": False})

        # [Step 4] 창 제목 통일 (사이트/미션/점검명) 및 출력
        draw_summary_table(final_img, summary_list)
        win_name = f"{first.get('site','Unk')}/{first['mission_name']}/{first['inspection_name']}"
        cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
        h, w = final_img.shape[:2]
        target_width = 1920
        target_height = int(h * (target_width / w))
        cv2.resizeWindow(win_name, target_width, target_height)
        cv2.imshow(win_name, final_img)
        
        key = cv2.waitKey(0) & 0xFF
        if key == ord('q'): break
        elif key == ord('a'): idx = max(0, idx - 1)
        else: idx += 1
        cv2.destroyWindow(win_name)

def test_integrated_inspection_grouped(system_setup):
    """
    [v5.1.0] "Left-First" 우선순위 적용
    - 상황별 정렬 전략 (Adaptive Sort):
      1. 엑셀에 '(rear)'가 명시된 경우 -> 크기(Area)순 정렬 (원근감 반영)
      2. 일반적인 경우 -> X축(Center_X)순 정렬 (왼쪽부터 차례대로 매칭)
    - 결과: 나란히 있는 객체는 왼쪽부터, 앞뒤로 있는 객체는 앞쪽부터 매칭됨
    """
    import cv2
    import numpy as np
    import config
    from collections import Counter
    from loguru import logger
    from utils.matching import is_type_compatible, evaluate_gauge_reading
    from utils.visualizer import draw_diagnosis_box, draw_summary_table, draw_outline_text

    # 1. 데이터 로드 및 그룹핑
    df = system_setup.df
    df['unique_key'] = df['mission_name'].astype(str) + "_" + df['inspection_name'].astype(str)
    # 엑셀 순서 유지를 위해 sort=False
    grouped_list = list(df.groupby('unique_key', sort=False))
    
    print(f"\n🚀 [SYSTEM] 총 점검할 그룹 수: {len(grouped_list)}개")
    if len(grouped_list) == 0: return

    idx = 0
    while 0 <= idx < len(grouped_list):
        key, group = grouped_list[idx]
        first = group.iloc[0]
        
        # 2. 이미지 로드
        img_path = system_setup.get_latest_image(system_setup.base_path, first['mission_name'], first['inspection_name'])
        if not img_path: 
            idx += 1; continue

        img = cv2.imread(img_path)
        if img is None: idx += 1; continue
        final_img = img.copy()

        # [Step 1] AI 모델 통합 추론
        ag_dets = system_setup.ag_inspector.inspect_all(img_path)
        for d in ag_dets: d['source'] = "Pose"
        dg_dets = system_setup.dg_inspector.inspect_all(img_path)
        for d in dg_dets: d['source'] = "OCR"
        raw_cls_dets = system_setup.sw_led_inspector.get_all_detections(system_setup, img_path)
        cls_dets = [d for d in raw_cls_dets if not (d['label'].startswith('AG_') or d['label'].startswith('DG_'))]
        for d in cls_dets: d['source'] = "Cls"
        
        all_detections = ag_dets + dg_dets + cls_dets

        # [Step 2] 라벨 매핑 및 전처리
        expected_types = group['inspection_point_type'].unique()
        for det in all_detections:
            if "extingisher" in det['label']: 
                det['label'] = det['label'].replace("extingisher", "extinguisher")
            
            if det['label'] in expected_types: 
                det['used'] = False; continue

            matched_target = None
            for target_type in expected_types:
                candidates = config.LABEL_MAP.get(target_type, [])
                if not isinstance(candidates, list): candidates = [candidates]
                for cand in candidates:
                    if cand == det['label'] or (cand in det['label']): 
                        matched_target = target_type; break
                if matched_target: break
            
            if matched_target: det['label'] = matched_target
            det['used'] = False

        # ---------------------------------------------------------------------
        # [Step 3] 라벨별(Per-Label) 할당 및 정렬 전략 적용 (핵심 수정)
        # ---------------------------------------------------------------------
        excel_rear = group[group['facility_2'].str.contains('(rear)', na=False, regex=False)]
        excel_front = group[~group['facility_2'].str.contains('(rear)', na=False, regex=False)]
        
        front_reqs = Counter(excel_front['inspection_point_type'])
        rear_reqs = Counter(excel_rear['inspection_point_type'])
        
        # 탐지된 후보군 라벨별 그룹화
        candidates = [d for d in all_detections if d['label'] in expected_types]
        candidates_by_label = {}
        for d in candidates:
            candidates_by_label.setdefault(d['label'], []).append(d)
            
        det_front_pool = []
        det_rear_pool = []
        
        for label, dets in candidates_by_label.items():
            n_front = front_reqs.get(label, 0)
            n_rear = rear_reqs.get(label, 0)
            
            # [Adaptive Sort]
            # Case 1: Rear(후방) 할당이 필요한 경우 -> 크기(Area)가 중요함 (큰게 앞, 작은게 뒤)
            if n_rear > 0:
                dets.sort(key=lambda d: d.get('area', 0), reverse=True)
            # Case 2: Front만 있거나 Depth 구분이 없는 경우 -> 왼쪽(X)부터 채우는 게 자연스러움 [Cite: 5]
            else:
                dets.sort(key=lambda d: d['center_x']) # 오름차순 (좌->우)

            # 할당 수행
            front_alloc = dets[:n_front]
            rear_alloc = dets[n_front : n_front+n_rear]
            
            det_front_pool.extend(front_alloc)
            det_rear_pool.extend(rear_alloc)
            
        # 최종 풀 내에서 다시 X축 정렬 (매칭 순서용)
        det_front_pool.sort(key=lambda d: d['center_x'])
        det_rear_pool.sort(key=lambda d: d['center_x'])
        
        # [Step 4] 매칭 수행
        results_map = {}

        for depth_name, ex_bucket, det_bucket in [("Front", excel_front, det_front_pool), ("Rear", excel_rear, det_rear_pool)]:
            if ex_bucket.empty: continue
            available_dets = list(det_bucket)
            
            for r_idx, row in ex_bucket.iterrows():
                target = str(row['inspection_point_type'])
                matched = next((d for i, d in enumerate(available_dets) if is_type_compatible(target, d['label'])), None)
                
                res = {"type": target, "found": False}
                
                if matched:
                    matched['used'] = True
                    available_dets = [d for d in available_dets if d is not matched]
                    
                    x1, y1 = matched['box'][0], matched['box'][1]
                    val_display, is_ok = "N/A", True

                    # [CASE A] AG
                    if target.startswith("AG"):
                        val_display, _, is_ok = evaluate_gauge_reading(matched, row)
                        if matched.get('source') == 'Pose' and 'keypoints' in matched:
                            for i, kp in enumerate(matched['keypoints']):
                                if len(kp) >= 3 and kp[2] > 0.25:
                                    cv2.circle(final_img, (int(kp[0]), int(kp[1])), 4, (0,0,255) if i in [2,4] else (255,0,0), -1)
                    
                    # [CASE B] DG
                    elif target.startswith("DG"):
                        val_display, _, is_ok = evaluate_gauge_reading({'value': matched.get('value'), 'label': matched['label']}, row)
                        M = matched.get('M'); ocr_details = matched.get('ocr_details', [])
                        if ocr_details and M is not None:
                            try:
                                M_inv = cv2.invertAffineTransform(M)
                                for item in ocr_details:
                                    pts = np.array(item['box'], dtype=np.float32)
                                    center_ocr = np.mean(pts, axis=0) 
                                    orig_pt = cv2.transform(np.array([[center_ocr]]), M_inv)[0][0]
                                    global_x, global_y = int(orig_pt[0] + x1), int(orig_pt[1] + y1)
                                    draw_outline_text(final_img, item['text'], (global_x, global_y), (0, 255, 255), 0.6)
                            except: pass
                        val_display = "" 

                    # [CASE C] Switch/LED/ETC
                    elif target.startswith("Sw") or target.startswith("LED") or target.startswith("ETC") or target.startswith("Class"):
                        if hasattr(system_setup.sw_led_inspector, 'check_status_compliance'):
                            is_ok, reason = system_setup.sw_led_inspector.check_status_compliance(matched['label'], target)
                            val_display = reason
                        else:
                            val_display = "Detected"

                    draw_diagnosis_box(final_img, matched['box'], row, matched['label'], "PASS", val_display, is_ok)
                    res["found"] = True
                
                results_map[r_idx] = res

        # [Step 5] 엑셀 순서대로 요약 리스트 재조립
        summary_list = []
        for i in group.index:
            if i in results_map:
                summary_list.append(results_map[i])
            else:
                summary_list.append({"type": str(group.loc[i]['inspection_point_type']), "found": False})

        # [Step 6] 미매칭 객체(Unmatched) 표시
        for det in all_detections:
            if not det.get('used'):
                x1, y1, x2, y2 = map(int, det['box'])
                if det['label'] in expected_types:
                    color = (0, 165, 255); status_text = "Unk(Cand)"
                else:
                    color = (200, 200, 200); status_text = "Unk"
                
                cv2.rectangle(final_img, (x1, y1), (x2, y2), color, 2)
                draw_outline_text(final_img, f"{status_text}: {det['label']}", (x1, y1 - 10), color, 0.5)

        # [Step 7] 화면 출력
        draw_summary_table(final_img, summary_list)
        
        h, w = final_img.shape[:2]
        cv2.rectangle(final_img, (0, h-40), (w, h), (0, 0, 0), -1)
        cv2.putText(final_img, f"[{idx+1}/{len(grouped_list)}] Space:Next | A:Prev | Q:Quit", (20, h-12), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        win_name = f"{first.get('sight','Unk')}/{first['mission_name']}/{first['inspection_name']}"
        print(f"📸 [{idx+1}/{len(grouped_list)}] {win_name}")

        cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(win_name, 1920, int(h * (1920 / w)))
        cv2.imshow(win_name, final_img)
        
        key = cv2.waitKey(0) & 0xFF
        cv2.destroyWindow(win_name)

        if key == ord('q') or key == ord('Q'): break
        elif key == ord('a') or key == ord('A'): idx = max(0, idx - 1)
        else: idx += 1

def test_vlm_class_items(system_setup):
    """
    [VLM 단위 테스트 - 인터랙티브 모드]
    - 이미지 윈도우 표시 (현재 분석 대상 확인용)
    - 분석 결과는 콘솔(디버거 창)에 실시간 스트리밍 출력
    - Space:다음, A:이전, Q:종료 키보드 제어 적용
    """
    import cv2
    import pandas as pd
    import config
    import pytest
    import os
    from inspectors.vlm_inspector import VLMInspector

    df = system_setup.df
    
    # 1. 'Class_' 로 시작하거나 포함된 데이터 필터링
    class_df = df[df['inspection_point_type'].str.startswith('Class_', na=False) | 
                  df['inspection_point_type'].str.contains('Class', case=False, na=False)].copy()
    
    if class_df.empty:
        print(f"\n❌ [ERROR] 'Class_'로 시작하는 항목을 찾을 수 없습니다.")
        pytest.skip("Skipped: Class 항목 없음")
        return

    # 미션/점검명 단위로 그룹핑하여 리스트로 변환 (인덱싱 이동을 위해)
    class_df['unique_key'] = class_df['mission_name'].astype(str) + "_" + class_df['inspection_name'].astype(str)
    grouped_list = list(class_df.groupby('unique_key', sort=False))

    print(f"\n🚀 [VLM TEST] 총 {len(grouped_list)}개의 이미지 그룹을 점검합니다.")
    print("   👉 사용법: 이미지가 뜨면 분석이 시작됩니다. 분석 후 [Space:다음 | A:이전 | Q:종료]를 누르세요.\n")

    # VLM 인스턴스 준비
    vlm_inspector = system_setup.vlm_inspector if hasattr(system_setup, 'vlm_inspector') else VLMInspector()

    idx = 0
    while 0 <= idx < len(grouped_list):
        key, group = grouped_list[idx]
        first = group.iloc[0]
        
        # 이미지 경로 확인
        img_path = system_setup.get_latest_image(system_setup.base_path, first['mission_name'], first['inspection_name'])
        
        # 이미지가 없으면 로그만 찍고 다음으로 자동 넘어감 (무한루프 방지)
        if not img_path or not os.path.exists(img_path):
            print(f"❌ 이미지 없음 (Skipping): {key}")
            idx += 1
            continue

        img = cv2.imread(img_path)
        if img is None: 
            print(f"❌ 이미지 로드 실패: {img_path}")
            idx += 1
            continue

        # ---------------------------------------------------------
        # [Step 1] 이미지 창 띄우기
        # ---------------------------------------------------------
        win_name = f"VLM Analysis: {first['mission_name']}/{first['inspection_name']}"
        cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
        
        # 해상도 조절 (HD급)
        h, w = img.shape[:2]
        target_w = 1920
        target_h = int(h * (target_w / w))
        cv2.resizeWindow(win_name, target_w, target_h)
        
        # 안내 문구 이미지에 표시
        display_img = img.copy()
        cv2.putText(display_img, "Analyzing... Check Console", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        cv2.imshow(win_name, display_img)
        
        # 윈도우를 즉시 그리기 위해 짧게 대기 (1ms)
        cv2.waitKey(1)

        # ---------------------------------------------------------
        # [Step 2] VLM 분석 수행 (콘솔 출력)
        # ---------------------------------------------------------
        print(f"\n📸 [Image {idx+1}/{len(grouped_list)}] {first['mission_name']} / {first['inspection_name']}")
        print(f"   📂 Path: {img_path}")

        for i, (r_idx, row) in enumerate(group.iterrows()):
            target_type = row['inspection_point_type']
            print("-" * 60)
            print(f"🔍 [{i+1}] 점검 항목: {target_type}")
            print("💡 분석 결과: ", end="", flush=True) # 줄바꿈 없이 대기
            
            # VLM 호출 (스트리밍으로 콘솔에 타다닥 찍힘)
            _ = vlm_inspector.analyze(img_path, target_type)
            print("\n" + "-" * 60)

        # ---------------------------------------------------------
        # [Step 3] 사용자 입력 대기
        # ---------------------------------------------------------
        # 분석 완료 후 안내 문구 변경
        cv2.putText(display_img, "Done. [Space:Next | A:Prev | Q:Quit]", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow(win_name, display_img)
        
        print("\n👉 분석 완료. 다음장: Space / 이전장: A / 종료: Q")
        key = cv2.waitKey(0) & 0xFF
        
        # 창 닫기 (다음 이미지 열기 전)
        cv2.destroyWindow(win_name)

        if key == ord('q') or key == ord('Q'):
            print("🛑 테스트를 종료합니다.")
            break
        elif key == ord('a') or key == ord('A'):
            idx = max(0, idx - 1) # 이전
        else:
            idx += 1 # 다음 (Space 포함 나머지 키)

    cv2.destroyAllWindows()


# 사이트/미션/SpotCam-PTZ-9_일자_시간.jpg

"""
프로그램명: VLM 비동기 병렬 진단 테스트 (test_vlm_class_items_parallel)
버전: v2.5.0 (2026-01-07)
사용 방법:
1. pytest test_vlm_parallel.py 실행
2. 이미지가 출력되면 백그라운드에서 모든 점검 항목(Class_*)이 병렬로 분석됩니다.
3. 결과는 콘솔에 실시간으로 출력되며, 모든 분석이 끝나기 전이라도 키 조작이 가능합니다.
4. [Space:다음 | A:이전 | Q:종료]

변경 사항:
- [Parallelism] ThreadPoolExecutor를 도입하여 다수 점검 항목 동시 분석 (속도 향상)
- [Non-blocking UI] 분석 중에도 OpenCV 창이 멈추지 않고 키 입력을 수신
- [Visual Feedback] 분석 중인 항목의 개수를 이미지 상단에 실시간 표시
"""


def test_vlm_class_items_parallel(system_setup):
    """
    VLM 분석 속도 개선 버전:
    - 항목별로 쓰레드를 생성하여 Ollama API에 동시 요청을 보냅니다.
    - 한 장의 이미지에 점검 항목이 많을수록 체감 속도가 비약적으로 향상됩니다.
    """
    df = system_setup.df
    
    # 1. Class 관련 항목 필터링
    class_df = df[df['inspection_point_type'].str.contains('Class', case=False, na=False)].copy()
    if class_df.empty:
        pytest.skip("Skipped: 분석할 Class 항목이 없습니다.")
        return

    class_df['unique_key'] = class_df['mission_name'].astype(str) + "_" + class_df['inspection_name'].astype(str)
    grouped_list = list(class_df.groupby('unique_key', sort=False))

    vlm_inspector = system_setup.vlm_inspector
    # 최대 병렬 쓰레드 수 설정 (Ollama 서버 사양에 따라 조절)
    MAX_WORKERS = 5 

    idx = 0
    while 0 <= idx < len(grouped_list):
        key, group = grouped_list[idx]
        first = group.iloc[0]
        img_path = system_setup.get_latest_image(system_setup.base_path, first['mission_name'], first['inspection_name'])
        
        if not img_path or not os.path.exists(img_path):
            idx += 1; continue

        img = cv2.imread(img_path)
        display_img = img.copy()
        
        # UI 설정
        win_name = f"VLM Parallel Analysis: {idx+1}/{len(grouped_list)}"
        cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(win_name, 1280, 720)

        # ---------------------------------------------------------
        # [Step 1] 쓰레드 풀을 이용한 병렬 분석 함수 정의
        # ---------------------------------------------------------
        def run_analysis(row_data):
            t_type = row_data['inspection_point_type']
            logger.info(f"자원 할당 중... 📡 분석 시작: {t_type}")
            # VLM 호출
            result = vlm_inspector.analyze(img_path, t_type)
            return t_type, result

        print(f"\n📸 [Image {idx+1}/{len(grouped_list)}] {key} 분석 시작 (병렬 모드)")
        
        # 분석 항목 리스트업
        rows = [row for _, row in group.iterrows()]
        analysis_results = []
        
        # ---------------------------------------------------------
        # [Step 2] 비동기 실행 (Future 객체 활용)
        # ---------------------------------------------------------
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # 모든 항목을 쓰레드 풀에 던짐
            future_to_type = {executor.submit(run_analysis, row): row['inspection_point_type'] for row in rows}
            
            # 분석이 돌아가는 동안 UI는 키 입력을 대기 (Non-blocking)
            finished_count = 0
            total_count = len(rows)
            
            while finished_count < total_count:
                # 중간 상태 이미지 업데이트
                temp_img = display_img.copy()
                cv2.putText(temp_img, f"Analyzing: {finished_count}/{total_count} completed...", (50, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                cv2.imshow(win_name, temp_img)
                
                # 키 입력을 아주 짧게 확인 (분석 중에도 취소/다음 가능하게)
                key_press = cv2.waitKey(100) & 0xFF
                if key_press in [ord('q'), ord('a'), ord(' ')]:
                    # 루프를 깨기 위해 현재 수행 중인 Future들을 취소 시도할 수 있으나, 
                    # API 요청은 보통 취소가 안 되므로 여기서는 인덱스 제어만 수행
                    break

                # 완료된 쓰레드 확인
                done, not_done = concurrent.futures.wait(future_to_type.keys(), timeout=0.1, 
                                                         return_when=concurrent.futures.FIRST_COMPLETED)
                for future in done:
                    if future not in [f for f, r in analysis_results]:
                        t_type, res = future.result()
                        print(f"\n✅ [{t_type}] 분석 완료\n{res}\n")
                        analysis_results.append((future, res))
                        finished_count += 1

        # ---------------------------------------------------------
        # [Step 3] 최종 결과 표시 및 사용자 입력
        # ---------------------------------------------------------
        cv2.putText(display_img, "Analysis Finished. [Space:Next | A:Prev | Q:Quit]", (50, 100), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow(win_name, display_img)
        
        final_key = cv2.waitKey(0) & 0xFF
        cv2.destroyWindow(win_name)

        if final_key == ord('q'): break
        elif final_key == ord('a'): idx = max(0, idx - 1)
        else: idx += 1

    cv2.destroyAllWindows()

# =============================================================================
# [Test] DG VLM Query (Parallel + Top-Right Display)
# =============================================================================
# =============================================================================
# [Test] DG VLM Query (Console Only - No GUI)
# =============================================================================
def test_dg_gauge_vlm_inference_grouped(system_setup):
    """
    [DG VLM 진단 테스트 - 콘솔 출력 전용]
    - 화면(GUI) 없이 순차적으로 VLM 질의 수행
    - 요청 정보, 소요 시간, 결과, 에러 등을 콘솔에 상세 출력
    """
    import cv2
    import numpy as np
    import os
    import config
    import uuid
    import re
    import pandas as pd
    import time
    import requests
    import base64
    from utils.matching import is_type_compatible, evaluate_gauge_reading

    # --- [Internal Helper] VLM Request ---
    def ask_vlm_direct(crop_path, query_text):
        if not query_text or pd.isna(query_text):
            query_text = "Read the digital number displayed on the screen."
        
        try:
            with open(crop_path, "rb") as img_file:
                b64_image = base64.b64encode(img_file.read()).decode('utf-8')
            
            payload = {
                "model": config.VLM_CONFIG["model"],
                "prompt": str(query_text),
                "images": [b64_image],
                "stream": False,
                "options": {
                    "temperature": 0.0,
                    "num_predict": 10 
                }
            }
            # Timeout 300초 (5분)
            start_time = time.time()
            response = requests.post(config.VLM_CONFIG["api_url"], json=payload, timeout=300)
            response.raise_for_status()
            elapsed = time.time() - start_time
            
            vlm_text = response.json().get("response", "").strip()
            return {"success": True, "text": vlm_text, "elapsed": elapsed}

        except Exception as e:
            return {"success": False, "error": str(e), "elapsed": 0}

    # -------------------------------------------------------------------------
    df = system_setup.df
    dg_df = df[df['inspection_point_type'].str.contains('DG', na=False)].copy()
    if dg_df.empty: 
        print("⚠️  No DG items found in excel.")
        return

    dg_df['unique_key'] = dg_df['mission_name'].astype(str) + "_" + dg_df['inspection_name'].astype(str)
    grouped_list = list(dg_df.groupby('unique_key', sort=False))
    
    # 임시 폴더
    temp_dir = os.path.join(os.getcwd(), "temp_crops_console")
    os.makedirs(temp_dir, exist_ok=True)

    print(f"\n🚀 [DG VLM Console Test] Total Groups: {len(grouped_list)}")
    print("=" * 80)

    for idx, (key, group) in enumerate(grouped_list):
        first = group.iloc[0]
        mission = first['mission_name']
        inspection = first['inspection_name']
        
        img_path = system_setup.get_latest_image(system_setup.base_path, mission, inspection)
        if not img_path or not os.path.exists(img_path):
            print(f"❌ Image Not Found: {mission}/{inspection}")
            continue

        print(f"\n📸 Processing [{idx+1}/{len(grouped_list)}]: {mission} / {inspection}")
        print(f"   📂 File: {os.path.basename(img_path)}")

        img = cv2.imread(img_path)
        if img is None: continue
        h_img, w_img = img.shape[:2]

        # [Step 1] YOLO 탐지
        raw_detections = system_setup.detector(img_path, verbose=False)[0]
        dg_candidates = []
        for box in raw_detections.boxes:
            label = raw_detections.names[int(box.cls[0])]
            if label.startswith("DG"):
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                dg_candidates.append({
                    'label': label,
                    'box': [max(0, x1), max(0, y1), min(w_img, x2), min(h_img, y2)],
                    'area': (x2 - x1) * (y2 - y1), 'center_x': (x1 + x2) / 2, 'used': False
                })

        # [Step 2] 매칭 및 순차 실행
        excel_rear = group[group['facility_2'].str.contains('(rear)', na=False, regex=False)]
        excel_front = group[~group['facility_2'].str.contains('(rear)', na=False, regex=False)]
        
        dg_candidates.sort(key=lambda d: d['area'], reverse=True)
        det_front_pool = sorted(dg_candidates[:len(excel_front)], key=lambda d: d['center_x'])
        det_rear_pool = sorted(dg_candidates[len(excel_front):], key=lambda d: d['center_x'])

        for depth_name, ex_bucket, det_bucket in [("Front", excel_front, det_front_pool), ("Rear", excel_rear, det_rear_pool)]:
            available_dets = list(det_bucket)
            for _, row in ex_bucket.iterrows():
                target = str(row['inspection_point_type'])
                query = row.get('query')
                
                matched = None
                for i, det in enumerate(available_dets):
                    if is_type_compatible(target, det['label']):
                        matched = det; det['used'] = True; available_dets.pop(i); break
                
                if matched:
                    # Crop 저장
                    x1, y1, x2, y2 = matched['box']
                    pad = 10
                    crop = img[max(0,y1-pad):min(h_img,y2+pad), max(0,x1-pad):min(w_img,x2+pad)]
                    
                    crop_name = f"{uuid.uuid4().hex}.jpg"
                    crop_path = os.path.join(temp_dir, crop_name)
                    cv2.imwrite(crop_path, crop)
                    
                    # [Step 3] VLM 질의 (동기식 - 순차 실행)
                    print(f"   ------------------------------------------------------------")
                    print(f"   🔍 Target: {target} | Label: {matched['label']}")
                    print(f"   ❓ Query : {query}")
                    print(f"   ⏳ Sending request to Ollama...", end="", flush=True)
                    
                    result = ask_vlm_direct(crop_path, query)
                    
                    if result['success']:
                        print(f" Done ({result['elapsed']:.2f}s)")
                        print(f"   👉 Response: {result['text']}")
                        
                        # 숫자 추출 및 판정
                        try:
                            numbers = re.findall(r"[-+]?\d*\.\d+|\d+", result['text'])
                            extracted_val = float(numbers[0]) if numbers else None
                        except: extracted_val = None
                        
                        mock_det = {'value': extracted_val, 'label': matched['label']}
                        val_str, _, is_norm = evaluate_gauge_reading(mock_det, row)
                        status = "PASS" if is_norm else "FAIL"
                        print(f"   📊 Verdict : {status} (Value: {val_str})")
                        
                    else:
                        print(" Failed")
                        print(f"   ❌ Error: {result['error']}")

                    # 임시 파일 삭제
                    if os.path.exists(crop_path): os.remove(crop_path)
                else:
                    print(f"   ⚠️  Unmatched: {target} (No matching detection found)")

    # Cleanup
    try: os.rmdir(temp_dir)
    except: pass