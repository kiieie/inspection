import sys
from pathlib import Path
import importlib.util

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_ROOT))
import config

if "models" not in sys.modules:
    models_path = Path(config.DB_CONFIG['models_dir']) / config.DB_CONFIG['models_file']
    spec = importlib.util.spec_from_file_location("models", str(models_path))
    models = importlib.util.module_from_spec(spec)
    sys.modules["models"] = models
    spec.loader.exec_module(models)

from database import SessionLocal
from models import InspectionData, InspectionPoint

db = SessionLocal()
print("--- [Checking Last Task] ---")
task = db.query(InspectionData).order_by(InspectionData.id.desc()).first()
if task:
    print(f"ID: {task.id}")
    print(f"Site: {task.site}")
    print(f"Mission: {task.mission_name}")
    print(f"Inspect: {task.inspection_name}")
    print(f"Raw Dir: {task.data_raw_dir}")
else:
    print("No tasks found.")
db.close()
