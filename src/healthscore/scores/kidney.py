"""Kidney-organ score formulae.

Each callable takes a ``Mapping[str, ...]`` of raw inputs and returns either
a ``Decimal`` raw_value or ``None`` if any required input is absent /
non-numeric / clinically invalid.

Citations live in the per-score JSON config's ``pmid_primary`` field;
formula bodies embed citations only where the form is non-obvious.

**Orientation convention** (architecture_spec.md §5, normalize.py docstring):
``normalise_distance_to_cutoff`` requires that higher raw_value = worse
health. eGFR-style scores (where higher = better health) are oriented
INSIDE the formula: ``calc_egfr_deficit`` returns ``max(0, 90 − eGFR)``,
so output 0 = healthy (eGFR ≥ 90) and output grows with kidney
impairment. The clinical eGFR remains visible in ``raw_inputs`` for
audit; ``raw_value`` is the deficit-oriented quantity.

Pure functions: no I/O, no time, no state.
"""

from __future__ import annotations

import math
from decimal import Decimal
from typing import Mapping


def _to_float(raw_inputs: Mapping[str, object], key: str) -> float | None:
    """Pull a numeric input. Returns None if absent, None-valued, or
    non-coercible. Strict: empty string is None; bool is rejected."""
    value = raw_inputs.get(key)
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str) and not value.strip():
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


# ──────────────────────────────────────────────────────────────────────────
# eGFR  --  Inker LA et al. NEJM 2021;385(19):1737-49 (PMID 34554658)
# CKD-EPI 2021 race-free creatinine-only equation.
#
# Formula (NEJM 2021 supplement Table S1):
#   eGFR = 142
#          * min(Scr/κ, 1)^α
#          * max(Scr/κ, 1)^(-1.200)
#          * 0.9938^age
#          * (1.012 if female else 1.0)
#   where (κ, α) = (0.7, -0.241) if female else (0.9, -0.302)
#   and Scr is serum creatinine in mg/dL.
#
# Units: eGFR in mL/min/1.73m².
# ──────────────────────────────────────────────────────────────────────────


def _calc_ckd_epi_2021(scr_mgdl: float, age: float, sex_is_female: bool) -> float:
    if sex_is_female:
        kappa, alpha, female_factor = 0.7, -0.241, 1.012
    else:
        kappa, alpha, female_factor = 0.9, -0.302, 1.0
    ratio = scr_mgdl / kappa
    egfr = (
        142.0
        * (min(ratio, 1.0) ** alpha)
        * (max(ratio, 1.0) ** -1.200)
        * (0.9938 ** age)
        * female_factor
    )
    return egfr


def _resolve_sex(raw_inputs: Mapping[str, object]) -> bool | None:
    """Return True if female, False if male, None if missing/invalid."""
    sex = raw_inputs.get("sex")
    if not isinstance(sex, str):
        return None
    s = sex.strip().lower()
    if s.startswith("f"):
        return True
    if s.startswith("m"):
        return False
    return None


def calc_egfr_deficit(raw_inputs: Mapping[str, object]) -> Decimal | None:
    """Kidney-function deficit oriented for distance-to-cutoff.

    Returns ``max(0, 90 − eGFR_CKD-EPI_2021)`` so that:
      eGFR ≥ 90  →  deficit = 0     (healthy, q=1.0)
      eGFR = 60  →  deficit = 30    (G3a / borderline, q=0.5)
      eGFR ≤ 30  →  deficit = 60    (G4-G5, q=0.0)

    Inputs:
        serum_creatinine_mgdl, age, sex (str: 'male'/'female')

    The clinical eGFR can be reconstructed for audit as ``90 − raw_value``
    when raw_value > 0, or as ``≥ 90`` when raw_value == 0.
    """
    scr = _to_float(raw_inputs, "serum_creatinine_mgdl")
    age = _to_float(raw_inputs, "age")
    female = _resolve_sex(raw_inputs)
    if scr is None or age is None or female is None:
        return None
    if scr <= 0 or age <= 0:
        return None
    egfr = _calc_ckd_epi_2021(scr, age, female)
    deficit = max(0.0, 90.0 - egfr)
    return Decimal(str(round(deficit, 4)))


