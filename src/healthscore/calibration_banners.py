"""Per-score calibration-uncertainty banners (architecture_spec.md §5.5).

A calibration banner is a user-facing string that fires when a score's
underlying calibration cohort is known to differ materially from the
user's population, AND a recalibration layer for that population has
not yet shipped.

Currently a single banner is committed (commitments_log.md 4 May 2026
action item #18):

    PREVENT for UAE-resident users -- the Al-Shamsi 2025 calibration
    layer is pending; until it ships, every UAE-resident PREVENT
    computation surfaces an uncertainty banner.

The banners live as plain functions (one per score_id) so each is
auditable independently. When a banner schema lands in a future phase,
this module will be promoted to a config-driven dispatch.

Pure functions: no I/O, no time, no state.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping


_PREVENT_UAE_BANNER = (
    "Risk estimate uses Khan 2024 PREVENT coefficients; the UAE-specific "
    "Al-Shamsi 2025 recalibration layer is pending. Treat this number as "
    "directional for UAE-resident users until recalibration ships."
)


def _prevent_calibration_banner(
    raw_inputs: Mapping[str, Any],
) -> str | None:
    """Fire on PREVENT for any user whose ``country_of_residence`` is
    'UAE' (case-insensitive). The banner protects against silently
    treating a Khan 2024 estimate as fully calibrated for an Emirati
    population while UAE recalibration is still pending."""
    country = raw_inputs.get("country_of_residence")
    if not isinstance(country, str):
        return None
    if country.strip().upper() in ("UAE", "U.A.E.", "UNITED ARAB EMIRATES"):
        return _PREVENT_UAE_BANNER
    return None


_BANNER_REGISTRY: dict[str, Callable[[Mapping[str, Any]], str | None]] = {
    "prevent": _prevent_calibration_banner,
}


def calibration_banner_for(
    score_id: str,
    raw_inputs: Mapping[str, Any],
) -> str | None:
    """Return the calibration banner string for ``score_id`` given the
    user's raw inputs, or None when no banner condition is met."""
    fn = _BANNER_REGISTRY.get(score_id)
    if fn is None:
        return None
    return fn(raw_inputs)
