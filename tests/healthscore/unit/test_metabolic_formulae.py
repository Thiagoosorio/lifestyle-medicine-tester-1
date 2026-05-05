"""Unit tests for the metabolic-organ formulae (Phase 5).

HOMA-IR (Matthews 1985), METS-IR (Bello-Chavolla 2018), TyG canonical
(Simental-Mendia 2008), FINDRISC (Lindstrom 2003), VAI (Amato 2010),
LAP (Kahn 2005). Reference points pinned so future re-derivations or
refactors do not silently drift.
"""

from __future__ import annotations

import math
from decimal import Decimal

import pytest

from healthscore.scores.metabolic import (
    calc_findrisc,
    calc_homa_ir,
    calc_lap,
    calc_mets_ir,
    calc_tyg,
    calc_vai,
)


# ── HOMA-IR ──────────────────────────────────────────────────────────────


def test_homa_ir_canonical_form():
    """Insulin 6 uIU/mL, glucose 90 mg/dL = 5.0 mmol/L
    HOMA-IR = 6 * 5.0 / 22.5 = 1.333"""
    val = calc_homa_ir({
        "fasting_insulin_uIUmL": 6.0, "fasting_glucose_mgdl": 90.0,
    })
    assert val is not None and float(val) == pytest.approx(1.333, abs=0.005)


def test_homa_ir_high_when_insulin_elevated():
    healthy = float(calc_homa_ir({
        "fasting_insulin_uIUmL": 6, "fasting_glucose_mgdl": 90,
    }))
    resistant = float(calc_homa_ir({
        "fasting_insulin_uIUmL": 25, "fasting_glucose_mgdl": 110,
    }))
    assert resistant > healthy * 3


def test_homa_ir_returns_none_on_missing():
    assert calc_homa_ir({"fasting_glucose_mgdl": 90}) is None
    assert calc_homa_ir({"fasting_insulin_uIUmL": 6}) is None


# ── METS-IR ──────────────────────────────────────────────────────────────


def test_mets_ir_published_form():
    """ln((2*100) + 100) * 25 / ln(50) = ln(300) * 25 / ln(50)"""
    val = calc_mets_ir({
        "fasting_glucose_mgdl": 100, "tg_mgdl": 100,
        "hdl_c_mgdl": 50, "bmi": 25,
    })
    expected = math.log(300) * 25 / math.log(50)
    assert val is not None and float(val) == pytest.approx(expected, abs=0.005)


# ── TyG canonical ───────────────────────────────────────────────────────


def test_tyg_canonical_form_simental_mendia():
    """TyG = ln(150 * 100 / 2) = ln(7500). Matches Simental-Mendia 2008
    canonical form (the bug-fix from prior 'ln/2' implementation)."""
    val = calc_tyg({"tg_mgdl": 150, "fasting_glucose_mgdl": 100})
    expected = math.log(150 * 100 / 2.0)
    assert val is not None and float(val) == pytest.approx(expected, abs=0.005)


def test_tyg_value_in_clinically_meaningful_range():
    """A typical adult: TG 130, glucose 95. TyG ~ ln(6175) ~ 8.73."""
    val = calc_tyg({"tg_mgdl": 130, "fasting_glucose_mgdl": 95})
    assert val is not None
    assert 8.0 <= float(val) <= 9.5


# ── FINDRISC ─────────────────────────────────────────────────────────────


def test_findrisc_low_risk_for_healthy_young_user():
    val = calc_findrisc({
        "age": 30, "sex": "female", "bmi": 22, "waist_cm": 76,
        "daily_activity_30min": True, "daily_fruit_veg": True,
        "on_bp_medication": False, "history_high_glucose": False,
        "family_history_diabetes": "none",
    })
    assert val == Decimal("0")


def test_findrisc_high_risk_classic_case():
    """65yo male, BMI 33, large waist, sedentary, BP medication, history
    of high glucose, first-degree FHX. = 4 + 3 + 4 + 2 + 1 + 2 + 5 + 5 = 26."""
    val = calc_findrisc({
        "age": 65, "sex": "male", "bmi": 33, "waist_cm": 110,
        "daily_activity_30min": False, "daily_fruit_veg": False,
        "on_bp_medication": True, "history_high_glucose": True,
        "family_history_diabetes": "first_degree",
    })
    assert val == Decimal("26")


def test_findrisc_age_buckets_step_correctly():
    base = dict(
        sex="male", bmi=22, waist_cm=80,
        daily_activity_30min=True, daily_fruit_veg=True,
        on_bp_medication=False, history_high_glucose=False,
        family_history_diabetes="none",
    )
    assert calc_findrisc({**base, "age": 44}) == Decimal("0")
    assert calc_findrisc({**base, "age": 45}) == Decimal("2")
    assert calc_findrisc({**base, "age": 55}) == Decimal("3")
    assert calc_findrisc({**base, "age": 65}) == Decimal("4")


# ── VAI ──────────────────────────────────────────────────────────────────


def test_vai_published_form_male():
    """Male, waist 90, BMI 25, TG 150, HDL 40.
    Tg_mmol = 150/88.57 = 1.694; HDL_mmol = 40/38.67 = 1.034
    VAI = (90 / (39.68 + 1.88*25)) * (1.694/1.03) * (1.31/1.034)
        = (90 / 86.68) * 1.6447 * 1.2669
        = 1.0383 * 1.6447 * 1.2669 = ~2.163"""
    val = calc_vai({
        "waist_cm": 90, "bmi": 25, "tg_mgdl": 150,
        "hdl_c_mgdl": 40, "sex": "male",
    })
    assert val is not None and 2.0 < float(val) < 2.4


def test_vai_higher_for_central_adiposity_pattern():
    healthy = float(calc_vai({
        "waist_cm": 80, "bmi": 23, "tg_mgdl": 80, "hdl_c_mgdl": 60,
        "sex": "male",
    }))
    risky = float(calc_vai({
        "waist_cm": 110, "bmi": 30, "tg_mgdl": 250, "hdl_c_mgdl": 35,
        "sex": "male",
    }))
    assert risky > healthy * 3


# ── LAP ──────────────────────────────────────────────────────────────────


def test_lap_published_form_male():
    """Male, waist 95, TG 200 mg/dL = 2.258 mmol/L
    LAP = (95 - 65) * 2.258 = 67.74"""
    val = calc_lap({"waist_cm": 95, "tg_mgdl": 200, "sex": "male"})
    assert val is not None and float(val) == pytest.approx(67.74, abs=0.5)


def test_lap_published_form_female():
    """Female, waist 85, TG 150 mg/dL = 1.694 mmol/L
    LAP = (85 - 58) * 1.694 = 45.74"""
    val = calc_lap({"waist_cm": 85, "tg_mgdl": 150, "sex": "female"})
    assert val is not None and float(val) == pytest.approx(45.74, abs=0.5)


def test_lap_floors_at_zero_when_waist_below_offset():
    """A user with waist below the male offset 65 should not get a
    negative LAP -- floor at 0."""
    val = calc_lap({"waist_cm": 60, "tg_mgdl": 100, "sex": "male"})
    assert val == Decimal("0")