# ──────────────────────────────────────────────────────────────────────────
# KFRE  --  Tangri N et al. JAMA 2011;305(15):1553-9 (PMID 21482743)
# Kidney Failure Risk Equation, 4-variable 5-year form.
#
# Linear predictor (Tangri 2011 Table 4):
#   LP = -0.2201 * (age/10 - 7.036)
#        - 0.5567 * (sex_male - 0.5642)        # sex_male: 1 if male, 0 if female
#        - 0.4510 * (eGFR/5 - 7.222)
#        + 0.4501 * (ln(UACR) - 5.137)         # UACR in mg/g
#   5-yr risk = 1 − 0.9365 ^ exp(LP)
#
# Output: probability in [0, 1] (we return as Decimal × 100 for percent).
# Computed only when the eGFR ≤ 60 gate passes (architecture_spec §6).
# ──────────────────────────────────────────────────────────────────────────


def calc_kfre_5yr(raw_inputs: Mapping[str, object]) -> Decimal | None:
    """KFRE 4-variable 5-year risk of kidney failure (%).

    Inputs:
        age (years), sex (str), egfr (mL/min/1.73m²), uacr (mg/g).

    The architecture_spec §6 KFRE gate (eGFR ≤ 60) must pass before this
    formula is invoked; out-of-domain (eGFR > 60) inputs would still
    compute mechanically but the score is gated upstream.
    """
    age = _to_float(raw_inputs, "age")
    egfr = _to_float(raw_inputs, "egfr")
    uacr = _to_float(raw_inputs, "uacr")
    female = _resolve_sex(raw_inputs)
    if None in (age, egfr, uacr) or female is None:
        return None
    if egfr is None or egfr <= 0 or uacr is None or uacr <= 0 or age is None or age <= 0:
        return None
    sex_male = 0.0 if female else 1.0
    lp = (
        -0.2201 * (age / 10.0 - 7.036)
        - 0.5567 * (sex_male - 0.5642)
        - 0.4510 * (egfr / 5.0 - 7.222)
        + 0.4501 * (math.log(uacr) - 5.137)
    )
    risk = 1.0 - (0.9365 ** math.exp(lp))
    return Decimal(str(round(risk * 100.0, 4)))


# ──────────────────────────────────────────────────────────────────────────
# KDIGO category  --  KDIGO 2024 Clinical Practice Guideline (no PMID per
# se; methodology cites the guideline directly).
#
# Maps eGFR + UACR to the KDIGO 2x heatmap category, then to harm units
# 0..3 for distance-to-cutoff normalisation:
#     low risk (green)         -> 0
#     moderately increased     -> 1
#     high risk (orange)       -> 2
#     very high risk (red)     -> 3
# ──────────────────────────────────────────────────────────────────────────


def _kdigo_egfr_band(egfr: float) -> int:
    """0=G1 (≥90), 1=G2 (60-89), 2=G3a (45-59), 3=G3b (30-44), 4=G4 (15-29), 5=G5 (<15)."""
    if egfr >= 90:
        return 0
    if egfr >= 60:
        return 1
    if egfr >= 45:
        return 2
    if egfr >= 30:
        return 3
    if egfr >= 15:
        return 4
    return 5


def _kdigo_uacr_band(uacr: float) -> int:
    """0=A1 (<30), 1=A2 (30-300), 2=A3 (>300) mg/g."""
    if uacr < 30:
        return 0
    if uacr <= 300:
        return 1
    return 2


# 6 (eGFR bands) x 3 (UACR bands) heatmap from KDIGO 2024:
#     0 = low risk, 1 = moderately increased, 2 = high, 3 = very high
_KDIGO_HEATMAP = (
    # A1, A2, A3
    (0, 1, 2),   # G1   (eGFR ≥ 90)
    (0, 1, 2),   # G2   (60-89)
    (1, 2, 3),   # G3a  (45-59)
    (2, 3, 3),   # G3b  (30-44)
    (3, 3, 3),   # G4   (15-29)
    (3, 3, 3),   # G5   (<15)
)


def calc_kdigo_category(raw_inputs: Mapping[str, object]) -> Decimal | None:
    """KDIGO 2024 prognosis category mapped to harm units 0..3.

    Inputs:
        egfr (mL/min/1.73m²), uacr (mg/g).
    Output: 0 (low risk) .. 3 (very high risk).
    """
    egfr = _to_float(raw_inputs, "egfr")
    uacr = _to_float(raw_inputs, "uacr")
    if egfr is None or egfr <= 0 or uacr is None or uacr < 0:
        return None
    cat = _KDIGO_HEATMAP[_kdigo_egfr_band(egfr)][_kdigo_uacr_band(uacr)]
    return Decimal(str(cat))
