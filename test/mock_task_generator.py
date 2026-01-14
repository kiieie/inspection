import os
import time
import sys
from pathlib import Path
from datetime import datetime
from loguru import logger

# [Relocation Fix] 부모 디렉토리를 path에 추가하여 상위 모듈 임포트 가능케 함
sys.path.append(str(Path(__file__).resolve().parent.parent))

import config
from database import SessionLocal
from main import DiagnosisSystem

# [RULE] 하이픈(-) 포함 디렉토리 동적 임포트
def load_models():
    models_path = Path(config.DB_CONFIG['models_dir']) / config.DB_CONFIG['models_file']
    spec = importlib.util.spec_from_file_location("models", str(models_path))
    models = importlib.util.module_from_spec(spec)
    sys.modules["models"] = models
    spec.loader.exec_module(models)
    return models

models = load_models()
InspectionPoint = models.InspectionPoint
InspectionData = models.InspectionData
DiagnosisState = models.DiagnosisState

def run_generator():
    """
    3초마다 InspectionPoint에서 데이터를 하나씩 가져와 InspectionData(태스크)를 생성합니다.
    """
    logger.info("🚀 Mock Task Generator 시작 (3초 간격)")
    system_setup = DiagnosisSystem()
    db = SessionLocal()
    
    try:
        # 모든 InspectionPoint 데이터를 리스트로 가져옴
        points = db.query(InspectionPoint).all()
        if not points:
            logger.warning("⚠️ DB에 InspectionPoint 데이터가 없습니다. 먼저 동기화를 진행하세요.")
            return

        idx = 0
        total = len(points)
        
        while True:
            point = points[idx % total]
            
            # 사용자 요구사항에 따른 경로 생성 로직
            # data_raw_dir: get_latest_image 사용
            raw_path = system_setup.get_latest_image(
                system_setup.base_path, 
                point.mission_name, 
                point.inspection_name
            )
            
            # data_result_dir: inspection_name_result 대응 (없을 경우 _result 접미사 사용)
            # 엑셀에 해당 컬럼이 없으므로 안전하게 처리
            insp_name_res = point.inspection_name + "_result"
            result_path = system_setup.get_latest_image(
                system_setup.base_path, 
                point.mission_name, 
                insp_name_res
            )
            
            # 경로가 발견되지 않을 경우 기본값 처리
            raw_path = raw_path if raw_path else f"/mock/raw/{point.mission_name}/{point.inspection_name}"
            result_path = result_path if result_path else f"/mock/result/{point.mission_name}/{point.inspection_name}"

            # 태스크 생성
            new_task = InspectionData(
                site=point.site,
                mission_name=point.mission_name,
                inspection_time=datetime.utcnow(),
                data_raw_dir=raw_path,
                data_result_dir=result_path,
                state=DiagnosisState.QUEUED
            )
            
            db.add(new_task)
            db.commit()
            
            logger.success(f"📝 [TASK ADDED] ID: {new_task.id} | Spot: {point.inspection_name} | State: {new_task.state}")
            
            idx += 1
            time.sleep(3)
            
    except KeyboardInterrupt:
        logger.info("🛑 Generator를 중단합니다.")
    except Exception as e:
        logger.error(f"❌ Generator 실행 중 에러 발생: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_generator()
