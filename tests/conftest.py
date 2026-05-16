import pytest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config.env import DB_PATH


@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
    return engine


@pytest.fixture
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="session")
def system_setup():
    from main import DiagnosisSystem
    system = DiagnosisSystem()
    return system


@pytest.fixture
def sample_excel(tmp_path):
    import pandas as pd
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
