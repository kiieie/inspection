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
    [V251215 고도화] -> [2026-03-16 display.md 룰 적용]
    1. status="PASS"(초록, 2), "FAIL"(빨강, 2), "UNKNOWN"(노랑, 2), "Unmatched"(회색, 1)
    2. 박스 주변에 레이블과 판독값(value)을 가독성 있게 렌더링 (겹치지 않게 배경 박스 사용)
    3. keypoints가 있으면 (AG_) 별도 표시 유지
    """
    x1, y1, x2, y2 = map(int, box)
    
    # 1. 색상 및 두께 결정
    thickness = 2
    if status == "PASS":
        box_color = config.COLORS.get("PASS", (0, 255, 0))
    elif status == "FAIL":
        box_color = config.COLORS.get("FAIL", (0, 0, 255))
    elif status == "UNKNOWN":
        box_color = config.COLORS.get("UNKNOWN", (0, 255, 255))
    elif status == "Unmatched":
        box_color = (128, 128, 128) # 회색
        thickness = 1
    else:
        box_color = (255, 255, 255)

    # 2. 바운딩 박스 그리기
    cv2.rectangle(img, (x1, y1), (x2, y2), box_color, thickness)
    
    # 3. 레이블 및 결과값 텍스트 조합
    display_text = found_label
    if value and value != "N/A":
        display_text += f" : {value}"
        
    # 4. 텍스트 그리기 (겹침 방지를 위해 배경 있는 유틸리티 사용)
    # y좌표는 박스의 바로 상단으로 하되, 상단 범위를 벗어나면 하단으로 그리는 로직이 `draw_text_with_bg` 안에 있음
    draw_text_with_bg(img, display_text, x1, y1, font_scale=0.5, color=box_color, thickness=1)

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
    pass # User requested to remove the [Inspection Summary] overlay from the top left of the image

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