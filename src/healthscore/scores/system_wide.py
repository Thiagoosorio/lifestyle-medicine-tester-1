"""System-wide score formulae (Phase 3 Tier-2 promotion subset).

Currently lands the Hb + RDW Mortality Risk score (Patel 2010, PMID
19880817) as a transparent simplified composite suitable for use as a
directional mortality-risk index. The full Patel-2010 Cox-regression
hazard model with age-stratified coefficients lives in a dedicated
calibration follow-up; the simplified form below preserves directional
correctness (RDW above 13.5% raises harm; haemoglobin below the WHO
anaemia threshold raises harm) and is anchored to the WHO 2011 cutoffs.

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
