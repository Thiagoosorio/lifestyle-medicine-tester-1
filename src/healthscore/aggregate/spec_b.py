"""Spec B aggregation: weighted geometric + non-compensatory red-flag layer.

Per architecture_spec.md §5 and methodology §1.3.

Organ level (identical to Spec A by methodology §1.3 -- both use the same
weighted geometric mean within organ). The two specs are kept as separate
modules so they remain swappable: if a future methodology revision diverges
them at organ level, only this module's organ function changes.

Domain level (no min term, no alpha):
    DomainScore_B = 100 * exp(Sum w_j * ln(OrganScore_j / 100))

Red flags are NOT folded into the Spec B numbers. They are surfaced
separately by redflags.collect() (Phase 1+) and rendered alongside the
composite. This preserves the methodology §1.4 "non-compensatory" rule:
a red flag is a flag regardless of any score.

Pure functions: no I/O, no time, no state.
"""

from __future__ import annotations

from typing import Mapping, Sequence

from healthscore.aggregate.common import weighted_geomean
from healthscore.enums import ScoreStatus
from healthscore.types import OrganScore, ScoreResult


def aggregate_organ_spec_b(
    *,
    score_results: Sequence[ScoreResult],
    weights: Mapping[str, float],
    epsilon: float,
) -> tuple[float | None, tuple[str, ...]]:
    """Spec B organ-level: identical to Spec A by methodology §1.3.

    Implemented as a separate function (not a delegating shim) so the two
    specs remain decoupled. If a future methodology revision diverges
    Spec B at organ level, only the body of this function changes.
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


def aggregate_domain_spec_b(
    *,
    organs: Sequence[OrganScore],
    organ_weights: Mapping[str, float],
    epsilon: float,
) -> float | None:
    """Spec B domain-level: weighted geometric mean of organ scores.

        DomainScore_B = 100 * exp(Sum w'_j * ln(OrganScore_j / 100))

    Surviving organ weights are renormalised to sum to 1. Epsilon floor
    applies to OrganScore_j / 100 via weighted_geomean.

    Red flags are NOT incorporated into this number.
    """
    valid: list[tuple[str, float, float]] = []
    for o in organs:
        if o.spec_b_value is None:
            continue
        w = organ_weights.get(o.organ_id, 0.0)
        if w <= 0.0:
            continue
        valid.append((o.organ_id, o.spec_b_value, w))

    if not valid:
        return None

    pairs_q = [(s / 100.0, w) for _, s, w in valid]
    geomean_100, _ = weighted_geomean(pairs_q, epsilon)
    return geomean_100
