"""Metabolic-organ score formulae (Phase 5).

Composite members:
    HOMA-IR    Matthews 1985 (PMID 3899825) -- insulin resistance.
    METS-IR    Bello-Chavolla 2018 (PMID 29535168) -- non-insulin proxy.
    TyG        Simental-Mendia 2008 (PMID 19067533) -- canonical form.
    FINDRISC   Lindstrom & Tuomilehto 2003 (PMID 12716821) -- Finnish DM
               risk score; placement decision per commitments_log #21.
    VAI        Amato 2010 (PMID 20067971) -- visceral adiposity proxy.
    LAP        Kahn 2005 (PMID 16150143) -- lipid accumulation product.

Pure functions: no I/O, no time, no state.
"""

from __future__ import annotations

import math
from decimal import Decimal
from typing import Mapping


_MGDL_TO_MMOL_GLUCOSE = 1.0 / 18.0
_MGDL_TO_MMOL_TG = 1.0 / 88.57
_MGDL_TO_MMOL_CHOL = 1.0 / 38.67


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


def _flag(raw_inputs: Mapping[str, object], key: str) -> bool:
    return bool(raw_inputs.get(key))


def _is_female(sex: object) -> bool | None:
    if not isinstance(sex, str):
        return None
    s = sex.strip().lower()
    if s.startswith("f"):
        return True
    if s.startswith("m"):
        return False
    return None


# ──────────────────────────────────────────────────────────────────────────
# HOMA-IR  --  Matthews 1985 (PMID 3899825)
# HOMA-IR = (insulin uIU/mL × glucose mmol/L) / 22.5
# ──────────────────────────────────────────────────────────────────────────


def calc_homa_ir(raw_inputs: Mapping[str, object]) -> Decimal | None:
    """HOMA-IR (canonical Matthews 1985 form)."""
    insulin = _to_float(raw_inputs, "fasting_insulin_uIUmL")
    glucose = _to_float(raw_inputs, "fasting_glucose_mgdl")
    if insulin is None or glucose is None:
        return None
    if insulin < 0 or glucose <= 0:
        return None
    glucose_mmol = glucose * _MGDL_TO_MMOL_GLUCOSE
    return Decimal(str(round(insulin * glucose_mmol / 22.5, 4)))


# ──────────────────────────────────────────────────────────────────────────
# METS-IR  --  Bello-Chavolla 2018 (PMID 29535168)
# METS-IR = ln((2 * glucose) + tg) * BMI / ln(HDL)
# ──────────────────────────────────────────────────────────────────────────


def calc_mets_ir(raw_inputs: Mapping[str, object]) -> Decimal | None:
    glucose = _to_float(raw_inputs, "fasting_glucose_mgdl")
    tg = _to_float(raw_inputs, "tg_mgdl")
    hdl = _to_float(raw_inputs, "hdl_c_mgdl")
    bmi = _to_float(raw_inputs, "bmi")
    if None in (glucose, tg, hdl, bmi):
        return None
    assert glucose is not None and tg is not None and hdl is not None and bmi is not None
    if glucose <= 0 or tg <= 0 or hdl <= 0 or bmi <= 0:
        return None
    denom = math.log(hdl)
    if denom <= 0:
        return None
    val = math.log((2 * glucose) + tg) * bmi / denom
    return Decimal(str(round(val, 4)))


# ──────────────────────────────────────────────────────────────────────────
# TyG Index  --  Simental-Mendia 2008 (PMID 19067533) canonical form
# TyG = ln(tg × glucose / 2)
# ──────────────────────────────────────────────────────────────────────────


def calc_tyg(raw_inputs: Mapping[str, object]) -> Decimal | None:
    tg = _to_float(raw_inputs, "tg_mgdl")
    glucose = _to_float(raw_inputs, "fasting_glucose_mgdl")
    if tg is None or glucose is None or tg <= 0 or glucose <= 0:
        return None
    return Decimal(str(round(math.log(tg * glucose / 2.0), 4)))


