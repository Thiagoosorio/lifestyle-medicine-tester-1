"""Cardiovascular-organ score formulae.

Citations live in the per-score JSON config's ``pmid_primary`` field;
formula bodies embed citations only where the form is non-obvious.

**Orientation convention** (architecture_spec.md §5): higher raw_value =
worse health. ApoB and Lp(a) are direct measurements where higher = worse,
so they pass through unchanged. PREVENT 10-yr risk and CHA₂DS₂-VASc both
already orient that way.

Pure functions: no I/O, no time, no state.
"""

from __future__ import annotations

import math
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


def _flag(raw_inputs: Mapping[str, object], key: str) -> bool:
    """Coerce a raw input to a boolean flag. Missing or non-truthy → False."""
    return bool(raw_inputs.get(key))


# ──────────────────────────────────────────────────────────────────────────
# CHA₂DS₂-VASc  --  Lip GYH et al. Chest 2010;137(2):263-72 (PMID 19762550)
# Stroke risk in atrial fibrillation. Gated upstream on
# raw_inputs.atrial_fibrillation_status == True (architecture_spec §6).
#
#   C  = CHF / LV dysfunction        (1 point)
#   H  = Hypertension                (1)
#   A2 = Age ≥ 75                    (2)
#   D  = Diabetes                    (1)
#   S2 = Stroke / TIA / thromboemb.  (2)
#   V  = Vascular disease            (1)
#   A  = Age 65-74                   (1)
#   Sc = Sex category female         (1)
#
# Total range: 0..9.
# ──────────────────────────────────────────────────────────────────────────


def calc_cha2ds2_vasc(raw_inputs: Mapping[str, object]) -> Decimal | None:
    """Return CHA₂DS₂-VASc score (0..9). Missing age or sex returns None."""
    age = _to_float(raw_inputs, "age")
    sex = raw_inputs.get("sex")
    if age is None or not isinstance(sex, str):
        return None
    if age <= 0:
        return None

    score = 0
    if _flag(raw_inputs, "chf_or_lv_dysfunction"):
        score += 1
    if _flag(raw_inputs, "hypertension"):
        score += 1
    if age >= 75:
        score += 2
    elif age >= 65:
        score += 1
    if _flag(raw_inputs, "diabetes"):
        score += 1
    if _flag(raw_inputs, "stroke_tia_thromboembolism"):
        score += 2
    if _flag(raw_inputs, "vascular_disease"):
        score += 1
    if sex.strip().lower().startswith("f"):
        score += 1
    return Decimal(str(score))


# ──────────────────────────────────────────────────────────────────────────
# ApoB  --  ESC 2021 dyslipidaemia guideline, AHA 2024 ApoB consensus.
# Direct laboratory measurement (mg/dL). No formula -- the raw lab value
# IS the score; the normaliser maps to risk bands per ESC cutoffs.
# ──────────────────────────────────────────────────────────────────────────


def calc_apob_passthrough(raw_inputs: Mapping[str, object]) -> Decimal | None:
    """Pass-through of the apoB lab measurement (mg/dL)."""
    val = _to_float(raw_inputs, "apob_mgdl")
    if val is None or val < 0:
        return None
    return Decimal(str(round(val, 4)))


# ──────────────────────────────────────────────────────────────────────────
# Lp(a)  --  Reyes-Soffer G et al. Circulation 2022;145(2):e1-e6
# (PMID 34818833 -- AHA scientific statement). EAS 2022 also cited.
# Direct laboratory measurement (mg/dL). Anchors: ~30 mg/dL low-risk
# threshold, ~75-100 mg/dL high-risk threshold (varies by guideline).
# ──────────────────────────────────────────────────────────────────────────


def calc_lpa_passthrough(raw_inputs: Mapping[str, object]) -> Decimal | None:
    """Pass-through of the Lp(a) lab measurement (mg/dL)."""
    val = _to_float(raw_inputs, "lpa_mgdl")
    if val is None or val < 0:
        return None
    return Decimal(str(round(val, 4)))


# ──────────────────────────────────────────────────────────────────────────
# PREVENT 10-year ASCVD  --  Khan SS et al. Circulation 2024;149:430-449
# (PMID 37947085). AHA's PREVENT base 10-year ASCVD model.
#
# Coefficients are sex-specific and live in
# config/prevent_coefficients.py (auto-generated from the AHA Table S12
# supplementary file via scripts/regen_prevent_coefficients.py).
#
# Inputs (canonical units used by the AHA equations):
#   age            years (30-79)
#   non_hdl_c      mg/dL  -> centred ((value/38.67) - 3.5)
#   hdl_c          mg/dL  -> centred ((value/38.67) - 1.3) / 0.3
#   sbp            mmHg   -> two splines: <110 and ≥110
#   diabetes       0/1
#   smoking        0/1
#   bmi            kg/m²  -> max(value, 18.5) / 5  (centred 5.4)
#   egfr           mL/min/1.73m²  -> two splines: <60 and ≥60 (centred)
#   bp_treatment   0/1
#   statin         0/1
#
# Output: 10-year ASCVD probability as a percent (0..100).
# This implementation reads the AHA 'base' model only; HbA1c / UACR
# extension models are deferred to a later phase per the architecture
# spec §3.1.
# ──────────────────────────────────────────────────────────────────────────


_MGDL_TO_MMOL_CHOL = 1.0 / 38.67


