import pytest
import pandas as pd
from main import DiagnosisSystem

@pytest.fixture
def mock_excel(tmp_path):
    # 테스트용 엑셀 데이터 생성
    data = {
        'mission_name': ['M1', 'M2'],
        'facility_1': ['F1', 'F2'],
        'inspection_point_type': ['AG_Gauge', 'SW_Button'],
        'min_value': [0, 0],
        'max_value': [100, 0],
        'normal_min': [20, 0],
        'normal_max': [80, 0]
    }
    df = pd.DataFrame(data)
    path = tmp_path / "test.xlsx"
    df.to_excel(path, index=False)
    return path

def test_pipeline_missing_image(mock_excel, tmp_path):
    # 이미지가 없는 상황에서의 파이프라인 견고성 테스트
    system = DiagnosisSystem(str(tmp_path), "test.xlsx")
    results = system.run()
    
    # 이미지가 없으므로 'Image Missing'이 들어가야 함
    assert results['diagnosis_result'].iloc[0] == "Image Missing"

def test_sw_inspector_error_handling():
    from inspectors.sw_inspector import SWInspector
    
    # 모델이 None을 반환하여 에러가 발생하는 상황 시뮬레이션
    inspector = SWInspector(model=lambda x: None)
    res = inspector.inspect("fake.jpg", {"inspection_point_type": "SW_Test"})
    
    assert res['status'] == "Error"
    assert "reason" in res