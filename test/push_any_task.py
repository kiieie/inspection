
import os
import sys
import glob
from pathlib import Path
from datetime import datetime
import importlib.util

# Add project root to sys.path
sys.path.insert(0, os.getcwd())

import config
import database

def load_models():
    spec = importlib.util.spec_from_file_location("models", str(Path(config.DB_CONFIG['models_dir']) / config.DB_CONFIG['models_file']))
    models = importlib.util.module_from_spec(spec)
    sys.modules["models"] = models
    spec.loader.exec_module(models)
    return models

def find_actual_image(base_dir, site, mission, insp_name):
    pure_name = os.path.splitext(insp_name)[0]
    search_dirs = [
        os.path.join(base_dir, site, mission),
        os.path.join(base_dir, f"{mission}.walk", f"{mission}.walk_{insp_name}"),
        os.path.join(base_dir, site, f"{mission}.walk", f"{mission}.walk_{insp_name}")
    ]
    for sd in search_dirs:
        if os.path.exists(sd):
            pattern = os.path.join(sd, f"{pure_name}*.[jJ][pP][gG]")
            files = glob.glob(pattern)
            if files: return max(files, key=os.path.getmtime)
    return None

def main():
    if len(sys.argv) < 4:
        print("Usage: python3 push_any_task.py <site> <mission> <insp_name>")
        return

    models = load_models()
    db = database.SessionLocal()
    
    site = sys.argv[1]
    mission = sys.argv[2]
    insp_name = sys.argv[3]
    
    img_path = find_actual_image(config.BASE_DIR, site, mission, insp_name)
    if not img_path:
        print(f"Could not find image for {insp_name}")
        return

    new_task = models.InspectionData(
        site=site,
        mission_name=mission,
        inspection_time=datetime.now(),
        data_raw_dir=os.path.abspath(img_path),
        data_result_dir=insp_name,
        state=models.DiagnosisState.QUEUED
    )
    db.add(new_task)
    db.commit()
    print(f"✅ Task Pushed: {insp_name}")
    db.close()

if __name__ == "__main__":
    main()
