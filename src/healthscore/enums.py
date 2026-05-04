"""Enumerations used across the scoring core.

Per architecture_spec.md §3 (Type definitions). Keep this list closed:
new categories must be added deliberately, not silently widened.
"""

from __future__ import annotations

from enum import Enum


class ScoreStatus(str, Enum):
    OK = "ok"
    GATED = "gated"                         # gate-check failed; not computed
    MISSING_INPUT = "missing_input"         # required input absent
    OUT_OF_RANGE = "out_of_range"           # input outside physiological bounds
    NORMALISATION_BREAKDOWN = "normalisation_breakdown"  # epsilon floor or anchor inversion
    UNAVAILABLE = "unavailable"             # instrument not selected for this run


class RiskBand(str, Enum):
    LOW = "low"
    INDETERMINATE = "indeterminate"
    HIGH = "high"


class RedFlagSeverity(str, Enum):
    INFO = "info"
    ATTENTION = "attention"
    URGENT_REVIEW = "urgent_review"         # never "urgent" alone (§8 wording)


class ScoreKind(str, Enum):
    CONTINUOUS_3ANCHOR = "continuous_3anchor"
    ABSOLUTE_RISK_PCT = "absolute_risk_pct"
    ORDINAL_CATEGORY = "ordinal_category"
    SYMPTOM_BAND = "symptom_band"
    BINARY_SCREEN = "binary_screen"         # FIT, calprotectin -- flag only


class AnchorSource(str, Enum):
    """Anchor source distinction (commitments_log 4 May 2026)."""
    PUBLISHED = "published"
    CONSTRUCTED_MIDPOINT = "constructed_midpoint"


class InterpolationMode(str, Enum):
    """Selected by anchor_sources in normalize.py.

    THREE_ANCHOR_PWL  -- all three anchors PUBLISHED (e.g. ASCVD 5/7.5/20%)
    TWO_ANCHOR_PWL    -- indeterminate is CONSTRUCTED_MIDPOINT; the midpoint
                         is recorded in audit but skipped in interpolation
                         (e.g. FIB-4 1.30 / 1.985 / 2.67 -- 1.985 constructed)
    """
    THREE_ANCHOR_PWL = "three_anchor_pwl"
    TWO_ANCHOR_PWL = "two_anchor_pwl"
