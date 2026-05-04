"""Unit tests for evaluate_score (the per-score Phase 2 evaluation pipeline).

Covers: gate-fail short-circuit, missing input, out-of-range input, formula
returning None, OK path with normalisation + risk-band + wording rendering.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from healthscore.enums import RiskBand, ScoreStatus
from healthscore.gates import GateLeaf
from healthscore.score_config import load_score_config, parse_gate_spec
from healthscore.score_eval import evaluate_score
from healthscore.scores import lookup_formula


_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCORE_CONFIGS = _REPO_ROOT / "configs" / "scores"


@pytest.fixture(scope="module")
def fib4_config():
    return load_score_config(_SCORE_CONFIGS / "fib4.json")


@pytest.fixture(scope="module")
def fib4_formula():
    return lookup_formula("fib4")


@pytest.fixture(scope="module")
def fib4_inputs():
    return {"age": 50, "ast": 43.8, "alt": 30.0, "platelets": 200}


# ── OK path ───────────────────────────────────────────────────────────────


def test_ok_path_produces_full_score_result(fib4_config, fib4_formula, fib4_inputs):
    res = evaluate_score(
        fib4_config,
        raw_inputs=fib4_inputs,
        prior_results={},
        formula=fib4_formula,
        gate=None,
    )
    assert res.status is ScoreStatus.OK
    assert res.normalised_q is not None
    assert 0.0 <= res.normalised_q <= 1.0
    assert res.risk_band in (RiskBand.LOW, RiskBand.INDETERMINATE, RiskBand.HIGH)
    assert res.pmid == fib4_config.pmid_primary
    assert res.confidence == fib4_config.confidence


def test_ok_path_renders_wording_when_template_supplied(
    fib4_config, fib4_formula, fib4_inputs
):
    templates = {"fib4": {
        "low": "Low band wording.",
        "indeterminate": "Indeterminate band wording.",
        "high": "High band wording.",
    }}
    res = evaluate_score(
        fib4_config,
        raw_inputs=fib4_inputs,
        prior_results={},
        formula=fib4_formula,
        gate=None,
        templates=templates,
    )
    assert res.wording in templates["fib4"].values()


# ── Failure modes ─────────────────────────────────────────────────────────


def test_missing_input_yields_missing_input_status(fib4_config, fib4_formula):
    res = evaluate_score(
        fib4_config,
        raw_inputs={"age": 50, "ast": 40, "alt": 30},   # platelets missing
        prior_results={},
        formula=fib4_formula,
        gate=None,
    )
    assert res.status is ScoreStatus.MISSING_INPUT
    assert res.reason and "platelets" in res.reason
    assert res.wording is None
    assert res.normalised_q is None


def test_out_of_range_input_yields_out_of_range_status(fib4_config, fib4_formula):
    res = evaluate_score(
        fib4_config,
        raw_inputs={"age": 150, "ast": 40, "alt": 30, "platelets": 200},
        prior_results={},
        formula=fib4_formula,
        gate=None,
    )
    assert res.status is ScoreStatus.OUT_OF_RANGE
    assert res.reason and "age" in res.reason


def test_gate_failure_short_circuits_the_pipeline(fib4_config, fib4_formula, fib4_inputs):
    """When a gate fails, formula and normalisation never run -- the
    GATED ScoreResult is returned directly per architecture_spec §6."""
    failing_gate = GateLeaf(
        field="raw_inputs.atrial_fibrillation_status",
        predicate="equals", expected=True,
        missing_policy="fail", failure_reason_code="af_not_documented",
    )
    res = evaluate_score(
        fib4_config,
        raw_inputs=fib4_inputs,
        prior_results={},
        formula=fib4_formula,
        gate=failing_gate,
    )
    assert res.status is ScoreStatus.GATED
    assert res.gate_failures == ("af_not_documented",)
    assert res.raw_value is None
    assert res.normalised_q is None
    assert res.wording is None


def test_formula_returning_none_yields_missing_input(fib4_config):
    """If a formula function returns None mid-pipeline (e.g. a derived
    sub-input is invalid), the score is reported as MISSING_INPUT."""

    def _always_none(_inputs):
        return None

    res = evaluate_score(
        fib4_config,
        raw_inputs={"age": 50, "ast": 40, "alt": 30, "platelets": 200},
        prior_results={},
        formula=_always_none,
        gate=None,
    )
    assert res.status is ScoreStatus.MISSING_INPUT
    assert res.reason == "formula_returned_none"


# ── Liver formulae unit checks ────────────────────────────────────────────


def test_albi_formula_matches_published_form():
    from healthscore.scores.liver import calc_albi
    # ALBI = log10(bili_umol/L) * 0.66 - albumin_g/L * 0.085
    # bilirubin 1.0 mg/dL -> 17.1 umol/L; albumin 3.16 g/dL -> 31.6 g/L
    # Expected: log10(17.1)*0.66 - 31.6*0.085 = 0.814 - 2.686 = -1.872
    val = calc_albi({"total_bilirubin_mgdl": 1.0, "albumin_gdl": 3.16})
    assert val is not None
    assert float(val) == pytest.approx(-1.872, abs=0.01)


def test_fib4_formula_matches_published_form():
    from healthscore.scores.liver import calc_fib4
    # FIB-4 = (50 * 43.8) / (200 * sqrt(30)) = 2190 / 1095.4 = 1.999
    val = calc_fib4({"age": 50, "ast": 43.8, "alt": 30, "platelets": 200})
    assert val is not None
    assert float(val) == pytest.approx(2.0, abs=0.005)


def test_apri_formula_matches_published_form():
    from healthscore.scores.liver import calc_apri
    # APRI = ((60/40)*100)/200 = 0.75
    val = calc_apri({"ast": 60, "platelets": 200, "ast_uln": 40})
    assert val is not None
    assert float(val) == pytest.approx(0.75, abs=0.001)
