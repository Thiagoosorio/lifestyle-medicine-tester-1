"""Unit tests for the score registry: dependency extraction, topological
sort, cycle detection (architecture_spec.md §6).

Engine-startup test that constructs a deliberately cyclic config and
asserts RegistryConflictError fires before any computation runs.
"""

from __future__ import annotations

import pytest

from healthscore.errors import RegistryConflictError
from healthscore.gates import GateAllOf, GateAnyOf, GateLeaf
from healthscore.registry import (
    extract_score_dependencies,
    topological_sort,
)


# ──────────────────────────────────────────────────────────────────────────
# extract_score_dependencies
# ──────────────────────────────────────────────────────────────────────────


def test_extract_dependencies_from_none_gate_is_empty():
    assert extract_score_dependencies(None) == set()


def test_extract_dependencies_from_raw_inputs_leaf_is_empty():
    leaf = GateLeaf("raw_inputs.egfr", "le", 60, "fail", "egfr_above_ckd_threshold")
    assert extract_score_dependencies(leaf) == set()


def test_extract_dependencies_from_score_results_leaf_returns_score_id():
    leaf = GateLeaf(
        "score_results.fib4.raw_value", "ge", 1.3,
        "fail", "fib4_unavailable_or_low",
    )
    assert extract_score_dependencies(leaf) == {"fib4"}


def test_extract_dependencies_from_compound_collects_union():
    gate = GateAnyOf(
        any_of=(
            GateLeaf(
                "raw_inputs.chronic_liver_disease_status",
                "equals", True, "skip", "cld_not_documented",
            ),
            GateAllOf(
                all_of=(
                    GateLeaf(
                        "score_results.fib4.raw_value", "ge", 1.3,
                        "fail", "fib4_unavailable_or_low",
                    ),
                    GateLeaf(
                        "score_results.fli.raw_value", "ge", 60,
                        "fail", "fli_unavailable_or_low",
                    ),
                )
            ),
        )
    )
    assert extract_score_dependencies(gate) == {"fib4", "fli"}


# ──────────────────────────────────────────────────────────────────────────
# topological_sort -- happy paths
# ──────────────────────────────────────────────────────────────────────────


def test_topological_sort_with_no_dependencies_returns_alphabetical_order():
    """Stable ordering: Kahn's BFS with sorted-tie-break must yield a
    deterministic sequence. Required for reproducible audit logs."""
    gates = {"alpha": None, "charlie": None, "bravo": None}
    assert topological_sort(gates) == ["alpha", "bravo", "charlie"]


def test_topological_sort_simple_chain():
    gates = {
        "fib4": None,
        "amap": GateLeaf(
            "score_results.fib4.raw_value", "ge", 1.3,
            "fail", "fib4_unavailable_or_low",
        ),
    }
    assert topological_sort(gates) == ["fib4", "amap"]


def test_topological_sort_diamond():
    """A depends on root1, B depends on root2, C depends on A and B."""
    a_gate = GateLeaf("score_results.root1.raw_value", "ge", 1, "fail", "root1_low")
    b_gate = GateLeaf("score_results.root2.raw_value", "ge", 1, "fail", "root2_low")
    c_gate = GateAllOf(
        all_of=(
            GateLeaf("score_results.A.raw_value", "ge", 1, "fail", "a_low"),
            GateLeaf("score_results.B.raw_value", "ge", 1, "fail", "b_low"),
        )
    )
    gates = {"root1": None, "root2": None, "A": a_gate, "B": b_gate, "C": c_gate}
    order = topological_sort(gates)
    # Roots before A and B; A and B before C.
    assert order.index("root1") < order.index("A")
    assert order.index("root2") < order.index("B")
    assert order.index("A") < order.index("C")
    assert order.index("B") < order.index("C")


def test_topological_sort_amap_compound_gate_with_cross_score_refs():
    """The architecture_spec §6 aMAP example: aMAP depends on FIB-4 + FLI."""
    amap_gate = GateAnyOf(
        any_of=(
            GateLeaf(
                "raw_inputs.chronic_liver_disease_status",
                "equals", True, "skip", "cld_not_documented",
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
    gates = {"fib4": None, "fli": None, "amap": amap_gate}
    order = topological_sort(gates)
    assert order.index("fib4") < order.index("amap")
    assert order.index("fli") < order.index("amap")


# ──────────────────────────────────────────────────────────────────────────
# topological_sort -- failure modes (engine startup tests)
# ──────────────────────────────────────────────────────────────────────────


def test_unknown_dependency_raises_registry_conflict_at_startup():
    """A gate references a score_id not in the registry -> startup error."""
    gates = {
        "amap": GateLeaf(
            "score_results.unknown_score.raw_value", "ge", 1,
            "fail", "missing_dep",
        ),
    }
    with pytest.raises(RegistryConflictError, match="unknown score_id 'unknown_score'"):
        topological_sort(gates)


def test_self_cycle_raises_registry_conflict():
    """A score whose gate references itself -> RegistryConflictError."""
    gates = {
        "self_ref": GateLeaf(
            "score_results.self_ref.raw_value", "ge", 1,
            "fail", "self_loop",
        ),
    }
    with pytest.raises(RegistryConflictError, match="self-cycle"):
        topological_sort(gates)


def test_two_node_cycle_raises_registry_conflict_before_any_computation():
    """A's gate references B; B's gate references A. Engine refuses to start."""
    gates = {
        "A": GateLeaf("score_results.B.raw_value", "ge", 1, "fail", "needs_b"),
        "B": GateLeaf("score_results.A.raw_value", "ge", 1, "fail", "needs_a"),
    }
    with pytest.raises(RegistryConflictError, match="cyclic gate dependency"):
        topological_sort(gates)


def test_three_node_cycle_raises_registry_conflict():
    """Longer cycle A -> B -> C -> A also caught."""
    gates = {
        "A": GateLeaf("score_results.C.raw_value", "ge", 1, "fail", "needs_c"),
        "B": GateLeaf("score_results.A.raw_value", "ge", 1, "fail", "needs_a"),
        "C": GateLeaf("score_results.B.raw_value", "ge", 1, "fail", "needs_b"),
    }
    with pytest.raises(RegistryConflictError, match="cyclic gate dependency"):
        topological_sort(gates)


def test_cycle_buried_inside_compound_gate_is_still_caught():
    """A's gate any_of branches to a leaf that references B; B's gate references A.
    The cycle exists inside compound combinators, not just at top level."""
    gates = {
        "A": GateAnyOf(
            any_of=(
                GateLeaf("raw_inputs.x", "equals", 1, "skip", "x_skip"),
                GateLeaf("score_results.B.raw_value", "ge", 1, "fail", "needs_b"),
            )
        ),
        "B": GateAllOf(
            all_of=(
                GateLeaf("score_results.A.raw_value", "ge", 1, "fail", "needs_a"),
            )
        ),
    }
    with pytest.raises(RegistryConflictError, match="cyclic gate dependency"):
        topological_sort(gates)


def test_partial_cycle_with_some_independent_scores_still_raises():
    """A and B form a cycle; C is independent. Engine still refuses to
    start because the system has a cycle even if part of the graph is fine."""
    gates = {
        "A": GateLeaf("score_results.B.raw_value", "ge", 1, "fail", "needs_b"),
        "B": GateLeaf("score_results.A.raw_value", "ge", 1, "fail", "needs_a"),
        "C": None,
    }
    with pytest.raises(RegistryConflictError, match="cyclic gate dependency"):
        topological_sort(gates)
