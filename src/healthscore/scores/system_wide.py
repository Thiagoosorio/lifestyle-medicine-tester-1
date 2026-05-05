"""System-wide score formulae.

Phase 3 Tier-2 promotion landed the Hb + RDW Mortality Risk score
(Patel 2010, PMID 19880817) as a transparent simplified harm score.

Phase 4 adds the rest of the system-wide organ panel:
    PhenoAge       Liu 2018 clinical-chemistry phenotypic age (PMID 30596641),
                   NOT the DNAm Levine 2018 (PMID 29676998) per
                   commitments_log Tier 2 PMID correction.
    SII            Systemic Immune-inflammation Index (Hu 2014, PMID 24890259).
    NLR            Neutrophil-to-Lymphocyte Ratio (Buonacera 2022, PMID 35408994).
    STOP-BANG      Chung 2008 OSA screening (PMID 18431116). Instrument-slot
                   primary; NoSAS is the no-licence fallback per
                   commitments_log §3.5.
    NoSAS          Marti-Soler 2016 (PMID 27306675). Instrument-slot fallback.

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
    return bool(raw_inputs.get(key))


# ──────────────────────────────────────────────────────────────────────────
# Hb + RDW Mortality Risk  --  Patel KV et al. JGIM 2010;25(8):817-23
# (PMID 19880817 -- methodology Tier 2 PMID replacement, supersedes the
# previously-cited 20921437 pacemaker paper).
#
# Anaemia thresholds (WHO 2011): Hb < 13 g/dL (male), < 12 g/dL (female).
# RDW reference: 11.5 - 13.5%. Patel 2010 reports HR ≈ 1.7 per RDW unit
# above the reference range.
#
# Simplified harm-scale form (transparent, directional, anchored to
# guideline cutoffs; ε floor and Sobol-perturbed coefficients for the
# full Patel hazard model are a calibration follow-up).
#
#   harm = max(0, RDW - 13.5) * 5
#        + max(0, hb_anaemia_threshold - Hb) * 8
#   anaemia_threshold = 13.0 (male) / 12.0 (female)
#
# Output: 0 - 100 harm scale.
# ──────────────────────────────────────────────────────────────────────────


def calc_hb_rdw_mortality(raw_inputs: Mapping[str, object]) -> Decimal | None:
    """Patel 2010-informed simplified Hb + RDW harm score.

    Inputs:
        hemoglobin_gdl, rdw_pct, sex.

    Output:
        Decimal in [0, 100]. 0 = no anaemia or anisocytosis; grows with
        deviations from the WHO 2011 / Patel 2010 reference ranges.
    """
    hb = _to_float(raw_inputs, "hemoglobin_gdl")
    rdw = _to_float(raw_inputs, "rdw_pct")
    sex = raw_inputs.get("sex")
    if hb is None or rdw is None or not isinstance(sex, str):
        return None
    if hb <= 0 or rdw <= 0:
        return None

    anaemia_threshold = 12.0 if sex.strip().lower().startswith("f") else 13.0
    rdw_excess = max(0.0, rdw - 13.5)
    hb_deficit = max(0.0, anaemia_threshold - hb)
    harm = rdw_excess * 5.0 + hb_deficit * 8.0
    harm = min(100.0, harm)
    return Decimal(str(round(harm, 4)))


# ──────────────────────────────────────────────────────────────────────────
# PhenoAge acceleration  --  Liu Z et al. PLOS Med 2018;15(12):e1002718
# (PMID 30596641, clinical-chemistry phenotypic age). NOT the DNAm
# Levine 2018 PhenoAge (PMID 29676998) — different score, different
# input set. See commitments_log Tier 2 PMID correction.
#
# Step 1: 9-biomarker linear predictor xb (Levine clinical-chemistry form).
# Step 2: Gompertz mortality score over 120 months.
# Step 3: Invert to phenotypic age in years.
# Step 4: Return acceleration = phenoage − chronological_age.
#
# Output orientation: positive acceleration = ageing faster than calendar
# age = worse health. Anchored at 0 (q=1.0), with high-band at +5 years.
# ──────────────────────────────────────────────────────────────────────────


def calc_phenoage_acceleration(raw_inputs: Mapping[str, object]) -> Decimal | None:
    """PhenoAge acceleration in years (PhenoAge − chronological age).

    Inputs (canonical units, matching configs/scores/phenoage.json):
        age (years), albumin_gdl (g/dL), creatinine_mgdl (mg/dL),
        fasting_glucose_mgdl (mg/dL), hs_crp_mgL (high-sensitivity CRP, mg/L),
        lymphocyte_pct (%), mcv_fL (fL), rdw_pct (%),
        wbc_10e9L (10^9/L = 10^3/uL — same numeric value).
    """
    age = _to_float(raw_inputs, "age")
    albumin = _to_float(raw_inputs, "albumin_gdl")
    creatinine = _to_float(raw_inputs, "creatinine_mgdl")
    glucose = _to_float(raw_inputs, "fasting_glucose_mgdl")
    crp_mgl = _to_float(raw_inputs, "hs_crp_mgL")
    lymph_pct = _to_float(raw_inputs, "lymphocyte_pct")
    mcv = _to_float(raw_inputs, "mcv_fL")
    rdw = _to_float(raw_inputs, "rdw_pct")
    wbc = _to_float(raw_inputs, "wbc_10e9L")
    if None in (age, albumin, creatinine, glucose, crp_mgl, lymph_pct, mcv, rdw, wbc):
        return None
    assert age is not None and albumin is not None and creatinine is not None
    assert glucose is not None and crp_mgl is not None and lymph_pct is not None
    assert mcv is not None and rdw is not None and wbc is not None
    if age <= 0 or albumin <= 0 or creatinine <= 0 or glucose <= 0:
        return None
    if mcv <= 0 or rdw <= 0 or wbc <= 0:
        return None

    # Convert hs-CRP mg/L -> mg/dL for the Levine 2018 xb form.
    crp_mgdl = crp_mgl / 10.0
    ln_crp = math.log(max(crp_mgdl, 0.001))

    xb = (
        -19.9067
        - 0.0336 * albumin
        + 0.0095 * creatinine
        + 0.1953 * glucose / 18.0          # mg/dL -> mmol/L
        + 0.0954 * ln_crp
        - 0.0120 * lymph_pct
        + 0.0268 * mcv
        + 0.3306 * rdw
        + 0.00188 * wbc
    )
    gamma = 0.0076927
    mort = 1 - math.exp(-math.exp(xb) * (math.exp(120 * gamma) - 1) / gamma)
    if mort <= 0 or mort >= 1:
        return None
    phenoage = 141.50225 + math.log(-0.00553 * math.log(1 - mort)) / 0.090165
    return Decimal(str(round(phenoage - age, 4)))


# ──────────────────────────────────────────────────────────────────────────
# SII = (platelets × neutrophils) / lymphocytes
# Hu B et al. Clin Cancer Res 2014;20(23):6212-22 (PMID 24890259).
# All inputs in K/uL (10^3/uL = 10^9/L for platelets).
# ──────────────────────────────────────────────────────────────────────────


def calc_sii(raw_inputs: Mapping[str, object]) -> Decimal | None:
    plt = _to_float(raw_inputs, "platelets_k_ul")
    neu = _to_float(raw_inputs, "neutrophils_k_ul")
    lym = _to_float(raw_inputs, "lymphocytes_k_ul")
    if None in (plt, neu, lym):
        return None
    assert plt is not None and neu is not None and lym is not None
    if plt <= 0 or neu <= 0 or lym <= 0:
        return None
    val = (plt * neu) / lym
    return Decimal(str(round(val, 2)))


# ──────────────────────────────────────────────────────────────────────────
# NLR = neutrophils / lymphocytes
# Buonacera A et al. Int J Mol Sci 2022;23(7):3636 (PMID 35408994).
# ──────────────────────────────────────────────────────────────────────────


def calc_nlr(raw_inputs: Mapping[str, object]) -> Decimal | None:
    neu = _to_float(raw_inputs, "neutrophils_k_ul")
    lym = _to_float(raw_inputs, "lymphocytes_k_ul")
    if neu is None or lym is None or lym <= 0 or neu <= 0:
        return None
    return Decimal(str(round(neu / lym, 4)))


# ──────────────────────────────────────────────────────────────────────────
# STOP-BANG  --  Chung F et al. Anesthesiology 2008;108(5):812-21
# (PMID 18431116). Eight-item OSA screening, 0-8 score.
# Cutoffs: ≥3 intermediate risk; ≥5 high risk for moderate-severe OSA.
# ──────────────────────────────────────────────────────────────────────────


def calc_stop_bang(raw_inputs: Mapping[str, object]) -> Decimal | None:
    """STOP-BANG score (0-8)."""
    age = _to_float(raw_inputs, "age")
    bmi = _to_float(raw_inputs, "bmi")
    neck = _to_float(raw_inputs, "neck_circumference_cm")
    sex = raw_inputs.get("sex")
    if age is None or bmi is None or neck is None or not isinstance(sex, str):
        return None
    if age <= 0 or bmi <= 0 or neck <= 0:
        return None
    score = 0
    if _flag(raw_inputs, "snoring_loud"):
        score += 1
    if _flag(raw_inputs, "tired_daytime"):
        score += 1
    if _flag(raw_inputs, "observed_apnoea"):
        score += 1
    if _flag(raw_inputs, "high_bp_or_treated"):
        score += 1
    if bmi >= 35:
        score += 1
    if age >= 50:
        score += 1
    if neck > 40:
        score += 1
    if sex.strip().lower().startswith("m"):
        score += 1
    return Decimal(str(score))


# ──────────────────────────────────────────────────────────────────────────
# NoSAS  --  Marti-Soler H et al. Lancet Resp Med 2016;4(9):742-8
# (PMID 27306675). 0-17 score, no-licence fallback for STOP-BANG.
# Cutoff ≥8 = positive screen for sleep-disordered breathing.
# ──────────────────────────────────────────────────────────────────────────


def calc_nosas(raw_inputs: Mapping[str, object]) -> Decimal | None:
    """NoSAS score (0-17)."""
    age = _to_float(raw_inputs, "age")
    bmi = _to_float(raw_inputs, "bmi")
    neck = _to_float(raw_inputs, "neck_circumference_cm")
    sex = raw_inputs.get("sex")
    if age is None or bmi is None or neck is None or not isinstance(sex, str):
        return None
    if age <= 0 or bmi <= 0 or neck <= 0:
        return None
    score = 0
    if neck > 40:
        score += 4
    if bmi >= 30:
        score += 5
    elif bmi >= 25:
        score += 3
    if _flag(raw_inputs, "snoring_loud"):
        score += 2
    if age > 55:
        score += 4
    if sex.strip().lower().startswith("m"):
        score += 2
    return Decimal(str(score))


# ──────────────────────────────────────────────────────────────────────────
# FRAIL scale  --  Morley JE et al. J Nutr Health Aging 2012;16(7):601-8
# (PMID 22836700). Five-item self-report frailty screen, 0-5.
#   Fatigue / Resistance / Aerobic / Illnesses (≥5) / Loss of weight (>5%)
# ──────────────────────────────────────────────────────────────────────────


def calc_frail_scale(raw_inputs: Mapping[str, object]) -> Decimal | None:
    """FRAIL scale (0-5)."""
    score = 0
    if _flag(raw_inputs, "fatigue"):
        score += 1
    if _flag(raw_inputs, "resistance_difficulty_stairs"):
        score += 1
    if _flag(raw_inputs, "aerobic_difficulty_walking_block"):
        score += 1
    illnesses = _to_float(raw_inputs, "illness_count") or 0.0
    if illnesses >= 5:
        score += 1
    if _flag(raw_inputs, "loss_of_weight_5pct"):
        score += 1
    return Decimal(str(score))


# ──────────────────────────────────────────────────────────────────────────
# MoCA  --  Nasreddine ZS et al. JAGS 2005;53(4):695-9 (PMID 15817019).
# Cognitive screen, 0-30 (higher = better). Phase 4 lands the score
# itself as a pass-through; the configured anchors are inverted via the
# config to map "higher = better" to the harm convention.
#
# Standard cutoffs: ≥26 normal (English), ≤22 cognitive impairment per
# Arabic multi-site convergence (commitments_log §3.3).
# ──────────────────────────────────────────────────────────────────────────


def calc_moca_deficit(raw_inputs: Mapping[str, object]) -> Decimal | None:
    """MoCA deficit oriented for distance-to-cutoff: max(0, 30 − MoCA)."""
    moca = _to_float(raw_inputs, "moca_score")
    if moca is None or moca < 0:
        return None
    return Decimal(str(round(max(0.0, 30.0 - moca), 4)))


# ──────────────────────────────────────────────────────────────────────────
# MMSE  --  Folstein MF et al. J Psychiatr Res 1975;12(3):189-98
# (PMID 1202204). Cognitive screen, 0-30 (higher = better).
# Cutoff <24 = cognitive impairment. Used as no-licence fallback for
# MoCA.
# ──────────────────────────────────────────────────────────────────────────


def calc_mmse_deficit(raw_inputs: Mapping[str, object]) -> Decimal | None:
    """MMSE deficit oriented for distance-to-cutoff: max(0, 30 − MMSE)."""
    mmse = _to_float(raw_inputs, "mmse_score")
    if mmse is None or mmse < 0:
        return None
    return Decimal(str(round(max(0.0, 30.0 - mmse), 4)))
