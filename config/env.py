"""환경 변수 로드 — 경로/배포 설정만 담당"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(os.getenv("BASE_DIR", "/data/inspection"))
RESULT_BASE_DIR = Path(os.getenv("RESULT_BASE_DIR", "/data/results"))
DB_PATH = Path(os.getenv("DB_PATH", str(Path(__file__).parent.parent / "database" / "robot-control-system-db" / "myapi.db")))
EXCEL_FILE = Path(os.getenv("EXCEL_FILE", "/data/checklist.xlsx"))
VLM_BACKEND = os.getenv("VLM_BACKEND", "ollama")  # "ollama" | "trtllm"

# DB models 동적 import용 경로
DB_MODELS_DIR = DB_PATH.parent
DB_MODELS_FILE = "models.py"

IMAGE_PATH_PREFIX = os.getenv("IMAGE_PATH_PREFIX", "inspection_data")
EX_PATH_PREFIX = os.getenv("EX_PATH_PREFIX", "DATA_FOR_EX")
