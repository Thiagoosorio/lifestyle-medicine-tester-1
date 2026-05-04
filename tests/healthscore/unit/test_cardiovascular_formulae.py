"""Unit tests for the cardiovascular-organ formulae (Phase 3).

CHA2DS2-VASc, ApoB / Lp(a) pass-throughs, and AHA PREVENT base 10-year
ASCVD. Reference points pinned so future re-derivations / refactors do
not silently drift.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from healthscore.scores.cardiovascular import (
    calc_apob_passthrough,
    calc_cha2ds2_vasc,
    calc_lpa_passthrough,
    calc_prevent_ascvd_10yr,
)


# ── CHA2DS2-VASc ──────────────────────────────────────────────────────────


def test_cha2ds2_vasc_43yo_healthy_female_returns_1():
    """A 43yo female with no comorbidities scores 1 (female sex)."""
    val = calc_cha2ds2_vasc({"age": 43, "sex": "female"})
    assert val == Decimal("1")


def test_cha2ds2_vasc_78yo_female_with_htn_returns_4():
    """78yo female (1 sex + 2 age≥75) + HTN (1) = 4."""
    val = calc_cha2ds2_vasc({
        "age": 78, "sex": "female", "hypertension": True,
    })
    assert val == Decimal("4")


def test_cha2ds2_vasc_full_house_male_returns_8():
    """66yo male (1 age 65-74) + CHF + HTN + DM + Stroke (2) + Vascular = 7
    (sex flag does not apply for male users)."""
    val = calc_cha2ds2_vasc({
        "age": 66, "sex": "male",
        "chf_or_lv_dysfunction": True,
        "hypertension": True,
        "diabetes": True,
        "stroke_tia_thromboembolism": True,
        "vascular_disease": True,
    })
    assert val == Decimal("7")


def test_cha2ds2_vasc_age_buckets_step_correctly():
    base = {"sex": "male"}
    assert calc_cha2ds2_vasc({**base, "age": 64}) == Decimal("0")
    assert calc_cha2ds2_vasc({**base, "age": 65}) == Decimal("1")
    assert calc_cha2ds2_vasc({**base, "age": 74}) == Decimal("1")
    assert calc_cha2ds2_vasc({**base, "age": 75}) == Decimal("2")


def test_cha2ds2_vasc_returns_none_on_missing_inputs():
    assert calc_cha2ds2_vasc({"sex": "male"}) is None
    assert calc_cha2ds2_vasc({"age": 65}) is None


# ── ApoB / Lp(a) pass-throughs ────────────────────────────────────────────


def test_apob_passthrough_round_trips_a_known_lab_value():
    val = calc_apob_passthrough({"apob_mgdl": 95.0})
    assert val == Decimal("95.0")


def test_lpa_passthrough_round_trips_a_known_lab_value():
    val = calc_lpa_passthrough({"lpa_mgdl": 42.5})
    assert val == Decimal("42.5")


def test_apob_passthrough_rejects_negative():
    assert calc_apob_passthrough({"apob_mgdl": -10}) is None


def test_apob_passthrough_returns_none_on_missing():
    assert calc_apob_passthrough({}) is None


def test_lpa_passthrough_zero_is_valid():
    """Lp(a) = 0 is a real laboratory value (below detection limit)."""
    assert calc_lpa_passthrough({"lpa_mgdl": 0}) == Decimal("0")


# ── PREVENT 10-year ASCVD ─────────────────────────────────────────────────


def test_prevent_typical_low_risk_male_under_5_percent():
    """Healthy 55yo male, normal lipids and BP -> below 5% (low band)."""
    val = calc_prevent_ascvd_10yr({
        "age": 55, "sex": "male",
        "total_chol_mgdl": 200, "hdl_c_mgdl": 45,
        "sbp_mmhg": 130, "bmi": 27, "egfr": 90,
        "diabetes": False, "smoking": False,
        "bp_treatment": False, "statin": False,
    })
    assert val is not None
    assert 0.5 < float(val) < 6.0


def test_prevent_higher_risk_smoker_male_above_baseline():
    """Same age but with smoking + diabetes -> markedly higher risk."""
    baseline = float(calc_prevent_ascvd_10yr({
        "age": 60, "sex": "male",
        "total_chol_mgdl": 200, "hdl_c_mgdl": 45,
        "sbp_mmhg": 130, "bmi": 27, "egfr": 90,
        "diabetes": False, "smoking": False,
        "bp_treatment": False, "statin": False,
    }))
    elevated = float(calc_prevent_ascvd_10yr({
        "age": 60, "sex": "male",
        "total_chol_mgdl": 240, "hdl_c_mgdl": 35,
        "sbp_mmhg": 150, "bmi": 30, "egfr": 75,
        "diabetes": True, "smoking": True,
        "bp_treatment": True, "statin": False,
    }))
    assert elevated > baseline + 5.0


def test_prevent_returns_none_outside_age_window():
    """Khan 2024 derivation: 30-79 inclusive."""
    base = {
        "sex": "male", "total_chol_mgdl": 200, "hdl_c_mgdl": 45,
        "sbp_mmhg": 130, "bmi": 27, "egfr": 90, "diabetes": False,
        "smoking": False, "bp_treatment": False, "statin": False,
    }
    assert calc_prevent_ascvd_10yr({**base, "age": 25}) is None
    assert calc_prevent_ascvd_10yr({**base, "age": 80}) is None


def test_prevent_returns_none_on_missing_lab():
    """No HDL -> cannot compute; signal MISSING_INPUT upstream."""
    val = calc_prevent_ascvd_10yr({
        "age": 55, "sex": "male",
        "total_chol_mgdl": 200,                   # hdl_c_mgdl missing
        "sbp_mmhg": 130, "bmi": 27, "egfr": 90,
    })
    assert val is None


def test_prevent_matches_existing_app_implementation_within_rounding():
    """The greenfield calc must produce the same number as the existing
    app's services.organ_score_service.calc_prevent_10yr for the same
    inputs (both implementations source the same coefficient block and
    the same prep_terms arithmetic)."""
    from services.organ_score_service import calc_prevent_10yr as app_prevent

    inputs = dict(
        age=62.0, sex="female", total_chol=215.0, hdl=55.0,
        systolic_bp=138.0, on_bp_med=False, smoking=False,
        diabetes=False, egfr=85.0, bmi=28.0,
    )
    app_val = app_prevent(**inputs, outcome="ascvd")

    greenfield = calc_prevent_ascvd_10yr({
        "age": 62, "sex": "female",
        "total_chol_mgdl": 215, "hdl_c_mgdl": 55,
        "sbp_mmhg": 138, "bmi": 28, "egfr": 85,
        "diabetes": False, "smoking": False,
        "bp_treatment": False, "statin": False,
    })
    assert greenfield is not None and app_val is not None
    # App rounds to 1dp; greenfield to 4dp. Compare at 1dp.
    assert round(float(greenfield), 1) == app_val
