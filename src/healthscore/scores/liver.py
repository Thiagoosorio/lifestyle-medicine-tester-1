"""Liver-organ score formulae.

Each callable takes a Mapping[str, ...] of raw inputs and returns either
a ``Decimal`` raw_value or ``None`` if any required input is absent /
non-numeric / clinically invalid (e.g. negative platelets, age = 0).

Citations land in the per-score JSON config's ``pmid_primary`` field;
the formula bodies here only embed citations inline where the
implementation is non-obvious or simplified.

Pure functions: no I/O, no time, no state.
"""

from __future__ import annotations

import math
from decimal import Decimal
from typing import Mapping


def _to_float(raw_inputs: Mapping[str, object], key: str) -> float | None:
    """Pull a numeric input. Returns None if absent, None-valued, or
    non-coercible. Strict: empty string is None; bool is rejected (True/False
    don't belong in numeric raw inputs)."""
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
# FIB-4  --  Sterling RK et al. Hepatology 2006;43(6):1317-25 (PMID 16729309)
# ──────────────────────────────────────────────────────────────────────────


def calc_fib4(raw_inputs: Mapping[str, object]) -> Decimal | None:
    """FIB-4 = (age * AST) / (platelets * sqrt(ALT))."""
    age = _to_float(raw_inputs, "age")
    ast = _to_float(raw_inputs, "ast")
    alt = _to_float(raw_inputs, "alt")
    plt = _to_float(raw_inputs, "platelets")
    if None in (age, ast, alt, plt):
        return None
    if alt is None or alt <= 0 or plt is None or plt <= 0:
        return None
    if ast is None or ast < 0 or age is None or age <= 0:
        return None
    val = (age * ast) / (plt * math.sqrt(alt))
    return Decimal(str(round(val, 6)))


# ──────────────────────────────────────────────────────────────────────────
# ALBI  --  Johnson PJ et al. J Clin Oncol 2015;33(6):550-8 (PMID 25512453)
# ──────────────────────────────────────────────────────────────────────────


def calc_albi(raw_inputs: Mapping[str, object]) -> Decimal | None:
    """ALBI = log10(bilirubin_umol/L) * 0.66 - albumin_g/L * 0.085.

    Inputs may arrive in either umol/L + g/L or mg/dL + g/dL; the canonical
    units expected here are bilirubin in mg/dL and albumin in g/dL (US
    convention) -- the function converts internally.
    """
    bili_mgdl = _to_float(raw_inputs, "total_bilirubin_mgdl")
    alb_gdl = _to_float(raw_inputs, "albumin_gdl")
    if bili_mgdl is None or alb_gdl is None:
        return None
    if bili_mgdl <= 0 or alb_gdl <= 0:
        return None
    bili_umol = bili_mgdl * 17.1                # mg/dL -> umol/L
    alb_gL = alb_gdl * 10                       # g/dL -> g/L
    val = math.log10(bili_umol) * 0.66 - alb_gL * 0.085
    return Decimal(str(round(val, 6)))


# ──────────────────────────────────────────────────────────────────────────
# aMAP  --  Fan R et al. J Hepatol 2020;73(6):1368-78 (PMID 32707225)
# ──────────────────────────────────────────────────────────────────────────


def calc_amap(raw_inputs: Mapping[str, object]) -> Decimal | None:
    """aMAP HCC risk score (Liu 2020 simplified implementation).

    Implementation form per Liu 2020 supplement (provisional coefficient
    parity; treat as directional pending full verification):

        inner       = age * 0.06 + male * 0.89
                      + ln(bilirubin_umol/L) * 0.48 + albumin_g/L * -0.01
        intermediate = inner * 0.86 + platelets * -0.01
        aMAP        = intermediate * 100/7.5 + 5

    Output is on a 0-100 scale; published cutoffs at 50 (low/medium) and
    60 (medium/high) HCC risk.
    """
    age = _to_float(raw_inputs, "age")
    bili_mgdl = _to_float(raw_inputs, "total_bilirubin_mgdl")
    alb_gdl = _to_float(raw_inputs, "albumin_gdl")
    plt = _to_float(raw_inputs, "platelets")
    sex = raw_inputs.get("sex")
    if None in (age, bili_mgdl, alb_gdl, plt) or not isinstance(sex, str):
        return None
    if age is None or age <= 0:
        return None
    if bili_mgdl is None or bili_mgdl <= 0:
        return None
    if alb_gdl is None or alb_gdl <= 0:
        return None
    if plt is None or plt <= 0:
        return None
    bili_umol = bili_mgdl * 17.1
    alb_gL = alb_gdl * 10
    male = 1.0 if sex.strip().lower().startswith("m") else 0.0
    inner = (
        age * 0.06
        + male * 0.89
        + math.log(bili_umol) * 0.48
        + alb_gL * -0.01
    )
    intermediate = inner * 0.86 + plt * -0.01
    val = intermediate * 100 / 7.5 + 5
    return Decimal(str(round(val, 4)))


