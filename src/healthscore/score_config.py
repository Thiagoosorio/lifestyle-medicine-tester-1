"""Score config schema + JSON loader + gate-spec parser.

Per architecture_spec.md §4 (Score config schema) and §6 (gate engine).

A score's per-file JSON config carries:
    score_id, display_name, kind, pmid_primary, pmid_supporting,
    guideline_anchor, input_variables, formula (dispatch key), anchors,
    anchors_unit, applicable_population, derivation_cohort,
    epsilon_override, red_flag (optional), gate_requirements (optional),
    confidence, instrument_slot (optional), version.

The loader validates the JSON via pydantic v2, refuses to load a config
that fails any check, and converts gate_requirements (a JSON tree of
``any_of`` / ``all_of`` / ``leaf`` nodes) into the recursive
``GatePredicate`` dataclasses defined in ``healthscore.gates``.

Pure functions: no I/O beyond reading the supplied path; no networking,
no time, no state.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from healthscore.enums import AnchorSource, ScoreKind
from healthscore.errors import ConfigValidationError
from healthscore.gates import GateAllOf, GateAnyOf, GateLeaf, GatePredicate


# ──────────────────────────────────────────────────────────────────────────
# Pydantic models
# ──────────────────────────────────────────────────────────────────────────


class InputVariableSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    name: str
    unit: str
    physio_min: Decimal | None = None
    physio_max: Decimal | None = None


class AnchorSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    value: Decimal
    q: float
    source: AnchorSource

    @field_validator("q")
    @classmethod
    def _q_in_unit_interval(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"anchor.q must be in [0, 1]; got {v}")
        return v


class AnchorsSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    low: AnchorSpec
    indeterminate: AnchorSpec
    high: AnchorSpec

    @model_validator(mode="after")
    def _validate_monotone_and_q_canonical(self) -> "AnchorsSpec":
        if not (self.low.value < self.indeterminate.value < self.high.value):
            raise ValueError(
                "anchors must satisfy low.value < indeterminate.value < high.value; "
                f"got {self.low.value} / {self.indeterminate.value} / {self.high.value}"
            )
        if self.low.q != 1.0 or self.indeterminate.q != 0.5 or self.high.q != 0.0:
            raise ValueError(
                "anchor q values must be exactly 1.0 / 0.5 / 0.0 "
                f"(got {self.low.q} / {self.indeterminate.q} / {self.high.q})"
            )
        return self


class ApplicablePopulationSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    min_age: float | None = None
    max_age: float | None = None
    exclusions: tuple[str, ...] = ()
    calibration_caveat: str | None = None


class DerivationCohortSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    study: str
    n: int | None = None
    geography: str | None = None
    ethnicity: str | None = None
    outcome: str | None = None


class RedFlagSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    trigger: Literal[">=", ">", "<=", "<", "=="]
    threshold: Decimal
    severity: Literal["info", "attention", "urgent_review"]
    wording_key: str


class ScoreConfig(BaseModel):
    """Validated score config loaded from configs/scores/<score_id>.json."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    score_id: str
    display_name: str
    kind: ScoreKind
    pmid_primary: str
    pmid_supporting: tuple[str, ...] = ()
    guideline_anchor: str | None = None
    input_variables: tuple[InputVariableSpec, ...]
    formula: str
    anchors: AnchorsSpec | None = None      # required for continuous_3anchor
    anchors_unit: str | None = None
    interpolation: Literal["piecewise_linear"] | None = "piecewise_linear"
    clamp: tuple[float, float] = (0.0, 1.0)
    applicable_population: ApplicablePopulationSpec | None = None
    derivation_cohort: DerivationCohortSpec | None = None
    epsilon_override: float | None = None
    red_flag: RedFlagSpec | None = None
    gate_requirements: Any = None           # parsed via parse_gate_spec
    confidence: Literal["high", "moderate", "low", "single_source"]
    instrument_slot: str | None = None
    version: str
    composite_member: bool = True
    composite_weight: float | None = None   # weight when composite_member is True

    @model_validator(mode="after")
    def _continuous_3anchor_requires_anchors(self) -> "ScoreConfig":
        if self.kind is ScoreKind.CONTINUOUS_3ANCHOR and self.anchors is None:
            raise ValueError(
                f"score {self.score_id!r}: kind=continuous_3anchor requires 'anchors'"
            )
        if self.composite_member and self.composite_weight is None:
            raise ValueError(
                f"score {self.score_id!r}: composite_member=true requires "
                "composite_weight"
            )
        if self.composite_weight is not None and self.composite_weight < 0.0:
            raise ValueError(
                f"score {self.score_id!r}: composite_weight must be >= 0; "
                f"got {self.composite_weight}"
            )
        return self


# ──────────────────────────────────────────────────────────────────────────
# Gate-spec parser
# ──────────────────────────────────────────────────────────────────────────


def parse_gate_spec(spec: Any) -> GatePredicate | None:
    """Convert the JSON ``gate_requirements`` field into a GatePredicate.

    Accepts:
        - None / empty list / empty dict        -> ungated (returns None)
        - {"any_of": [...]}                     -> GateAnyOf
        - {"all_of": [...]}                     -> GateAllOf
        - {"field": ..., "predicate": ...}      -> GateLeaf
    """
    if spec is None:
        return None
    if isinstance(spec, list) and not spec:
        return None
    if isinstance(spec, dict) and not spec:
        return None

    if isinstance(spec, dict):
        if "any_of" in spec:
            children = tuple(parse_gate_spec(c) for c in spec["any_of"])
            if any(c is None for c in children):
                raise ConfigValidationError(
                    "any_of children must all be valid gate specs; got an empty/None"
                )
            return GateAnyOf(any_of=children)
        if "all_of" in spec:
            children = tuple(parse_gate_spec(c) for c in spec["all_of"])
            if any(c is None for c in children):
                raise ConfigValidationError(
                    "all_of children must all be valid gate specs; got an empty/None"
                )
            return GateAllOf(all_of=children)
        if "field" in spec and "predicate" in spec:
            return GateLeaf(
                field=spec["field"],
                predicate=spec["predicate"],
                expected=spec.get("expected"),
                missing_policy=spec["missing_policy"],
                failure_reason_code=spec["failure_reason_code"],
            )

    raise ConfigValidationError(f"unrecognised gate spec: {spec!r}")


# ──────────────────────────────────────────────────────────────────────────
# Loader
# ──────────────────────────────────────────────────────────────────────────


def load_score_config(path: Path) -> ScoreConfig:
    """Load and validate a single score config from a JSON file.

    Raises ConfigValidationError on any structural or semantic problem so
    the engine refuses to start instead of silently mis-scoring.
    """
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigValidationError(f"score config not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigValidationError(f"invalid JSON in {path}: {exc}") from exc
    try:
        return ScoreConfig.model_validate(raw)
    except Exception as exc:
        raise ConfigValidationError(
            f"score config {path} failed validation: {exc}"
        ) from exc


def load_score_configs(directory: Path) -> dict[str, ScoreConfig]:
    """Load every ``*.json`` under ``directory`` as a ScoreConfig.

    Detects duplicate score_ids (RegistryConflictError-class problem).
    Raises ConfigValidationError on any individual file's validation
    failure or on duplicate score_ids.
    """
    configs: dict[str, ScoreConfig] = {}
    for path in sorted(Path(directory).glob("*.json")):
        cfg = load_score_config(path)
        if cfg.score_id in configs:
            raise ConfigValidationError(
                f"duplicate score_id {cfg.score_id!r} in {path}"
            )
        configs[cfg.score_id] = cfg
    return configs
