# [Version v1.1] 환경 설정 분리 모듈
import os

# [Paths]
BASE_DIR = "/home/kiie/projects/python/inspection"
EXCEL_FILE = os.path.join(BASE_DIR, "data/Inspection_point, Labeling_251230.xlsx")

# [Model Settings]
MODEL_CONFIG = {
    "classifier": "models/classifier/weights/best.pt",
    "ag_pose": "models/ag_inspector/weights/best.pt"
}

# [VLM Settings - 5.1 반영]
VLM_CONFIG = {
    "api_url": "http://localhost:11434/api/generate",
    "model": "llava"
}

# [Display Colors - 설계서 4.1 반영]
COLORS = {
    "PASS": (0, 255, 0),      # Green (정상)
    "FAIL": (0, 0, 255),      # Red (비정상)
    "UNKNOWN": (0, 255, 255)  # Yellow (매칭 실패/잉여)
}