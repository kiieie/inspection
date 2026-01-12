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

def draw_diagnosis_box(img, box, excel_row, found_label, status="PASS", value=None, is_normal=True):
    """
    [V251215 고도화] 
    1. status="PASS"면 박스는 무조건 초록색 (사용자 요청: 매칭되면 PASS)
    2. is_normal=False면 수치 정보가 포함된 두 번째 줄을 적색으로 표시
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

    # 첫 번째 줄: 기대 항목 (박스 색상과 동일)
    draw_outline_text(img, line1, (x1, y1 - 32), box_color, font_scale=0.45)
    
    # [핵심] 두 번째 줄: 수치 이상이거나 정의 안 됨(is_normal=False)이면 적색으로 표시
    text_color_line2 = box_color if is_normal else config.COLORS["FAIL"] # 적색
    draw_outline_text(img, line2, (x1, y1 - 10), text_color_line2, font_scale=0.5, thickness=2)
    
    # --- 하단 정보 표시 (설비 명칭) ---
    fac_text = f"{excel_row.get('facility_1','')} | {excel_row.get('facility_2','')}"
    draw_outline_text(img, fac_text, (x1, y2 + 20), (255, 255, 255), font_scale=0.45)

def draw_summary_table(img, summary_list):
    """화면 좌측 상단 O/X 점검 목록 리스트 표시"""
    y_pos = 100
    draw_outline_text(img, "[ Inspection Summary ]", (15, 70), (255, 255, 255), 0.7, 2)
    for item in summary_list:
        mark = "O" if item['found'] else "X"
        color = config.COLORS["PASS"] if item['found'] else config.COLORS["FAIL"]
        draw_outline_text(img, f"{mark} | {item['type']}", (15, y_pos), color, 0.6, 2)
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