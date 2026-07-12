"""Brain-organ score formulae (Phase 5).

PHQ-9 (Kroenke 2001, PMID 11556941) -- depression severity 0..27.
GAD-7 (Spitzer 2006, PMID 16717171)  -- anxiety severity 0..21.
CAIDE (Kivipelto 2006, PMID 17005158) -- midlife dementia risk 0..15.
Homocysteine (direct lab measurement, umol/L).

Cognitive screening (MoCA primary, MMSE fallback) lives in system_wide
under the cognitive instrument slot from Phase 4; the brain panel
references the active instrument by score_id rather than by formula.

Locale-driven anchor overrides (Arabic cutoffs PHQ-9 ≥9, GAD-7 ≥6 vs
English ≥10) live on the score config, not the formula. The formula
returns the raw severity score; the normaliser consumes the
locale-specific anchors per score_eval.py.

Pure functions: no I/O, no time, no state.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Mapping


def _to_float(raw_inputs: Mapping[str, object], key: str) -> float | None:
    value = raw_inputs.get(key)
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str) and not value.strip():
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _is_female(sex: object) -> bool | None:
    if not isinstance(sex, str):
        return None
    s = sex.strip().lower()
    if s.startswith("f"):
        return True
    if s.startswith("m"):
        return False
    return None


def _flag(raw_inputs: Mapping[str, object], key: str) -> bool:
    return bool(raw_inputs.get(key))


# ──────────────────────────────────────────────────────────────────────────
# PHQ-9  --  Kroenke 2001 (PMID 11556941). Depression severity, 0..27.
# Sum of nine items each 0..3. Inputs: phq9_q1 .. phq9_q9.
# Cutoffs: English ≥10 = positive screen for major depression;
# Arabic ≥9 (Hammoudeh 2020 Saudi cancer cohort, single-source).
# ──────────────────────────────────────────────────────────────────────────


def calc_phq9(raw_inputs: Mapping[str, object]) -> Decimal | None:
    """Sum the nine PHQ-9 item scores (0..3 each)."""
    total = 0
    for i in range(1, 10):
        val = _to_float(raw_inputs, f"phq9_q{i}")
        if val is None:
            return None
        if val < 0 or val > 3:
            return None
        total += int(val)
    return Decimal(str(total))


# ──────────────────────────────────────────────────────────────────────────
# GAD-7  --  Spitzer 2006 (PMID 16717171). Anxiety severity, 0..21.
# Sum of seven items each 0..3.
# Cutoffs: English ≥10; Arabic ≥6 (Hammoudeh 2020, single-source).
# ──────────────────────────────────────────────────────────────────────────


def calc_gad7(raw_inputs: Mapping[str, object]) -> Decimal | None:
    total = 0
    for i in range(1, 8):
        val = _to_float(raw_inputs, f"gad7_q{i}")
        if val is None:
            return None
        if val < 0 or val > 3:
            return None
        total += int(val)
    return Decimal(str(total))


# ──────────────────────────────────────────────────────────────────────────
# CAIDE  --  Kivipelto 2006 (PMID 17005158). Midlife dementia risk
# stratifier. 0..15 points.
#
# Items + weights (Kivipelto 2006 Table 4):
#   age < 47           0
#   age 47-53          3
#   age >= 54          4
#   education years 10+              0
#   education 7-9                    2
#   education 0-6                    3
#   sex_male                         1
#   sbp >= 140                       2
#   bmi > 30                         2
#   total_chol >= 6.5 mmol/L
#       (251 mg/dL)                  2
#   physically_active = no           1
# ──────────────────────────────────────────────────────────────────────────


_MGDL_TO_MMOL_CHOL = 1.0 / 38.67


def calc_caide(raw_inputs: Mapping[str, object]) -> Decimal | None:
    age = _to_float(raw_inputs, "age")
    edu = _to_float(raw_inputs, "education_years")
    sbp = _to_float(raw_inputs, "sbp_mmhg")
    bmi = _to_float(raw_inputs, "bmi")
    chol = _to_float(raw_inputs, "total_chol_mgdl")
    female = _is_female(raw_inputs.get("sex"))
    if None in (age, edu, sbp, bmi, chol) or female is None:
        return None
    assert age is not None and edu is not None and sbp is not None
    assert bmi is not None and chol is not None
    if age <= 0 or edu < 0 or sbp <= 0 or bmi <= 0 or chol <= 0:
        return None

    score = 0
    if age >= 54:   score += 4
    elif age >= 47: score += 3
    if edu < 7:     score += 3
    elif edu < 10:  score += 2
    if not female:  score += 1
    if sbp >= 140:  score += 2
    if bmi > 30:    score += 2
    if chol * _MGDL_TO_MMOL_CHOL >= 6.5:
        score += 2
    if not _flag(raw_inputs, "physically_active"):
        score += 1
    return Decimal(str(score))


# ──────────────────────────────────────────────────────────────────────────
# Homocysteine pass-through.
#
# Anchors per typical clinical reference:
#   <10 umol/L = normal (low harm)
#   10-15      = borderline
#   >15        = elevated
# ──────────────────────────────────────────────────────────────────────────


def calc_homocysteine_passthrough(raw_inputs: Mapping[str, object]) -> Decimal | None:
    val = _to_float(raw_inputs, "homocysteine_umol_L")
    if val is None or val < 0:
        return None
    return Decimal(str(round(val, 4)))
