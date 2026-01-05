import math
import numpy as np

def get_angle(center, point):
    """
    중심점과 특정 점 사이의 각도(degree)를 반환
    참조 코드의 로직 적용: Y축 반전(-(pt[1]-center[1])) 하여 일반 데카르트 좌표계 기준 각도 산출
    """
    dx = point[0] - center[0]
    dy = point[1] - center[1]
    # 이미지 좌표계(y가 아래로 증가)를 수학적 좌표계(y가 위로 증가)로 보정하기 위해 -dy 사용
    return (math.degrees(math.atan2(-dy, dx)) + 360) % 360

def calculate_clockwise_distance(start_angle, end_angle):
    """시계 방향 거리 계산 (참조 코드 로직)"""
    return (start_angle - end_angle) % 360

def validate_gauge_geometry(p_c, p_s, p_m, p_e, img_w=None, img_h=None):
    """
    [검증 모듈] 게이지 형상이 기하학적으로 타당한지 검사
    Returns: (True/False, "Reason")
    """
    # 1. 반지름 계산
    d_s = np.linalg.norm(np.array(p_s) - np.array(p_c))
    d_m = np.linalg.norm(np.array(p_m) - np.array(p_c))
    d_e = np.linalg.norm(np.array(p_e) - np.array(p_c))
    
    radii = [d_s, d_m, d_e]
    min_r, max_r = min(radii), max(radii)
    
    # (A) 최소 크기 체크 (노이즈)
    if max_r < 15.0:
        return False, "Too Small"

    # (B) 찌그러짐 체크 (타원형/투영 왜곡 심한 경우)
    # 참조 코드 기준: min_r / max_r < 0.4
    if max_r > 0 and (min_r / max_r) < 0.4:
        return False, "Distorted (Ratio < 0.4)"

    # (C) 경계선 침범 체크 (이미지 밖으로 중심이 나간 경우 등)
    if img_w is not None and img_h is not None:
        margin = 10
        cx, cy = p_c
        if cx < margin or cx > img_w - margin or cy < margin or cy > img_h - margin:
            return False, "Center out of bounds"

    return True, "Valid"

def calculate_gauge_ratio(p_c, p_s, p_e, p_h):
    """
    Start, End, Head(Needle) 좌표를 이용해 0.0 ~ 1.0 사이의 비율 계산
    """
    ang_s = get_angle(p_c, p_s)
    ang_e = get_angle(p_c, p_e)
    ang_h = get_angle(p_c, p_h)

    # 참조 코드의 clockwise_dist 함수 사용
    span = calculate_clockwise_distance(ang_s, ang_e)
    prog = calculate_clockwise_distance(ang_s, ang_h)

    # Span이 0에 가까우면(360도) 전체 원으로 간주
    if span < 1e-6: 
        span = 360.0
    
    # Buffer 로직 (시작점/끝점을 살짝 벗어난 떨림 보정)
    buffer = 20.0
    
    if prog > span + buffer: 
        return 0.0 # Min보다 더 뒤로 간 경우
    elif prog > span: 
        return 1.0 # Max를 넘은 경우
    else: 
        return prog / span