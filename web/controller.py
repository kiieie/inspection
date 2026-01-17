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
        self.df = None
        self.current_idx = 0
        self.filtered_indices = []
        self.col_mapping = {}
        self.load_excel()

    def load_excel(self):
        excel_path = config.EXCEL_FILE
        if not os.path.exists(excel_path):
            print(f"❌ Excel file not found: {excel_path}")
            return
            
        self.df = pd.read_excel(excel_path, header=0)
        
        # normalization logic from push_task.py
        self.df.columns = [str(c).strip().lower() for c in self.df.columns]
        
        # Column Mapping (Must match normalized names)
        # push_task.py uses: 'site', 'mission_name', 'inspection_name'
        self.col_mapping = {
            'site': 'site',
            'mission': 'mission_name',
            'insp': 'inspection_name'
        }
        
        req_cols = list(self.col_mapping.values())
        missing = [c for c in req_cols if c not in self.df.columns]
        if missing:
            print(f"❌ Missing columns in Excel: {missing}")
            print(f"   Available: {self.df.columns.tolist()}")
            return
        
        # Filter Logic (Spot Cam)
        filter_col = self.col_mapping['insp']
        if filter_col:
            # Drop duplicates based on Inspection Name (Task Unit)
            unique_df = self.df.drop_duplicates(subset=[filter_col])
            
            # Use broader keyword or check matches
            keyword = "Spot Cam"
            mask = unique_df[filter_col].astype(str).str.contains(keyword, case=False, na=False)
            filtered = unique_df[mask]
            
            if filtered.empty:
                print(f"⚠️ No tasks found matching '{keyword}'. Trying 'Spot'...")
                keyword = "Spot"
                mask = unique_df[filter_col].astype(str).str.contains(keyword, case=False, na=False)
                filtered = unique_df[mask]
                
            self.filtered_indices = filtered.index.tolist()
            print(f"✅ Loaded {len(self.filtered_indices)} tasks matching '{keyword}'")
            
            if not self.filtered_indices:
                print("❌ No tasks found even with fallback. Check Excel 'Inspection' column.")
                print(f"   Available Columns: {self.df.columns.tolist()}")
                print(f"   Sample Data: {unique_df[filter_col].head().tolist()}")
        else:
            self.filtered_indices = []
            print("❌ 'Inspection' column not found in Excel.")

    def get_current_task_info(self):
        if not self.filtered_indices: return None
        
        idx = self.filtered_indices[self.current_idx]
        row = self.df.loc[idx]
        
        site = str(row[self.col_mapping['site']]).strip()
        mission = str(row[self.col_mapping['mission']]).strip()
        insp_name = str(row[self.col_mapping['insp']]).strip()
        
        return {
            "index": self.current_idx,
            "total": len(self.filtered_indices),
            "site": site,
            "mission": mission,
            "inspection": insp_name
        }

    def push_current_task(self):
        if not self.filtered_indices: return False, "No tasks loaded"
        
        idx = self.filtered_indices[self.current_idx]
        row = self.df.loc[idx]
        return self._push_row_to_db(row)

    def _push_row_to_db(self, row):
        site = str(row[self.col_mapping['site']]).strip()
        mission = str(row[self.col_mapping['mission']]).strip()
        insp_name = str(row[self.col_mapping['insp']]).strip()
        
        img_path = get_image_file_from_dir(config.BASE_DIR, mission, insp_name)
        if not img_path: return False, "Image not found"

        db = SessionLocal()
        try:
            # 1. Master Info Check/Create
            existing_point = db.query(InspectionPoint).filter(
                InspectionPoint.mission_name == mission,
                InspectionPoint.inspection_name == insp_name
            ).first()

            if not existing_point:
                def get_val(key, default=None):
                    v = row.get(key)
                    return v if pd.notna(v) else default

                new_point = InspectionPoint(
                    site=site, mission_name=mission, inspection_name=insp_name,
                    inspection_point_type=get_val("inspection_point_type"),
                    facility_1=get_val("facility_1"), facility_2=get_val("facility_2"),
                    model_type=get_val("model_type"), model_ver=get_val("model_ver"),
                    min_value=get_val("min_value"), max_value=get_val("max_value"),
                    normal_min_value=get_val("normal_min_value"), normal_max_value=get_val("normal_max_value"),
                    comment=get_val("comment"), query=get_val("query"), report_name=get_val("report_items")
                )
                db.add(new_point)
                db.commit()

            # 2. Create Task
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
        if self.current_idx < len(self.filtered_indices) - 1:
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
            results = db.query(InspectionResult).filter(
                InspectionResult.data_result_dir == task.data_result_dir
            ).all()

            # Construct response
            res_data = {
                "task_id": task.id,
                "site": task.site,
                "mission": task.mission_name,
                "inspection": task.inspection_name if hasattr(task, 'inspection_name') else task.data_result_dir,
                "image_path": task.data_result_dir, 
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
