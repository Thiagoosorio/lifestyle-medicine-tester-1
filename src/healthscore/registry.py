"""Score registry: dependency extraction, topological sort, cycle detection.

Per architecture_spec.md §6:

    At engine startup, walk every score's gate tree. Collect
    ``score_results.<id>`` references as edges: ``<id>`` -> this score (this
    score depends on ``<id>``).

    Topologically sort the score registry. Cycle -> RegistryConflictError
    at startup.

This module fires at engine startup; it never runs in the per-computation
hot path. Per architecture_spec.md §9, registry conflicts and cycles are
*exceptions* (not ScoreResult.status values) -- they belong to the
"engine refuses to start" class.

Pure functions: no I/O, no time, no state.
"""

from __future__ import annotations

from typing import Mapping

from healthscore.errors import RegistryConflictError
from healthscore.gates import GateAllOf, GateAnyOf, GateLeaf, GatePredicate


def extract_score_dependencies(predicate: GatePredicate | None) -> set[str]:
    """Collect every score_id referenced via ``score_results.<id>.<field>``.

    None gate -> empty set. Any combinator -> union of children. A leaf's
    field path that doesn't reference another score -> not a dependency.
    """
    if predicate is None:
        return set()
    if isinstance(predicate, GateLeaf):
        if predicate.field.startswith("score_results."):
            parts = predicate.field.split(".")
            if len(parts) >= 2 and parts[1]:
                return {parts[1]}
        return set()
    if isinstance(predicate, GateAllOf):
        out: set[str] = set()
        for child in predicate.all_of:
            out |= extract_score_dependencies(child)
        return out
    if isinstance(predicate, GateAnyOf):
        out2: set[str] = set()
        for child in predicate.any_of:
            out2 |= extract_score_dependencies(child)
        return out2
    raise TypeError(f"Unknown GatePredicate variant: {type(predicate).__name__}")


def topological_sort(
    score_gates: Mapping[str, GatePredicate | None],
) -> list[str]:
    """Return a topological ordering of the registered score IDs.

    ``score_gates`` maps each score_id to its gate predicate (or None).
    A score whose gate references ``score_results.<other>.<field>``
    depends on ``<other>``: ``<other>`` must be ordered before this score.

    Raises:
        RegistryConflictError if any score's gate references an unknown
        score_id, or if any cycle exists.

    Algorithm: Kahn's BFS. Stable ordering (sorted score_ids at each
    level) so the audit log's ``score_eval_order`` is deterministic.
    """
    # Build dependency graph and in-degree map.
    score_ids = sorted(score_gates.keys())
    deps: dict[str, set[str]] = {sid: set() for sid in score_ids}
    dependents: dict[str, set[str]] = {sid: set() for sid in score_ids}

    for sid, gate in score_gates.items():
        ref_ids = extract_score_dependencies(gate)
        for ref in ref_ids:
            if ref not in deps:
                raise RegistryConflictError(
                    f"score {sid!r} gate references unknown score_id {ref!r}"
                )
            if ref == sid:
                raise RegistryConflictError(
                    f"score {sid!r} gate references itself; self-cycle"
                )
            deps[sid].add(ref)
            dependents[ref].add(sid)

    in_degree = {sid: len(deps[sid]) for sid in score_ids}

    # Start with all zero-in-degree nodes, sorted for determinism.
    ready = sorted(sid for sid in score_ids if in_degree[sid] == 0)
    ordered: list[str] = []

    while ready:
        sid = ready.pop(0)
        ordered.append(sid)
        # Drain edges out of this node, sorted for stable output.
        for child in sorted(dependents[sid]):
            in_degree[child] -= 1
            if in_degree[child] == 0:
                # Insertion-sort into ``ready`` to keep it ordered.
                _insort(ready, child)

    if len(ordered) != len(score_ids):
        cycle_members = [sid for sid in score_ids if in_degree[sid] > 0]
        raise RegistryConflictError(
            f"cyclic gate dependency detected; remaining nodes with non-zero "
            f"in-degree: {cycle_members}"
        )

    return ordered


def _insort(seq: list[str], item: str) -> None:
    """Tiny in-place sorted insertion (avoids importing bisect)."""
    lo, hi = 0, len(seq)
    while lo < hi:
        mid = (lo + hi) // 2
        if seq[mid] < item:
            lo = mid + 1
        else:
            hi = mid
    seq.insert(lo, item)
