import cv2
import numpy as np
import glob
import os
import math
from paddleocr import PaddleOCR

# ================================
# 환경 설정
# ================================
INPUT_DIR  = "./"
OUTPUT_DIR = "./esult"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# PaddleOCR 초기화
ocr = PaddleOCR(
    use_angle_cls=True,
    lang='en'
    )


# ================================
# 회전 함수
# ================================
def rotate_image(image, angle):
    h, w = image.shape[:2]
    center = (w//2, h//2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_LINEAR)


# ================================
# Rough angle (Hough 기반)
# ================================
def estimate_angle_hough(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)

    h, w = img.shape[:2]
    roi = edges[int(h*0.2):int(h*0.8), int(w*0.2):int(w*0.8)]

    lines = cv2.HoughLinesP(
        roi, 1, np.pi/180, threshold=40,
        minLineLength=80, maxLineGap=60
    )
    if lines is None:
        return 0.0

    angles = []
    for l in lines:
        x1,y1,x2,y2 = l[0]
        dx, dy = x2-x1, y2-y1
        ang = math.degrees(math.atan2(dy, dx))
        if -45 < ang < 45:
            angles.append(ang)

    if not angles: 
        return 0.0

    return float(np.median(angles))


# ================================
# 파란선 그리기
# ================================
def draw_blue_line(img, angle):
    h, w = img.shape[:2]
    cx = w // 2
    cy = int(h * 0.1)   # 이미지 위쪽 10%

    rad = math.radians(angle)
    dx = math.cos(rad)
    dy = math.sin(rad)

    length = int(w * 0.9)

    x1 = int(cx - dx * length * 0.5)
    y1 = int(cy - dy * length * 0.5)
    x2 = int(cx + dx * length * 0.5)
    y2 = int(cy + dy * length * 0.5)

    img2 = img.copy()
    cv2.line(img2, (x1,y1), (x2,y2), (255,0,0), 8)  # 순수 BGR Blue
    return img2


# ================================
# STRICT 파란선 detect → angle
# ================================
def detect_blue_line_angle_strict(img):

    mask = (img[:,:,0] == 255) & (img[:,:,1] == 0) & (img[:,:,2] == 0)

    ys, xs = np.where(mask)
    if len(xs) < 20:
        return None

    pts = np.vstack([xs, ys]).T.astype(np.float32)

    mean = np.mean(pts, axis=0)
    pts_centered = pts - mean
    cov = np.cov(pts_centered.T)

    eigvals, eigvecs = np.linalg.eig(cov)
    vec = eigvecs[:, np.argmax(eigvals)]
    dx, dy = vec[0], vec[1]

    angle = math.degrees(math.atan2(dy, dx))
    if angle > 90: angle -= 180
    if angle < -90: angle += 180

    return angle


# ================================
# PaddleOCR 수행 + bbox 그리기
# ================================
def run_ocr(rotated_img):
    rgb = cv2.cvtColor(rotated_img, cv2.COLOR_BGR2RGB)
    raw = ocr.ocr(rgb, cls=True)

    if not raw:
        return rotated_img, None

    raw = raw[0]
    vis = rotated_img.copy()

    for line in raw:
        box = line[0]
        text = line[1][0]
        conf = line[1][1]

        pts = [(int(x), int(y)) for x, y in box]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]

        x1, y1 = min(xs), min(ys)
        x2, y2 = max(xs), max(ys)

        cv2.rectangle(vis, (x1,y1), (x2,y2), (0,0,255), 2)
        cv2.putText(vis, f"{text} ({conf:.2f})",
                    (x1, y1-10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (0,255,0), 2, cv2.LINE_AA)

    return vis, raw


# ================================
# 메인 처리
# ================================
def process_image(path):

    img = cv2.imread(path)
    if img is None:
        print("[ERR] Load failed:", path)
        return

    name = os.path.basename(path)
    print("\n[IMAGE]", name)

    # 1) Rough angle
    rough_angle = estimate_angle_hough(img)
    print("[INFO] Rough angle:", rough_angle)

    # 2) 그 angle로 파란선 그림
    img_with_line = draw_blue_line(img, rough_angle)

    # 3) 파란선 detect
    blue_angle = detect_blue_line_angle_strict(img_with_line)

    if blue_angle is None:
        print("[WARN] Blue line NOT detected → NO rotation")
        save = os.path.join(OUTPUT_DIR, name.replace(".jpg","_norot.jpg"))
        cv2.imwrite(save, img)
        print("[SAVED no-rotation]", save)
        return

    print("[INFO] Final rotation angle =", blue_angle)

    # 4) 회전
    rotated = rotate_image(img, blue_angle)

    # 5) OCR 수행
    ocr_img, ocr_result = run_ocr(rotated)

    # 6) 저장 (pair 삭제됨!)
    save_rot = os.path.join(OUTPUT_DIR, name.replace(".jpg","_rot.jpg"))
    save_ocr = os.path.join(OUTPUT_DIR, name.replace(".jpg","_ocr.jpg"))

    cv2.imwrite(save_rot, rotated)
    cv2.imwrite(save_ocr, ocr_img)

    print("[SAVED rotated]", save_rot)
    print("[SAVED ocr     ]", save_ocr)


# ================================
# 실행
# ================================
# ================================
# 실행
# ================================
images = []
for ext in ("*.jpg", "*.jpeg", "*.png"):
    images.extend(glob.glob(os.path.join(INPUT_DIR, ext)))

print("[INFO] 입력 이미지 개수:", len(images))

for p in images:
    process_image(p)

print("\n[DONE] 모든 이미지 처리 완료")