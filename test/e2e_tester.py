
import os
import sys
import time
import pandas as pd
from datetime import datetime
from loguru import logger
import subprocess

# 프로젝트 경로 추가
sys.path.insert(0, os.getcwd())

import config
from database import SessionLocal, engine
import importlib.util
from pathlib import Path

# [DB Setup]
spec = importlib.util.spec_from_file_location("models", str(Path(config.DB_CONFIG['models_dir']) / config.DB_CONFIG['models_file']))
models = importlib.util.module_from_spec(spec)
sys.modules["models"] = models
spec.loader.exec_module(models)

def run_test():
    logger.info("🧪 [Test] End-to-End System Test Started (2026-01-13)")
    
    # 1. DB 초기화
    models.InspectionData.__table__.drop(engine, checkfirst=True)
    models.InspectionResult.__table__.drop(engine, checkfirst=True)
    models.InspectionData.__table__.create(engine)
    models.InspectionResult.__table__.create(engine)
    logger.info("✅ DB Tables Resetted.")

    # 2. Watcher 실행 (비동기)
    watcher_proc = subprocess.Popen([sys.executable, "test/diagnosis_watcher.py"])
    logger.info("🚀 Watcher Started in background.")
    time.sleep(3)

    # 3. 데이터 수동 주입 (Filler 역할 시뮬레이션 - Interactive Mode 검증용)
    db = SessionLocal()
    points = db.query(models.InspectionPoint).limit(3).all()
    
    for idx, p in enumerate(points):
        # Filler 로직: 이미지 찾기 (main.DiagnosisSystem.get_latest_image와 유사)
        import glob
        path = os.path.join(config.BASE_DIR, f"{p.mission_name}.walk", f"{p.mission_name}.walk_{p.inspection_name}")
        files = glob.glob(os.path.join(path, "*.[jJ][pP][gG]"))
        img_path = max(files, key=os.path.getmtime) if files else "No Image"
        
        new_task = models.InspectionData(
            site=p.site,
            mission_name=p.mission_name,
            inspection_time=datetime.now(),
            data_raw_dir=os.path.abspath(img_path),
            data_result_dir=p.inspection_name,
            state=models.DiagnosisState.QUEUED
        )
        db.add(new_task)
        db.commit()
        logger.info(f"📤 Pushed Task {idx+1}: {p.inspection_name} (ID: {new_task.id})")
        time.sleep(10) # 진단 및 전시 시간 대기

    # 4. 결과 확인
    logger.info("🔍 Fetching Results from DB...")
    results = db.query(models.InspectionResult).limit(10).all()
    df = pd.DataFrame([r.__dict__ for r in results])
    if '_sa_instance_state' in df.columns: df = df.drop(columns=['_sa_instance_state'])
    
    print("\n--- Integrated Inspection Results (Master + Actual) ---")
    cols = ['id', 'inspection_name', 'inspection_point_type', 'min_value', 'max_value', 'result_value', 'judgement']
    print(df[cols].to_string(index=False))
    
    # 5. 종료
    watcher_proc.terminate()
    db.close()
    logger.success("✅ E2E Test Completed.")

if __name__ == "__main__":
    run_test()
