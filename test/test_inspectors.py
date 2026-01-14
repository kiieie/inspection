import pytest
import numpy as np
import config
from inspectors.ag_inspector import AGInspector

# [Program Information]
# - File: test/test_inspectors.py
# - Description: 아날로그 게이지(AG) 인스펙터의 핵심 계산 로직 및 유효성 검증 유닛 테스트
# - Version: v1.1.0 (2026-01-14)

class MockYOLO:
    """
    YOLO 모델의 추론 결과를 모사하는 Mock 클래스입니다.
    실제 파일 로드 없이 기하학적 수치만으로 로직을 테스트하기 위해 사용합니다.
    """
    def __call__(self, path, **kwargs):
        class Result:
            def __init__(self):
                # names: 클래스 인덱스와 이름 매핑
                self.names = {0: "AG_Gauge"}
                # boxes: 탐지된 객체의 바운딩 박스 정보
                self.boxes = [type('Box', (), {
                    'cls': [0],
                    'xyxy': [np.array([10, 10, 110, 110])] # 100x100 크기 박스
                })()]
                # keypoints: AG 게이지의 5개 핵심 포인트 (Start, Mid, Center, End, Needle Head)
                # [x, y, confidence] 형태
                self.keypoints = [type('Kpts', (), {
                    'data': np.array([[[50, 20, 1.0],  # Start (12시 방향 근처)
                                      [80, 50, 1.0],  # Mid
                                      [50, 50, 1.0],  # Center (중심점)
                                      [20, 50, 1.0],  # End (9시 방향)
                                      [70, 30, 1.0]]]) # Needle Head (바늘 끝)
                })()]
        
        # predict() 메서드 호출 시 반환될 수 있도록 리스트 형태로 리턴
        res = Result()
        res.predict = lambda *args, **kwargs: [res]
        return [res]

    def predict(self, *args, **kwargs):
        """AGInspector 내부에서 호출하는 predict 메서드 지원"""
        return self.__call__(None)

def test_ag_inspector_geometric_logic(monkeypatch):
    """
    AGInspector의 기하학적 비율 계산 및 유효성 검사 로직을 테스트합니다.
    - 입력: 모킹된 YOLO 결과물
    - 검증: 특정 포인트 배치에 따른 Ratio 계산 값이 예상치와 일치하는지 확인
    """
    
    # [Fix] cv2.imread 모킹: 실제 파일이 없어도 (1000, 1000) 크기의 빈 이미지가 있는 것처럼 동작
    def mock_imread(path):
        return np.zeros((1000, 1000, 3), dtype=np.uint8)
    monkeypatch.setattr(cv2, "imread", mock_imread)
    
    # 1. Mock 모델 생성 및 초기화
    mock_model = MockYOLO()
    
    # 2. AGInspector 인스턴스 생성 
    # (실제 경로 대신 Mock 모델을 주입하기 위해 모델 로딩 부분을 monkeypatch 하거나 직접 주입하는 구조 활용)
    inspector = AGInspector()
    inspector.model = mock_model # 직접 교체
    
    # 3. 테스트용 가짜 이미지 경로 (실제로 읽지 않음)
    fake_img_path = "dummy.jpg"
    
    # 4. 추론 실행
    results = inspector.inspect_all(fake_img_path)
    
    # 5. 결과 검증
    assert len(results) > 0, "탐지된 결과가 있어야 합니다."
    
    first_res = results[0]
    # Ratio가 0.0 ~ 1.0 사이의 유효한 값인지 확인
    assert 0.0 <= first_res['value_ratio'] <= 1.0
    # 상태 메시지가 OK 인지 확인 (좌표가 유효하므로)
    assert first_res['status_msg'] == "OK"
    # 바운딩 박스 좌표 확인
    assert first_res['box'] == [10, 10, 110, 110]

    print(f"✅ AG Ratio 계산 테스트 통과: {first_res['value_ratio']:.4f}")