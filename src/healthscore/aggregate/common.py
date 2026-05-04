"""Aggregation primitives shared by Spec A and Spec B.

Per architecture_spec.md §5 ("Epsilon floor handling"):

    `normalise_for_geomean` is the *only* place epsilon is applied.

    It returns whether activation occurred, and that boolean propagates up
    into OrganScore.epsilon_activations and the audit log.

    Epsilon is a parameter, never a constant -- §12 (the harness seam)
    perturbs it across runs without modifying the core.

Pure functions: no I/O, no time, no state. Both specs import from here.
"""

from __future__ import annotations

import math
from typing import Sequence


def normalise_for_geomean(q: float, epsilon: float) -> tuple[float, bool]:
    """Apply the epsilon floor before the logarithm.

    Returns (q_floored, epsilon_was_applied).

    Geometric mean breaks at zero, so any q below epsilon is replaced with
    epsilon and the activation is reported up the call chain. The audit
    log records epsilon activations per score; the harness Sobol-perturbs
    epsilon across {0.005, 0.01, 0.02, 0.05} per architecture_spec §12.
    """
    if not (0.0 <= q <= 1.0):
        raise ValueError(f"q must be in [0, 1]; got {q}")
    if not (0.0 < epsilon < 1.0):
        raise ValueError(f"epsilon must be in (0, 1); got {epsilon}")
    if q < epsilon:
        return epsilon, True
    return q, False


def weighted_geomean(
    values: Sequence[tuple[float, float]],
    epsilon: float,
) -> tuple[float, list[bool]]:
    """Weighted geometric mean of q values, returned on the 0-100 scale.

    ``values`` is a sequence of ``(q_i, w_i)`` pairs where each ``q_i`` is in
    [0, 1] and each ``w_i`` is >= 0. Weights are renormalised to sum to 1.0
    inside this function so callers don't have to pre-normalise after
    skipping non-OK / gated / missing scores (architecture_spec §5).

    Returns:
        (score_100, eps_flags)
            score_100 is 100 * exp(Sum_i w'_i * ln(q'_i)) where w'_i is the
            renormalised weight and q'_i is q_i after the epsilon floor.
            eps_flags[i] is True if q_i fell below epsilon and was floored.

    Raises:
        ValueError if values is empty, all weights are zero, or any value
        is malformed.
    """
    if not values:
        raise ValueError("weighted_geomean requires at least one (q, w) pair")

    total_w = 0.0
    for q, w in values:
        if w < 0.0:
            raise ValueError(f"weights must be non-negative; got {w}")
        total_w += w
    if total_w <= 0.0:
        raise ValueError("at least one weight must be positive")

    eps_flags: list[bool] = []
    log_sum = 0.0
    for q, w in values:
        q_floor, eps_applied = normalise_for_geomean(q, epsilon)
        eps_flags.append(eps_applied)
        norm_w = w / total_w
        log_sum += norm_w * math.log(q_floor)

    return 100.0 * math.exp(log_sum), eps_flags
