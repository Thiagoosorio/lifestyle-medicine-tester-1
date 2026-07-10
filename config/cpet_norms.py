"""Cardiorespiratory-fitness (VO2max/peak) reference standards for CPET interpretation.

Percentile reference values are mL/kg/min. The treadmill table follows the
FRIEND registry / ACSM Guidelines (11th ed.) percentile standards; the women
20-29 column is anchored to the published values (5th 21.7, 25th 30.5, 50th 37.6,
75th 44.7, 90th 51.3). Other cells are the standard age/sex reference values and
should be read as population reference estimates, not lab-specific cut-offs.

Cycle-ergometer VO2peak runs materially BELOW treadmill VO2max for the same
person (registry medians differ ~15-18%; within-subject ~8-15%). A cycle test
must therefore be graded against CYCLE norms, not treadmill norms — grading a
cycle value against treadmill norms is exactly the error that makes a healthy
result look "fair/poor" (FRIEND cycle women 20-29 median = 31.0 mL/kg/min;
Kaminsky/de Souza e Silva, Mayo Clin Proc 2017).

References:
- Kaminsky LA, et al. FRIEND registry treadmill standards, Mayo Clin Proc 2015.
- Kaminsky LA, de Souza e Silva CG, et al. FRIEND cycle-ergometry standards,
  Mayo Clin Proc 2017 (PMID 27938891).
- Ross R, Blair SN, Arena R, et al. Fitness as a clinical vital sign, AHA
  Scientific Statement, Circulation 2016;134:e653-e699.
- ACSM's Guidelines for Exercise Testing and Prescription, 11th ed.
"""

from __future__ import annotations

from typing import Any

# Percentile breakpoints (percentile -> VO2 mL/kg/min), treadmill-derived.
_TREADMILL: dict[tuple[str, str], dict[int, float]] = {
    ("female", "20-29"): {10: 24.0, 25: 30.5, 50: 37.6, 75: 44.7, 90: 51.3},
    ("female", "30-39"): {10: 22.0, 25: 28.0, 50: 34.0, 75: 40.0, 90: 46.0},
    ("female", "40-49"): {10: 20.0, 25: 25.0, 50: 31.0, 75: 37.0, 90: 43.0},
    ("female", "50-59"): {10: 18.0, 25: 22.0, 50: 27.0, 75: 33.0, 90: 39.0},
    ("female", "60-69"): {10: 16.0, 25: 20.0, 50: 24.0, 75: 29.0, 90: 35.0},
    ("female", "70-79"): {10: 15.0, 25: 18.0, 50: 22.0, 75: 26.0, 90: 31.0},
    ("male", "20-29"): {10: 33.0, 25: 40.0, 50: 48.0, 75: 55.0, 90: 61.0},
    ("male", "30-39"): {10: 30.0, 25: 36.0, 50: 44.0, 75: 51.0, 90: 57.0},
    ("male", "40-49"): {10: 27.0, 25: 33.0, 50: 40.0, 75: 47.0, 90: 53.0},
    ("male", "50-59"): {10: 24.0, 25: 29.0, 50: 36.0, 75: 43.0, 90: 49.0},
    ("male", "60-69"): {10: 21.0, 25: 25.0, 50: 31.0, 75: 38.0, 90: 44.0},
    ("male", "70-79"): {10: 18.0, 25: 22.0, 50: 27.0, 75: 33.0, 90: 40.0},
}

# Direct cycle-ergometer percentile cells (FRIEND cycle registry). Where a cell is
# absent we derive it from the treadmill column (see _cycle_breakpoints).
_CYCLE_DIRECT: dict[tuple[str, str], dict[int, float]] = {
    ("female", "20-29"): {10: 21.0, 25: 25.5, 50: 31.0, 75: 37.0, 90: 43.5},
}

# Registry-level cycle:treadmill median ratio used to derive cycle norms when a
# direct cycle cell is unavailable (FRIEND women 20-29: 31.0/37.6 = 0.82).
_CYCLE_FROM_TREADMILL = 0.82

_AGE_BANDS = ["20-29", "30-39", "40-49", "50-59", "60-69", "70-79"]


