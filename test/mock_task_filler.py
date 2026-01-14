
import os
import sys
import time
import glob
import pandas as pd
from datetime import datetime
from loguru import logger
from pathlib import Path
import importlib.util
import subprocess

# 프로젝트 경로 추가
sys.path.insert(0, os.getcwd())

import config
from database import SessionLocal

# [DB Setup]
spec = importlib.util.spec_from_file_location("models", str(Path(config.DB_CONFIG['models_dir']) / config.DB_CONFIG['models_file']))
models = importlib.util.module_from_spec(spec)
sys.modules["models"] = models
spec.loader.exec_module(models)

def kill_watcher():
    """Watcher 프로세스 강제 종료 (2026-01-14)"""
    try:
        subprocess.run(["pkill", "-f", "diagnosis_watcher.py"], check=False)
        logger.info("💀 [Filler] Watcher process terminated.")
    except Exception as e:
        logger.error(f"❌ Failed to kill watcher: {e}")

def find_actual_image(base_dir, site, mission, insp_name):
    """사용자 규격에 맞는 실제 이미지 경로 탐색"""
    pure_name = os.path.splitext(insp_name)[0]
    search_dir = os.path.join(base_dir, site, mission)
    if not os.path.exists(search_dir):
        search_dir = os.path.join(base_dir, f"{mission}.walk", f"{mission}.walk_{insp_name}")
        if not os.path.exists(search_dir): return None
            
    pattern = os.path.join(search_dir, f"{pure_name}*.[jJ][pP][gG]")
    files = glob.glob(pattern)
    return max(files, key=os.path.getmtime) if files else None

def run_mock_task_filler(loop=False, interactive=True):
    """
    점검 태스크 주입 프로세스
    - [Update 2026-01-14]: 'q' 입력 시 Watcher 동시 종료
    """
    logger.info(f"🚀 [Filler] 데이터 주입 시작 (Loop: {loop}, Interactive: {interactive})")
    if interactive:
        logger.info("👉 [Interactive Menu] 'Enter': Push | 'q': Exit (Kills Watcher too)")
        
    db = SessionLocal()
    points = db.query(models.InspectionPoint).all()
    if not points:
        logger.error("❌ DB 데이터 없음")
        return

    df_points = pd.DataFrame([p.__dict__ for p in points])
    if '_sa_instance_state' in df_points.columns:
        df_points = df_points.drop(columns=['_sa_instance_state'])
    
    groups = df_points[['site', 'mission_name', 'inspection_name']].drop_duplicates().values.tolist()
    idx = 0; total = len(groups)
    
    try:
        while True:
            if idx >= total and not loop:
                logger.success(f"✅ [Filler] 모든 사진 그룹 주입 완료.")
                break
            
            if interactive:
                user_cmd = input(f"\n[{idx+1}/{total}] Push next task? (Enter/q): ").strip().lower()
                if user_cmd == 'q':
                    logger.info("🛑 [Filler] 사용자 요청 종료.")
                    break
                
            site, mission, insp_name = groups[idx % total]
            img_path = find_actual_image(config.BASE_DIR, site, mission, insp_name)
            
            new_task = models.InspectionData(
                site=site, mission_name=mission, inspection_time=datetime.now(),
                data_raw_dir=os.path.abspath(img_path) if img_path else "No Image",
                data_result_dir=insp_name, state=models.DiagnosisState.QUEUED
            )
            db.add(new_task); db.commit()
            logger.info(f"📤 [Pushed] ID: {new_task.id} | {mission} / {insp_name}")
            idx += 1
            if not interactive: time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("🛑 [Filler] Interrupted.")
    finally:
        kill_watcher() # Watcher 동시 종료
        db.close()

if __name__ == "__main__":
    run_mock_task_filler(loop=False, interactive=True)
