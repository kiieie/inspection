import pytest
import pandas as pd
import os
from main import DiagnosisSystem

@pytest.fixture
def system_setup():
    """실제 경로의 엑셀 파일을 사용하여 시스템 객체 생성"""
    # 사용자가 지정한 실제 경로와 파일명
    BASE_DIR = "/home/kiie/synology/Projects/R25IA04"
    EXCEL_FILE = "Inspection_point, Labeling_251215.xlsx"
    
    # 실제 파일이 있는지 먼저 확인 (없으면 테스트 실패)
    assert os.path.exists(os.path.join(BASE_DIR, EXCEL_FILE)), "실제 엑셀 파일이 경로에 없습니다!"
    
    return DiagnosisSystem(BASE_DIR, EXCEL_FILE)

def test_excel_data_loading(system_setup):
    """실제 엑셀 데이터가 제대로 로드되었는지 검사"""
    df = system_setup.df
    
    # 1. 데이터프레임이 비어있지 않은지 확인
    assert not df.empty
    
    # 2. 특정 컬럼이 존재하는지 확인 (예: Point, Label 컬럼이 있는지)
    assert "Point" in df.columns
    print(f"\n로드된 데이터 개수: {len(df)}개")
    
def test_get_latest_image_no_folder(system_setup):
    # 2. 폴더가 아예 없을 때 (None 반환 여부)
    latest = system_setup.get_latest_image("non_exist", "fac_1")
    assert latest is None

def test_get_latest_image_empty_folder(tmp_path, system_setup):
    # 3. 폴더는 있지만 이미지가 없을 때
    mission_dir = tmp_path / "empty_mission.walk" / "fac_1"
    mission_dir.mkdir(parents=True)
    
    latest = system_setup.get_latest_image("empty_mission", "fac_1")
    assert latest is None

def test_get_latest_image_only_non_images(tmp_path, system_setup):
    # 4. 다른 확장자 파일(txt 등)만 있을 때 무시하는지 테스트
    mission_dir = tmp_path / "text_mission.walk" / "fac_1"
    mission_dir.mkdir(parents=True)
    (mission_dir / "report.txt").write_text("this is not an image")
    
    latest = system_setup.get_latest_image("text_mission", "fac_1")
    assert latest is None