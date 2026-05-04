"""Unit tests for the kidney-organ formulae (Phase 3).

eGFR (CKD-EPI 2021), KFRE (Tangri 2011, 4-variable 5-year), and KDIGO
2024 prognosis category. Inker / Tangri / KDIGO reference points pinned
so that future re-derivations / refactors do not silently drift.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from healthscore.scores.kidney import (
    _calc_ckd_epi_2021,
    calc_egfr_deficit,
    calc_kdigo_category,
    calc_kfre_5yr,
)


# ── eGFR / CKD-EPI 2021 ────────────────────────────────────────────────────


def test_ckd_epi_2021_healthy_young_female_matches_published_form():
    """35-year-old female, Scr 0.8 mg/dL → ≈ 98 mL/min/1.73m²."""
    egfr = _calc_ckd_epi_2021(0.8, 35, sex_is_female=True)
    assert egfr == pytest.approx(98.5, abs=1.0)


def test_ckd_epi_2021_healthy_middle_aged_male_matches_published_form():
    """50-year-old male, Scr 0.9 mg/dL → ≈ 104 mL/min/1.73m²."""
    egfr = _calc_ckd_epi_2021(0.9, 50, sex_is_female=False)
    assert egfr == pytest.approx(104.0, abs=1.0)


def test_ckd_epi_2021_g4_male_matches_published_form():
    """70-year-old male, Scr 2.5 mg/dL → ≈ 27 mL/min/1.73m² (G4 zone)."""
    egfr = _calc_ckd_epi_2021(2.5, 70, sex_is_female=False)
    assert egfr == pytest.approx(27.0, abs=1.0)


def test_egfr_deficit_zero_when_egfr_above_90():
    val = calc_egfr_deficit(
        {"serum_creatinine_mgdl": 0.8, "age": 35, "sex": "female"}
    )
    assert val == Decimal("0")


def test_egfr_deficit_grows_with_kidney_impairment():
    healthy = calc_egfr_deficit(
        {"serum_creatinine_mgdl": 0.9, "age": 50, "sex": "male"}
    )
    impaired = calc_egfr_deficit(
        {"serum_creatinine_mgdl": 2.5, "age": 70, "sex": "male"}
    )
    assert healthy is not None and impaired is not None
    assert float(healthy) < float(impaired)
    assert float(impaired) > 30  # past indeterminate threshold


def test_egfr_deficit_returns_none_on_missing_inputs():
    assert calc_egfr_deficit({"age": 35, "sex": "female"}) is None
    assert calc_egfr_deficit(
        {"serum_creatinine_mgdl": 0.8, "sex": "female"}
    ) is None
    assert calc_egfr_deficit(
        {"serum_creatinine_mgdl": 0.8, "age": 35}
    ) is None


def test_egfr_deficit_returns_none_on_unrecognised_sex():
    assert calc_egfr_deficit(
        {"serum_creatinine_mgdl": 0.8, "age": 35, "sex": "other"}
    ) is None


# ── KFRE 4-variable 5-year ─────────────────────────────────────────────────


def test_kfre_higher_risk_for_lower_egfr_higher_uacr():
    low_risk = calc_kfre_5yr(
        {"age": 50, "sex": "female", "egfr": 50, "uacr": 50}
    )
    high_risk = calc_kfre_5yr(
        {"age": 65, "sex": "male", "egfr": 25, "uacr": 1000}
    )
    assert low_risk is not None and high_risk is not None
    assert float(low_risk) < float(high_risk)


def test_kfre_returns_none_on_missing_inputs():
    assert calc_kfre_5yr(
        {"age": 65, "sex": "male", "egfr": 30}                   # uacr missing
    ) is None
    assert calc_kfre_5yr(
        {"sex": "male", "egfr": 30, "uacr": 300}                 # age missing
    ) is None


def test_kfre_typical_g4_returns_meaningful_percent():
    """65M, eGFR 30, UACR 300 mg/g — Tangri 2011 reports ~10-15% risk for
    similar profiles. Pin a tolerant range so future re-derivations of the
    coefficient block fail loudly if they drift far."""
    val = calc_kfre_5yr(
        {"age": 65, "sex": "male", "egfr": 30, "uacr": 300}
    )
    assert val is not None
    assert 8.0 <= float(val) <= 18.0


# ── KDIGO 2024 prognosis category ──────────────────────────────────────────


@pytest.mark.parametrize(
    "egfr,uacr,expected",
    [
        (95, 10,  Decimal("0")),    # G1 / A1 — low risk
        (75, 10,  Decimal("0")),    # G2 / A1 — low risk
        (75, 50,  Decimal("1")),    # G2 / A2 — moderately increased
        (50, 200, Decimal("2")),    # G3a / A2 — high
        (40, 400, Decimal("3")),    # G3b / A3 — very high
        (20, 5,   Decimal("3")),    # G4 / A1 — very high (eGFR-dominant)
        (10, 5,   Decimal("3")),    # G5 / A1 — very high
    ],
)
def test_kdigo_category_heatmap(egfr, uacr, expected):
    val = calc_kdigo_category({"egfr": egfr, "uacr": uacr})
    assert val == expected


def test_kdigo_category_returns_none_on_missing_inputs():
    assert calc_kdigo_category({"egfr": 60}) is None
    assert calc_kdigo_category({"uacr": 30}) is None
    assert calc_kdigo_category({"egfr": 0, "uacr": 30}) is None
