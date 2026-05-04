"""Frozen regression: the Phase 3 KFRE canonical gate fixture.

architecture_spec.md §6 Pre-launch gate registry, KFRE row:

    leaf{ field=raw_inputs.egfr, le 60, missing=fail }

End-to-end verification: a healthy user with eGFR = 93.7 mL/min/1.73m²
must not receive a KFRE score (the equation was derived in CKD G3a-G5;
running it on healthy kidneys produces a 5-year kidney-failure risk
output that is meaningless for the input population).

The expected GATED ScoreResult mirrors the Phase 1 CHA2DS2-VASc fixture:

    ScoreResult(
        status=GATED,
        wording=None,
        gate_failures=("egfr_above_ckd_threshold",),
        gate_evaluation_trace=("leaf:egfr_above_ckd_threshold:fail",),
    )

This test pins the entire shape of that GATED ScoreResult so any future
change that loosens the gate -- e.g. defaulting eGFR to None, producing
a wording for a gated score, computing a value for a gated score --
breaks loudly.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from healthscore.enums import ScoreStatus
from healthscore.score_config import load_score_config, parse_gate_spec
from healthscore.score_eval import evaluate_score
from healthscore.scores import lookup_formula


_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCORE_CONFIGS = _REPO_ROOT / "configs" / "scores"


@pytest.fixture(scope="module")
def kfre_config():
    return load_score_config(_SCORE_CONFIGS / "kfre.json")


def test_healthy_user_with_egfr_93pt7_returns_canonical_gated_result(kfre_config):
    """The architecturally important fixture: healthy user with normal
    eGFR must be gated, with no risk band, no wording, no normalised q,
    no raw value. Direct mirror of CHA2DS2-VASc Phase 1 fixture."""
    raw_inputs = {
        "age": 43,
        "sex": "female",
        "egfr": 93.7,
        "uacr": 5,
    }
    res = evaluate_score(
        kfre_config,
        raw_inputs=raw_inputs,
        prior_results={},
        formula=lookup_formula(kfre_config.formula),
        gate=parse_gate_spec(kfre_config.gate_requirements),
    )

    assert res.score_id == "kfre"
    assert res.status is ScoreStatus.GATED
    assert res.gate_failures == ("egfr_above_ckd_threshold",)
    assert res.gate_evaluation_trace == (
        "leaf:egfr_above_ckd_threshold:fail",
    )

    # No number, no band, no wording -- structural guarantee.
    assert res.wording is None
    assert res.raw_value is None
    assert res.normalised_q is None
    assert res.risk_band is None
    assert res.epsilon_applied is False
    assert res.anchors_used is None
    assert res.anchor_sources is None
    assert res.interpolation_mode is None
    assert res.confidence is None
    assert res.active_instrument is None
    assert res.reason is None


def test_egfr_exactly_60_passes_the_gate(kfre_config):
    """eGFR == 60 (right at the CKD boundary) should pass per ``le 60``
    semantics — KFRE is meaningful at the G3a / G2 boundary."""
    raw_inputs = {
        "age": 60,
        "sex": "male",
        "egfr": 60,
        "uacr": 50,
    }
    res = evaluate_score(
        kfre_config,
        raw_inputs=raw_inputs,
        prior_results={},
        formula=lookup_formula(kfre_config.formula),
        gate=parse_gate_spec(kfre_config.gate_requirements),
    )
    assert res.status is ScoreStatus.OK
    assert res.gate_failures == ()
    assert res.raw_value is not None
    assert res.normalised_q is not None


def test_egfr_above_threshold_gated_for_typical_healthy_male(kfre_config):
    """Verify the gate fails for a healthy 50-year-old male with eGFR
    around 100, the most common "user with no kidney concerns" case."""
    raw_inputs = {
        "age": 50,
        "sex": "male",
        "egfr": 100,
        "uacr": 10,
    }
    res = evaluate_score(
        kfre_config,
        raw_inputs=raw_inputs,
        prior_results={},
        formula=lookup_formula(kfre_config.formula),
        gate=parse_gate_spec(kfre_config.gate_requirements),
    )
    assert res.status is ScoreStatus.GATED
    assert res.gate_failures == ("egfr_above_ckd_threshold",)


def test_missing_egfr_input_fails_gate_with_canonical_reason(kfre_config):
    """missing_policy=fail: a user with no eGFR input gets the same
    gate-failure reason code, not a confusing missing_input status."""
    raw_inputs = {
        "age": 65,
        "sex": "male",
        # egfr missing entirely
        "uacr": 50,
    }
    res = evaluate_score(
        kfre_config,
        raw_inputs=raw_inputs,
        prior_results={},
        formula=lookup_formula(kfre_config.formula),
        gate=parse_gate_spec(kfre_config.gate_requirements),
    )
    assert res.status is ScoreStatus.GATED
    assert res.gate_failures == ("egfr_above_ckd_threshold",)
