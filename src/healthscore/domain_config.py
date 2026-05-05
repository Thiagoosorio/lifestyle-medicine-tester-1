"""Domain / organ / score weight configuration loader (architecture_spec.md §4).

Loads ``configs/domains.yaml`` into a frozen pydantic ``DomainsConfig``.
Provides ``resolved_score_weights()`` which, given an InstrumentRegistry,
drops instrument-slot inactive twins and renormalises the surviving
score weights so each organ's surviving members sum to 1.0.

Pure functions: no I/O beyond reading the supplied YAML path.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

import yaml
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from healthscore.errors import ConfigValidationError
from healthscore.instruments import InstrumentRegistry


class OrganWeightSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    weight: float
    scores: dict[str, float]   # score_id -> weight (per-organ); empty allowed for "not yet populated"

    @field_validator("weight")
    @classmethod
    def _weight_in_unit_interval(cls, v: float) -> float:
        if v < 0.0 or v > 1.0:
            raise ValueError(f"organ weight must be in [0, 1]; got {v}")
        return v


class DomainSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    weight: float
    organs: dict[str, OrganWeightSpec]

    @field_validator("weight")
    @classmethod
    def _weight_in_unit_interval(cls, v: float) -> float:
        if v < 0.0 or v > 1.0:
            raise ValueError(f"domain weight must be in [0, 1]; got {v}")
        return v


class DomainsConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    epsilon_default: float = 0.01
    alpha_default: float = 0.5
    disagreement_threshold: float = 5.0
    domains: dict[str, DomainSpec]

    @model_validator(mode="after")
    def _domain_weights_sum_to_one(self) -> "DomainsConfig":
        total = sum(d.weight for d in self.domains.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                f"domain weights must sum to 1.0; got {total} "
                f"({[(k, d.weight) for k, d in self.domains.items()]})"
            )
        return self

    def resolved_score_weights(
        self, organ_id: str, instrument_registry: InstrumentRegistry,
    ) -> dict[str, float]:
        """Return the post-instrument-resolution score-weight map for an
        organ, with surviving weights normalised to sum to 1.0.

        Drops every score that is in an instrument slot but is the
        non-active twin (`InstrumentRegistry.is_inactive_instrument`).
        Empty organs (e.g. gut pre-implementation) return {} unchanged.
        """
        for domain in self.domains.values():
            if organ_id in domain.organs:
                raw = domain.organs[organ_id].scores
                survivors = {
                    sid: w for sid, w in raw.items()
                    if not instrument_registry.is_inactive_instrument(sid)
                    and w > 0.0
                }
                if not survivors:
                    return {}
                total = sum(survivors.values())
                if abs(total - 1.0) > 1e-6:
                    return {sid: w / total for sid, w in survivors.items()}
                return dict(survivors)
        raise KeyError(f"organ {organ_id!r} not in domains config")

    def organ_to_domain(self) -> dict[str, str]:
        """Reverse map for audit-log construction."""
        out: dict[str, str] = {}
        for domain_id, domain in self.domains.items():
            for organ_id in domain.organs:
                out[organ_id] = domain_id
        return out


def load_domains_config(yaml_path: Path) -> DomainsConfig:
    """Load and validate ``configs/domains.yaml``."""
    try:
        raw = yaml.safe_load(Path(yaml_path).read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigValidationError(f"domains.yaml not found at {yaml_path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigValidationError(f"domains.yaml invalid YAML: {exc}") from exc
    try:
        return DomainsConfig.model_validate(raw)
    except Exception as exc:
        raise ConfigValidationError(
            f"domains.yaml at {yaml_path} failed validation: {exc}"
        ) from exc
