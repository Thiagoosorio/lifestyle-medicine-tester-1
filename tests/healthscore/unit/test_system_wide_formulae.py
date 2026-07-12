"""Unit tests for the system-wide organ-panel formulae (Phase 4).

PhenoAge (Liu 2018, PMID 30596641, clinical-chemistry — NOT DNAm Levine
PMID 29676998), SII, NLR, STOP-BANG, NoSAS, FRAIL scale, MoCA-deficit,
MMSE-deficit. Reference points pinned so future re-derivations or
refactors do not silently drift.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from healthscore.scores.system_wide import (
    calc_frail_scale,
    calc_mmse_deficit,
    calc_moca_deficit,
    calc_nlr,
    calc_nosas,
    calc_phenoage_acceleration,
    calc_sii,
    calc_stop_bang,
)


# ── PhenoAge acceleration ────────────────────────────────────────────────


def _pheno_inputs(**overrides):
    base = dict(
        age=55, albumin_gdl=4.2, creatinine_mgdl=1.0, fasting_glucose_mgdl=100,
        hs_crp_mgL=2.0, lymphocyte_pct=28, mcv_fL=90, rdw_pct=13.5,
        alkaline_phosphatase_uL=65, wbc_10e9L=6.5,
    )
    base.update(overrides)
    return base


def test_phenoage_returns_a_decimal():
    val = calc_phenoage_acceleration(_pheno_inputs())
    assert isinstance(val, Decimal)


def test_phenoage_pins_reference_value():
    """Guards the corrected linear predictor: the age term (0.0804*age), the
    ALP term (0.00188*ALP, with WBC on its own 0.0554 coefficient), and the
    albumin g/L / creatinine umol/L unit conversions must all be present.
    Dropping any of them shifts the result by many years."""
    val = float(calc_phenoage_acceleration(_pheno_inputs()))
    assert val == pytest.approx(-2.40, abs=0.1)


def test_phenoage_requires_alkaline_phosphatase():
    inputs = _pheno_inputs()
    del inputs["alkaline_phosphatase_uL"]
    assert calc_phenoage_acceleration(inputs) is None


def test_phenoage_accelerates_with_higher_inflammation_and_glucose():
    """Same chronological age, two profiles: one well-controlled, one
    inflamed + dysglycaemic. The dysglycaemic profile must have higher
    PhenoAge acceleration."""
    healthy = float(calc_phenoage_acceleration(_pheno_inputs(
        fasting_glucose_mgdl=90, hs_crp_mgL=0.8, rdw_pct=12.5,
    )))
    sick = float(calc_phenoage_acceleration(_pheno_inputs(
        fasting_glucose_mgdl=160, hs_crp_mgL=8.0, rdw_pct=15.5,
    )))
    assert sick > healthy + 1.0


def test_phenoage_returns_none_on_missing_input():
    inputs = _pheno_inputs()
    del inputs["albumin_gdl"]
    assert calc_phenoage_acceleration(inputs) is None


# ── SII ──────────────────────────────────────────────────────────────────


def test_sii_round_trips_published_form():
    """SII = (platelets * neutrophils) / lymphocytes. Numbers chosen so
    answer is exact."""
    val = calc_sii({
        "platelets_k_ul": 250, "neutrophils_k_ul": 4.0, "lymphocytes_k_ul": 2.0,
    })
    assert val is not None and float(val) == 500.0


def test_sii_zero_lymphocytes_returns_none():
    assert calc_sii({
        "platelets_k_ul": 250, "neutrophils_k_ul": 4, "lymphocytes_k_ul": 0,
    }) is None


# ── NLR ──────────────────────────────────────────────────────────────────


def test_nlr_round_trips_published_form():
    val = calc_nlr({"neutrophils_k_ul": 6.0, "lymphocytes_k_ul": 2.0})
    assert val is not None and float(val) == 3.0


def test_nlr_zero_lymphocytes_returns_none():
    assert calc_nlr({"neutrophils_k_ul": 6, "lymphocytes_k_ul": 0}) is None


# ── STOP-BANG ────────────────────────────────────────────────────────────


def test_stop_bang_zero_for_low_risk_user():
    val = calc_stop_bang({
        "age": 35, "sex": "female", "bmi": 22, "neck_circumference_cm": 32,
        "snoring_loud": False, "tired_daytime": False,
        "observed_apnoea": False, "high_bp_or_treated": False,
    })
    assert val == Decimal("0")


def test_stop_bang_high_score_for_classic_high_risk_male():
    """Classic STOP-BANG-positive male: snoring + tired + observed apnoea
    + HTN + BMI>=35 + age>=50 + neck>40 + male = 8."""
    val = calc_stop_bang({
        "age": 60, "sex": "male", "bmi": 36, "neck_circumference_cm": 44,
        "snoring_loud": True, "tired_daytime": True,
        "observed_apnoea": True, "high_bp_or_treated": True,
    })
    assert val == Decimal("8")


def test_stop_bang_returns_none_on_missing_inputs():
    assert calc_stop_bang({"sex": "male"}) is None


# ── NoSAS ────────────────────────────────────────────────────────────────


def test_nosas_published_zero_when_low_risk():
    val = calc_nosas({
        "age": 35, "sex": "female", "bmi": 22, "neck_circumference_cm": 32,
        "snoring_loud": False,
    })
    assert val == Decimal("0")


def test_nosas_max_for_high_risk_male():
    """Neck>40 (4) + BMI>=30 (5) + snoring (2) + age>55 (4) + male (2) = 17."""
    val = calc_nosas({
        "age": 60, "sex": "male", "bmi": 32, "neck_circumference_cm": 44,
        "snoring_loud": True,
    })
    assert val == Decimal("17")


# ── FRAIL ────────────────────────────────────────────────────────────────


def test_frail_zero_for_robust_user():
    val = calc_frail_scale({
        "fatigue": False, "resistance_difficulty_stairs": False,
        "aerobic_difficulty_walking_block": False, "illness_count": 0,
        "loss_of_weight_5pct": False,
    })
    assert val == Decimal("0")


def test_frail_full_house():
    val = calc_frail_scale({
        "fatigue": True, "resistance_difficulty_stairs": True,
        "aerobic_difficulty_walking_block": True, "illness_count": 6,
        "loss_of_weight_5pct": True,
    })
    assert val == Decimal("5")


def test_frail_illness_threshold_at_5():
    """Illness count contributes 1 point only when >= 5."""
    base = {"fatigue": False, "resistance_difficulty_stairs": False,
            "aerobic_difficulty_walking_block": False,
            "loss_of_weight_5pct": False}
    assert calc_frail_scale({**base, "illness_count": 4}) == Decimal("0")
    assert calc_frail_scale({**base, "illness_count": 5}) == Decimal("1")


# ── MoCA / MMSE deficit forms ────────────────────────────────────────────


def test_moca_deficit_oriented_correctly():
    """MoCA 30 -> 0 deficit; MoCA 22 -> 8 deficit."""
    assert calc_moca_deficit({"moca_score": 30}) == Decimal("0")
    assert calc_moca_deficit({"moca_score": 22}) == Decimal("8")


def test_mmse_deficit_oriented_correctly():
    assert calc_mmse_deficit({"mmse_score": 30}) == Decimal("0")
    assert calc_mmse_deficit({"mmse_score": 22}) == Decimal("8")
