"""Distance-to-clinical-cutoff normalisation.

Per architecture_spec.md §5 and methodology §1.2:

    Three anchor points per continuous score:
        low_value          q = 1.0   (best health on this metric)
        indeterminate_v    q = 0.5
        high_value         q = 0.0   (worst health on this metric)

    Anchor-source distinction (commitments_log 4 May 2026):
        all three anchors PUBLISHED       -> THREE_ANCHOR_PWL through all three
        indeterminate CONSTRUCTED_MIDPOINT -> TWO_ANCHOR_PWL between low and high
                                              (constructed midpoint recorded in audit
                                              but skipped in interpolation maths)

The output q is clamped to [0, 1]. The epsilon floor is NOT applied here --
it is applied in aggregate.common.normalise_for_geomean before the log
(architecture_spec §5: "the only place epsilon is applied"). normalize.py
returns the pre-floor q so the audit trail can record the unfloored value.

Pure function: no I/O, no time, no state.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from healthscore.enums import AnchorSource, InterpolationMode


# Result of a normalisation call: the q value plus the interpolation mode used
# (for audit). Anchor-inversion / non-monotone configs are detected at engine
# startup, not here (config validation in Phase 1+).
@dataclass(frozen=True, slots=True)
class NormalisationOutcome:
    q: float                                       # in [0, 1] after clamp
    interpolation_mode: InterpolationMode
    clamped_high: bool                             # True if raw_value <= low_value (q hit ceiling)
    clamped_low: bool                              # True if raw_value >= high_value (q hit floor)


def select_interpolation_mode(
    low_source: AnchorSource,
    indeterminate_source: AnchorSource,
    high_source: AnchorSource,
) -> InterpolationMode:
    """Pick the interpolation mode from anchor sources.

    Per commitments_log 4 May 2026:
    - all three PUBLISHED  -> THREE_ANCHOR_PWL
    - indeterminate CONSTRUCTED_MIDPOINT (with low/high published) -> TWO_ANCHOR_PWL
    - any other combination is rejected as malformed config; raise ValueError
      so config-load surfaces it cleanly.
    """
    if (
        low_source is AnchorSource.PUBLISHED
        and indeterminate_source is AnchorSource.PUBLISHED
        and high_source is AnchorSource.PUBLISHED
    ):
        return InterpolationMode.THREE_ANCHOR_PWL
    if (
        low_source is AnchorSource.PUBLISHED
        and indeterminate_source is AnchorSource.CONSTRUCTED_MIDPOINT
        and high_source is AnchorSource.PUBLISHED
    ):
        return InterpolationMode.TWO_ANCHOR_PWL
    raise ValueError(
        "Anchor-source combination not supported: "
        f"low={low_source}, indeterminate={indeterminate_source}, high={high_source}. "
        "Allowed: (published, published, published) or "
        "(published, constructed_midpoint, published)."
    )


def _two_anchor_pwl(raw: float, low_v: float, high_v: float) -> tuple[float, bool, bool]:
    """Linear interpolation between (low_v, q=1) and (high_v, q=0)."""
    if high_v <= low_v:
        raise ValueError(f"high_value ({high_v}) must be greater than low_value ({low_v})")
    if raw <= low_v:
        return 1.0, True, False
    if raw >= high_v:
        return 0.0, False, True
    q = 1.0 - (raw - low_v) / (high_v - low_v)
    return q, False, False


def _three_anchor_pwl(
    raw: float, low_v: float, mid_v: float, high_v: float
) -> tuple[float, bool, bool]:
    """Piecewise-linear through (low_v, 1) -> (mid_v, 0.5) -> (high_v, 0)."""
    if not (low_v < mid_v < high_v):
        raise ValueError(
            f"anchors must satisfy low ({low_v}) < indeterminate ({mid_v}) < high ({high_v})"
        )
    if raw <= low_v:
        return 1.0, True, False
    if raw >= high_v:
        return 0.0, False, True
    if raw <= mid_v:
        # interpolate between (low_v, 1.0) and (mid_v, 0.5)
        q = 1.0 - 0.5 * (raw - low_v) / (mid_v - low_v)
        return q, False, False
    # raw is in (mid_v, high_v): interpolate between (mid_v, 0.5) and (high_v, 0.0)
    q = 0.5 - 0.5 * (raw - mid_v) / (high_v - mid_v)
    return q, False, False


def normalise_distance_to_cutoff(
    raw_value: Decimal,
    *,
    low_value: Decimal,
    indeterminate_value: Decimal,
    high_value: Decimal,
    low_source: AnchorSource,
    indeterminate_source: AnchorSource,
    high_source: AnchorSource,
) -> NormalisationOutcome:
    """Map a raw score value to a health value q in [0, 1].

    Convention (architecture_spec §5, methodology §1.2): higher raw_value =
    worse health, so q = 1.0 at low_value and q = 0.0 at high_value. Scores
    where higher = better health (e.g. eGFR) must be oriented BEFORE calling
    this function; orientation is a per-score concern, not a normalisation
    concern.

    Anchor-source rule (commitments_log 4 May 2026):
    - All three published -> three-anchor PWL through all three.
    - Indeterminate constructed_midpoint -> two-anchor PWL between low and
      high; the midpoint is recorded for audit but not used in maths.
    """
    mode = select_interpolation_mode(low_source, indeterminate_source, high_source)

    # math goes through float; raw is presented as Decimal at boundary
    raw = float(raw_value)
    low_v = float(low_value)
    mid_v = float(indeterminate_value)
    high_v = float(high_value)

    if mode is InterpolationMode.TWO_ANCHOR_PWL:
        q, hi, lo = _two_anchor_pwl(raw, low_v, high_v)
    else:
        q, hi, lo = _three_anchor_pwl(raw, low_v, mid_v, high_v)

    # Defensive clamp; should already hold from the helpers above.
    q = max(0.0, min(1.0, q))
    return NormalisationOutcome(
        q=q,
        interpolation_mode=mode,
        clamped_high=hi,
        clamped_low=lo,
    )