# ──────────────────────────────────────────────────────────────────────────
# FLI  --  Bedogni G et al. BMC Gastroenterol 2006;6:33 (PMID 17081293)
# ──────────────────────────────────────────────────────────────────────────


def calc_fli(raw_inputs: Mapping[str, object]) -> Decimal | None:
    """Fatty Liver Index (Bedogni 2006).

        L   = 0.953 * ln(TG mg/dL)
              + 0.139 * BMI
              + 0.718 * ln(GGT U/L)
              + 0.053 * waist_cm
              - 15.745
        FLI = e^L / (1 + e^L) * 100
    """
    tg = _to_float(raw_inputs, "tg_mgdl")
    bmi = _to_float(raw_inputs, "bmi")
    ggt = _to_float(raw_inputs, "ggt_ul")
    waist = _to_float(raw_inputs, "waist_cm")
    if None in (tg, bmi, ggt, waist):
        return None
    if tg is None or tg <= 0 or ggt is None or ggt <= 0:
        return None
    if bmi is None or bmi <= 0 or waist is None or waist <= 0:
        return None
    L = (
        0.953 * math.log(tg)
        + 0.139 * bmi
        + 0.718 * math.log(ggt)
        + 0.053 * waist
        - 15.745
    )
    fli = math.exp(L) / (1 + math.exp(L)) * 100
    return Decimal(str(round(fli, 4)))


# ──────────────────────────────────────────────────────────────────────────
# NAFLD-FS  --  Angulo P et al. Hepatology 2007;45(4):846-54 (PMID 17393509)
# Confirmatory only (not in composite per methodology §1.5).
# ──────────────────────────────────────────────────────────────────────────


def calc_nafld_fs(raw_inputs: Mapping[str, object]) -> Decimal | None:
    """NAFLD Fibrosis Score (Angulo 2007).

        NFS = -1.675
              + 0.037 * age
              + 0.094 * BMI
              + 1.13  * (T2DM == True or impaired fasting glucose -> 1, else 0)
              + 0.99  * (AST/ALT)
              - 0.013 * platelets
              - 0.66  * albumin_g/dL
    """
    age = _to_float(raw_inputs, "age")
    bmi = _to_float(raw_inputs, "bmi")
    ast = _to_float(raw_inputs, "ast")
    alt = _to_float(raw_inputs, "alt")
    plt = _to_float(raw_inputs, "platelets")
    alb = _to_float(raw_inputs, "albumin_gdl")
    diabetes = bool(raw_inputs.get("diabetes_or_ifg"))
    if None in (age, bmi, ast, alt, plt, alb):
        return None
    if alt is None or alt <= 0:
        return None
    nfs = (
        -1.675
        + 0.037 * age
        + 0.094 * bmi
        + 1.13 * (1.0 if diabetes else 0.0)
        + 0.99 * (ast / alt)
        - 0.013 * plt
        - 0.66 * alb
    )
    return Decimal(str(round(nfs, 4)))


# ──────────────────────────────────────────────────────────────────────────
# APRI  --  Wai CT et al. Hepatology 2003;38(2):518-26 (PMID 12883497)
# Confirmatory only.
# ──────────────────────────────────────────────────────────────────────────


def calc_apri(raw_inputs: Mapping[str, object]) -> Decimal | None:
    """APRI = ((AST / AST_uln) * 100) / platelets.  Default AST upper limit 40 U/L."""
    ast = _to_float(raw_inputs, "ast")
    plt = _to_float(raw_inputs, "platelets")
    ast_uln = _to_float(raw_inputs, "ast_uln") or 40.0
    if ast is None or plt is None or plt <= 0 or ast_uln <= 0:
        return None
    val = ((ast / ast_uln) * 100) / plt
    return Decimal(str(round(val, 6)))


# ──────────────────────────────────────────────────────────────────────────
# HSI  --  Lee JH et al. Dig Liver Dis 2010;42(7):503-8 (PMID 19766548)
# Confirmatory only.
# ──────────────────────────────────────────────────────────────────────────


def calc_hsi(raw_inputs: Mapping[str, object]) -> Decimal | None:
    """Hepatic Steatosis Index.

        HSI = 8 * (ALT / AST) + BMI + 2*(female) + 2*(diabetes)
    """
    alt = _to_float(raw_inputs, "alt")
    ast = _to_float(raw_inputs, "ast")
    bmi = _to_float(raw_inputs, "bmi")
    sex = raw_inputs.get("sex")
    diabetes = bool(raw_inputs.get("diabetes_status"))
    if alt is None or ast is None or ast <= 0 or bmi is None:
        return None
    if not isinstance(sex, str):
        return None
    female = 1.0 if sex.strip().lower().startswith("f") else 0.0
    val = 8 * (alt / ast) + bmi + 2 * female + 2 * (1.0 if diabetes else 0.0)
    return Decimal(str(round(val, 4)))