def _age_band(age: float | None) -> str | None:
    if age is None:
        return None
    try:
        decade = int(age // 10) * 10
    except (TypeError, ValueError):
        return None
    if decade < 20:
        return "20-29"
    if decade > 70:
        return "70-79"
    return f"{decade}-{decade + 9}"


def _norm_sex(sex: Any) -> str | None:
    if not sex:
        return None
    token = str(sex).strip().lower()
    if token in {"f", "female", "woman", "w"}:
        return "female"
    if token in {"m", "male", "man"}:
        return "male"
    return None


def _norm_modality(modality: Any) -> str:
    token = str(modality or "").lower()
    # Rowing / arm / ski ergometers must NOT collapse to cycle just because they
    # contain "ergometer" — they have no matching reference set here.
    if any(word in token for word in ("row", "arm", "ski", "upper body", "upper-body")):
        return "other"
    if any(word in token for word in ("cycle", "bike", "bicycle")):
        return "cycle"
    if any(word in token for word in ("treadmill", "run", "tread", "walk")):
        return "treadmill"
    # A bare "ergometer" with no rowing/arm/cycle qualifier is most often a cycle
    # ergometer, but flag it as ambiguous rather than assuming.
    if "ergometer" in token or "ergo" in token:
        return "cycle_assumed"
    return "unknown"


def _cycle_breakpoints(sex: str, band: str) -> tuple[dict[int, float], bool]:
    direct = _CYCLE_DIRECT.get((sex, band))
    if direct:
        return direct, True
    tm = _TREADMILL.get((sex, band))
    if not tm:
        return {}, False
    return {pct: round(value * _CYCLE_FROM_TREADMILL, 1) for pct, value in tm.items()}, False


def _percentile_from_breakpoints(value: float, breakpoints: dict[int, float]) -> float:
    points = sorted(breakpoints.items())  # list of (percentile, vo2)
    lowest_pct, lowest_v = points[0]
    highest_pct, highest_v = points[-1]
    if value <= lowest_v:
        # Extrapolate gently below the lowest anchor, floor at 1.
        span = points[1][1] - lowest_v if len(points) > 1 else 1.0
        step = (points[1][0] - lowest_pct) if len(points) > 1 else 10
        est = lowest_pct - (lowest_v - value) / span * step if span else lowest_pct
        return max(1.0, round(est, 1))
    if value >= highest_v:
        span = highest_v - points[-2][1] if len(points) > 1 else 1.0
        step = (highest_pct - points[-2][0]) if len(points) > 1 else 10
        est = highest_pct + (value - highest_v) / span * step if span else highest_pct
        return min(99.0, round(est, 1))
    for (low_pct, low_v), (high_pct, high_v) in zip(points, points[1:]):
        if low_v <= value <= high_v:
            frac = (value - low_v) / (high_v - low_v) if high_v > low_v else 0.0
            return round(low_pct + frac * (high_pct - low_pct), 1)
    return round((lowest_pct + highest_pct) / 2, 1)


def _category(percentile: float) -> str:
    if percentile >= 90:
        return "Excellent-Superior"
    if percentile >= 75:
        return "Good-Excellent"
    if percentile >= 60:
        return "Above average (Good)"
    if percentile >= 40:
        return "Average"
    if percentile >= 20:
        return "Fair (below average)"
    return "Low"


def _ordinal(percentile: float) -> str:
    p = round(percentile)
    if p <= 1:
        return "<1st percentile"
    if p >= 99:
        return ">99th percentile"
    suffix = "th"
    if p % 100 not in (11, 12, 13):
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(p % 10, "th")
    return f"~{p}{suffix} percentile"


def classify_vo2max(
    vo2_ml_kg_min: float | None,
    sex: Any,
    age: float | None,
    modality: Any = None,
) -> dict[str, Any] | None:
    """Classify a VO2peak against age/sex/modality percentile norms.

    Returns a dict with category, percentile, reference, and caveats, or None
    when sex or age is missing (both are required for a valid comparison).
    """
    if vo2_ml_kg_min is None:
        return None
    sex_norm = _norm_sex(sex)
    band = _age_band(age)
    if sex_norm is None or band is None:
        return {
            "category": "Not classified",
            "percentile": None,
            "reference": "FRIEND / ACSM percentile standards",
            "modality_used": _norm_modality(modality),
            "caveats": [
                "Age and biological sex are both required to place VO2peak on age/sex percentile norms."
            ],
            "insufficient_context": True,
        }

    mode = _norm_modality(modality)
    caveats: list[str] = []
    try:
        age_val = float(age)
    except (TypeError, ValueError):
        age_val = None
    if age_val is not None and (age_val < 20 or age_val >= 80):
        caveats.append(
            f"Age {age_val:.0f} is outside the 20-79 reference range; compared against the nearest "
            f"band ({band}). Interpret the percentile with extra caution."
        )

    if mode in ("cycle", "cycle_assumed"):
        breakpoints, direct = _cycle_breakpoints(sex_norm, band)
        reference = "FRIEND cycle-ergometry standards" if direct else "FRIEND/ACSM norms (cycle-adjusted from treadmill)"
        if mode == "cycle_assumed":
            caveats.append(
                "Modality read as a generic 'ergometer'; assumed cycle. Confirm it was not a rowing or "
                "arm ergometer, which have no matching reference set here."
            )
        if not direct:
            caveats.append(
                "No direct cycle-norm cell for this age/sex; cycle percentile derived from treadmill "
                "norms scaled by the registry cycle:treadmill median ratio (~0.82). Treat as approximate."
            )
    elif mode == "other":
        breakpoints = _TREADMILL.get((sex_norm, band), {})
        reference = "FRIEND/ACSM treadmill standards (no modality-specific reference)"
        caveats.append(
            "This modality (e.g. rowing / arm / ski ergometer) has no reference set here; the value is "
            "compared to treadmill norms only as a rough orientation. Do not report the percentile as exact."
        )
    else:
        breakpoints = _TREADMILL.get((sex_norm, band), {})
        reference = "FRIEND/ACSM treadmill standards"
        if mode == "unknown":
            caveats.append(
                "Test modality was not recorded; assumed treadmill norms. A cycle test compared to "
                "treadmill norms understates true fitness by roughly 15%."
            )

    if not breakpoints:
        return {
            "category": "Not classified",
            "percentile": None,
            "reference": reference,
            "modality_used": mode,
            "caveats": ["No reference cell available for this age/sex."],
            "insufficient_context": True,
        }

    percentile = _percentile_from_breakpoints(float(vo2_ml_kg_min), breakpoints)
    caveats.append(
        "Population reference estimate; the exact percentile depends on the lab's chosen reference set."
    )
    return {
        "category": _category(percentile),
        "percentile": percentile,
        "percentile_label": _ordinal(percentile),
        "reference": reference,
        "reference_group": f"{sex_norm} {band}",
        "modality_used": mode,
        "caveats": caveats,
        "insufficient_context": False,
    }
