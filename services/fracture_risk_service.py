"""Helpers for official fracture-risk workflows that are not computed locally."""

from models.clinical_profile import get_age, get_bmi, get_profile
from services.body_metrics_service import get_latest_dexa

FRAX_OFFICIAL_URL = "https://www.fraxplus.org/calculation-tool"
FRAX_UAE_MODEL_LABEL = "Abu Dhabi"


def _format_yes_no_unknown(value):
    if value is None:
        return "Not set"
    return "Yes" if bool(value) else "No"


def _infer_secondary_osteoporosis(profile: dict) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if (profile.get("diabetes_type") or "").lower() == "type1":
        reasons.append("Type 1 diabetes")
    if bool(profile.get("endocrine_bone_disorder")):
        reasons.append("Endocrine bone disorder")
    if bool(profile.get("malabsorption")):
        reasons.append("Malabsorption")
    if bool(profile.get("chronic_liver_disease")):
        reasons.append("Chronic liver disease")
    return bool(reasons), reasons


def build_frax_workflow_context(user_id: int) -> dict:
    """Build a UAE-oriented FRAX workflow summary for the UI."""
    profile = get_profile(user_id) or {}
    latest_dexa = get_latest_dexa(user_id) or {}

    age = get_age(user_id)
    sex = profile.get("sex")
    bmi = get_bmi(user_id)
    smoking_status = profile.get("smoking_status")

    femoral_neck_bmd = latest_dexa.get("femoral_neck_bmd_g_cm2")
    femoral_neck_t_score = latest_dexa.get("femoral_neck_t_score")
    generic_bmd = latest_dexa.get("bmd_g_cm2")
    generic_t_score = latest_dexa.get("t_score")

    missing_core: list[str] = []
    if age is None:
        missing_core.append("Date of Birth")
    if sex not in {"male", "female"}:
        missing_core.append("Biological Sex")
    if bmi is None:
        missing_core.append("Height and Weight")

    secondary_osteoporosis, secondary_reasons = _infer_secondary_osteoporosis(profile)
    alcohol_level = (profile.get("alcohol_intake_level") or "none").lower()
    alcohol_3plus = alcohol_level in {"heavy", "very_heavy"}

    if missing_core:
        status_label = "Missing core inputs"
    elif femoral_neck_bmd is not None or femoral_neck_t_score is not None:
        status_label = "Ready with femoral-neck DXA"
    else:
        status_label = "Ready with BMI only"

    if age is None:
        age_status = "Need DOB"
    elif age < 40:
        age_status = "Will use age 40"
    elif age > 90:
        age_status = "Will cap at 90"
    else:
        age_status = "40-90 eligible"

    return {
        "model_label": FRAX_UAE_MODEL_LABEL,
        "calculator_url": FRAX_OFFICIAL_URL,
        "missing_core": missing_core,
        "status_label": status_label,
        "age_status": age_status,
        "bmd_ready": femoral_neck_bmd is not None or femoral_neck_t_score is not None,
        "generic_dexa_without_femoral_neck": (
            (generic_bmd is not None or generic_t_score is not None)
            and femoral_neck_bmd is None
            and femoral_neck_t_score is None
        ),
        "secondary_osteoporosis": secondary_osteoporosis,
        "secondary_reasons": secondary_reasons,
        "prepared_inputs": [
            ("Age", f"{int(age)} years" if age is not None else "Not set"),
            ("Sex", sex.capitalize() if sex else "Not set"),
            ("BMI", f"{bmi:.1f} kg/m²" if bmi is not None else "Not set"),
            ("Previous fragility fracture", _format_yes_no_unknown(profile.get("prior_fragility_fracture"))),
            ("Parent hip fracture", _format_yes_no_unknown(profile.get("parent_hip_fracture"))),
            (
                "Current smoking",
                "Yes" if smoking_status == "current" else (
                    "No" if smoking_status in {"never", "former"} else "Not set"
                ),
            ),
            ("Glucocorticoids", _format_yes_no_unknown(profile.get("corticosteroid_use"))),
            ("Rheumatoid arthritis", _format_yes_no_unknown(profile.get("rheumatoid_arthritis"))),
            ("Alcohol 3+ units/day", "Yes" if alcohol_3plus else "No"),
        ],
        "bone_inputs": [
            ("Secondary osteoporosis", "Yes" if secondary_osteoporosis else "No"),
            (
                "Femoral-neck BMD",
                f"{femoral_neck_bmd:.3f} g/cm²" if femoral_neck_bmd is not None else "Not set",
            ),
            (
                "Femoral-neck T-score",
                f"{femoral_neck_t_score:.2f}" if femoral_neck_t_score is not None else "Not set",
            ),
            ("Scanner", latest_dexa.get("scanner_model") or "Not set"),
        ],
    }
