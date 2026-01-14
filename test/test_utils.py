import pytest
import os
from main import DiagnosisSystem

def test_get_latest_image(tmp_path):
    """get_latest_image가 가장 최근에 수정된 이미지를 올바르게 찾는지 검증"""
    # 테스트 구조 생성: base_dir/mission.walk/mission.walk_insp/
    mission = "TestMission"
    insp = "TestInsp"
    target_dir = tmp_path / f"{mission}.walk" / f"{mission}.walk_{insp}"
    target_dir.mkdir(parents=True)
    
    # 두 개의 이미지 생성 (시간차를 둠)
    img1 = target_dir / "image1.jpg"
    img1.write_text("fake image 1")
    
    import time
    time.sleep(0.1)
    
    img2 = target_dir / "image2.jpg"
    img2.write_text("fake image 2")
    
    # 최신 이미지가 img2인지 확인
    latest = DiagnosisSystem.get_latest_image(str(tmp_path), mission, insp)
    
    assert latest is not None
    assert os.path.basename(latest) == "image2.jpg"

def test_get_latest_image_empty(tmp_path):
    """이미지가 없을 경우 None을 반환하는지 검증"""
    mission = "EmptyMission"
    insp = "EmptyInsp"
    target_dir = tmp_path / f"{mission}.walk" / f"{mission}.walk_{insp}"
    target_dir.mkdir(parents=True)
    
    latest = DiagnosisSystem.get_latest_image(str(tmp_path), mission, insp)
    assert latest is None
