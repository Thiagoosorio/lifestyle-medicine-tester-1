"""Bone & muscle organ-panel formulae.

Phase 3 Tier-2 promotion: QFracture×2 (Hippisley-Cox & Coupland 2012,
PMID 22619194). The full coefficient block lives in
``services.organ_score_service`` (200+ lines per outcome × sex);
re-deriving it here would duplicate well-tested code, so this module
adapts the existing app's calculator behind the greenfield's pure-
function interface (Mapping[str, object] → Decimal | None).

A future refactor can extract the QFracture coefficients into
``config/qfracture_coefficients.py`` (mirroring
``config/prevent_coefficients.py``) and have both call sites import
from there.

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


def _flag_int(raw_inputs: Mapping[str, object], key: str) -> int:
    """Convert a raw input to 0/1 for the QFracture binary covariate set."""
    return 1 if bool(raw_inputs.get(key)) else 0


def _resolve_qfracture_inputs(raw_inputs: Mapping[str, object]) -> dict | None:
    """Map the greenfield raw_inputs dict to the existing app's keyword
    arguments. Returns None if minimum required inputs are absent."""
    age = _to_float(raw_inputs, "age")
    bmi = _to_float(raw_inputs, "bmi")
    sex = raw_inputs.get("sex")
    if age is None or bmi is None or not isinstance(sex, str):
        return None
    if bmi <= 0:
        return None
    base = dict(
        age=age, sex=sex, bmi=bmi,
        ethrisk=int(raw_inputs.get("ethrisk") or 1),       # default white
        smoke_cat=int(raw_inputs.get("smoke_cat") or 0),
        alcohol_cat6=int(raw_inputs.get("alcohol_cat6") or 0),
        b_antidepressant=_flag_int(raw_inputs, "b_antidepressant"),
        b_anycancer=_flag_int(raw_inputs, "b_anycancer"),
        b_asthmacopd=_flag_int(raw_inputs, "b_asthmacopd"),
        b_carehome=_flag_int(raw_inputs, "b_carehome"),
        b_corticosteroids=_flag_int(raw_inputs, "b_corticosteroids"),
        b_cvd=_flag_int(raw_inputs, "b_cvd"),
        b_dementia=_flag_int(raw_inputs, "b_dementia"),
        b_endocrine=_flag_int(raw_inputs, "b_endocrine"),
        b_epilepsy2=_flag_int(raw_inputs, "b_epilepsy2"),
        b_falls=_flag_int(raw_inputs, "b_falls"),
        b_hrt_oest=_flag_int(raw_inputs, "b_hrt_oest"),
        b_liver=_flag_int(raw_inputs, "b_liver"),
        b_parkinsons=_flag_int(raw_inputs, "b_parkinsons"),
        b_ra_sle=_flag_int(raw_inputs, "b_ra_sle"),
        b_renal=_flag_int(raw_inputs, "b_renal"),
        b_type1=_flag_int(raw_inputs, "b_type1"),
        b_type2=_flag_int(raw_inputs, "b_type2"),
        fh_osteoporosis=_flag_int(raw_inputs, "fh_osteoporosis"),
    )
    return base


# ──────────────────────────────────────────────────────────────────────────
# QFracture-2012 -- Hippisley-Cox J & Coupland C. BMJ 2012;344:e3427
# (PMID 22619194). Promoted from Phase 2 stub to a full implementation
# bridged to the existing app's coefficient-bearing calculator.
# ──────────────────────────────────────────────────────────────────────────


def calc_qfracture_major(raw_inputs: Mapping[str, object]) -> Decimal | None:
    """QFracture-2012 10-year major-osteoporotic-fracture risk (%)."""
    args = _resolve_qfracture_inputs(raw_inputs)
    if args is None:
        return None
    # b_malabsorption is in the 'major' female model only; pass through.
    args["b_malabsorption"] = _flag_int(raw_inputs, "b_malabsorption")
    try:
        from services.organ_score_service import calc_qfracture_major as _existing
    except ImportError:
        return None
    val = _existing(**args)
    if val is None:
        return None
    return Decimal(str(round(val, 4)))


def calc_qfracture_hip(raw_inputs: Mapping[str, object]) -> Decimal | None:
    """QFracture-2012 10-year hip-fracture risk (%)."""
    args = _resolve_qfracture_inputs(raw_inputs)
    if args is None:
        return None
    # b_fracture4 is the prior major-fracture flag (hip model only).
    args["b_fracture4"] = _flag_int(raw_inputs, "b_fracture4")
    try:
        from services.organ_score_service import calc_qfracture_hip as _existing
    except ImportError:
        return None
    val = _existing(**args)
    if val is None:
        return None
    return Decimal(str(round(val, 4)))
