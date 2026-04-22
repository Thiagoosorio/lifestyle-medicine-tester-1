"""Published reference cases for organ-score parity regression.

Every entry pairs a score_code with:
    * inputs    -- kwargs to pass to the formula function
    * expected  -- the value published in the source paper, its supplement,
                   or an authoritative reference implementation (e.g. the
                   preventr R package test-suite we already mirror in
                   tests/test_prevent_full.py).
    * tolerance -- absolute tolerance allowed around expected
    * source    -- one-line attribution (PMID / paper / calculator)

Rules:
    * Never invent a reference case. Every entry must cite a source that a
      reviewer can open and verify.
    * Prefer sources in this priority order:
        1. The source paper's own Table / Figure / supplement
        2. The paper's companion reference implementation (official
           calculator or R / Python package released by the authors)
        3. A peer-reviewed secondary validation study
    * Tolerance should be tight (<=0.1 pct for Cox-model risk outputs,
      <=1 integer for bucket-based scores) unless the source rounds more
      aggressively. Document the reason when loosening.

Run via: python -m services.score_calibration.reference_cases
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from services import organ_score_service as oss


@dataclass(frozen=True)
class ReferenceCase:
    score_code: str
    inputs: dict
    expected: float
    tolerance: float = 0.1
    source: str = ""
    note: str = ""


def _get_formula(score_code: str) -> Callable:
    """Resolve the formula function for a score code via FORMULA_DISPATCH."""
    from config.organ_scores_data import ORGAN_SCORE_DEFINITIONS

    for defn in ORGAN_SCORE_DEFINITIONS:
        if defn["code"] == score_code:
            formula_key = defn["formula_key"]
            formula, _ = oss.FORMULA_DISPATCH[formula_key]
            return formula
    raise KeyError(f"Unknown score_code: {score_code}")


def check_score(case: ReferenceCase) -> dict:
    """Execute a single reference case, return {status, computed, diff}."""
    formula = _get_formula(case.score_code)
    computed = formula(**case.inputs)
    if computed is None:
        return {
            "status": "error",
            "computed": None,
            "diff": None,
            "reason": "formula returned None (missing inputs?)",
        }
    diff = abs(float(computed) - float(case.expected))
    status = "pass" if diff <= case.tolerance else "fail"
    return {"status": status, "computed": computed, "diff": diff, "reason": ""}


def iter_reference_cases():
    yield from REFERENCE_CASES


# ──────────────────────────────────────────────────────────────────────────────
# PREVENT 10-year — reference values from the preventr R-package test suite
# which transcribes Khan SS et al. Circulation 2024 Table S12 verbatim.
# (same reference patient used in tests/test_prevent_full.py)
# ──────────────────────────────────────────────────────────────────────────────
_PREVENT_REF_PATIENT = dict(
    age=50, sex="female", total_chol=200, hdl=45,
    systolic_bp=160, on_bp_med=True, smoking=False,
    diabetes=True, egfr=90, bmi=35, statin=False,
)

# ACC/AHA 2013 Pooled Cohort Equations worked examples from
# Goff DC Jr et al. Circulation 2014;129(25 Suppl 2):S49-73 Appendix 7.
# Reproduced by the AHA PCE Risk Estimator Plus web calculator.
_ASCVD_PCE_CASES = [
    # 55yo white female, TC 213, HDL 50, SBP 120 untreated, nonsmoker, no DM
    # -> 2.1% per AHA Risk Estimator Plus (and Appendix 7 Case 1)
    ReferenceCase("ascvd_pce",
                  dict(age=55, sex="female", total_chol=213, hdl=50,
                       systolic_bp=120, on_bp_med=False,
                       smoking=False, diabetes=False),
                  expected=2.1, tolerance=0.3,
                  source="Goff 2013 Appendix 7 Case 1 / AHA Risk Estimator Plus"),
    # 55yo white male, TC 213, HDL 50, SBP 120 untreated, nonsmoker, no DM
    # -> 5.3% per AHA Risk Estimator Plus
    ReferenceCase("ascvd_pce",
                  dict(age=55, sex="male", total_chol=213, hdl=50,
                       systolic_bp=120, on_bp_med=False,
                       smoking=False, diabetes=False),
                  expected=5.3, tolerance=0.4,
                  source="AHA Risk Estimator Plus (Goff 2013 Appendix 7)"),
]


_PREVENT_CASES = [
    ReferenceCase("prevent_10yr",
                  dict(_PREVENT_REF_PATIENT, outcome="total_cvd"),
                  expected=14.7, tolerance=0.1,
                  source="preventr R test suite (Khan 2024 Table S12)"),
    ReferenceCase("prevent_10yr_ascvd",
                  dict(_PREVENT_REF_PATIENT),
                  expected=9.2, tolerance=0.1,
                  source="preventr R test suite (Khan 2024 Table S12)"),
    ReferenceCase("prevent_10yr_hf",
                  dict(_PREVENT_REF_PATIENT),
                  expected=8.1, tolerance=0.1,
                  source="preventr R test suite (Khan 2024 Table S12)"),
]


# ──────────────────────────────────────────────────────────────────────────────
# Liver — FIB-4, APRI, ALBI reference values from the derivation papers.
# ──────────────────────────────────────────────────────────────────────────────
_LIVER_CASES = [
    # FIB-4 = (Age x AST) / (Platelets x sqrt(ALT))
    # Worked example: 50 * 40 / (200 * sqrt(30)) = 2000 / 1095.4 ~= 1.83
    ReferenceCase("fib4",
                  dict(age=50, ast=40, alt=30, platelets=200),
                  expected=1.83, tolerance=0.02,
                  source="Sterling RK et al. Hepatology 2006 (PMID 16729309) -- formula definition"),
    # APRI = ((AST / AST_ULN) * 100) / Platelets   with ULN = 40
    # Worked example: ((60/40)*100)/200 = 0.75
    ReferenceCase("apri",
                  dict(ast=60, platelets=200),
                  expected=0.75, tolerance=0.02,
                  source="Wai CT et al. Hepatology 2003 (PMID 12883497) -- formula definition"),
    # ALBI = log10(bilirubin_umol) * 0.66 - albumin_g_L * 0.085
    # bilirubin 0.8 mg/dL = 13.68 umol/L; albumin 4.5 g/dL = 45 g/L
    # ALBI = log10(13.68) * 0.66 - 45 * 0.085 = 1.1362 * 0.66 - 3.825 = -3.075
    ReferenceCase("albi_score",
                  dict(total_bilirubin_mgdl=0.8, albumin_gdl=4.5),
                  expected=-3.075, tolerance=0.005,
                  source="Johnson PJ et al. J Clin Oncol 2015 (PMID 25445455) -- formula definition"),
]


# ──────────────────────────────────────────────────────────────────────────────
# Metabolic / insulin resistance — worked examples from derivation papers.
# ──────────────────────────────────────────────────────────────────────────────
_METABOLIC_CASES = [
    # HOMA-IR = fasting_insulin * fasting_glucose_mmol / 22.5
    # Insulin 10 uIU/mL, glucose 100 mg/dL -> 5.55 mmol/L
    # HOMA-IR = 10 * 5.55 / 22.5 = 2.467
    ReferenceCase("homa_ir",
                  dict(fasting_insulin=10.0, fasting_glucose_mgdl=100),
                  expected=2.47, tolerance=0.02,
                  source="Matthews DR et al. Diabetologia 1985 (PMID 3899825)"),
    # TyG = ln(TG * glucose / 2) ; TG 150, glucose 100 -> ln(150*100/2) = ln(7500) = 8.923
    ReferenceCase("tyg_index",
                  dict(tg_mgdl=150, glucose_mgdl=100),
                  expected=8.923, tolerance=0.005,
                  source="Simental-Mendia LE et al. Metab Syndr Relat Disord 2008 (PMID 18850113)"),
    # METS-IR = ln((2*glucose) + TG) * BMI / ln(HDL)
    # glucose 100, TG 150, HDL 45, BMI 30: ln(350)*30/ln(45) = 5.858*30/3.807 = 46.17
    ReferenceCase("mets_ir",
                  dict(glucose_mgdl=100, tg_mgdl=150, hdl_mgdl=45, bmi=30),
                  expected=46.17, tolerance=0.05,
                  source="Bello-Chavolla OY et al. Eur J Endocrinol 2018 (PMID 29535168)"),
]


# ──────────────────────────────────────────────────────────────────────────────
# Musculoskeletal — FNIH + EWGSOP2 thresholds from derivation consensus.
# ──────────────────────────────────────────────────────────────────────────────
_BONE_CASES = [
    # WHO/ISCD: T-score -1.3 -> osteopenia (ordinal 1)
    ReferenceCase("dxa_osteoporosis_who",
                  dict(dexa_t_score=-1.3),
                  expected=1.0, tolerance=0.0,
                  source="Kanis JA et al. Bone 2008 (PMID 18180210)"),
    # WHO/ISCD: T-score -2.7 -> osteoporosis (ordinal 2)
    ReferenceCase("dxa_osteoporosis_who",
                  dict(dexa_t_score=-2.7),
                  expected=2.0, tolerance=0.0,
                  source="Kanis JA et al. Bone 2008 (PMID 18180210)"),
    # FNIH low lean mass: F ALM/BMI 0.40 < 0.512 -> 1 (low)
    ReferenceCase("fnih_low_lean_mass",
                  dict(dexa_alm_kg=10.0, bmi=25.0, sex="female"),
                  expected=1.0, tolerance=0.0,
                  source="Cawthon PM et al. J Gerontol A 2014 (PMID 24737559)"),
]


REFERENCE_CASES: list[ReferenceCase] = (
    _PREVENT_CASES + _ASCVD_PCE_CASES + _LIVER_CASES + _METABOLIC_CASES + _BONE_CASES
)


def run_all() -> list[dict]:
    """Execute every registered case and return a table of results."""
    rows = []
    for case in REFERENCE_CASES:
        result = check_score(case)
        rows.append({
            "score_code": case.score_code,
            "expected": case.expected,
            "computed": result["computed"],
            "diff": result["diff"],
            "tolerance": case.tolerance,
            "status": result["status"],
            "source": case.source,
        })
    return rows


if __name__ == "__main__":
    import json
    results = run_all()
    print(json.dumps(results, indent=2, default=str))
    failures = [r for r in results if r["status"] != "pass"]
    if failures:
        raise SystemExit(f"{len(failures)} reference-case failure(s)")
