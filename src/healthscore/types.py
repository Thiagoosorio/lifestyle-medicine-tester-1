"""Type definitions for the scoring core.

Per architecture_spec.md §3:

- pydantic v2 BaseModel for anything that crosses a config or API boundary
  (ScoreInput, AggregationOutput).
- @dataclass(frozen=True, slots=True) for internal-only structures
  (ScoreResult, RedFlag, OrganScore, DomainScore).
- Decimal at user-facing boundaries; float in aggregation maths.
- Every nullable field is typed `T | None`. Missing scores arrive as a
  ScoreResult with status != OK and a populated reason -- never silently
  dropped.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field

from healthscore.enums import (
    AnchorSource,
    InterpolationMode,
    RedFlagSeverity,
    RiskBand,
    ScoreStatus,
)


# ── Boundary type: user-side input ───────────────────────────────────────────


class ScoreInput(BaseModel):
    """User-side inputs for a single score computation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    score_id: str
    raw_inputs: Mapping[str, Decimal | str | bool | None]
    locale: Literal["en", "ar"] = "en"      # drives Arabic-cutoff selection (§5.5)
    population: str | None = None           # e.g. "uae_emirati"; None = derivation default


# ── Internal types: ScoreResult, RedFlag, OrganScore, DomainScore ───────────


@dataclass(frozen=True, slots=True)
class ScoreResult:
    score_id: str
    status: ScoreStatus
    raw_value: Decimal | None                                # native units (FIB-4 = 2.0)
    normalised_q: float | None                               # health value in [0, 1] AFTER eps floor (None if not OK)
    epsilon_applied: bool                                    # True if epsilon floor activated
    risk_band: RiskBand | None
    anchors_used: tuple[Decimal, Decimal, Decimal] | None    # (low, indet, high)
    anchor_sources: tuple[AnchorSource, AnchorSource, AnchorSource] | None
    interpolation_mode: InterpolationMode | None
    confidence: Literal["high", "moderate", "low", "single_source"] | None
    pmid: str | None
    active_instrument: str | None                            # e.g. "moca" if this slot resolved to MoCA
    gate_failures: tuple[str, ...]                           # empty if gates passed
    gate_evaluation_trace: tuple[str, ...]                   # ordered audit trace of gate node evaluations
    reason: str | None                                       # for non-OK statuses; not user-facing
    wording: str | None                                      # rendered, regulator-safe; user-facing
    calibration_banner: str | None = None                    # §5.5; e.g. UAE-PREVENT pending recalibration


@dataclass(frozen=True, slots=True)
class RedFlag:
    score_id: str
    severity: RedFlagSeverity
    threshold_label: str                                     # e.g. "FIB-4 >= 2.67"
    actual_value: Decimal
    wording: str                                             # rendered, regulator-safe (§8)
    pmid: str


@dataclass(frozen=True, slots=True)
class OrganScore:
    organ_id: str                                            # "liver", "kidney", "cvd", ...
    domain_id: str                                           # "heart_metab", "brain", ...
    inputs: tuple[ScoreResult, ...]                          # contributing ScoreResults
    spec_a_value: float | None                               # 0-100; None if every input failed
    spec_b_value: float | None                               # 0-100; identical to A at organ level
    epsilon_activations: tuple[str, ...]                     # score_ids where eps fired
    weights_used: Mapping[str, float]                        # weights AFTER renormalisation; sums to 1
    red_flags: tuple[RedFlag, ...]                           # collected from inputs
    confidence: Literal["high", "moderate", "low"]


@dataclass(frozen=True, slots=True)
class DomainScore:
    domain_id: str                                           # one of the 5
    organs: tuple[OrganScore, ...]
    spec_a_value: float | None                               # alpha-blend per §1.3
    spec_b_value: float | None                               # weighted geometric per §1.3
    disagreement: float | None                               # |spec_a - spec_b|; None if either missing
    disagreement_flag: bool                                  # True if disagreement > threshold (§1.3)
    red_flags: tuple[RedFlag, ...]                           # rolled up from organs
    alpha_used: float                                        # the alpha actually used in this run
    epsilon_used: float                                      # the epsilon actually used in this run


# ── Boundary type: top-level result ──────────────────────────────────────────


class AggregationOutput(BaseModel):
    """Top-level result from engine.compute()."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    schema_version: str = "1.0.0"
    run_id: str                                              # ULID; ties to audit log
    config_hash: str                                         # SHA-256 of resolved config
    locale: Literal["en", "ar"]
    population: str | None
    domains: Sequence[DomainScore]
    score_results: Sequence[ScoreResult]                     # all per-score computations
    red_flags: Sequence[RedFlag]                             # union across organs
    active_instruments: Mapping[str, str]                    # {"cognitive": "moca", "osa": "stop_bang"}
    timestamp_utc: str                                       # ISO-8601, fixed by caller (not core)
    disclaimer: str = Field(                                 # §8: every output carries the §5.3 disclaimer
        default=(
            "This score is a wellness and risk-stratification aid based on published "
            "screening tools. It is not a diagnosis, does not rule disease in or out, "
            "and does not replace a clinician's judgment. Abnormal or high-risk results "
            "should be discussed with a licensed clinician. Do not change medications, "
            "start treatment, or delay medical care based on this score alone."
        )
    )
