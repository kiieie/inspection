"""core/matching.py 핵심 로직 검증"""
import pytest
from core.matching import (
    is_type_compatible,
    evaluate_gauge_reading,
    sort_by_x_priority,
    sort_by_grid_position,
    normalize_text,
)


class TestIsTypeCompatible:
    def test_exact_match(self):
        assert is_type_compatible("LED_Green_on", "LED_Green_on")

    def test_label_map_lookup(self):
        # AG_Pressure01_P-0-1 → AG_Pressure01_NA_NA (via LABEL_MAP)
        assert is_type_compatible("AG_Pressure01_P-0-1", "AG_Pressure01_NA_NA")

    def test_suffix_ok(self):
        assert is_type_compatible("LED_Green_on", "LED_Green_on_ok")

    def test_suffix_nok(self):
        assert is_type_compatible("LED_Green_off", "LED_Green_off_nok")

    def test_no_match(self):
        assert not is_type_compatible("AG_Pressure01_P-0-1", "DG_Temp_Air-Conditioner_NA")

    def test_fuzzy_dg(self):
        # DG_Air-Conditioner core = "airconditioner" ⊂ "dg_temp_air-conditioner_na"
        assert is_type_compatible("DG_Air-Conditioner", "DG_Temp_Air-Conditioner_NA")

    def test_dash_underscore_normalization(self):
        assert is_type_compatible("AG_Thermo-hygro", "AG_Thermo-hygro_NA_NA")


class TestEvaluateGaugeReading:
    def _row(self, mn=0, mx=100, nmn=20, nmx=80):
        return {"min_value": mn, "max_value": mx, "normal_min_value": nmn, "normal_max_value": nmx}

    def test_ratio_pass(self):
        det = {"value_ratio": 0.5}  # 50 → within 20~80
        val, status, ok = evaluate_gauge_reading(det, self._row())
        assert status == "PASS" and ok

    def test_ratio_fail(self):
        det = {"value_ratio": 0.0}  # 0 → below 20
        val, status, ok = evaluate_gauge_reading(det, self._row())
        assert status == "FAIL" and not ok

    def test_direct_value_pass(self):
        det = {"value": 50.0}
        val, status, ok = evaluate_gauge_reading(det, self._row())
        assert val == 50.0 and status == "PASS"

    def test_direct_value_fail(self):
        det = {"value": 90.0}
        val, status, ok = evaluate_gauge_reading(det, self._row())
        assert status == "FAIL"

    def test_text_value_returns_unknown(self):
        det = {"value": "OCR Disabled"}
        val, status, ok = evaluate_gauge_reading(det, self._row())
        assert val == "OCR Disabled" and status == "Unknown"

    def test_missing_value_and_ratio(self):
        det = {}
        val, status, ok = evaluate_gauge_reading(det, self._row())
        assert val is None and status == "No Value"


class TestSortByXPriority:
    def _det(self, x1, y1, x2, y2):
        return {"box": [x1, y1, x2, y2]}

    def test_left_first(self):
        dets = [self._det(100, 0, 200, 50), self._det(10, 0, 60, 50)]
        result = sort_by_x_priority(dets)
        assert result[0]["box"][0] == 10

    def test_empty(self):
        assert sort_by_x_priority([]) == []


class TestNormalizeText:
    def test_lowercase_strip(self):
        assert normalize_text("  Hello World  ") == "hello_world"
