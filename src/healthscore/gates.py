"""Score-eligibility gate engine.

Per architecture_spec.md §6:

A ``GatePredicate`` is one of three frozen dataclasses:
    GateLeaf    a single condition on a field
    GateAllOf   every child predicate must pass
    GateAnyOf   at least one child predicate must pass

Field-path semantics (leaf):
    ``raw_inputs.<name>``               look up the value in raw_inputs
    ``score_results.<id>.<field>``      look up a previously computed
                                        ScoreResult for ``<id>`` and pull
                                        the named attribute. If that prior
                                        result has status != OK (or is
                                        absent), the field is treated as
                                        unresolvable.

Operators (leaf): equals, in, ge, le, gt, lt, truthy.

Missing policy (leaf):
    "fail"   unresolvable field => leaf is decisive FAIL.
    "skip"   unresolvable field => leaf is NON-DECISIVE (3-state: PASS /
             FAIL / SKIP). A skip leaf neither satisfies an ``any_of``
             branch nor violates an ``all_of`` constraint -- the gate
             falls through to the next branch / next constraint.

Combinator propagation under 3-state logic:
    any_of(skip, fail) -> fail            any_of(skip, pass) -> pass
    any_of(skip)        -> skip           any_of()             -> fail (vacuous)
    all_of(skip, pass) -> pass            all_of(skip, fail)  -> fail
    all_of(skip)        -> skip           all_of()             -> pass (vacuous)

The public ``evaluate_predicate`` API still returns a 2-state
``passed: bool``; a top-level SKIP maps to ``passed=True`` because no
decisive failure was found. Reconciles the architecture_spec.md §6
"falls through" narrative with the leaf-level semantics it requires
(per commitments_log erratum #3, 4 May 2026).

Trace format (audit log per architecture_spec §11):
    ``leaf:<failure_reason_code>:<pass|fail|skip>``
    ``all_of:start`` ... per-child entries ... ``all_of:<pass|fail>``
    ``any_of:start`` ... per-child entries ... ``any_of:<pass|fail>``

Pure functions: no I/O, no time, no state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence, Union

from healthscore.enums import ScoreStatus
from healthscore.types import ScoreResult


# ──────────────────────────────────────────────────────────────────────────
# Predicate types
# ──────────────────────────────────────────────────────────────────────────

_LEAF_OPERATORS = ("equals", "in", "ge", "le", "gt", "lt", "truthy")
_MISSING_POLICIES = ("fail", "skip")


@dataclass(frozen=True, slots=True)
class GateLeaf:
    """A single field condition.

    ``field``                   dotted path: ``raw_inputs.<name>`` or
                                ``score_results.<id>.<field>``.
    ``predicate``               one of ``equals | in | ge | le | gt | lt | truthy``.
    ``expected``                value the predicate compares against.
                                Ignored for ``truthy``.
    ``missing_policy``          ``"fail"`` (decisive fail on missing) or
                                ``"skip"`` (non-decisive on missing -- the
                                leaf neither satisfies any_of nor violates
                                all_of; see module docstring for the full
                                3-state combinator-propagation rules).
    ``failure_reason_code``     short snake_case code recorded on
                                ScoreResult.gate_failures and in the
                                evaluation trace. Mandatory.
    """

    field: str
    predicate: str
    expected: object | None
    missing_policy: str
    failure_reason_code: str

    def __post_init__(self) -> None:
        if self.predicate not in _LEAF_OPERATORS:
            raise ValueError(
                f"GateLeaf.predicate must be one of {_LEAF_OPERATORS}; "
                f"got {self.predicate!r}"
            )
        if self.missing_policy not in _MISSING_POLICIES:
            raise ValueError(
                f"GateLeaf.missing_policy must be one of {_MISSING_POLICIES}; "
                f"got {self.missing_policy!r}"
            )
        if not self.failure_reason_code:
            raise ValueError("GateLeaf.failure_reason_code is mandatory")
        if not (
            self.field.startswith("raw_inputs.")
            or self.field.startswith("score_results.")
        ):
            raise ValueError(
                f"GateLeaf.field must start with 'raw_inputs.' or 'score_results.'; "
                f"got {self.field!r}"
            )


@dataclass(frozen=True, slots=True)
class GateAllOf:
    """All child predicates must pass."""

    all_of: tuple["GatePredicate", ...]


@dataclass(frozen=True, slots=True)
class GateAnyOf:
    """At least one child predicate must pass."""

    any_of: tuple["GatePredicate", ...]


GatePredicate = Union[GateLeaf, GateAllOf, GateAnyOf]


# ──────────────────────────────────────────────────────────────────────────
# Field resolution
# ──────────────────────────────────────────────────────────────────────────


_UNRESOLVED = object()


def _resolve_field(
    field: str,
    raw_inputs: Mapping[str, object],
    prior_results: Mapping[str, ScoreResult],
) -> object:
    """Walk a dotted field path. Returns ``_UNRESOLVED`` if not resolvable.

    ``raw_inputs.<name>`` -> raw_inputs.get(name). None counts as unresolved.

    ``score_results.<id>.<field>`` -> prior_results.get(id). If absent or
    status != OK, unresolved. Otherwise getattr(result, field). If the
    pulled value is None, also unresolved.
    """
    parts = field.split(".")
    if len(parts) < 2:
        return _UNRESOLVED

    if parts[0] == "raw_inputs":
        if len(parts) != 2:
            return _UNRESOLVED
        value = raw_inputs.get(parts[1])
        if value is None:
            return _UNRESOLVED
        return value

    if parts[0] == "score_results":
        if len(parts) != 3:
            return _UNRESOLVED
        score_id, attr = parts[1], parts[2]
        prior = prior_results.get(score_id)
        if prior is None or prior.status is not ScoreStatus.OK:
            return _UNRESOLVED
        try:
            value = getattr(prior, attr)
        except AttributeError:
            return _UNRESOLVED
        if value is None:
            return _UNRESOLVED
        return value

    return _UNRESOLVED


# ──────────────────────────────────────────────────────────────────────────
# Leaf-operator evaluation
# ──────────────────────────────────────────────────────────────────────────


def _apply_operator(operator: str, value: object, expected: object | None) -> bool:
    if operator == "equals":
        return value == expected
    if operator == "truthy":
        return bool(value)
    if operator == "in":
        if not isinstance(expected, (list, tuple, set, frozenset)):
            raise ValueError(
                f"'in' operator expects a list/tuple/set; got {type(expected).__name__}"
            )
        return value in expected
    # numeric comparisons
    try:
        v = float(value)  # type: ignore[arg-type]
        e = float(expected)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"operator {operator!r} requires numeric value/expected; "
            f"got value={value!r} expected={expected!r}"
        ) from exc
    if operator == "ge":
        return v >= e
    if operator == "le":
        return v <= e
    if operator == "gt":
        return v > e
    if operator == "lt":
        return v < e
    raise ValueError(f"unknown operator {operator!r}")


# ──────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────


# Three-state internal outcomes for combinators with a "skip" leaf:
#
# Per architecture_spec.md §6 narrative ("the engine falls through to the
# screening-evidence branch"), a leaf whose missing_policy is "skip" must
# be NON-DECISIVE -- it does not satisfy an any_of branch nor does it
# violate an all_of constraint. The Phase 2 implementation uses 3-state
# {pass | fail | skip} internally; the public API still returns a 2-state
# (passed: bool) where a top-level skip is mapped to "passed" because there
# is no decisive failure to report.
_PASS = "pass"
_FAIL = "fail"
_SKIP = "skip"


def evaluate_predicate(
    predicate: GatePredicate,
    raw_inputs: Mapping[str, object],
    prior_results: Mapping[str, ScoreResult],
) -> tuple[bool, tuple[str, ...], tuple[str, ...]]:
    """Evaluate a (possibly nested) predicate.

    Returns ``(passed, failure_reason_codes, evaluation_trace)``:
        ``passed``                whether the predicate as a whole passes.
                                  A top-level "skip" maps to passed=True
                                  because no decisive failure was found.
        ``failure_reason_codes``  every leaf-failure reason code reachable
                                  from the failing branches; preserves
                                  evaluation order; deduplicated by first
                                  occurrence.
        ``evaluation_trace``      ordered audit trail of node decisions.
                                  Format documented in the module docstring.
    """
    state, failures, trace_list = _evaluate(predicate, raw_inputs, prior_results)
    passed = state in (_PASS, _SKIP)
    return passed, _dedupe(failures), tuple(trace_list)


def _dedupe(seq: Sequence[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    out: list[str] = []
    for item in seq:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return tuple(out)


def _evaluate(
    predicate: GatePredicate,
    raw_inputs: Mapping[str, object],
    prior_results: Mapping[str, ScoreResult],
) -> tuple[str, list[str], list[str]]:
    """Internal: returns (state, failures-in-order-with-dupes, trace-list).

    ``state`` is one of _PASS / _FAIL / _SKIP (3-state logic).
    """
    if isinstance(predicate, GateLeaf):
        return _evaluate_leaf(predicate, raw_inputs, prior_results)
    if isinstance(predicate, GateAllOf):
        return _evaluate_all_of(predicate, raw_inputs, prior_results)
    if isinstance(predicate, GateAnyOf):
        return _evaluate_any_of(predicate, raw_inputs, prior_results)
    raise TypeError(f"Unknown GatePredicate variant: {type(predicate).__name__}")


def _evaluate_leaf(
    leaf: GateLeaf,
    raw_inputs: Mapping[str, object],
    prior_results: Mapping[str, ScoreResult],
) -> tuple[str, list[str], list[str]]:
    value = _resolve_field(leaf.field, raw_inputs, prior_results)

    if value is _UNRESOLVED:
        if leaf.missing_policy == "skip":
            # 3-state SKIP: this leaf is non-decisive. It does not satisfy an
            # any_of branch nor violate an all_of constraint -- the gate
            # falls through to the next branch / next constraint.
            return _SKIP, [], [f"leaf:{leaf.failure_reason_code}:skip"]
        # missing_policy == "fail"
        return _FAIL, [leaf.failure_reason_code], [f"leaf:{leaf.failure_reason_code}:fail"]

    truth = _apply_operator(leaf.predicate, value, leaf.expected)
    if truth:
        return _PASS, [], [f"leaf:{leaf.failure_reason_code}:pass"]
    return _FAIL, [leaf.failure_reason_code], [f"leaf:{leaf.failure_reason_code}:fail"]


def _evaluate_all_of(
    node: GateAllOf,
    raw_inputs: Mapping[str, object],
    prior_results: Mapping[str, ScoreResult],
) -> tuple[str, list[str], list[str]]:
    """All decisive children must pass.

    A SKIP child is non-decisive: it neither satisfies nor violates the
    all_of. all_of(skip, ...) is equivalent to all_of(...) with the skip
    removed. all_of() with no decisive children passes (vacuous truth).
    No short-circuit: every child evaluates so the audit trail is full.
    """
    trace: list[str] = ["all_of:start"]
    failures: list[str] = []
    has_decisive_pass = False
    has_fail = False
    for child in node.all_of:
        c_state, c_fails, c_trace = _evaluate(child, raw_inputs, prior_results)
        trace.extend(c_trace)
        if c_state == _FAIL:
            has_fail = True
            failures.extend(c_fails)
        elif c_state == _PASS:
            has_decisive_pass = True
        # _SKIP is non-decisive

    if has_fail:
        trace.append("all_of:fail")
        return _FAIL, failures, trace
    if has_decisive_pass or not node.all_of:
        # Either at least one decisive pass, or vacuously empty all_of.
        trace.append("all_of:pass")
        return _PASS, [], trace
    # all children skipped
    trace.append("all_of:skip")
    return _SKIP, [], trace


def _evaluate_any_of(
    node: GateAnyOf,
    raw_inputs: Mapping[str, object],
    prior_results: Mapping[str, ScoreResult],
) -> tuple[str, list[str], list[str]]:
    """At least one decisive child must pass.

    A SKIP child is non-decisive: it neither satisfies the any_of's
    existential nor counts as a failure. any_of(skip, fail) -> fail (no
    pass, one decisive fail). any_of(skip, pass) -> pass. any_of() -> fail
    (vacuous existential). any_of(skip) -> skip (the whole compound is
    non-decisive). No short-circuit on success.
    """
    trace: list[str] = ["any_of:start"]
    failures_per_child: list[list[str]] = []
    has_pass = False
    has_decisive = False

    if not node.any_of:
        trace.append("any_of:fail")
        return _FAIL, [], trace

    for child in node.any_of:
        c_state, c_fails, c_trace = _evaluate(child, raw_inputs, prior_results)
        trace.extend(c_trace)
        if c_state == _PASS:
            has_pass = True
            has_decisive = True
        elif c_state == _FAIL:
            has_decisive = True
            failures_per_child.append(c_fails)
        # _SKIP is non-decisive

    if has_pass:
        trace.append("any_of:pass")
        return _PASS, [], trace
    if not has_decisive:
        # Every child SKIPped -- the any_of itself is non-decisive.
        trace.append("any_of:skip")
        return _SKIP, [], trace
    # No pass, but at least one decisive fail.
    flat = [f for fl in failures_per_child for f in fl]
    trace.append("any_of:fail")
    return _FAIL, flat, trace


# ──────────────────────────────────────────────────────────────────────────
# Gate -> ScoreResult helper
# ──────────────────────────────────────────────────────────────────────────


def evaluate_gate_to_result(
    score_id: str,
    predicate: GatePredicate | None,
    raw_inputs: Mapping[str, object],
    prior_results: Mapping[str, ScoreResult],
) -> ScoreResult | None:
    """Apply a score's gate; return a GATED ScoreResult on failure, else None.

    Per architecture_spec.md §6:
        A score whose gate fails is *never computed*: it returns
        ScoreResult(status=GATED, gate_failures=(...), gate_evaluation_trace=(...))
        with raw_value, normalised_q, risk_band, and wording all None.

    A return of None means the gate passed (or there is no gate) -- the
    caller proceeds to compute the score.
    """
    if predicate is None:
        return None
    passed, failures, trace = evaluate_predicate(predicate, raw_inputs, prior_results)
    if passed:
        return None
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
        gate_failures=failures,
        gate_evaluation_trace=trace,
        reason=None,
        wording=None,
    )
