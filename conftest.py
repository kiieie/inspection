import pytest
import os
import sys
import pandas as pd
from pathlib import Path
import importlib.util
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import config as proj_config

# [conftest.py] 전역 테스트 설정 및 픽스처 관리

def pytest_configure(config):
    """모든 테스트 수집 및 실행 전 모델을 동적으로 임포트하여 전역 네임스페이스에 등록"""
    # models_path = Path(proj_config.DB_CONFIG['models_dir']) / proj_config.DB_CONFIG['models_file']
    # spec = importlib.util.spec_from_file_location("models", str(models_path))
    # models = importlib.util.module_from_spec(spec)
    # sys.modules["models"] = models
    # spec.loader.exec_module(models)
    pass

@pytest.fixture(scope="session")
def db_engine():
    """테스트용 DB 엔진 (메모리 내 SQLite 권장되나 현재 설정을 따름)"""
    engine = create_engine(f"sqlite:///{proj_config.DB_CONFIG['db_path']}", connect_args={"check_same_thread": False})
    return engine

@pytest.fixture
def db_session(db_engine):
    """각 테스트 전용 DB 세션"""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture(scope="session")
def system_setup():
    """DiagnosisSystem 인스턴스 (무거운 모델 로딩을 1회만 수행)"""
    from main import DiagnosisSystem
    system = DiagnosisSystem()
    return system

@pytest.fixture
def sample_excel(tmp_path):
    """테스트용 임시 엑셀 파일 생성"""
    data = {
        'site': ['TestSite'],
        'mission_name': ['TestMission'],
        'inspection_name': ['TestInsp'],
        'inspection_point_type': ['AG_Pressure_Fire-extinguisher'],
        'min_value': [0],
        'max_value': [1.5],
        'facility_1': ['F1'],
        'facility_2': ['F2']
    }
    df = pd.DataFrame(data)
    excel_file = tmp_path / "test_inspection.xlsx"
    df.to_excel(excel_file, sheet_name='inspection_point', index=False)
    return str(excel_file)
