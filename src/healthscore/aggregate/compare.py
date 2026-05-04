"""Disagreement helper for parallel Spec A and Spec B output.

Per architecture_spec.md §5 and methodology §1.3:

    If |Spec A - Spec B| > 5 points (on the 0-100 scale), the user-facing
    surface raises a "scores point in different directions" flag. The
    threshold is configurable (configs/domains.yaml::disagreement_threshold,
    default 5.0).

Pure function.
"""

from __future__ import annotations


def disagreement(
    spec_a: float | None,
    spec_b: float | None,
    threshold: float,
) -> tuple[float | None, bool]:
    """Compute |spec_a - spec_b| and whether it crosses ``threshold``.

    Returns:
        (abs_difference, exceeded)
        If either spec is None, returns (None, False) -- a missing spec is
        not "in disagreement", it's "not computed".
    """
    if threshold < 0.0:
        raise ValueError(f"threshold must be non-negative; got {threshold}")
    if spec_a is None or spec_b is None:
        return None, False
    diff = abs(spec_a - spec_b)
    return diff, diff > threshold
