"""Pluggable weighting strategies for the overall organ composite.

A weighting strategy takes a single score row (code, tier, severity, plus
its entry in config/score_classification.py) and returns a non-negative
weight. The composite is a weighted mean of the per-score severity-to-health
values within an organ, and then a weighted mean across organs.

Four strategies ship; adding a new one is a single subclass with
``compute_weight``. None are outcome-calibrated -- that's Phase 2 and needs
a linked-mortality cohort. See services/score_calibration/methodology.md
for the full design note.

Strategy summary
----------------
equal
    Every score gets weight 1. OECD Handbook's explicit baseline.
    Transparent but assumes every score is equally important, which is
    almost never true in biology.

evidence_tier
    Weight = tier_weight only (validated 1.0 / derived 0.6). This was the
    app's historical behaviour before the lifecycle + outcome-proximity
    tagging landed.

outcome_proximity
    Weight = outcome_proximity multiplier only
    (risk_calculator 1.5 / mechanistic 1.0 / derivative 0.6 / exploratory 0.4).
    Reflects "closer-to-outcome scores count more"; ignores tier and severity.

hybrid_recommended
    Weight = tier_weight * proximity * severity_emphasis. Current
    recommended default; combines the three signals the clinical-composite
    literature (OECD 2008, Greco 2019, Levine 2018) converges on as
    defensible without a linked-outcome cohort.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from config.score_classification import get_classification


# ─── Canonical multiplier tables (Phase-1, no outcomes data) ────────────────
_TIER_MULTIPLIER: dict[str, float] = {
    "validated": 1.0,
    "derived": 0.6,
}

_PROXIMITY_MULTIPLIER: dict[str, float] = {
    "risk_calculator": 1.5,
    "mechanistic": 1.0,
    "derivative": 0.6,
    "exploratory": 0.4,
}

# Severity emphasis mirrors _PREVENTION_SEVERITY_WEIGHTS in
# organ_score_service.py -- keep the two in sync.
_SEVERITY_EMPHASIS: dict[str, float] = {
    "optimal": 0.9,
    "normal": 0.9,
    "elevated": 1.2,
    "high": 1.5,
    "critical": 1.8,
}


@dataclass(frozen=True)
class Strategy:
    code: str
    label: str
    description: str
    compute_weight: Callable[[dict], float]


def _tier_only(score: dict) -> float:
    return _TIER_MULTIPLIER.get(str(score.get("tier", "")).lower(), 0.6)


def _proximity_only(score: dict) -> float:
    info = get_classification(score.get("code", ""))
    return _PROXIMITY_MULTIPLIER.get(info.get("outcome_proximity", "mechanistic"), 1.0)


def _hybrid(score: dict) -> float:
    info = get_classification(score.get("code", ""))
    tier = _TIER_MULTIPLIER.get(str(score.get("tier", "")).lower(), 0.6)
    proximity = _PROXIMITY_MULTIPLIER.get(info.get("outcome_proximity", "mechanistic"), 1.0)
    severity = _SEVERITY_EMPHASIS.get(str(score.get("severity", "")).lower(), 0.9)
    return tier * proximity * severity


def _equal(_score: dict) -> float:
    return 1.0


STRATEGIES: dict[str, Strategy] = {
    "equal": Strategy(
        code="equal",
        label="Equal weights",
        description="Every score counts equally. Baseline per OECD/JRC Handbook 2008, not a clinical recommendation.",
        compute_weight=_equal,
    ),
    "evidence_tier": Strategy(
        code="evidence_tier",
        label="Evidence tier only",
        description="Validated scores weighted 1.0x, derived 0.6x. App's historical default.",
        compute_weight=_tier_only,
    ),
    "outcome_proximity": Strategy(
        code="outcome_proximity",
        label="Outcome proximity only",
        description="Risk calculators 1.5x, mechanistic 1.0x, derivative 0.6x, exploratory 0.4x.",
        compute_weight=_proximity_only,
    ),
    "hybrid_recommended": Strategy(
        code="hybrid_recommended",
        label="Hybrid (recommended)",
        description="Evidence tier * outcome proximity * severity emphasis. Phase-1 default per Greco 2019.",
        compute_weight=_hybrid,
    ),
}

DEFAULT_STRATEGY = "hybrid_recommended"


def get_strategy(code: str) -> Strategy:
    return STRATEGIES.get(code, STRATEGIES[DEFAULT_STRATEGY])


def list_strategies() -> list[Strategy]:
    """Return strategies in a clinically meaningful display order."""
    order = ("equal", "evidence_tier", "outcome_proximity", "hybrid_recommended")
    return [STRATEGIES[c] for c in order]
