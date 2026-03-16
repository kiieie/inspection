import sys
import os
import glob
import pandas as pd
from pathlib import Path
from datetime import datetime
import importlib.util

# Setup Project Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))
import config

# Dynamic Import of models
if "models" not in sys.modules:
    models_path = Path(config.DB_CONFIG['models_dir']) / config.DB_CONFIG['models_file']
    spec = importlib.util.spec_from_file_location("models", str(models_path))
    models = importlib.util.module_from_spec(spec)
    sys.modules["models"] = models
    spec.loader.exec_module(models)
else:
    models = sys.modules["models"]

from database import SessionLocal
from models import InspectionData, DiagnosisState, InspectionPoint, InspectionResult

def get_image_file_from_dir(base_dir, mission, insp_name):
    """Finds the actual JPG file inside the directory structure."""
    exact_dir_name = f"{mission}.walk_{insp_name}"
    target_dir = os.path.join(base_dir, f"{mission}.walk", exact_dir_name)
    
    if not os.path.exists(target_dir):
        if not insp_name.lower().endswith(".jpg"):
            target_dir_jpg = target_dir + ".jpg"
            if os.path.exists(target_dir_jpg):
                target_dir = target_dir_jpg
            else:
                parent_dir = os.path.join(base_dir, f"{mission}.walk")
                if os.path.exists(parent_dir):
                    prefix = f"{mission}.walk_{insp_name}"
                    candidates = [d for d in glob.glob(os.path.join(parent_dir, "*")) if os.path.isdir(d) and os.path.basename(d).startswith(prefix)]
                    if candidates: targe_dir = candidates[0]
                    else: return None
                else: return None
        else: return None

    files = glob.glob(os.path.join(target_dir, "*.[jJ][pP][gG]"))
    return max(files, key=os.path.getmtime) if files else None

class TaskController:
    def __init__(self):
        self.tasks_list = []
        self.current_idx = 0
        self.load_from_db()

    def load_from_db(self):
        self.tasks_list = []
        db = SessionLocal()
        try:
            query = db.query(
                InspectionPoint.site, 
                InspectionPoint.mission_name, 
                InspectionPoint.inspection_name
            ).distinct()
            all_points = query.all()
            
            # Filter Logic (Spot Cam)
            keyword = "Spot Cam"
            filtered = [p for p in all_points if p.inspection_name and keyword.lower() in p.inspection_name.lower()]
            
            if not filtered:
                print(f"⚠️ No tasks found matching '{keyword}'. Trying 'Spot'...")
                keyword = "Spot"
                filtered = [p for p in all_points if p.inspection_name and keyword.lower() in p.inspection_name.lower()]
                
            self.tasks_list = filtered
            print(f"✅ Loaded {len(self.tasks_list)} tasks from DB matching '{keyword}'")
            
            if not self.tasks_list:
                print("❌ No tasks found in DB. Check InspectionPoint table.")
        except Exception as e:
            print(f"❌ Error loading from DB: {e}")
        finally:
            db.close()

    def get_current_task_info(self):
        if not self.tasks_list: return None
        
        task = self.tasks_list[self.current_idx]
        
        return {
            "index": self.current_idx,
            "total": len(self.tasks_list),
            "site": task.site,
            "mission": task.mission_name,
            "inspection": task.inspection_name
        }

    def push_current_task(self):
        if not self.tasks_list: return False, "No tasks loaded"
        
        task = self.tasks_list[self.current_idx]
        return self._push_point_to_db(task.site, task.mission_name, task.inspection_name)

    def _push_point_to_db(self, site, mission, insp_name):
        img_path = get_image_file_from_dir(config.BASE_DIR, mission, insp_name)
        if not img_path: return False, "Image not found"

        db = SessionLocal()
        try:
            # Create Task Data based on existing InspectionPoint
            abs_path = str(Path(img_path).resolve())
            new_task = InspectionData(
                site=site, mission_name=mission,
                inspection_time=datetime.now(),
                data_raw_dir=abs_path,
                data_result_dir=insp_name,
                state=DiagnosisState.QUEUED
            )
            db.add(new_task)
            db.commit()
            db.refresh(new_task)
            return True, f"Task {new_task.id} Created"
            
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally:
            db.close()

    def next_task(self):
        if self.current_idx < len(self.tasks_list) - 1:
            self.current_idx += 1
            return True
        return False

    def prev_task(self):
        if self.current_idx > 0:
            self.current_idx -= 1
            return True
        return False
        
    def _format_result(self, task):
        if not task: return None
        
        db = SessionLocal()
        try:
            # 1. Detected Results
            results = db.query(InspectionResult).filter(
                InspectionResult.data_result_dir == task.data_result_dir
            ).all()

            # 2. Expected Points
            insp_name = task.inspection_name if hasattr(task, 'inspection_name') else task.data_result_dir
            points = db.query(InspectionPoint).filter(
                InspectionPoint.mission_name == task.mission_name,
                InspectionPoint.inspection_name == insp_name
            ).all()

            # Construct response
            res_data = {
                "task_id": task.id,
                "site": task.site,
                "mission": task.mission_name,
                "inspection": insp_name,
                "image_path": task.data_result_dir, 
                "expected_items": [
                    {
                        "type": p.inspection_point_type,
                        "facility_1": p.facility_1,
                        "facility_2": p.facility_2,
                        "min_value": p.min_value,
                        "max_value": p.max_value
                    } for p in points
                ],
                "items": [
                    {
                        "type": r.inspection_point_type,
                        "value": r.result_value,
                        "status": r.judgement,
                        "pos": r.spatial_info 
                    } for r in results
                ]
            }
            return res_data
        finally:
            db.close()

    def get_latest_result(self):
        db = SessionLocal()
        try:
            # Get latest COMPLETED task
            last_task = db.query(InspectionData).filter(
                InspectionData.state == DiagnosisState.COMPLETED
            ).order_by(InspectionData.id.desc()).first()
            return self._format_result(last_task)
        finally:
            db.close()

    def get_history_prev(self, current_task_id):
        db = SessionLocal()
        try:
            prev_task = db.query(InspectionData).filter(
                InspectionData.state == DiagnosisState.COMPLETED,
                InspectionData.id < current_task_id
            ).order_by(InspectionData.id.desc()).first()
            return self._format_result(prev_task)
        finally:
            db.close()

    def get_history_next(self, current_task_id):
        db = SessionLocal()
        try:
            next_task = db.query(InspectionData).filter(
                InspectionData.state == DiagnosisState.COMPLETED,
                InspectionData.id > current_task_id
            ).order_by(InspectionData.id.asc()).first()
            return self._format_result(next_task)
        finally:
            db.close()
