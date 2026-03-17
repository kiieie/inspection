import sys
import os
import glob
import pandas as pd
from pathlib import Path
from datetime import datetime
import importlib.util
import time
import select

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
            inspection_time=datetime.now().replace(microsecond=0), 
            data_raw_dir=abs_path,
            data_result_dir="", 
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
    """Reads a single character from stdin without requiring return (Cross-platform)."""
    if os.name == 'nt':
        import msvcrt
        # msvcrt.getch() returns bytes, needs decoding
        return msvcrt.getch().decode('utf-8')
    else:
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
            elif char.lower() == 'f':
                # Jump to Next Inspection Point & Push LATEST
                current_insp = str(df.iloc[current_idx-1][col_mapping['insp']]).strip() if current_idx > 0 else None
                found_next = False
                
                search_idx = current_idx
                while search_idx < len(df):
                    row = df.iloc[search_idx]
                    insp_name = str(row[col_mapping['insp']]).strip()
                    if insp_name != current_insp:
                        found_next = True
                        break
                    search_idx += 1
                
                if found_next:
                    row = df.iloc[search_idx]
                    mission = str(row[col_mapping['mission']]).strip()
                    insp_name = str(row[col_mapping['insp']]).strip()
                    
                    print(f"   ⏩ Jumping to: {insp_name}")
                    if push_row_to_db(row, col_mapping):
                        last_pushed_insp = insp_name
                        current_idx = search_idx + 1
                    else:
                        print(f"   ⚠️ Failed to push latest for {insp_name}")
                        current_idx = search_idx + 1 # Still move there
                else:
                    print("   ⚠️ No more inspection points found.")
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


