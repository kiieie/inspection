import sys
import os
import glob
import pandas as pd
from pathlib import Path
from datetime import datetime
import importlib.util

# ======================================================
# [Program Information]
# - File: push_task.py
# - Description: Manually inserts an InspectionData task into the DB
# - Feature: Resolves Image Path from Excel Metadata (Robust)
# - Usage: python3 push_task.py [search_keyword]
#   Example: python3 push_task.py "Spot Cam"
# ======================================================

# 1. Setup Environment & Path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_ROOT))
import config

# 2. Dynamic Import of models
if "models" not in sys.modules:
    models_path = Path(config.DB_CONFIG['models_dir']) / config.DB_CONFIG['models_file']
    if not models_path.exists():
        print(f"❌ Error: Models file not found at {models_path}")
        sys.exit(1)
        
    spec = importlib.util.spec_from_file_location("models", str(models_path))
    models = importlib.util.module_from_spec(spec)
    sys.modules["models"] = models
    spec.loader.exec_module(models)
else:
    models = sys.modules["models"]

from database import SessionLocal
from models import InspectionData, DiagnosisState, InspectionPoint

def get_image_file_from_dir(base_dir, mission, insp_name):
    """
    Finds the actual JPG file inside the directory structure.
    Structure: BASE_DIR / {mission}.walk / {mission}.walk_{insp_name} / *.jpg
    """
    # 1. Target Directory Construction
    # 'insp_name' from Excel might already include .jpg extension (e.g. "foo.jpg")
    # Directory naming usually follows: mission.walk_{insp_name}
    
    # Clean insp_name if needed?
    # Data check showed: insp_name = "Spot Cam - PTZ - 1 spot-cam-ptz.jpg"
    # Directory = "...walk_Spot Cam - PTZ - 1 spot-cam-ptz.jpg"
    
    exact_dir_name = f"{mission}.walk_{insp_name}"
    target_dir = os.path.join(base_dir, f"{mission}.walk", exact_dir_name)
    
    if not os.path.exists(target_dir):
        # Case 2: Maybe insp_name doesn't have .jpg, but folder does?
        if not insp_name.lower().endswith(".jpg"):
            target_dir_jpg = target_dir + ".jpg"
            if os.path.exists(target_dir_jpg):
                target_dir = target_dir_jpg
            else:
                # Case 3: Fuzzy / Glob Search
                # Try finding folder that starts with prefix
                parent_dir = os.path.join(base_dir, f"{mission}.walk")
                if os.path.exists(parent_dir):
                    prefix = f"{mission}.walk_{insp_name}"
                    # Glob for directories matching prefix
                    # Escape special chars in prefix for glob?
                    # glob might fail with brackets []. 
                    candidates = [d for d in glob.glob(os.path.join(parent_dir, "*")) if os.path.isdir(d) and os.path.basename(d).startswith(prefix)]
                    
                    if candidates:
                        target_dir = candidates[0] # Pick first match
                    else:
                        print(f"   ⚠️ Dir not found for: {exact_dir_name}")
                        return None
                else:
                    print(f"   ⚠️ Mission Dir not found: {os.path.basename(parent_dir)}")
                    return None
        else:
             print(f"   ⚠️ Dir not found for: {exact_dir_name}")
             return None

    # 2. Find JPG inside the specific directory
    # Note: case insensitive match
    files = glob.glob(os.path.join(target_dir, "*.[jJ][pP][gG]"))
    
    if not files:
        print(f"   ⚠️ No JPG files in: {os.path.basename(target_dir)}")
        return None
        
    # Return latest file
    return max(files, key=os.path.getmtime)

    # Return latest file
    return max(files, key=os.path.getmtime)

def push_row_to_db(row, col_mapping):
    """
    Helper to push a single Excel row to DB.
    Returns True if successful, False otherwise.
    """
    site = str(row[col_mapping['site']]).strip()
    mission = str(row[col_mapping['mission']]).strip()
    insp_name = str(row[col_mapping['insp']]).strip()
    
    # Resolve Image
    img_path = get_image_file_from_dir(config.BASE_DIR, mission, insp_name)
    
    if not img_path:
        # print(f"   ⚠️ Image not found for: {insp_name}") # Verbose?
        return False
        
    print(f"   🎯 Match Found: {insp_name}")
    print(f"      Process: {mission} -> {os.path.basename(img_path)}")

    # Insert to DB
    db = SessionLocal()
    try:
        # 1. Ensure InspectionPoint (Master Info) exists
        existing_point = db.query(InspectionPoint).filter(
            InspectionPoint.mission_name == mission,
            InspectionPoint.inspection_name == insp_name
        ).first()

        if not existing_point:
            # print(f"⚠️ Master Info missing. Creating...")
            
            def get_val(key, default=None):
                v = row.get(key)
                return v if pd.notna(v) else default

            new_point = InspectionPoint(
                site=site,
                mission_name=mission,
                inspection_name=insp_name,
                inspection_point_type=get_val("inspection_point_type"),
                facility_1=get_val("facility_1"),
                facility_2=get_val("facility_2"), 
                model_type=get_val("model_type"),
                model_ver=get_val("model_ver"),
                min_value=get_val("min_value"),
                max_value=get_val("max_value"),
                normal_min_value=get_val("normal_min_value"),
                normal_max_value=get_val("normal_max_value"),
                comment=get_val("comment"),
                query=get_val("query"),
                report_name=get_val("report_items") 
            )
            db.add(new_point)
            db.commit() 
        
        # 2. Create Task
        abs_path = str(Path(img_path).resolve())
        
        new_task = InspectionData(
            site=site,
            mission_name=mission,
            inspection_time=datetime.now(), 
            data_raw_dir=abs_path,
            data_result_dir=insp_name, 
            state=DiagnosisState.QUEUED
        )
        
        db.add(new_task)
        db.commit()
        db.refresh(new_task)
        
        print(f"✅ Task Created! [ID: {new_task.id}] {insp_name}")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ DB Insert Failed: {e}")
        return False
    finally:
        db.close()

