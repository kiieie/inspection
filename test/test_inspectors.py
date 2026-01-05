import pytest
from inspectors.ag_inspector import AGInspector

class MockYOLO:
    def __call__(self, path):
        class Result:
            names = {0: "AG_Gauge"}
            class boxes:
                cls = [0]
                xyxy = [[10, 10, 50, 50]]
        return [Result()]

def test_ag_inspector_logic():
    mock_model = MockYOLO()
    inspector = AGInspector(mock_model)
    
    spec = {
        'inspection_point_type': 'AG_Gauge',
        'min_value': 0,
        'max_value': 100,
        'normal_min': 20,
        'normal_max': 80
    }
    
    # 0.75(고정값) * (100 - 0) = 75 -> 정상범위(20~80) 이내
    result = inspector.inspect("fake_path.jpg", spec)
    
    assert result['is_normal'] is True
    assert result['value'] == 75
    assert result['point_type'] == 'AG_Gauge'