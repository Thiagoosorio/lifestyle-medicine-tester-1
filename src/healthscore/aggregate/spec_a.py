"""Spec A aggregation: alpha-blended partial-min x weighted geometric.

Per architecture_spec.md §5 and methodology §1.3.

Organ level (same as Spec B by methodology §1.3):
    OrganScore_A = 100 * exp(Sum w_i * ln(max(q_i, eps)))

Domain level (alpha-blend; alpha and epsilon are exposed for Sobol):
    DomainScore_A = alpha * min(OrganScore_j) + (1 - alpha) * Pi OrganScore_j ** w_j

Pure functions: no I/O, no time, no state.
"""

from __future__ import annotations

from typing import Mapping, Sequence

from healthscore.aggregate.common import weighted_geomean
from healthscore.enums import ScoreStatus
from healthscore.types import OrganScore, ScoreResult


def aggregate_organ_spec_a(
    *,
    score_results: Sequence[ScoreResult],
    weights: Mapping[str, float],
    epsilon: float,
) -> tuple[float | None, tuple[str, ...]]:
    """Spec A organ-level: weighted geometric mean of contributing q values.

    Inputs whose status is not OK, whose normalised_q is None, or whose
    score_id has zero or missing weight are skipped. Surviving weights are
    renormalised to sum to 1 inside ``weighted_geomean``.

    Returns:
        (organ_score_0_100 | None, tuple of score_ids where epsilon floor activated)
        Returns (None, ()) when no input survives.
    """
    valid: list[tuple[str, float, float]] = []
    for r in score_results:
        if r.status is not ScoreStatus.OK or r.normalised_q is None:
            continue
        w = weights.get(r.score_id, 0.0)
        if w <= 0.0:
            continue
        valid.append((r.score_id, r.normalised_q, w))

    if not valid:
        return None, ()

    pairs = [(q, w) for _, q, w in valid]
    score_100, eps_flags = weighted_geomean(pairs, epsilon)
    eps_codes = tuple(sid for (sid, _, _), flagged in zip(valid, eps_flags) if flagged)
    return score_100, eps_codes


def aggregate_domain_spec_a(
    *,
    organs: Sequence[OrganScore],
    organ_weights: Mapping[str, float],
    alpha: float,
    epsilon: float,
) -> float | None:
    """Spec A domain-level alpha-blend.

        DomainScore_A = alpha * min(OrganScore_j)
                      + (1 - alpha) * 100 * exp(Sum w'_j * ln(OrganScore_j / 100))

    Both terms operate over the same set of surviving organs. Surviving
    weights are renormalised to sum to 1. The epsilon floor applies to
    OrganScore_j / 100 (which is in [0, 1]) via weighted_geomean.

    Returns None if no organ has a Spec A value or if no positive weight
    survives.
    """
    if not (0.0 <= alpha <= 1.0):
        raise ValueError(f"alpha must be in [0, 1]; got {alpha}")

    valid: list[tuple[str, float, float]] = []
    for o in organs:
        if o.spec_a_value is None:
            continue
        w = organ_weights.get(o.organ_id, 0.0)
        if w <= 0.0:
            continue
        valid.append((o.organ_id, o.spec_a_value, w))

    if not valid:
        return None

    organ_scores = [v[1] for v in valid]
    pairs_q = [(s / 100.0, w) for _, s, w in valid]
    geomean_100, _ = weighted_geomean(pairs_q, epsilon)
    min_score = min(organ_scores)

    return alpha * min_score + (1.0 - alpha) * geomean_100
