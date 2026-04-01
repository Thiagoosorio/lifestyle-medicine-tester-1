"""Clinical command-center snapshot service.

Builds a physician-style summary from structured and computed app data:
- patient profile
- confirmed diagnoses
- confirmed interventions
- labs requiring attention
- organ score risk summary
- key objective tests (DEXA + clinician-entered tests + wearable)
"""

from __future__ import annotations

from models.user import get_user
from models.clinical_profile import get_profile, get_age, get_bmi
from models.clinical_registry import (
    list_diagnoses,
    list_interventions,
    list_test_results,
)
from services.biomarker_service import get_latest_results, classify_result
from services.protocol_service import get_user_protocols
from services.exercise_prescription_service import get_saved_program
from services.cycling_service import get_cycling_profile, get_active_plan
from services.body_metrics_service import get_latest_metrics, get_latest_dexa
from services.organ_score_service import get_latest_computed_scores

try:
    from services.organ_score_service import compute_overall_organ_score
except Exception:  # pragma: no cover - backward-compatible for older deploys
    compute_overall_organ_score = None

try:
    from services.wearable_wheel_service import compute_wearable_wheel
except Exception:  # pragma: no cover - optional dependency in older deploys
    compute_wearable_wheel = None


_LAB_CLASS_SEVERITY_RANK = {
    "critical_high": 0,
    "critical_low": 0,
    "high": 1,
    "low": 1,
    "borderline_high": 2,
    "borderline_low": 2,
}


def _fmt_range(low, high, unit) -> str:
    unit_str = unit or ""
    if low is not None and high is not None:
        return f"{low}-{high} {unit_str}".strip()
    if low is not None:
        return f">={low} {unit_str}".strip()
    if high is not None:
        return f"<={high} {unit_str}".strip()
    return "N/A"


def get_labs_requiring_attention(user_id: int) -> dict:
    """Return latest lab markers that are outside normal/target ranges."""
    latest = get_latest_results(user_id)
    flagged = []
    for row in latest:
        value = row.get("value")
        cls = classify_result(value, row)
        if cls in {"optimal", "normal", "unknown"}:
            continue
        flagged.append(
            {
                "code": row.get("code"),
                "name": row.get("name"),
                "value": value,
                "unit": row.get("unit"),
                "classification": cls,
                "lab_date": row.get("lab_date"),
                "standard_range": _fmt_range(row.get("standard_low"), row.get("standard_high"), row.get("unit")),
                "optimal_range": _fmt_range(row.get("optimal_low"), row.get("optimal_high"), row.get("unit")),
            }
        )

    flagged.sort(key=lambda r: (_LAB_CLASS_SEVERITY_RANK.get(r["classification"], 9), r["name"] or ""))
    return {
        "critical": [r for r in flagged if r["classification"].startswith("critical")],
        "abnormal": [r for r in flagged if r["classification"] in {"high", "low"}],
        "borderline": [r for r in flagged if r["classification"].startswith("borderline")],
        "all": flagged,
    }


def _build_intervention_rollup(user_id: int) -> list[dict]:
    interventions = list_interventions(user_id, active_only=True)

    # Lifestyle protocols actively adopted by the user
    for proto in get_user_protocols(user_id):
        interventions.append(
            {
                "id": f"protocol_{proto['protocol_id']}",
                "intervention_type": "lifestyle",
                "name": proto.get("name"),
                "dose": None,
                "schedule": proto.get("timing") or proto.get("frequency"),
                "start_date": proto.get("started_at"),
                "status": "active",
                "prescriber": None,
                "notes": "From Daily Protocols",
                "source": "protocols",
            }
        )

    # Saved training programs are shown as interventions
    saved_program = get_saved_program(user_id)
    if saved_program:
        interventions.append(
            {
                "id": f"training_strength_{saved_program.get('_db_id', 'latest')}",
                "intervention_type": "training",
                "name": "Strength Program",
                "dose": saved_program.get("goal"),
                "schedule": saved_program.get("schedule_info", {}).get("label"),
                "start_date": saved_program.get("_created_at"),
                "status": "active",
                "prescriber": None,
                "notes": "From Exercise Prescription",
                "source": "exercise_prescription",
            }
        )

    cycling_profile = get_cycling_profile(user_id)
    if cycling_profile:
        interventions.append(
            {
                "id": f"training_cycling_{cycling_profile.get('id', 'latest')}",
                "intervention_type": "training",
                "name": "Cycling Plan",
                "dose": f"FTP {cycling_profile.get('ftp_watts')} W",
                "schedule": cycling_profile.get("athlete_type"),
                "start_date": cycling_profile.get("updated_at"),
                "status": "active",
                "prescriber": None,
                "notes": "From Cycling Training",
                "source": "cycling",
            }
        )
    else:
        active_cycling_plan = get_active_plan(user_id)
        if active_cycling_plan:
            interventions.append(
                {
                    "id": f"training_cycling_{active_cycling_plan.get('id', 'latest')}",
                    "intervention_type": "training",
                    "name": "Cycling Plan",
                    "dose": active_cycling_plan.get("phase"),
                    "schedule": f"{active_cycling_plan.get('days_per_week', 0)} days/week",
                    "start_date": active_cycling_plan.get("start_date"),
                    "status": "active",
                    "prescriber": None,
                    "notes": "From Cycling Training",
                    "source": "cycling",
                }
            )

    return interventions


