"""Minimal engine orchestrator (Phase 4 integration test seam).

Walks every loaded ``ScoreConfig`` in topological order over the gate
dependency graph, evaluates each score via the per-score pipeline
(``score_eval.evaluate_score``), and groups the surviving OK scores
into per-organ ``OrganScore`` aggregates via the Spec A and Spec B
aggregators.

The full ``engine.compute()`` orchestration with audit logging,
``AggregationOverrides``, and Sobol harness wiring is a later phase
(architecture_spec.md §11, §12). This module is the slim subset
needed for the Phase 4 integration test suite.

Pure functions (the supplied wording / instrument registries are
read-only). No I/O, no time, no state.
"""

from __future__ import annotations

from typing import Mapping, Sequence

from healthscore.aggregate.spec_a import aggregate_organ_spec_a
from healthscore.aggregate.spec_b import aggregate_organ_spec_b
from healthscore.gates import GateAllOf, GateAnyOf, GateLeaf, GatePredicate
from healthscore.instruments import InstrumentRegistry
from healthscore.registry import topological_sort
from healthscore.score_config import ScoreConfig, parse_gate_spec
from healthscore.score_eval import evaluate_score
from healthscore.scores import lookup_formula
from healthscore.types import OrganScore, ScoreResult


def _gate_for(config: ScoreConfig) -> GatePredicate | None:
    return parse_gate_spec(config.gate_requirements)


def _resolve_eval_order(configs: Mapping[str, ScoreConfig]) -> tuple[str, ...]:
    """Topologically sort scores so any score whose gate references
    another score's result evaluates after that other score."""
    score_gates: dict[str, GatePredicate | None] = {
        sid: _gate_for(cfg) for sid, cfg in configs.items()
    }
    # Build graph with all known scores and their gates.
    # topological_sort raises RegistryConflictError on cycles.
    return tuple(topological_sort(score_gates))


def evaluate_all_scores(
    *,
    configs: Mapping[str, ScoreConfig],
    raw_inputs: Mapping[str, object],
    instrument_registry: InstrumentRegistry | None = None,
    epsilon: float = 0.01,
    templates: Mapping[str, Mapping[str, str]] | None = None,
) -> dict[str, ScoreResult]:
    """Run every loaded score through ``evaluate_score`` in topological
    order. Returns a ``score_id -> ScoreResult`` mapping."""
    eval_order = _resolve_eval_order(configs)
    results: dict[str, ScoreResult] = {}
    for sid in eval_order:
        cfg = configs[sid]
        result = evaluate_score(
            cfg,
            raw_inputs=raw_inputs,
            prior_results=results,
            formula=lookup_formula(cfg.formula),
            gate=_gate_for(cfg),
            epsilon=epsilon,
            templates=templates,
            instrument_registry=instrument_registry,
        )
        results[sid] = result
    return results


def aggregate_organ(
    *,
    organ_id: str,
    domain_id: str,
    member_results: Sequence[ScoreResult],
    weights: Mapping[str, float],
    epsilon: float = 0.01,
    confidence: str = "moderate",
) -> OrganScore:
    """Bundle the per-organ Spec A + Spec B aggregation into an
    ``OrganScore``. Inputs whose status is not OK are dropped per
    methodology §1.5; surviving weights renormalise inside the
    aggregators."""
    spec_a, eps_a = aggregate_organ_spec_a(
        score_results=list(member_results), weights=weights, epsilon=epsilon,
    )
    spec_b, _ = aggregate_organ_spec_b(
        score_results=list(member_results), weights=weights, epsilon=epsilon,
    )
    return OrganScore(
        organ_id=organ_id,
        domain_id=domain_id,
        inputs=tuple(member_results),
        spec_a_value=spec_a,
        spec_b_value=spec_b,
        epsilon_activations=eps_a,
        weights_used={
            sid: w for sid, w in weights.items() if w > 0.0
        },
        red_flags=(),
        confidence=confidence,  # type: ignore[arg-type]
    )
