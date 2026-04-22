"""Cross-score sanity checker.

Runs a small panel of standard test patients through every CVD 10-year risk
score we support and returns the family's median plus the per-score deviation.

Scores computing the same underlying outcome on overlapping inputs should
agree within a plausible clinical band. Divergence almost always means a bug
(wrong unit, wrong coefficient, wrong age-band bucket, wrong reference value)
or a mismatched patient mapping (e.g. sex string case, ethnicity code).

Thresholds below are conservative first-pass bands; they are NOT clinical
truth. Narrow them as reference data accumulates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median

from services import organ_score_service as oss


@dataclass(frozen=True)
class Patient:
    name: str
    age: int
    sex: str
    total_chol: float   # mg/dL
    hdl: float          # mg/dL
    total_chol_mmol: float  # mmol/L  (for WHO chart)
    systolic_bp: float  # mmHg
    on_bp_med: bool
    smoking: bool
    diabetes: bool
    egfr: float
    bmi: float
    statin: bool = False


# Five representative patients covering the clinically useful risk range.
STANDARD_PATIENTS: list[Patient] = [
    Patient("Healthy F45",
            age=45, sex="female",
            total_chol=180, hdl=60, total_chol_mmol=4.66,
            systolic_bp=115, on_bp_med=False, smoking=False,
            diabetes=False, egfr=95, bmi=23),
    Patient("Borderline M55",
            age=55, sex="male",
            total_chol=210, hdl=45, total_chol_mmol=5.44,
            systolic_bp=130, on_bp_med=False, smoking=False,
            diabetes=False, egfr=88, bmi=27),
    Patient("Intermediate F62 (bp med)",
            age=62, sex="female",
            total_chol=220, hdl=50, total_chol_mmol=5.70,
            systolic_bp=150, on_bp_med=True, smoking=False,
            diabetes=False, egfr=80, bmi=29),
    Patient("High M65 (smoker, dm)",
            age=65, sex="male",
            total_chol=230, hdl=40, total_chol_mmol=5.96,
            systolic_bp=145, on_bp_med=True, smoking=True,
            diabetes=True, egfr=70, bmi=30),
    Patient("Very high M70 (multi-risk)",
            age=70, sex="male",
            total_chol=260, hdl=35, total_chol_mmol=6.73,
            systolic_bp=165, on_bp_med=True, smoking=True,
            diabetes=True, egfr=55, bmi=33),
]


def _cvd_scores_for(patient: Patient) -> dict[str, float | None]:
    """Compute every CVD 10-year score this codebase exposes for a patient.

    Returns a dict mapping score_code -> percent risk (or None if the score
    can't accept that patient -- e.g. PCE below age 40, PREVENT below 30).
    """
    scores: dict[str, float | None] = {}

    scores["prevent_10yr"] = oss.calc_prevent_10yr(
        age=patient.age, sex=patient.sex,
        total_chol=patient.total_chol, hdl=patient.hdl,
        systolic_bp=patient.systolic_bp, on_bp_med=patient.on_bp_med,
        smoking=patient.smoking, diabetes=patient.diabetes,
        egfr=patient.egfr, bmi=patient.bmi, statin=patient.statin,
        outcome="total_cvd",
    )
    scores["prevent_10yr_ascvd"] = oss.calc_prevent_10yr_ascvd(
        age=patient.age, sex=patient.sex,
        total_chol=patient.total_chol, hdl=patient.hdl,
        systolic_bp=patient.systolic_bp, on_bp_med=patient.on_bp_med,
        smoking=patient.smoking, diabetes=patient.diabetes,
        egfr=patient.egfr, bmi=patient.bmi, statin=patient.statin,
    )
    scores["ascvd_pce"] = oss.calc_ascvd_pce(
        age=patient.age, sex=patient.sex,
        total_chol=patient.total_chol, hdl=patient.hdl,
        systolic_bp=patient.systolic_bp, on_bp_med=patient.on_bp_med,
        smoking=patient.smoking, diabetes=patient.diabetes,
    )
    scores["who_na_me_cvd_lab"] = oss.calc_who_na_me_cvd_lab(
        age=patient.age, sex=patient.sex,
        total_chol=patient.total_chol_mmol,
        systolic_bp=patient.systolic_bp,
        smoking=patient.smoking, diabetes=patient.diabetes,
    )
    scores["who_na_me_cvd_nonlab"] = oss.calc_who_na_me_cvd_nonlab(
        age=patient.age, sex=patient.sex, bmi=patient.bmi,
        systolic_bp=patient.systolic_bp, smoking=patient.smoking,
    )
    return scores


def cross_check_cvd_10yr(
    patients: list[Patient] | None = None,
    abs_band_pp: float = 5.0,
    relative_band: float = 0.5,
) -> list[dict]:
    """Compute every CVD 10-year score on every patient, flag divergence.

    Divergence rules:
      * Flag any score that deviates from the family median by more than
        ``abs_band_pp`` percentage points.
      * When the median is above 10%, also require relative deviation to
        stay within ``relative_band`` (default 50%).
      * Absent scores (None) are ignored -- the score simply isn't valid
        for that patient (e.g. PCE below age 40).

    Returns one row per patient with the agreement summary.
    """
    patients = patients or STANDARD_PATIENTS
    out: list[dict] = []
    for patient in patients:
        scored = _cvd_scores_for(patient)
        present = {k: v for k, v in scored.items() if v is not None}
        if not present:
            out.append({
                "patient": patient.name,
                "median": None,
                "family": scored,
                "divergent": [],
                "note": "no applicable scores",
            })
            continue
        family_median = median(present.values())
        divergent: list[dict] = []
        for code, value in present.items():
            abs_diff = abs(value - family_median)
            rel_diff = abs_diff / family_median if family_median else 0.0
            flagged = abs_diff > abs_band_pp or (
                family_median > 10.0 and rel_diff > relative_band
            )
            if flagged:
                divergent.append({
                    "code": code,
                    "value": value,
                    "abs_diff_pp": round(abs_diff, 1),
                    "rel_diff": round(rel_diff, 2),
                })
        out.append({
            "patient": patient.name,
            "median": round(family_median, 1),
            "family": scored,
            "divergent": divergent,
        })
    return out


def summarize(report: list[dict]) -> str:
    """Human-readable summary of cross_check output, suitable for a CLI."""
    lines: list[str] = []
    for row in report:
        lines.append(
            f"{row['patient']} | family median = "
            f"{row['median'] if row['median'] is not None else 'n/a'}%"
        )
        for code, value in (row.get("family") or {}).items():
            v_str = f"{value}%" if value is not None else "n/a"
            marker = "   "
            for d in row.get("divergent", []):
                if d["code"] == code:
                    marker = " ! "
                    break
            lines.append(f"  {marker}{code:<22} {v_str}")
        if row.get("divergent"):
            for d in row["divergent"]:
                lines.append(
                    f"     divergence: {d['code']} off by "
                    f"{d['abs_diff_pp']} pp ({d['rel_diff']*100:.0f}% of median)"
                )
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    report = cross_check_cvd_10yr()
    print(summarize(report))
    any_divergent = any(row.get("divergent") for row in report)
    raise SystemExit(1 if any_divergent else 0)