def _prevent_prep_terms(
    *,
    age: float,
    total_chol_mgdl: float,
    hdl_mgdl: float,
    sbp: float,
    bp_tx: bool,
    smoking: bool,
    diabetes: bool,
    statin: bool,
    egfr: float,
    bmi: float,
) -> dict[str, float]:
    """Centred / spline predictors per Khan 2024 supplement Table S12.

    Mirrors ``preventr::prep_terms()`` (R) and the existing app's
    services.organ_score_service._prevent_prep_terms. Same arithmetic so
    the greenfield implementation matches the existing app exactly.
    """
    age_c = (age - 55) / 10.0
    non_hdl_mmol = (total_chol_mgdl - hdl_mgdl) * _MGDL_TO_MMOL_CHOL
    hdl_mmol = hdl_mgdl * _MGDL_TO_MMOL_CHOL
    non_hdl_c = non_hdl_mmol - 3.5
    hdl_c = (hdl_mmol - 1.3) / 0.3
    sbp_lt_110 = (min(sbp, 110.0) - 110.0) / 20.0
    sbp_gte_110 = (max(sbp, 110.0) - 130.0) / 20.0
    bmi_lt_30 = (min(bmi, 30.0) - 25.0) / 5.0
    bmi_gte_30 = (max(bmi, 30.0) - 30.0) / 5.0
    egfr_lt_60 = (min(egfr, 60.0) - 60.0) / -15.0
    egfr_gte_60 = (max(egfr, 60.0) - 90.0) / -15.0
    dm = 1.0 if diabetes else 0.0
    smk = 1.0 if smoking else 0.0
    bptx = 1.0 if bp_tx else 0.0
    stat = 1.0 if statin else 0.0
    return {
        "age": age_c,
        "non_hdl_c": non_hdl_c,
        "hdl_c": hdl_c,
        "sbp_lt_110": sbp_lt_110,
        "sbp_gte_110": sbp_gte_110,
        "dm": dm,
        "smoking": smk,
        "bmi_lt_30": bmi_lt_30,
        "bmi_gte_30": bmi_gte_30,
        "egfr_lt_60": egfr_lt_60,
        "egfr_gte_60": egfr_gte_60,
        "bp_tx": bptx,
        "statin": stat,
        "bp_tx_sbp_gte_110": bptx * sbp_gte_110,
        "statin_non_hdl_c": stat * non_hdl_c,
        "age_non_hdl_c": age_c * non_hdl_c,
        "age_hdl_c": age_c * hdl_c,
        "age_sbp_gte_110": age_c * sbp_gte_110,
        "age_dm": age_c * dm,
        "age_smoking": age_c * smk,
        "age_bmi_gte_30": age_c * bmi_gte_30,
        "age_egfr_lt_60": age_c * egfr_lt_60,
        "constant": 1.0,
    }


def calc_prevent_ascvd_10yr(raw_inputs: Mapping[str, object]) -> Decimal | None:
    """AHA PREVENT base 10-year ASCVD risk (%) per Khan 2024.

    Reads the published coefficient block from
    ``config.prevent_coefficients.PREVENT_BASE_10YR``. If the lookup module
    is not importable (e.g. running in an isolated unit-test environment),
    returns None so the engine treats the score as unavailable rather than
    silently wrong.

    Inputs:
        age (years), sex, total_chol_mgdl, hdl_c_mgdl, sbp_mmhg, bmi,
        egfr, diabetes, smoking, bp_treatment, statin
    """
    try:
        from config.prevent_coefficients import PREVENT_BASE_10YR
    except ImportError:
        return None

    age = _to_float(raw_inputs, "age")
    sex = raw_inputs.get("sex")
    total_chol = _to_float(raw_inputs, "total_chol_mgdl")
    hdl = _to_float(raw_inputs, "hdl_c_mgdl")
    sbp = _to_float(raw_inputs, "sbp_mmhg")
    bmi = _to_float(raw_inputs, "bmi")
    egfr = _to_float(raw_inputs, "egfr")
    if None in (age, total_chol, hdl, sbp, bmi, egfr) or not isinstance(sex, str):
        return None
    assert age is not None and total_chol is not None and hdl is not None
    assert sbp is not None and bmi is not None and egfr is not None
    if age < 30 or age > 79:
        return None
    if total_chol <= 0 or hdl <= 0 or sbp <= 0 or egfr <= 0 or bmi <= 0:
        return None

    sex_key = "female" if sex.strip().lower().startswith("f") else "male"
    coefs = PREVENT_BASE_10YR.get(sex_key, {}).get("ascvd")
    if coefs is None:
        return None

    terms = _prevent_prep_terms(
        age=age, total_chol_mgdl=total_chol, hdl_mgdl=hdl, sbp=sbp,
        bp_tx=_flag(raw_inputs, "bp_treatment"),
        smoking=_flag(raw_inputs, "smoking"),
        diabetes=_flag(raw_inputs, "diabetes"),
        statin=_flag(raw_inputs, "statin"),
        egfr=egfr, bmi=bmi,
    )
    log_odds = sum(coefs[k] * terms.get(k, 0.0) for k in coefs)
    risk = 1.0 / (1.0 + math.exp(-log_odds))
    risk_pct = max(0.0, min(risk * 100.0, 100.0))
    return Decimal(str(round(risk_pct, 4)))