def build_clinical_snapshot(user_id: int) -> dict:
    """Build one structured physician-style summary payload."""
    user = get_user(user_id) or {}
    profile = get_profile(user_id) or {}
    age = get_age(user_id)
    bmi = get_bmi(user_id)
    latest_body = get_latest_metrics(user_id)
    latest_dexa = get_latest_dexa(user_id)
    diagnoses_active = list_diagnoses(user_id, active_only=True)
    diagnoses_all = list_diagnoses(user_id, active_only=False)
    interventions_active = _build_intervention_rollup(user_id)
    lab_attention = get_labs_requiring_attention(user_id)
    test_results = list_test_results(user_id, confirmed_only=True, limit=50)
    organ_scores = get_latest_computed_scores(user_id)
    high_risk_organs = [
        s for s in organ_scores if s.get("severity") in {"high", "critical"}
    ]

    overall_organ = None
    if compute_overall_organ_score:
        try:
            overall_organ = compute_overall_organ_score(user_id)
        except Exception:
            overall_organ = None

    wearable = None
    if compute_wearable_wheel:
        try:
            wearable = compute_wearable_wheel(user_id)
        except Exception:
            wearable = None

    profile_summary = {
        "display_name": user.get("display_name") or user.get("username") or "Patient",
        "email": user.get("email"),
        "age": age,
        "sex": profile.get("sex"),
        "bmi": bmi,
        "weight_kg": (latest_body or {}).get("weight_kg") or profile.get("weight_kg"),
        "height_cm": (latest_body or {}).get("height_cm") or profile.get("height_cm"),
        "systolic_bp": profile.get("systolic_bp"),
        "diastolic_bp": profile.get("diastolic_bp"),
        "smoking_status": profile.get("smoking_status"),
        "diabetes_status": profile.get("diabetes_status"),
    }

    key_tests = []
    if latest_dexa:
        key_tests.append(
            {
                "test_type": "DEXA",
                "test_date": latest_dexa.get("scan_date"),
                "summary": (
                    f"Body fat {latest_dexa.get('total_fat_pct')}%, "
                    f"lean mass {round((latest_dexa.get('lean_mass_g') or 0) / 1000, 1)} kg, "
                    f"BMD {latest_dexa.get('bmd_g_cm2')}"
                ),
                "risk_flag": "unknown",
                "source": "dexa_scans",
            }
        )

    # Keep only key clinician-entered tests likely to matter at first glance.
    preferred_types = {"CPET", "KINEMO", "CAROTID ULTRASOUND", "CAROTID", "ULTRASOUND"}
    for t in test_results:
        t_type = (t.get("test_type") or "").upper()
        if t_type in preferred_types:
            key_tests.append(
                {
                    "test_type": t.get("test_type"),
                    "test_date": t.get("test_date"),
                    "summary": t.get("summary"),
                    "risk_flag": t.get("risk_flag"),
                    "source": "clinical_test_results",
                }
            )

    return {
        "patient": profile_summary,
        "diagnoses_active": diagnoses_active,
        "diagnoses_all": diagnoses_all,
        "interventions_active": interventions_active,
        "labs_attention": lab_attention,
        "organ_overall": overall_organ,
        "organ_high_risk_count": len(high_risk_organs),
        "wearable": wearable,
        "key_tests": key_tests,
        "test_results": test_results,
        "counts": {
            "diagnoses_active": len(diagnoses_active),
            "interventions_active": len(interventions_active),
            "labs_flagged": len(lab_attention["all"]),
            "labs_critical": len(lab_attention["critical"]),
            "labs_abnormal": len(lab_attention["abnormal"]),
            "labs_borderline": len(lab_attention["borderline"]),
            "tests_total": len(test_results),
            "organ_scores_total": len(organ_scores),
            "organ_scores_high_risk": len(high_risk_organs),
        },
    }
