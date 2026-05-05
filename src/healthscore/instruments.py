"""Runtime instrument-slot resolution (architecture_spec.md §7).

Two slots ship with committed primary + fallback pairs (commitments_log
§5.6 4 May 2026):

    cognitive : MoCA primary, MMSE fallback
    osa       : STOP-BANG primary, NoSAS fallback

Deployment toggles the ``active`` field per slot in
``configs/instruments.yaml``. The non-active instrument's score is
registered as ``UNAVAILABLE``: it does not contribute to aggregation,
does not emit a wording, and is logged once at startup.

Fallback activation forces ``ScoreResult.confidence = low`` regardless
of the underlying config and stamps ``reason =
"fallback_active:<primary>->><fallback>"``.

Pure functions: no I/O beyond reading the supplied YAML path; no
networking, no time, no state.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import yaml

from healthscore.errors import ConfigValidationError


@dataclass(frozen=True, slots=True)
class InstrumentSlotResolution:
    """Resolved state for a single instrument slot at engine startup."""

    slot: str                     # "cognitive" / "osa" / ...
    primary: str                  # primary score_id
    fallback: str                 # fallback score_id
    active: str                   # the score_id that actually computes
    fallback_active: bool         # True iff active == fallback
    fallback_reason: str | None   # populated when active == fallback


@dataclass(frozen=True, slots=True)
class InstrumentRegistry:
    """Frozen at engine startup; consulted per evaluate_score call."""

    by_slot: Mapping[str, InstrumentSlotResolution]
    score_to_slot: Mapping[str, str]              # MoCA→cognitive, etc.

    def resolution_for_score(self, score_id: str) -> InstrumentSlotResolution | None:
        slot = self.score_to_slot.get(score_id)
        if slot is None:
            return None
        return self.by_slot[slot]

    def is_inactive_instrument(self, score_id: str) -> bool:
        """True iff this score is the non-active instrument in its slot."""
        res = self.resolution_for_score(score_id)
        if res is None:
            return False
        return score_id != res.active


def load_instrument_registry(yaml_path: Path) -> InstrumentRegistry:
    """Load and validate ``configs/instruments.yaml`` into an
    ``InstrumentRegistry``. Raises ``ConfigValidationError`` on any
    structural problem so the engine refuses to start instead of
    silently misrouting."""
    try:
        raw = yaml.safe_load(Path(yaml_path).read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigValidationError(
            f"instruments.yaml not found at {yaml_path}"
        ) from exc
    except yaml.YAMLError as exc:
        raise ConfigValidationError(
            f"instruments.yaml at {yaml_path} is invalid YAML: {exc}"
        ) from exc

    if not isinstance(raw, dict) or "slots" not in raw:
        raise ConfigValidationError("instruments.yaml must have a top-level 'slots' map")
    slots_dict = raw["slots"]
    if not isinstance(slots_dict, dict) or not slots_dict:
        raise ConfigValidationError("instruments.yaml 'slots' must be a non-empty map")

    by_slot: dict[str, InstrumentSlotResolution] = {}
    score_to_slot: dict[str, str] = {}

    for slot_name, slot_cfg in slots_dict.items():
        if not isinstance(slot_cfg, dict):
            raise ConfigValidationError(
                f"slot {slot_name!r} must be a mapping with primary/fallback/active"
            )
        primary = slot_cfg.get("primary")
        fallback = slot_cfg.get("fallback")
        active = slot_cfg.get("active")
        fallback_reason = slot_cfg.get("fallback_reason")
        if not isinstance(primary, str) or not isinstance(fallback, str):
            raise ConfigValidationError(
                f"slot {slot_name!r}: 'primary' and 'fallback' must be score_id strings"
            )
        if active not in (primary, fallback):
            raise ConfigValidationError(
                f"slot {slot_name!r}: 'active' must equal primary or fallback "
                f"(got {active!r}; primary={primary!r}, fallback={fallback!r})"
            )
        fallback_active = active == fallback
        if fallback_active and fallback_reason is None:
            fallback_reason = f"fallback_active:{primary}->>{fallback}"
        if not fallback_active:
            fallback_reason = None

        resolution = InstrumentSlotResolution(
            slot=slot_name,
            primary=primary,
            fallback=fallback,
            active=active,
            fallback_active=fallback_active,
            fallback_reason=fallback_reason,
        )
        by_slot[slot_name] = resolution

        # Both primary and fallback map back to this slot.
        for sid in (primary, fallback):
            if sid in score_to_slot:
                raise ConfigValidationError(
                    f"score_id {sid!r} appears in multiple instrument slots: "
                    f"{score_to_slot[sid]!r} and {slot_name!r}"
                )
            score_to_slot[sid] = slot_name

    return InstrumentRegistry(by_slot=by_slot, score_to_slot=score_to_slot)