def push_tasks_from_folder():
    """
    config.BASE_DIR 하위의 폴더들을 스캔하여 인터랙티브하게 태스크를 생성합니다.
    폴더 구조: BASE_DIR / [PREFIX] / {site} / {mission} / {file_name}
    
    키 조작:
    - 'd': 현재 파일 Push 후 다음으로 이동
    - 's': 현재 파일 Skip 후 다음으로 이동
    - 'a': 이전 파일로 이동
    - 'q': 종료
    """
    import os
    from datetime import datetime
    
    base_dir = config.BASE_DIR
    prefix = getattr(config, 'IMAGE_PATH_PREFIX', "")
    
    if not os.path.exists(base_dir):
        print(f"❌ BASE_DIR not found: {base_dir}")
        return

    print(f"📂 Scanning BASE_DIR: {base_dir}")
    if prefix:
        print(f"   Prefix Filter: {prefix}")
    print("   Collecting files...")
    
    # Prefix가 있으면 해당 하위부터 스캔 시작
    scan_start_dir = os.path.join(base_dir, prefix) if prefix else base_dir
    
    if not os.path.exists(scan_start_dir):
        print(f"❌ Scan directory not found: {scan_start_dir}")
        return

    # Collect all valid files first
    file_list = []
    for root, dirs, files in os.walk(scan_start_dir):
        for file in files:
            if not file.lower().endswith((".jpg", ".jpeg")):
                continue
                
            full_path = os.path.join(root, file)
            # rel_path는 여전히 BASE_DIR 기준 (사용자 요청: BASE_DIR 제외한 나머지)
            rel_path = os.path.relpath(full_path, base_dir)
            
            # Path 파싱을 위해 Prefix 제외한 부분 추출
            if prefix:
                # rel_path_no_prefix = rel_path - prefix
                rel_path_no_prefix = os.path.relpath(full_path, scan_start_dir)
                parts = rel_path_no_prefix.split(os.sep)
            else:
                parts = rel_path.split(os.sep)
            
            # Check minimum depth (Site / Mission / insp_name / File)
            if len(parts) < 4:
                continue
            
            site = parts[0]
            mission = parts[1]
            insp_name = parts[2]
            file_name = parts[3]

            # [Smart Folder & Master Sync]
            # rel_folder_path is the key main.py uses to find images: BASE_DIR + insp_name
            rel_folder_path = os.path.relpath(root, base_dir)
            folder_name = os.path.basename(root)
            
            file_list.append({
                'rel_path': rel_path,
                'rel_folder_path': rel_folder_path,
                'site': site,
                'mission': mission,
                'insp_name': insp_name,
                'file_name': file_name,
            })
    
    # [Sort by Path] Ensure deterministic order for 'f' key logic
    file_list.sort(key=lambda x: x['rel_path'])

    total = len(file_list)
    print(f"✅ Found {total} valid files.")
    
    if total == 0:
        print("⚠️ No files to process.")
        return
    
    print("⌨️  Interactive Mode: [d]=Push & Next, [f]=Next Insp, [s]=Same, [a]=Prev, [q]=Quit")
    
    db = SessionLocal()
    current_idx = 0
    pushed_count = 0
    
    try:
        while 0 <= current_idx < total:
            item = file_list[current_idx]
            print(f"\n[{current_idx + 1}/{total}] Site={item['site']}, Mission={item['mission']}, Inspect={item['insp_name']}")
            print(f"   Path: {item['rel_path']}")
            
            # [Match Master Info]
            # DB의 InspectionPoint를 조회하여 일치하는 키를 찾습니다.
            folder_name = item['insp_name']
            
            # 1. 일치하는 마스터 정보 탐색
            point = db.query(InspectionPoint).filter(
                InspectionPoint.site == item['site'],
                InspectionPoint.mission_name == item['mission'],
                InspectionPoint.inspection_name == item['insp_name']
            ).first()
            
            if point:
                master_key = point.inspection_name
                print(f"   🎯 Matched Master: {master_key}")
            else:
                print(f"   ⚠️ Warning: No Master Info found for '{item['insp_name']}' in mission '{item['mission']}'")
                master_key = item['insp_name']



            print("   [d]=Push&Next, [f]=Next Insp, [n]=Skip&Next, [a]=Prev, [s]=Same, [q]=Quit: ", end="", flush=True)
            
            char_raw = getch()
            char = char_raw.lower()
            print(char_raw) # Echo the key
            
            if char == 'q':
                print("👋 Quit.")
                break
            elif char == 'd' or char == 's':
                # Push current
                new_task = InspectionData(
                    site=item['site'],
                    mission_name=item['mission'],
                    inspection_name=item['insp_name'],
                    inspection_time=datetime.now().replace(microsecond=0),
                    data_raw_dir=item['rel_path'],
                    data_result_dir="",
                    state=DiagnosisState.QUEUED
                )
                db.add(new_task)
                db.commit()
                db.refresh(new_task)
                pushed_count += 1
                
                status_icon = "✅" if char == 'd' else "🔄"
                print(f"   {status_icon} Pushed (ID: {new_task.id})")
                
                if char == 'd':
                    current_idx += 1
                # if 's', current_idx stays same
            elif char == 'f':
                # Jump to Next Inspection Point & Push LATEST
                current_insp = item['insp_name']
                next_idx = current_idx + 1
                found_next = False
                
                while next_idx < total:
                    if file_list[next_idx]['insp_name'] != current_insp:
                        found_next = True
                        break
                    next_idx += 1
                
                if found_next:
                    target_item = file_list[next_idx]
                    target_insp_name = target_item['insp_name']
                    
                    # Find LATEST image in the target folder
                    target_folder_rel = target_item['rel_folder_path']
                    target_folder_abs = os.path.join(base_dir, target_folder_rel)
                    
                    jpg_files = glob.glob(os.path.join(target_folder_abs, "*.[jJ][pP][gG]"))
                    if jpg_files:
                        latest_jpg_abs = max(jpg_files, key=os.path.getmtime)
                        latest_jpg_rel = os.path.relpath(latest_jpg_abs, base_dir)
                        
                        print(f"   ⏩ Jumping to: {target_insp_name}")
                        print(f"   🎯 Latest Image: {os.path.basename(latest_jpg_rel)}")
                        
                        new_task = InspectionData(
                            site=target_item['site'],
                            mission_name=target_item['mission'],
                            inspection_name=target_item['insp_name'],
                            inspection_time=datetime.now().replace(microsecond=0),
                            data_raw_dir=latest_jpg_rel,
                            data_result_dir="",
                            state=DiagnosisState.QUEUED
                        )
                        db.add(new_task)
                        db.commit()
                        db.refresh(new_task)
                        pushed_count += 1
                        print(f"   ✅ Pushed (ID: {new_task.id})")
                        
                        # Update current_idx to the first file of the next folder
                        current_idx = next_idx
                    else:
                        print(f"   ⚠️ No JPG files found in next folder: {target_insp_name}")
                        current_idx = next_idx # Still move there
                else:
                    print("   ⚠️ No more inspection points found.")
            elif char == 'n':
                # Skip & Next
                print("   ⏭️ Skipped.")
                current_idx += 1
            elif char == 'a':
                # Go back
                if current_idx > 0:
                    current_idx -= 1
                    print(f"   ◀️  Moved back to {current_idx + 1}")
                else:
                    print("   ⚠️ Already at the beginning.")
            else:
                print(f"   💡 Unknown key: {repr(char_raw)}. Use [d, n, a, s, q]")

        
        print(f"\n✅ Done. Total Pushed: {pushed_count}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
    finally:
        db.close()
        
def scan_auto():
    """
    config.BASE_DIR 하위의 파일들을 스캔하여 기존 리스트와 비교하고,
    변경사항이 있으면 리스트를 갱신하며 새 파일을 DB에 추가합니다.
    """
    config_dir = PROJECT_ROOT / "config"
    config_dir.mkdir(exist_ok=True)
    list_path = config_dir / "push_file_list"
    
    # 1. 기존 리스트 로드
    existing_files = set()
    if list_path.exists():
        with open(list_path, "r", encoding="utf-8") as f:
            existing_files = {line.strip() for line in f if line.strip()}
    
    # 2. 현재 파일 스캔
    base_dir = config.BASE_DIR
    current_files = []
    print(f"📂 Scanning BASE_DIR for changes: {base_dir}")
    
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.lower().endswith((".jpg", ".jpeg", ".png")):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, base_dir)
                current_files.append(rel_path)
    
    current_files.sort()
    current_files_set = set(current_files)
    
    # 3. 변경 감지 및 처리
    if current_files_set == existing_files:
        print("✅ No changes detected. File list is up to date.")
        return

    print("⚠️ Changes detected in BASE_DIR!")
    
    # 새 파일 식별
    new_files = current_files_set - existing_files
    if new_files:
        print(f"🆕 Found {len(new_files)} new files. Synchronizing with DB...")
        db = SessionLocal()
        try:
            added_count = 0
            for rel_path in sorted(list(new_files)):
                parts = rel_path.split(os.sep)
                # 예상 구조: Site / Mission / InspName / File
                if len(parts) >= 4:
                    site, mission, insp_name = parts[0], parts[1], parts[2]
                    
                    # 이미 존재하는지 확인
                    exists = db.query(InspectionPoint).filter(
                        InspectionPoint.site == site,
                        InspectionPoint.mission_name == mission,
                        InspectionPoint.inspection_name == insp_name
                    ).first()
                    
                    if not exists:
                        new_point = InspectionPoint(
                            site=site,
                            mission_name=mission,
                            inspection_name=insp_name,
                            inspection_point_type="Detected",
                            comment="Auto-detected via --scanauto"
                        )
                        db.add(new_point)
                        added_count += 1
            
            db.commit()
            print(f"✅ DB Synchronization complete. Added {added_count} new inspection points.")
        except Exception as e:
            db.rollback()
            print(f"❌ DB Update failed: {e}")
        finally:
            db.close()
    
    # 4. 리스트 갱신 저장
    with open(list_path, "w", encoding="utf-8") as f:
        for path in current_files:
            f.write(path + "\n")
    print(f"💾 Updated file list saved to: {list_path}")