# ──────────────────────────────────────────────────────────────────────────
# FINDRISC  --  Lindstrom & Tuomilehto 2003 (PMID 12716821)
# 0-26 point Finnish Diabetes Risk Score.
# Inputs: age, BMI, waist_cm, sex, daily_activity_30min, daily_fruit_veg,
#         on_bp_medication, history_high_glucose, family_history_diabetes
#         ("none" / "second_degree" / "first_degree").
# ──────────────────────────────────────────────────────────────────────────


def calc_findrisc(raw_inputs: Mapping[str, object]) -> Decimal | None:
    age = _to_float(raw_inputs, "age")
    bmi = _to_float(raw_inputs, "bmi")
    waist = _to_float(raw_inputs, "waist_cm")
    female = _is_female(raw_inputs.get("sex"))
    if age is None or bmi is None or waist is None or female is None:
        return None
    if age <= 0 or bmi <= 0 or waist <= 0:
        return None

    fhx_raw = raw_inputs.get("family_history_diabetes")
    fhx = (fhx_raw if isinstance(fhx_raw, str) else "none").strip().lower()

    score = 0
    if age >= 65:   score += 4
    elif age >= 55: score += 3
    elif age >= 45: score += 2

    if bmi >= 30:   score += 3
    elif bmi >= 25: score += 1

    if female:
        if waist > 88:    score += 4
        elif waist >= 80: score += 3
    else:
        if waist > 102:   score += 4
        elif waist >= 94: score += 3

    if not _flag(raw_inputs, "daily_activity_30min"): score += 2
    if not _flag(raw_inputs, "daily_fruit_veg"):      score += 1
    if _flag(raw_inputs, "on_bp_medication"):         score += 2
    if _flag(raw_inputs, "history_high_glucose"):     score += 5
    if fhx == "first_degree":  score += 5
    elif fhx == "second_degree": score += 3

    return Decimal(str(score))


# ──────────────────────────────────────────────────────────────────────────
# VAI  --  Amato 2010 (PMID 20067971)
# Sex-specific visceral-adiposity proxy. TG / HDL converted to mmol/L
# internally per the published derivation.
# ──────────────────────────────────────────────────────────────────────────


def calc_vai(raw_inputs: Mapping[str, object]) -> Decimal | None:
    waist = _to_float(raw_inputs, "waist_cm")
    bmi = _to_float(raw_inputs, "bmi")
    tg = _to_float(raw_inputs, "tg_mgdl")
    hdl = _to_float(raw_inputs, "hdl_c_mgdl")
    female = _is_female(raw_inputs.get("sex"))
    if None in (waist, bmi, tg, hdl) or female is None:
        return None
    assert waist is not None and bmi is not None and tg is not None and hdl is not None
    if waist <= 0 or bmi <= 0 or tg <= 0 or hdl <= 0:
        return None
    tg_mmol = tg * _MGDL_TO_MMOL_TG
    hdl_mmol = hdl * _MGDL_TO_MMOL_CHOL
    if hdl_mmol <= 0:
        return None
    if female:
        wc_denom = 36.58 + 1.89 * bmi
        val = (waist / wc_denom) * (tg_mmol / 0.81) * (1.52 / hdl_mmol)
    else:
        wc_denom = 39.68 + 1.88 * bmi
        val = (waist / wc_denom) * (tg_mmol / 1.03) * (1.31 / hdl_mmol)
    return Decimal(str(round(val, 4)))


# ──────────────────────────────────────────────────────────────────────────
# LAP  --  Kahn 2005 (PMID 16150143)
# Male:   (waist - 65) * tg_mmol/L
# Female: (waist - 58) * tg_mmol/L
# ──────────────────────────────────────────────────────────────────────────


def calc_lap(raw_inputs: Mapping[str, object]) -> Decimal | None:
    waist = _to_float(raw_inputs, "waist_cm")
    tg = _to_float(raw_inputs, "tg_mgdl")
    female = _is_female(raw_inputs.get("sex"))
    if waist is None or tg is None or female is None:
        return None
    if waist <= 0 or tg <= 0:
        return None
    tg_mmol = tg * _MGDL_TO_MMOL_TG
    offset = 58.0 if female else 65.0
    val = max(0.0, (waist - offset) * tg_mmol)
    return Decimal(str(round(val, 4)))
