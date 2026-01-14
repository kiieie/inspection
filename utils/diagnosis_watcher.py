import os
import time
import sys
from pathlib import Path
from loguru import logger

# [Relocation Fix] 부모 디렉토리를 path에 추가하여 상위 모듈 임포트 가능케 함
sys.path.append(str(Path(__file__).resolve().parent.parent))

import config
from database import SessionLocal

# [RULE] 하이픈(-) 포함 디렉토리 동적 임포트
def load_models():
    models_path = Path(config.DB_CONFIG['models_dir']) / config.DB_CONFIG['models_file']
    spec = importlib.util.spec_from_file_location("models", str(models_path))
    models = importlib.util.module_from_spec(spec)
    sys.modules["models"] = models
    spec.loader.exec_module(models)
    return models

models = load_models()
InspectionData = models.InspectionData
DiagnosisState = models.DiagnosisState

def run_watcher():
    """
    InspectionData 테이블의 QUEUED 상태 태스크를 감시하여 처리합니다.
    """
    logger.info("👀 Diagnosis Watcher 시작 (Polling...)")
    
    try:
        while True:
            db = SessionLocal()
            # 1. QUEUED 상태의 가장 오래된 태스크 하나를 가져옴
            task = db.query(InspectionData).filter(
                InspectionData.state == DiagnosisState.QUEUED
            ).order_by(InspectionData.inspection_time.asc()).first()
            
            if task:
                logger.info(f"🔍 [TASK FOUND] ID: {task.id} | Site: {task.site}")
                
                # 2. 상태를 RUNNING으로 변경
                task.state = DiagnosisState.RUNNING
                db.commit()
                logger.info(f"🏃 [STATE CHANGE] ID: {task.id} -> RUNNING")
                
                # 3. 진단 프로세스 시뮬레이션 (실제 구현 시 여기서 DiagnosisSystem 호출)
                logger.debug(f"⚙️ Processing task {task.id}...")
                time.sleep(1.5) # 처리 시간 시뮬레이션
                
                # 4. 상태를 COMPLETED (FINISHED 의미)로 변경
                task.state = DiagnosisState.COMPLETED
                db.commit()
                logger.success(f"✅ [TASK FINISHED] ID: {task.id} -> COMPLETED")
                
            db.close()
            time.sleep(1) # 부하 방지를 위한 폴링 간격
            
    except KeyboardInterrupt:
        logger.info("🛑 Watcher를 중단합니다.")
    except Exception as e:
        logger.error(f"❌ Watcher 실행 중 에러 발생: {e}")

if __name__ == "__main__":
    run_watcher()
