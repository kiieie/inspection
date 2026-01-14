import pytest
import pandas as pd
from main import DiagnosisSystem
from inspectors.sw_led_inspector import SW_LED_Inspector

def test_pipeline_initialization(system_setup):
    """DiagnosisSystem 초기화 및 기본 필드 확인"""
    assert system_setup.detector is not None
    assert system_setup.ag_inspector is not None
    assert system_setup.dg_inspector is not None
    assert system_setup.sw_led_inspector is not None

def test_sw_led_inspector_compliance():
    """SW_LED_Inspector의 상태 일치 판정 로직 검증"""
    inspector = SW_LED_Inspector()
    
    # 정상 케이스
    ok, reason = inspector.check_status_compliance("LED_Green_on_ok", "LED_Green_on")
    assert ok is True
    
    # 상태 불일치 케이스
    ok, reason = inspector.check_status_compliance("LED_Green_off_ok", "LED_Green_on")
    assert ok is False
    assert "Mismatch" in reason

def test_diagnosis_system_run_empty(system_setup, monkeypatch):
    """데이터가 없을 때 run 메서드가 예외 없이 동작하는지 확인"""
    # 실제 실행을 막기 위해 필요한 부분만 모킹하거나 빈 데이터프레임 확인
    system_setup.df = pd.DataFrame()
    # run() 메서드가 아직 구현 전이거나 pass인 경우를 대비
    system_setup.run() 