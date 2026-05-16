"""AGInspector 단위 테스트 — 모델 파일 없이 로직만 검증"""
import math
import numpy as np
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def inspector():
    with patch("core.matching.LABEL_MAP", {}):
        with patch("ultralytics.YOLO", MagicMock()):
            from importlib import reload
            import inspectors.ag_inspector as mod
            with patch.object(mod, "MODEL_CONFIG", {"ag_pose": "dummy.pt"}):
                inst = mod.AGInspector.__new__(mod.AGInspector)
                inst.KP_IDX = {"Start": 0, "Mid": 1, "Center": 2, "End": 3, "ND_HEAD": 4}
                return inst


class TestCalculateRatio:
    def _make_inspector(self):
        with patch("ultralytics.YOLO", MagicMock()):
            from inspectors.ag_inspector import AGInspector
            inst = AGInspector.__new__(AGInspector)
            inst.KP_IDX = {"Start": 0, "Mid": 1, "Center": 2, "End": 3, "ND_HEAD": 4}
            return inst

    def test_ratio_at_start_is_zero(self):
        inst = self._make_inspector()
        c = np.array([200.0, 200.0])
        s = np.array([200.0, 100.0])   # top (12 o'clock)
        e = np.array([300.0, 200.0])   # right (3 o'clock)
        h = np.array([200.0, 100.0])   # head == start → ratio 0
        ratio = inst._calculate_ratio(c, s, e, h)
        assert ratio == pytest.approx(0.0, abs=0.05)

    def test_ratio_at_end_is_one(self):
        inst = self._make_inspector()
        c = np.array([200.0, 200.0])
        s = np.array([200.0, 100.0])
        e = np.array([300.0, 200.0])
        h = np.array([300.0, 200.0])   # head == end → ratio 1
        ratio = inst._calculate_ratio(c, s, e, h)
        assert ratio == pytest.approx(1.0, abs=0.05)

    def test_ratio_midpoint(self):
        inst = self._make_inspector()
        # Simple case: start=top, end=bottom (180° span)
        c = np.array([0.0, 0.0])
        s = np.array([0.0, -100.0])    # top
        e = np.array([0.0, 100.0])     # bottom
        h = np.array([100.0, 0.0])     # right = midpoint
        ratio = inst._calculate_ratio(c, s, e, h)
        assert 0.4 <= ratio <= 0.6