def getch():
    """Reads a single character from stdin without requiring return."""
    import tty, termios
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def interactive_mode():
    excel_path = config.EXCEL_FILE
    if not os.path.exists(excel_path):
        print(f"❌ Excel file not found: {excel_path}")
        return

    print(f"📖 Reading Excel: {excel_path}")
    try:
        df = pd.read_excel(excel_path, header=0)
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        col_mapping = {
            'site': "site",
            'mission': "mission_name",
            'insp': "inspection_name"
        }
        
        if col_mapping['insp'] not in df.columns:
            print(f"❌ Column '{col_mapping['insp']}' not found.")
            return

        print(f"✅ Loaded {len(df)} rows.")
        print("⌨️  Interactive Mode: Press 'd' for Next, 'a' for Previous. (q to quit)")
        
        # User explicitly set current_idx to start from 157 in previous edit
        # Keeping use of current_idx as the "Next" pointer.
        current_idx = 157
        
        last_pushed_insp = None
        
        while True:
            print("\n👉 Ready. [d]=Next, [a]=Previous, [s]=Same, [q]=Quit... ", end="", flush=True)
            char = getch()
            print() 
            
            if char.lower() == 'q':
                break
            
            if char.lower() == 's':
                # Push SAME task again (the one we just pushed or passed)
                target_idx = current_idx - 1
                if target_idx >= 0:
                    row = df.iloc[target_idx]
                    print(f"🔄 Re-pushing Same Task (Row {target_idx})...")
                    push_row_to_db(row, col_mapping)
                else:
                    print("⚠️ No valid task to re-push.")
                continue

            if char.lower() == 'a':
                # Move Backward (Previous)
                # We want to go back to the one BEFORE the last one we handled.
                # current_idx (Next) -> Last (idx-1) -> Previous (idx-2)
                search_idx = current_idx - 2
                found_back = False
                
                if search_idx < 0:
                    print("⚠️ Start of list reached.")
                    continue

                print(f"🔄 Searching Previous (starting from row {search_idx})...")
                
                scanned = 0
                while search_idx >= 0:
                    row = df.iloc[search_idx]
                    
                    if push_row_to_db(row, col_mapping):
                        last_pushed_insp = str(row[col_mapping['insp']]).strip()
                        current_idx = search_idx + 1 # Update Next pointer
                        found_back = True
                        break
                    
                    search_idx -= 1
                    scanned += 1
                    if scanned % 50 == 0:
                        print(f"   ... scanned {scanned} rows back ...")
                
                if not found_back:
                    print("⚠️ No valid previous tasks found.")


            elif char.lower() == 'd':
                # Move Forward (Next)
                found = False
                scanned = 0
                
                while current_idx < len(df):
                    row = df.iloc[current_idx]
                    current_idx += 1
                    
                    insp_name = str(row[col_mapping['insp']]).strip()
                    
                    # Skip duplicates only if consecutive match with *actual last pushed*
                    # This prevents spamming d on same image
                    if insp_name == last_pushed_insp:
                        continue
                        
                    scanned += 1
                    if push_row_to_db(row, col_mapping):
                        last_pushed_insp = insp_name
                        found = True
                        break
                    
                    if scanned % 50 == 0:
                        print(f"   ... scanned {scanned} distinct rows forward ...")

                if not found:
                    print("⚠️ No more valid tasks found in Excel.")
            else:
                pass
                
    except Exception as e:
         print(f"❌ Error: {e}")
         import traceback
         traceback.print_exc()

def push_task_from_excel(keyword=None):
    """
    Original single-shot search mode.
    """
    excel_path = config.EXCEL_FILE
    if not os.path.exists(excel_path): return

    try:
        df = pd.read_excel(excel_path, header=0)
        df.columns = [str(c).strip().lower() for c in df.columns]
        col_mapping = {'site': "site", 'mission': "mission_name", 'insp': "inspection_name"}

        if keyword:
            print(f"🔎 Searching for keyword: '{keyword}'")
            mask = df['inspection_name'].astype(str).str.contains(keyword, case=False, na=False)
            results = df[mask]
        else:
            # If no keyword provided, maybe default to interactive?
            interactive_mode() 
            return

        if results.empty:
            print("❌ No matching rows found.")
            return

        # Push first match
        for idx, row in results.iterrows():
            if push_row_to_db(row, col_mapping):
                break

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        keyword = sys.argv[1]
        push_task_from_excel(keyword)
    else:
        # Default to interactive mode if no arguments
        interactive_mode()
