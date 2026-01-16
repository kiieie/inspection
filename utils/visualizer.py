# [utils/visualizer.py] 고가독성 시각화 유틸리티
import cv2
import config

def draw_outline_text(img, text, pos, color, font_scale=0.5, thickness=1):
    """검정색 아웃라인이 적용된 텍스트 작성"""
    x, y = pos
    cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), thickness + 2)
    cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)

def draw_text_with_bg(img, text, x, y, font_scale=0.6, color=(0, 255, 255), thickness=2):
    """
    텍스트 주변에 검은색 박스 배경을 그려 가독성을 높임 (VLM 결과 등 표시에 사용)
    """
    (w, h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
    # 이미지를 벗어나지 않게 좌표 조정
    if y - h - 5 < 0: y = y + h + 10 # 위쪽 공간 없으면 아래로
    else: y = y - 5
    
    cv2.rectangle(img, (x, y - h - 5), (x + w, y + 5), (0, 0, 0), -1)
    cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)

def draw_stack_text(img, text, current_y, font_scale=0.7, color=(0, 255, 255), thickness=2):
    """
    우측 상단에 텍스트를 쌓아서(Stacking) 출력
    Returns: 다음 텍스트가 위치할 Y 좌표
    """
    h_img, w_img = img.shape[:2]
    (text_w, text_h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
    
    # 우측 정렬 좌표 계산 (오른쪽 여백 20px)
    x_pos = w_img - text_w - 20
    
    # 배경 박스 (검정)
    cv2.rectangle(img, (x_pos - 10, current_y - text_h - 10), (w_img, current_y + 10), (0, 0, 0), -1)
    # 텍스트 그리기
    cv2.putText(img, text, (x_pos, current_y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)
    
    # 다음 줄을 위한 Y 좌표 반환 (줄간격 포함)
    return current_y + text_h + 20

def draw_diagnosis_box(img, box, excel_row, found_label, status="PASS", value=None, is_normal=True, keypoints=None):
    """
    [V251215 고도화] 
    1. status="PASS"면 박스는 무조건 초록색 (사용자 요청: 매칭되면 PASS)
    2. is_normal=False면 수치 정보가 포함된 두 번째 줄을 적색으로 표시
    3. keypoints가 있으면 (AG_) 별도 표시 (2026-01-14)
    """
    x1, y1, x2, y2 = map(int, box)
    
    # [사용자 요청] 매칭되면 무조건 PASS(초록색) 박스 사용
    box_color = config.COLORS["PASS"] # 고정 초록색
    status_txt = "[OK]" if is_normal else "[ABNORMAL]" # 내부 상태는 텍스트로 표현

    # 바운딩 박스 그리기
    cv2.rectangle(img, (x1, y1), (x2, y2), box_color, 2)
    
    # --- 상단 정보 표시 (두 줄) ---
    exp_type = excel_row['inspection_point_type']
    val_txt = f" ({value})" if value is not None else " (N/A)"
    
    line1 = f"Exp: {exp_type}"
    line2 = f"Fnd: {found_label}{val_txt} {status_txt}"

    # [Fix] 텍스트 위치 보정
    # y1이 너무 위쪽이면 박스 안쪽이나 아래쪽으로 이동해야 함
    text_y_start = y1 - 32
    text_is_inside = False
    
    if y1 < 60: # 화면 상단에 박스가 붙어있는 경우 (Class Item 등)
        text_y_start = y1 + 30 # 박스 안쪽 상단으로 이동
        text_is_inside = True

    # 첫 번째 줄: 기대 항목
    draw_outline_text(img, line1, (x1, text_y_start), box_color, font_scale=0.5 if text_is_inside else 0.45)
    
    # 두 번째 줄: 결과값 (긴 텍스트 줄바꿈 처리)
    text_color_line2 = box_color if is_normal else config.COLORS["FAIL"]
    current_y = text_y_start + 22
    
    # | 또는 \n 으로 분리하여 멀티라인 출력
    lines = line2.replace("|", "\n").split("\n")
    for i, seq_line in enumerate(lines):
        clean_line = seq_line.strip()
        if not clean_line: continue
        draw_outline_text(img, clean_line, (x1, current_y), text_color_line2, font_scale=0.5 if text_is_inside else 0.5, thickness=2)
        current_y += 20
    
    # --- 하단 정보 표시 (설비 명칭) ---
    # 만약 텍스트가 안쪽에 있으면 하단 정보도 위치 조정 고려 필요하나, 보통 하단 여백은 충분함
    fac_text = f"{excel_row.get('facility_1','')} | {excel_row.get('facility_2','')}"
    draw_outline_text(img, fac_text, (x1, y2 + 20), (255, 255, 255), font_scale=0.45)

    # --- [New] Keypoints 시각화 (AG 전용) ---
    if keypoints is not None:
        kp_names = ["Start", "Mid", "Center", "End", "Needle"]
        # 점색상: 시작(파랑), 중간(노랑), 중심(흰색), 종료(빨강), 바늘(연두)
        kp_colors = [(255, 0, 0), (0, 255, 255), (255, 255, 255), (0, 0, 255), (0, 255, 0)]
        
        for idx, kp in enumerate(keypoints):
            if idx >= len(kp_names): break
            kx, ky = map(int, kp[:2])
            conf = kp[2] if len(kp) > 2 else 1.0
            
            if conf > 0.5:
                cv2.circle(img, (kx, ky), 4, kp_colors[idx], -1)
                cv2.circle(img, (kx, ky), 5, (0, 0, 0), 1) # 테두리
                draw_outline_text(img, kp_names[idx], (kx + 5, ky - 5), kp_colors[idx], font_scale=0.4, thickness=1)

def draw_summary_table(img, summary_list):
    """화면 좌측 상단 O/X 점검 목록 리스트 표시"""
    y_pos = 100
    draw_outline_text(img, "[ Inspection Summary ]", (15, 70), (255, 255, 255), 0.7, 2)
    for item in summary_list:
        mark = "O" if item['found'] else "X"
        color = config.COLORS["PASS"] if item['found'] else config.COLORS["FAIL"]
        draw_outline_text(img, f"{mark} | {item['type']}", (15, y_pos), color, 0.6, 2)
        y_pos += 25

def draw_right_summary_table(img, summary_list):
    """
    [2026-01-13 New]: 화면 우측 상단에 점검 목록 전체 표시 (2026-01-14 고도화)
    """
    h_img, w_img = img.shape[:2]
    y_pos = 70
    title = "[ POINT STATUS ]"
    
    # 우측 정렬 (여백 20px)
    start_x = w_img - 450 # 폭을 조금 더 넓힘
    
    draw_outline_text(img, title, (start_x, y_pos), (255, 255, 255), 0.7, 2)
    y_pos += 35
    
    for item in summary_list:
        mark = "OK" if item['found'] else "MISS"
        color = config.COLORS["PASS"] if item['found'] else config.COLORS["FAIL"]
        
        # Facility 2와 Type을 조합하여 상세 표시
        fac = item.get('fac2', 'N/A')
        pt_type = item.get('type', 'N/A')
        txt = f"{mark} | {fac} | {pt_type}"
        
        draw_outline_text(img, txt, (start_x, y_pos), color, 0.45, 1) # 폰트 크기 조절
        y_pos += 25

def show_navigation_window(img, win_title, current_idx, total_count, target_width=1920):
    """
    [UI Helper] 이미지를 표준 규격(1920px)으로 리사이징하고,
    화면 우측 상단에 배치한 후 키 입력을 처리함.
    
    Returns:
        next_idx (int): 키 입력에 따라 계산된 다음 인덱스
        action (str): 'next', 'prev', 'quit' 중 하나
    """
    
    h, w = img.shape[:2]
    # 가로 1920 기준 세로 비율 계산
    target_height = int(h * (target_width / w))
    
    # 하단 상태바 그리기
    display_img = img.copy()
    cv2.rectangle(display_img, (0, h-50), (w, h), (0, 0, 0), -1)
    status_text = f"[{current_idx+1}/{total_count}] Space:Next | A:Prev | Q:Quit"
    cv2.putText(display_img, status_text, (20, h-15), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    # 윈도우 생성 및 크기/위치 조절
    cv2.namedWindow(win_title, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win_title, target_width, target_height)
    
    # 화면 우측 상단 정렬 (Tkinter 사용)
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        screen_width = root.winfo_screenwidth()
        x_pos = max(0, screen_width - target_width)
        cv2.moveWindow(win_title, x_pos, 0)
    except:
        pass # Tkinter가 없거나 에러나도 그냥 무시하고 진행

    cv2.imshow(win_title, display_img)
    
    # 키 입력 대기
    key = cv2.waitKey(0) & 0xFF
    cv2.destroyWindow(win_title)
    
    if key == ord('q') or key == ord('Q'):
        return current_idx, 'quit'
    elif key == ord('a') or key == ord('A'):
        return max(0, current_idx - 1), 'prev'
    else:
        return current_idx + 1, 'next'