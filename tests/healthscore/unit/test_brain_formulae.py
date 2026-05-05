"""Unit tests for the brain-organ formulae (Phase 5).

PHQ-9 (Kroenke 2001), GAD-7 (Spitzer 2006), CAIDE (Kivipelto 2006),
homocysteine pass-through. Plus locale-driven Arabic-cutoff override
end-to-end through evaluate_score for PHQ-9.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from healthscore.enums import ScoreStatus
from healthscore.score_config import load_score_config
from healthscore.score_eval import evaluate_score
from healthscore.scores import lookup_formula
from healthscore.scores.brain import (
    calc_caide,
    calc_gad7,
    calc_homocysteine_passthrough,
    calc_phq9,
)


_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCORE_CONFIGS = _REPO_ROOT / "configs" / "scores"


# ── PHQ-9 sum-of-items ───────────────────────────────────────────────────


def test_phq9_sums_nine_items():
    val = calc_phq9({f"phq9_q{i}": 1 for i in range(1, 10)})
    assert val == Decimal("9")


def test_phq9_severe_at_max_score():
    val = calc_phq9({f"phq9_q{i}": 3 for i in range(1, 10)})
    assert val == Decimal("27")


def test_phq9_returns_none_on_missing_item():
    inputs = {f"phq9_q{i}": 1 for i in range(1, 10)}
    del inputs["phq9_q5"]
    assert calc_phq9(inputs) is None


# ── GAD-7 sum-of-items ───────────────────────────────────────────────────


def test_gad7_sums_seven_items():
    val = calc_gad7({f"gad7_q{i}": 2 for i in range(1, 8)})
    assert val == Decimal("14")


def test_gad7_returns_none_on_missing_item():
    inputs = {f"gad7_q{i}": 1 for i in range(1, 8)}
    del inputs["gad7_q3"]
    assert calc_gad7(inputs) is None


# ── CAIDE ────────────────────────────────────────────────────────────────


def test_caide_minimal_risk_for_younger_active_user():
    """45yo female, 12 yrs education, normal BP/BMI/chol, active = 0 points."""
    val = calc_caide({
        "age": 45, "sex": "female", "education_years": 12,
        "sbp_mmhg": 115, "bmi": 22, "total_chol_mgdl": 180,
        "physically_active": True,
    })
    assert val == Decimal("0")


def test_caide_high_risk_classic_case():
    """65yo male, low education, hypertensive, obese, hyperchol, sedentary.
    age>=61 (4) + edu<7 (3) + male (1) + sbp>=140 (2) + bmi>30 (2) + chol>=6.5 (2)
    + inactive (1) = 15 (max)."""
    val = calc_caide({
        "age": 65, "sex": "male", "education_years": 5,
        "sbp_mmhg": 145, "bmi": 32, "total_chol_mgdl": 270,
        "physically_active": False,
    })
    assert val == Decimal("15")


def test_caide_returns_none_on_missing_input():
    assert calc_caide({
        "sex": "female", "education_years": 12, "sbp_mmhg": 120,
        "bmi": 22, "total_chol_mgdl": 180, "physically_active": True,
    }) is None      # age missing


# ── Homocysteine pass-through ────────────────────────────────────────────


def test_homocysteine_passthrough_round_trips():
    val = calc_homocysteine_passthrough({"homocysteine_umol_L": 12.4})
    assert val == Decimal("12.4")


def test_homocysteine_returns_none_on_missing():
    assert calc_homocysteine_passthrough({}) is None


# ── Arabic-cutoff override end-to-end (PHQ-9) ────────────────────────────


@pytest.fixture(scope="module")
def phq9_config():
    return load_score_config(_SCORE_CONFIGS / "phq9.json")


def _phq9_inputs(total: int, **extra) -> dict[str, object]:
    """Distribute `total` across 9 items as evenly as possible, then add
    `extra` overrides (typically `locale`)."""
    base, rem = divmod(total, 9)
    inputs: dict[str, object] = {}
    for i in range(1, 10):
        inputs[f"phq9_q{i}"] = min(3, base + (1 if i <= rem else 0))
    inputs.update(extra)
    return inputs


def test_phq9_score_9_is_indeterminate_in_arabic_locale(phq9_config):
    """Arabic anchors low=4, indeterm=8, high=12. PHQ-9 score 9 sits
    just past the indeterm anchor -> q < 0.5 (heading toward high)."""
    res = evaluate_score(
        phq9_config,
        raw_inputs=_phq9_inputs(9, locale="ar"),
        prior_results={}, formula=lookup_formula(phq9_config.formula),
        gate=None,
    )
    assert res.status is ScoreStatus.OK
    assert res.language_cutoff_active == "ar"
    assert res.confidence == "single_source"        # Arabic override demotion
    assert res.normalised_q is not None
    assert res.normalised_q < 0.5                    # past Arabic indeterm cutoff


def test_phq9_score_9_remains_low_band_in_english_locale(phq9_config):
    """English anchors low=4, indeterm=9, high=14. PHQ-9 score 9 sits
    AT the indeterm anchor -> q = 0.5; same raw value, different band."""
    res = evaluate_score(
        phq9_config,
        raw_inputs=_phq9_inputs(9, locale="en"),
        prior_results={}, formula=lookup_formula(phq9_config.formula),
        gate=None,
    )
    assert res.status is ScoreStatus.OK
    assert res.language_cutoff_active == "en"        # explicit non-override
    assert res.confidence == phq9_config.confidence   # NOT demoted
    assert res.normalised_q == pytest.approx(0.5, abs=0.05)


def test_phq9_default_locale_is_english(phq9_config):
    """No locale supplied -> defaults to English anchors."""
    res = evaluate_score(
        phq9_config,
        raw_inputs=_phq9_inputs(9),
        prior_results={}, formula=lookup_formula(phq9_config.formula),
        gate=None,
    )
    assert res.status is ScoreStatus.OK
    assert res.language_cutoff_active == "en"
    assert res.confidence == phq9_config.confidence
