"""Parity tests for the full AHA PREVENT 2024 equations.

Reference values copied verbatim from the preventr R package test suite
(https://github.com/martingmayer/preventr/blob/main/tests/testthat/test-prevent_equations.R)
which itself transcribes the Khan 2024 Circulation Table S12 coefficients.
"""

import pytest

from services.organ_score_service import (
    calc_prevent_10yr,
    calc_prevent_10yr_ascvd,
    calc_prevent_10yr_hf,
)


_REFERENCE_PATIENT = dict(
    age=50, sex="female", total_chol=200, hdl=45,
    systolic_bp=160, on_bp_med=True, smoking=False,
    diabetes=True, egfr=90, bmi=35, statin=False,
)


@pytest.mark.parametrize("outcome,expected_pct", [
    ("total_cvd", 14.7),
    ("ascvd", 9.2),
    ("heart_failure", 8.1),
    ("chd", 4.4),
    ("stroke", 5.4),
])
def test_prevent_base_model_matches_preventr_reference(outcome, expected_pct):
    value = calc_prevent_10yr(**_REFERENCE_PATIENT, outcome=outcome)
    assert value == pytest.approx(expected_pct, abs=0.1)


@pytest.mark.parametrize("outcome,expected_pct", [
    ("total_cvd", 16.5),
    ("ascvd", 10.3),
    ("heart_failure", 10.7),
])
def test_prevent_hba1c_model_matches_preventr_reference(outcome, expected_pct):
    value = calc_prevent_10yr(**_REFERENCE_PATIENT, hba1c=9.2, outcome=outcome)
    assert value == pytest.approx(expected_pct, abs=0.1)


@pytest.mark.parametrize("outcome,expected_pct", [
    ("total_cvd", 18.1),
    ("ascvd", 11.1),
    ("heart_failure", 10.5),
])
def test_prevent_uacr_model_matches_preventr_reference(outcome, expected_pct):
    value = calc_prevent_10yr(**_REFERENCE_PATIENT, uacr=92, outcome=outcome)
    assert value == pytest.approx(expected_pct, abs=0.1)


def test_ascvd_and_hf_wrappers_agree_with_outcome_kwarg():
    base = dict(_REFERENCE_PATIENT)
    assert calc_prevent_10yr_ascvd(**base) == calc_prevent_10yr(**base, outcome="ascvd")
    assert calc_prevent_10yr_hf(**base) == calc_prevent_10yr(**base, outcome="heart_failure")


def test_prevent_returns_none_outside_validated_age_range():
    below = dict(_REFERENCE_PATIENT, age=29)
    above = dict(_REFERENCE_PATIENT, age=80)
    assert calc_prevent_10yr(**below) is None
    assert calc_prevent_10yr(**above) is None


def test_prevent_returns_none_for_missing_inputs():
    bad = dict(_REFERENCE_PATIENT, total_chol=None)
    assert calc_prevent_10yr(**bad) is None