def scan_auto():
    """
    config.BASE_DIR 하위의 파일들을 스캔하여 기존 리스트와 비교하고,
    변경사항이 있으면 리스트를 갱신하며 새 파일을 DB에 추가합니다.
    (60초 주기로 반복 수행하며 'q'를 누르면 종료합니다)
    """
    config_dir = PROJECT_ROOT / "config"
    config_dir.mkdir(exist_ok=True)
    list_path = config_dir / "push_file_list"
    
    print("🚀 Starting continuous scan mode. (Press 'q' to quit)")
    
    while True:
        # 1. 기존 리스트 로드
        existing_files = set()
        if list_path.exists():
            with open(list_path, "r", encoding="utf-8") as f:
                existing_files = {line.strip() for line in f if line.strip()}
        
        # 2. 현재 파일 스캔
        base_dir = config.BASE_DIR
        prefix = getattr(config, 'IMAGE_PATH_PREFIX', "")
        scan_dir = os.path.join(base_dir, prefix) if prefix else base_dir
        
        current_files = []
        # print(f"📂 Scanning for changes in: {scan_dir}")
        
        for root, dirs, files in os.walk(scan_dir):
            for file in files:
                if file.lower().endswith((".jpg", ".jpeg", ".png")):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, base_dir)
                    current_files.append(rel_path)
        
        current_files.sort()
        current_files_set = set(current_files)
        
        # 3. 변경 감지 및 처리
        if current_files_set != existing_files:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Changes detected in BASE_DIR!")
            
            # 새 파일 식별
            new_files = current_files_set - existing_files
            if new_files:
                print(f"🆕 Found {len(new_files)} new files. Synchronizing with DB...")
                db = SessionLocal()
                try:
                    added_count = 0
                    for rel_path in sorted(list(new_files)):
                        parts = rel_path.split(os.sep)
                        # config.IMAGE_PATH_PREFIX가 설정되어 있고 경로의 시작이 prefix와 같다면 prefix를 건너뜁니다.
                        prefix = getattr(config, 'IMAGE_PATH_PREFIX', "")
                        if prefix and len(parts) > 0 and parts[0] == prefix:
                            parts = parts[1:]

                        # 예상 구조: Site / Mission / InspName / File
                        if len(parts) >= 4:
                            site, mission, insp_name = parts[0], parts[1], parts[2]
                            
                            # 1. 마스터 정보 확인 및 생성
                            exists = db.query(InspectionPoint).filter(
                                InspectionPoint.site == site,
                                InspectionPoint.mission_name == mission,
                                InspectionPoint.inspection_name == insp_name
                            ).first()
                            
                            if not exists:
                                new_point = InspectionPoint(
                                    site=site,
                                    mission_name=mission,
                                    inspection_name=insp_name,
                                    inspection_point_type="Detected",
                                    comment="Auto-detected via --scanauto"
                                )
                                db.add(new_point)
                                db.flush() # ID 생성을 위해 flush

                            # 2. 태스크 생성 (InspectionData)
                            new_task = InspectionData(
                                site=site,
                                mission_name=mission,
                                inspection_name=insp_name,
                                inspection_time=datetime.now().replace(microsecond=0),
                                data_raw_dir=rel_path,
                                data_result_dir="",
                                state=DiagnosisState.QUEUED
                            )
                            db.add(new_task)
                            
                            try:
                                db.commit()
                                added_count += 1
                                print(f"   ✅ [New Task] {insp_name} ({os.path.basename(rel_path)})")
                            except Exception as e:
                                db.rollback()
                                print(f"   ❌ [DB Lock/Error] {insp_name}: {e}")
                
                    # 리스트 갱신 저장
                    with open(list_path, "w", encoding="utf-8") as f:
                        for path in current_files:
                            f.write(path + "\n")
                    if added_count > 0:
                        print(f"✅ DB Synchronization complete. Created {added_count} new tasks.")
                        print(f"💾 Updated file list saved to: {list_path}")
                except Exception as e:
                    print(f"❌ DB Session Error: {e}")
                finally:
                    db.close()
            
            # 리스트 갱신 저장
            with open(list_path, "w", encoding="utf-8") as f:
                for path in current_files:
                    f.write(path + "\n")
        else:
            # print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ No changes detected.")
            pass

        # 4. 'q' 입력 대기 (60초 또는 즉시 종료)
        if wait_for_quit(60):
            break

def wait_for_quit(timeout):
    """60초 동안 'q' 입력을 감시합니다."""
    import tty, termios
    fd = sys.stdin.fileno()
    if not os.isatty(fd):
        time.sleep(timeout)
        return False

    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        start_time = time.time()
        while time.time() - start_time < timeout:
            # 0.1초 간격으로 스캔
            rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
            if rlist:
                ch = sys.stdin.read(1)
                if ch.lower() == 'q':
                    print("\n👋 Stop signal ('q') received. Exiting...")
                    return True
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scan":
            push_tasks_from_folder()
        elif sys.argv[1] == "--scanauto":
            scan_auto()
        else:
            keyword = sys.argv[1]
            push_task_from_excel(keyword)
    else:
        # Default to interactive mode if no arguments
        interactive_mode()
