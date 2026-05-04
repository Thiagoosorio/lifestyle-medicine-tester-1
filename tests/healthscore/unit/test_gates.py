"""Unit tests for the gate engine (architecture_spec.md §6).

Covers every leaf operator, both missing-policy values, all_of/any_of
combinators, nested compounds, cross-score field references, and the
trace-format contract.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from healthscore.enums import (
    AnchorSource,
    InterpolationMode,
    RiskBand,
    ScoreStatus,
)
from healthscore.gates import (
    GateAllOf,
    GateAnyOf,
    GateLeaf,
    evaluate_gate_to_result,
    evaluate_predicate,
)
from healthscore.types import ScoreResult


# ──────────────────────────────────────────────────────────────────────────
# Builders
# ──────────────────────────────────────────────────────────────────────────


def _ok_result(score_id: str, raw: str, q: float = 0.5) -> ScoreResult:
    return ScoreResult(
        score_id=score_id,
        status=ScoreStatus.OK,
        raw_value=Decimal(raw),
        normalised_q=q,
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


# ──────────────────────────────────────────────────────────────────────────
# Construction validation
# ──────────────────────────────────────────────────────────────────────────


def test_gate_leaf_rejects_unknown_operator():
    with pytest.raises(ValueError):
        GateLeaf(
            field="raw_inputs.x", predicate="approximately",
            expected=1, missing_policy="fail", failure_reason_code="x",
        )


def test_gate_leaf_rejects_unknown_missing_policy():
    with pytest.raises(ValueError):
        GateLeaf(
            field="raw_inputs.x", predicate="equals",
            expected=1, missing_policy="ignore", failure_reason_code="x",
        )


def test_gate_leaf_rejects_blank_failure_reason_code():
    with pytest.raises(ValueError):
        GateLeaf(
            field="raw_inputs.x", predicate="equals",
            expected=1, missing_policy="fail", failure_reason_code="",
        )


def test_gate_leaf_rejects_field_path_not_starting_with_known_root():
    with pytest.raises(ValueError):
        GateLeaf(
            field="profile.age", predicate="ge",
            expected=18, missing_policy="fail", failure_reason_code="too_young",
        )


# ──────────────────────────────────────────────────────────────────────────
# Operator coverage
# ──────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "operator, expected, value, should_pass",
    [
        ("equals", True, True, True),
        ("equals", True, False, False),
        ("equals", "uae", "uae", True),
        ("equals", 5, 5, True),
        ("equals", 5, 6, False),
        ("ge", 60, 60, True),
        ("ge", 60, 59.9, False),
        ("le", 60, 60, True),
        ("le", 60, 60.1, False),
        ("gt", 60, 60.0001, True),
        ("gt", 60, 60, False),
        ("lt", 60, 59.9999, True),
        ("lt", 60, 60, False),
        ("in", ("a", "b", "c"), "b", True),
        ("in", ("a", "b", "c"), "z", False),
        ("truthy", None, True, True),
        ("truthy", None, 1, True),
        ("truthy", None, 0, False),
        ("truthy", None, False, False),
    ],
)
def test_leaf_operators(operator, expected, value, should_pass):
    leaf = GateLeaf(
        field="raw_inputs.x",
        predicate=operator,
        expected=expected,
        missing_policy="fail",
        failure_reason_code="x_check",
    )
    passed, fails, trace = evaluate_predicate(
        leaf, raw_inputs={"x": value}, prior_results={}
    )
    assert passed is should_pass
    if should_pass:
        assert fails == ()
        assert trace == ("leaf:x_check:pass",)
    else:
        assert fails == ("x_check",)
        assert trace == ("leaf:x_check:fail",)


def test_in_operator_requires_sequence_expected():
    leaf = GateLeaf(
        field="raw_inputs.x",
        predicate="in",
        expected="abc",  # plain string, not a sequence-of-allowed-values
        missing_policy="fail",
        failure_reason_code="x_check",
    )
    with pytest.raises(ValueError):
        evaluate_predicate(leaf, raw_inputs={"x": "a"}, prior_results={})


def test_numeric_operator_with_non_numeric_value_raises():
    leaf = GateLeaf(
        field="raw_inputs.x",
        predicate="ge",
        expected=10,
        missing_policy="fail",
        failure_reason_code="x_check",
    )
    with pytest.raises(ValueError):
        evaluate_predicate(leaf, raw_inputs={"x": "not_a_number"}, prior_results={})


# ──────────────────────────────────────────────────────────────────────────
# Missing policies
# ──────────────────────────────────────────────────────────────────────────


def test_missing_input_with_fail_policy_fails_leaf():
    leaf = GateLeaf(
        field="raw_inputs.atrial_fibrillation_status",
        predicate="equals",
        expected=True,
        missing_policy="fail",
        failure_reason_code="af_not_documented",
    )
    passed, fails, trace = evaluate_predicate(
        leaf, raw_inputs={"atrial_fibrillation_status": None}, prior_results={}
    )
    assert passed is False
    assert fails == ("af_not_documented",)
    assert trace == ("leaf:af_not_documented:fail",)


def test_missing_input_with_skip_policy_passes_leaf():
    leaf = GateLeaf(
        field="raw_inputs.chronic_liver_disease_status",
        predicate="equals",
        expected=True,
        missing_policy="skip",
        failure_reason_code="cld_not_documented",
    )
    passed, fails, trace = evaluate_predicate(
        leaf, raw_inputs={}, prior_results={}
    )
    assert passed is True
    assert fails == ()
    assert trace == ("leaf:cld_not_documented:skip",)


def test_absent_input_key_with_fail_policy_fails_leaf():
    leaf = GateLeaf(
        field="raw_inputs.absent_key",
        predicate="equals", expected=True,
        missing_policy="fail", failure_reason_code="absent",
    )
    passed, fails, trace = evaluate_predicate(leaf, raw_inputs={}, prior_results={})
    assert passed is False
    assert fails == ("absent",)


# ──────────────────────────────────────────────────────────────────────────
# Cross-score references
# ──────────────────────────────────────────────────────────────────────────


def test_score_results_reference_passes_when_prior_score_meets_threshold():
    leaf = GateLeaf(
        field="score_results.fib4.raw_value",
        predicate="ge", expected=1.3,
        missing_policy="fail", failure_reason_code="fib4_unavailable_or_low",
    )
    passed, fails, trace = evaluate_predicate(
        leaf, raw_inputs={}, prior_results={"fib4": _ok_result("fib4", "1.5")}
    )
    assert passed is True
    assert trace == ("leaf:fib4_unavailable_or_low:pass",)


def test_score_results_reference_fails_when_prior_score_is_gated():
    leaf = GateLeaf(
        field="score_results.fib4.raw_value",
        predicate="ge", expected=1.3,
        missing_policy="fail", failure_reason_code="fib4_unavailable_or_low",
    )
    passed, fails, trace = evaluate_predicate(
        leaf, raw_inputs={}, prior_results={"fib4": _gated_result("fib4")}
    )
    assert passed is False
    assert fails == ("fib4_unavailable_or_low",)


def test_score_results_reference_with_skip_policy_passes_when_unresolved():
    leaf = GateLeaf(
        field="score_results.unknown_score.raw_value",
        predicate="ge", expected=1.0,
        missing_policy="skip", failure_reason_code="optional_dep_missing",
    )
    passed, fails, trace = evaluate_predicate(leaf, raw_inputs={}, prior_results={})
    assert passed is True
    assert trace == ("leaf:optional_dep_missing:skip",)


# ──────────────────────────────────────────────────────────────────────────
# all_of combinator
# ──────────────────────────────────────────────────────────────────────────


def test_all_of_passes_only_when_every_child_passes():
    gate = GateAllOf(
        all_of=(
            GateLeaf("raw_inputs.a", "ge", 1, "fail", "a_low"),
            GateLeaf("raw_inputs.b", "ge", 1, "fail", "b_low"),
        )
    )
    passed, fails, trace = evaluate_predicate(
        gate, raw_inputs={"a": 5, "b": 5}, prior_results={}
    )
    assert passed is True
    assert fails == ()
    assert trace == (
        "all_of:start",
        "leaf:a_low:pass",
        "leaf:b_low:pass",
        "all_of:pass",
    )


def test_all_of_fails_when_any_child_fails_and_collects_every_failure_reason():
    gate = GateAllOf(
        all_of=(
            GateLeaf("raw_inputs.a", "ge", 1, "fail", "a_low"),
            GateLeaf("raw_inputs.b", "ge", 1, "fail", "b_low"),
        )
    )
    passed, fails, trace = evaluate_predicate(
        gate, raw_inputs={"a": 0, "b": 0}, prior_results={}
    )
    assert passed is False
    # No short-circuit -- both children evaluate, both reasons reported.
    assert fails == ("a_low", "b_low")
    assert trace == (
        "all_of:start",
        "leaf:a_low:fail",
        "leaf:b_low:fail",
        "all_of:fail",
    )


def test_empty_all_of_is_vacuously_true():
    gate = GateAllOf(all_of=())
    passed, fails, trace = evaluate_predicate(gate, raw_inputs={}, prior_results={})
    assert passed is True
    assert fails == ()
    assert trace == ("all_of:start", "all_of:pass")


# ──────────────────────────────────────────────────────────────────────────
# any_of combinator
# ──────────────────────────────────────────────────────────────────────────


def test_any_of_passes_when_one_branch_passes_even_after_a_failing_branch():
    gate = GateAnyOf(
        any_of=(
            GateLeaf(
                "raw_inputs.cld_status", "equals", True,
                "skip", "cld_not_documented",
            ),
            GateAllOf(
                all_of=(
                    GateLeaf("score_results.fib4.raw_value", "ge", 1.3,
                             "fail", "fib4_unavailable_or_low"),
                    GateLeaf("score_results.fli.raw_value", "ge", 60,
                             "fail", "fli_unavailable_or_low"),
                )
            ),
        )
    )
    raw_inputs = {}                     # cld_status absent -> first branch skips
    prior = {
        "fib4": _ok_result("fib4", "1.5"),
        "fli": _ok_result("fli", "70"),
    }
    passed, fails, trace = evaluate_predicate(gate, raw_inputs, prior)
    assert passed is True
    assert fails == ()
    # The trace mirrors architecture_spec §11's worked example shape.
    assert trace == (
        "any_of:start",
        "leaf:cld_not_documented:skip",
        "all_of:start",
        "leaf:fib4_unavailable_or_low:pass",
        "leaf:fli_unavailable_or_low:pass",
        "all_of:pass",
        "any_of:pass",
    )


def test_any_of_fails_when_every_branch_fails_and_lists_all_reasons():
    gate = GateAnyOf(
        any_of=(
            GateLeaf("raw_inputs.x", "equals", "yes",
                     "fail", "x_not_yes"),
            GateLeaf("raw_inputs.y", "equals", "yes",
                     "fail", "y_not_yes"),
        )
    )
    passed, fails, trace = evaluate_predicate(
        gate, raw_inputs={"x": "no", "y": "no"}, prior_results={}
    )
    assert passed is False
    assert fails == ("x_not_yes", "y_not_yes")
    assert trace == (
        "any_of:start",
        "leaf:x_not_yes:fail",
        "leaf:y_not_yes:fail",
        "any_of:fail",
    )


def test_empty_any_of_is_false():
    """Vacuous existential: there is no child to satisfy, so any_of=()
    cannot pass. Symmetric to all_of=() being vacuously true."""
    gate = GateAnyOf(any_of=())
    passed, fails, trace = evaluate_predicate(gate, raw_inputs={}, prior_results={})
    assert passed is False
    assert fails == ()
    assert trace == ("any_of:start", "any_of:fail")


# ──────────────────────────────────────────────────────────────────────────
# Failure-reason deduplication
# ──────────────────────────────────────────────────────────────────────────


def test_repeated_failure_reasons_are_deduplicated_by_first_occurrence():
    """A single failure_reason_code referenced by two leaves at different
    sites should appear once in gate_failures (first occurrence wins).
    The trace itself preserves both occurrences for audit fidelity."""
    gate = GateAllOf(
        all_of=(
            GateLeaf("raw_inputs.a", "ge", 1, "fail", "shared_reason"),
            GateLeaf("raw_inputs.b", "ge", 1, "fail", "shared_reason"),
        )
    )
    passed, fails, trace = evaluate_predicate(
        gate, raw_inputs={"a": 0, "b": 0}, prior_results={}
    )
    assert passed is False
    assert fails == ("shared_reason",)            # deduplicated
    # Trace keeps both occurrences (dupes preserved for forensic value).
    assert trace.count("leaf:shared_reason:fail") == 2


# ──────────────────────────────────────────────────────────────────────────
# Gate -> ScoreResult helper
# ──────────────────────────────────────────────────────────────────────────


def test_evaluate_gate_to_result_returns_none_when_gate_passes():
    leaf = GateLeaf("raw_inputs.x", "equals", True, "fail", "x_false")
    res = evaluate_gate_to_result(
        "fib4", leaf, raw_inputs={"x": True}, prior_results={}
    )
    assert res is None


def test_evaluate_gate_to_result_returns_gated_score_result_on_failure():
    leaf = GateLeaf(
        "raw_inputs.atrial_fibrillation_status",
        "equals", True, "fail", "af_not_documented",
    )
    res = evaluate_gate_to_result(
        "cha2ds2vasc",
        leaf,
        raw_inputs={"atrial_fibrillation_status": None},
        prior_results={},
    )
    assert res is not None
    assert res.score_id == "cha2ds2vasc"
    assert res.status is ScoreStatus.GATED
    assert res.gate_failures == ("af_not_documented",)
    assert res.gate_evaluation_trace == ("leaf:af_not_documented:fail",)
    # Architecture_spec §6: gated scores carry no value, no band, no wording.
    assert res.raw_value is None
    assert res.normalised_q is None
    assert res.risk_band is None
    assert res.wording is None
    assert res.anchors_used is None
    assert res.interpolation_mode is None


def test_evaluate_gate_to_result_with_no_gate_returns_none():
    res = evaluate_gate_to_result("ungated", None, raw_inputs={}, prior_results={})
    assert res is None
