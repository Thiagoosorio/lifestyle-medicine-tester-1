"""aMAP compound gate -- the five scenarios specified in
architecture_spec.md §6 (line 531):

    (i)   CLD documented                                            -> pass
    (ii)  CLD null + FIB-4 >= 1.3 + FLI >= 60                       -> pass via second branch
    (iii) CLD null + FIB-4 < 1.3                                    -> fail
    (iv)  CLD null + FLI missing                                    -> fail with `fli_unavailable_or_low`
    (v)   CLD null + FIB-4 GATED itself                             -> fail with `fib4_unavailable_or_low`

Plus an auxiliary test that loads the gate config from configs/scores/amap.json
(via parse_gate_spec) so the JSON form is also exercised.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from healthscore.enums import RiskBand, ScoreStatus
from healthscore.gates import (
    GateAllOf,
    GateAnyOf,
    GateLeaf,
    evaluate_gate_to_result,
    evaluate_predicate,
)
from healthscore.score_config import parse_gate_spec
from healthscore.types import ScoreResult


_REPO_ROOT = Path(__file__).resolve().parents[3]
_AMAP_CONFIG = _REPO_ROOT / "configs" / "scores" / "amap.json"


# ──────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────


def _ok_result(score_id: str, raw: str) -> ScoreResult:
    return ScoreResult(
        score_id=score_id,
        status=ScoreStatus.OK,
        raw_value=Decimal(raw),
        normalised_q=0.5,
        epsilon_applied=False,
        risk_band=RiskBand.INDETERMINATE,
        anchors_used=None,
        anchor_sources=None,
        interpolation_mode=None,
        confidence="high",
        pmid=None,
        active_instrument=None,
        gate_failures=(),
        gate_evaluation_trace=(),
        reason=None,
        wording=None,
    )


def _gated_result(score_id: str) -> ScoreResult:
    return ScoreResult(
        score_id=score_id,
        status=ScoreStatus.GATED,
        raw_value=None,
        normalised_q=None,
        epsilon_applied=False,
        risk_band=None,
        anchors_used=None,
        anchor_sources=None,
        interpolation_mode=None,
        confidence=None,
        pmid=None,
        active_instrument=None,
        gate_failures=("dependency_gated",),
        gate_evaluation_trace=("leaf:dependency_gated:fail",),
        reason=None,
        wording=None,
    )


def _amap_gate_from_config():
    spec = json.loads(_AMAP_CONFIG.read_text(encoding="utf-8"))
    return parse_gate_spec(spec["gate_requirements"])


# ──────────────────────────────────────────────────────────────────────────
# Scenario (i)  -- CLD documented => pass via first branch
# ──────────────────────────────────────────────────────────────────────────


def test_amap_scenario_i_cld_documented_passes_via_first_branch():
    gate = _amap_gate_from_config()
    raw_inputs = {
        "chronic_liver_disease_status": True,
        "age": 50, "sex": "male",
        "total_bilirubin_mgdl": 1.0,
        "albumin_gdl": 3.8, "platelets": 200,
    }
    passed, fails, trace = evaluate_predicate(
        gate, raw_inputs, prior_results={}
    )
    assert passed is True
    assert fails == ()
    # The CLD branch passed; the FIB-4/FLI branch should also have evaluated
    # because we don't short-circuit (architecture_spec §6, audit fidelity).
    assert "leaf:cld_not_documented:pass" in trace
    assert trace[0] == "any_of:start"
    assert trace[-1] == "any_of:pass"


# ──────────────────────────────────────────────────────────────────────────
# Scenario (ii) -- CLD null + FIB-4 >= 1.3 + FLI >= 60 => pass via second branch
# ──────────────────────────────────────────────────────────────────────────


def test_amap_scenario_ii_cld_null_with_masld_screening_evidence_passes():
    gate = _amap_gate_from_config()
    raw_inputs = {
        # chronic_liver_disease_status absent -> first leaf is SKIPPED via
        # missing_policy="skip".  Without skip, an empty CLD field would
        # short-circuit any_of to fail and the FIB-4/FLI branch would
        # never be evaluated.  This is the load-bearing semantics in the
        # architecture spec.
        "age": 50, "sex": "female",
        "total_bilirubin_mgdl": 1.0,
        "albumin_gdl": 3.8, "platelets": 200,
    }
    prior = {
        "fib4": _ok_result("fib4", "1.5"),
        "fli":  _ok_result("fli",  "70"),
    }
    passed, fails, trace = evaluate_predicate(gate, raw_inputs, prior)
    assert passed is True
    assert fails == ()
    # Trace shape: any_of -> CLD skip -> all_of with both leaves pass -> any_of pass
    assert "leaf:cld_not_documented:skip" in trace
    assert "leaf:fib4_unavailable_or_low:pass" in trace
    assert "leaf:fli_unavailable_or_low:pass" in trace


# ──────────────────────────────────────────────────────────────────────────
# Scenario (iii) -- CLD null + FIB-4 < 1.3 => fail
# ──────────────────────────────────────────────────────────────────────────


def test_amap_scenario_iii_cld_null_with_low_fib4_fails():
    gate = _amap_gate_from_config()
    raw_inputs = {
        "age": 50, "sex": "female",
    }
    prior = {
        "fib4": _ok_result("fib4", "1.0"),    # below 1.3
        "fli":  _ok_result("fli",  "70"),
    }
    passed, fails, trace = evaluate_predicate(gate, raw_inputs, prior)
    assert passed is False
    assert "fib4_unavailable_or_low" in fails


# ──────────────────────────────────────────────────────────────────────────
# Scenario (iv) -- CLD null + FLI missing => fail with `fli_unavailable_or_low`
# ──────────────────────────────────────────────────────────────────────────


def test_amap_scenario_iv_cld_null_with_fli_missing_fails():
    gate = _amap_gate_from_config()
    raw_inputs = {
        "age": 50, "sex": "female",
    }
    prior = {
        "fib4": _ok_result("fib4", "1.5"),
        # fli not in prior_results -> field unresolved -> missing_policy=fail
    }
    passed, fails, trace = evaluate_predicate(gate, raw_inputs, prior)
    assert passed is False
    assert "fli_unavailable_or_low" in fails


# ──────────────────────────────────────────────────────────────────────────
# Scenario (v) -- CLD null + FIB-4 GATED itself => fail with fib4_unavailable_or_low
# ──────────────────────────────────────────────────────────────────────────


def test_amap_scenario_v_cld_null_with_fib4_gated_fails():
    gate = _amap_gate_from_config()
    raw_inputs = {
        "age": 50, "sex": "female",
    }
    prior = {
        "fib4": _gated_result("fib4"),       # gated -> field treated as unresolvable
        "fli":  _ok_result("fli",  "70"),
    }
    passed, fails, trace = evaluate_predicate(gate, raw_inputs, prior)
    assert passed is False
    assert "fib4_unavailable_or_low" in fails


# ──────────────────────────────────────────────────────────────────────────
# Auxiliary -- the gate parsed from JSON has the expected structure
# ──────────────────────────────────────────────────────────────────────────


def test_amap_gate_json_round_trips_to_expected_dataclass_tree():
    gate = _amap_gate_from_config()
    # any_of[ leaf, all_of[leaf, leaf] ]
    assert isinstance(gate, GateAnyOf)
    assert len(gate.any_of) == 2
    cld_leaf, masld_branch = gate.any_of
    assert isinstance(cld_leaf, GateLeaf)
    assert cld_leaf.field == "raw_inputs.chronic_liver_disease_status"
    assert cld_leaf.predicate == "equals"
    assert cld_leaf.expected is True
    assert cld_leaf.missing_policy == "skip"      # the load-bearing skip
    assert cld_leaf.failure_reason_code == "cld_not_documented"

    assert isinstance(masld_branch, GateAllOf)
    fib4_leaf, fli_leaf = masld_branch.all_of
    assert isinstance(fib4_leaf, GateLeaf)
    assert fib4_leaf.field == "score_results.fib4.raw_value"
    assert fib4_leaf.predicate == "ge"
    assert float(fib4_leaf.expected) == 1.3       # type: ignore[arg-type]
    assert fib4_leaf.missing_policy == "fail"
    assert fib4_leaf.failure_reason_code == "fib4_unavailable_or_low"

    assert isinstance(fli_leaf, GateLeaf)
    assert fli_leaf.field == "score_results.fli.raw_value"
    assert fli_leaf.predicate == "ge"
    assert float(fli_leaf.expected) == 60         # type: ignore[arg-type]
    assert fli_leaf.failure_reason_code == "fli_unavailable_or_low"


def test_amap_gate_to_result_returns_gated_with_correct_failure_codes():
    """End-to-end: the gate-to-result wrapper applied to scenario (iii)
    yields a properly shaped GATED ScoreResult. (Scenario (iii) was the
    cleanest "must fail" case in the spec.)"""
    gate = _amap_gate_from_config()
    raw_inputs = {"age": 50, "sex": "female"}
    prior = {
        "fib4": _ok_result("fib4", "1.0"),
        "fli":  _ok_result("fli",  "70"),
    }
    res = evaluate_gate_to_result("amap", gate, raw_inputs, prior)
    assert res is not None
    assert res.status is ScoreStatus.GATED
    assert "fib4_unavailable_or_low" in res.gate_failures
    assert res.wording is None
    assert res.normalised_q is None
    assert res.raw_value is None
