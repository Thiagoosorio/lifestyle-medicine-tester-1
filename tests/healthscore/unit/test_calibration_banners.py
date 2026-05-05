"""Unit tests for the per-score calibration-uncertainty banner mechanism
(Phase 4; commitments_log #18: PREVENT-UAE banner).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from healthscore.calibration_banners import calibration_banner_for
from healthscore.enums import ScoreStatus
from healthscore.score_config import load_score_config, parse_gate_spec
from healthscore.score_eval import evaluate_score
from healthscore.scores import lookup_formula


_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCORE_CONFIGS = _REPO_ROOT / "configs" / "scores"


@pytest.fixture(scope="module")
def prevent_config():
    return load_score_config(_SCORE_CONFIGS / "prevent.json")


@pytest.fixture(scope="module")
def prevent_inputs():
    return {
        "age": 55, "sex": "male",
        "total_chol_mgdl": 200, "hdl_c_mgdl": 45,
        "sbp_mmhg": 130, "bmi": 27, "egfr": 90,
        "diabetes": False, "smoking": False,
        "bp_treatment": False, "statin": False,
    }


# ── Pure function ────────────────────────────────────────────────────────


def test_banner_function_returns_none_for_non_uae_user():
    assert calibration_banner_for("prevent", {"country_of_residence": "USA"}) is None


def test_banner_function_returns_string_for_uae_user():
    msg = calibration_banner_for("prevent", {"country_of_residence": "UAE"})
    assert msg is not None
    assert "Al-Shamsi 2025" in msg
    assert "directional" in msg


def test_banner_function_handles_uae_aliases():
    for alias in ("UAE", "uae", "U.A.E.", "United Arab Emirates"):
        assert calibration_banner_for("prevent", {"country_of_residence": alias}) is not None


def test_banner_function_returns_none_for_score_with_no_banner():
    """Scores without registered banners return None unconditionally."""
    assert calibration_banner_for("fib4", {"country_of_residence": "UAE"}) is None


def test_banner_function_returns_none_when_country_missing():
    assert calibration_banner_for("prevent", {"age": 55}) is None


# ── End-to-end through evaluate_score ────────────────────────────────────


def test_prevent_for_us_user_has_no_banner(prevent_config, prevent_inputs):
    res = evaluate_score(
        prevent_config,
        raw_inputs={**prevent_inputs, "country_of_residence": "USA"},
        prior_results={},
        formula=lookup_formula(prevent_config.formula),
        gate=parse_gate_spec(prevent_config.gate_requirements),
    )
    assert res.status is ScoreStatus.OK
    assert res.calibration_banner is None


def test_prevent_for_uae_user_carries_banner(prevent_config, prevent_inputs):
    """The architecturally important fixture: any UAE-resident user
    computing PREVENT must surface the calibration banner per
    commitments_log #18 (launch-blocker)."""
    res = evaluate_score(
        prevent_config,
        raw_inputs={**prevent_inputs, "country_of_residence": "UAE"},
        prior_results={},
        formula=lookup_formula(prevent_config.formula),
        gate=parse_gate_spec(prevent_config.gate_requirements),
    )
    assert res.status is ScoreStatus.OK
    assert res.calibration_banner is not None
    assert "Al-Shamsi" in res.calibration_banner


def test_no_banner_for_score_with_no_country(prevent_config, prevent_inputs):
    """A user who hasn't supplied country_of_residence gets no banner
    (we do not assume UAE / non-UAE without a positive signal)."""
    res = evaluate_score(
        prevent_config, raw_inputs=prevent_inputs, prior_results={},
        formula=lookup_formula(prevent_config.formula),
        gate=parse_gate_spec(prevent_config.gate_requirements),
    )
    assert res.status is ScoreStatus.OK
    assert res.calibration_banner is None
