"""Sobol-perturbable overrides (architecture_spec.md §12).

Every parameter the §4.5 Monte Carlo robustness protocol perturbs is
exposed via ``AggregationOverrides``. None means "use config default."
Any field that fires is recorded in the audit log under
``overrides_applied`` so a harness run is fully reconstructable.

Pure: pydantic boundary type, no I/O.
"""

from __future__ import annotations

from typing import Literal, Mapping

from pydantic import BaseModel, ConfigDict


class AggregationOverrides(BaseModel):
    """All Sobol-perturbable parameters; all optional."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Score-level weight overrides per organ: organ_id -> score_id -> weight.
    score_weights: Mapping[str, Mapping[str, float]] | None = None

    # Organ-level weight overrides per domain: domain_id -> organ_id -> weight.
    organ_weights: Mapping[str, Mapping[str, float]] | None = None

    # Domain-level alpha-blend (Spec A only).
    alpha: float | None = None

    # Global epsilon override.
    epsilon: float | None = None

    # Per-score epsilon override: score_id -> epsilon.
    epsilon_per_score: Mapping[str, float] | None = None

    # Normalisation alternative. Phase 6 ships only distance_to_cutoff
    # behind the seam; min_max / ordinal_ranked are placeholders for the
    # harness-mode branches in spec_a / spec_b.
    normalisation: Literal[
        "distance_to_cutoff", "min_max", "ordinal_ranked"
    ] | None = None

    # Aggregation alternative. Phase 6 ships only weighted_geometric
    # behind the seam; weighted_arithmetic / partial_min / owa are the
    # harness-mode branches per spec §12.
    aggregation: Literal[
        "weighted_geometric", "weighted_arithmetic", "partial_min", "owa"
    ] | None = None

    # Score-inclusion overrides for leave-one-out.
    score_inclusion: Mapping[str, bool] | None = None

    def applied_summary(self) -> dict[str, object]:
        """A compact dict of every override that fired, for the audit
        log's ``overrides_applied`` field."""
        out: dict[str, object] = {}
        if self.score_weights is not None:
            out["score_weights"] = {
                organ: dict(scores) for organ, scores in self.score_weights.items()
            }
        if self.organ_weights is not None:
            out["organ_weights"] = {
                dom: dict(organs) for dom, organs in self.organ_weights.items()
            }
        if self.alpha is not None:
            out["alpha"] = self.alpha
        if self.epsilon is not None:
            out["epsilon"] = self.epsilon
        if self.epsilon_per_score is not None:
            out["epsilon_per_score"] = dict(self.epsilon_per_score)
        if self.normalisation is not None:
            out["normalisation"] = self.normalisation
        if self.aggregation is not None:
            out["aggregation"] = self.aggregation
        if self.score_inclusion is not None:
            out["score_inclusion"] = dict(self.score_inclusion)
        return out
