"""CRUD operations for user clinical/demographic profile."""

from datetime import date, datetime
from db.database import get_connection


PROFILE_FIELDS = [
    "date_of_birth",
    "sex",
    "height_cm",
    "weight_kg",
    "smoking_status",
    "diabetes_status",
    "systolic_bp",
    "diastolic_bp",
    "on_bp_medication",
    "on_statin",
    "ethnicity",
    "diabetes_type",
    "family_history_chd",
    "atrial_fibrillation",
    "rheumatoid_arthritis",
    "chronic_kidney_disease",
    "migraine",
    "sle",
    "severe_mental_illness",
    "erectile_dysfunction",
    "atypical_antipsychotic",
    "corticosteroid_use",
    "sbp_variability",
    "cigarettes_per_day",
    "congestive_heart_failure",
    "prior_stroke_tia",
    "vascular_disease",
    "education_years",
    "physical_activity_level",
    "family_history_diabetes",
    "history_high_glucose",
    "daily_fruit_veg",
    "daily_activity_30min",
    "neck_circumference_cm",
    "loud_snoring",
    "grip_strength_kg",
    "chair_stand_time_s",
    "gait_speed_m_per_s",
    "prior_fragility_fracture",
    "family_history_osteoporosis",
    "falls_last_year",
    "alcohol_intake_level",
    "care_home",
    "dementia",
    "cancer",
    "asthma_copd",
    "chronic_liver_disease",
    "advanced_ckd_stage45",
    "epilepsy",
    "parkinsons",
    "malabsorption",
    "endocrine_bone_disorder",
    "antidepressant_use",
    "hrt_estrogen_only",
]

PROFILE_DEFAULTS = {
    "diabetes_status": 0,
    "on_bp_medication": 0,
    "on_statin": 0,
    "ethnicity": "white",
    "diabetes_type": "none",
    "family_history_chd": 0,
    "atrial_fibrillation": 0,
    "rheumatoid_arthritis": 0,
    "chronic_kidney_disease": 0,
    "migraine": 0,
    "sle": 0,
    "severe_mental_illness": 0,
    "erectile_dysfunction": 0,
    "atypical_antipsychotic": 0,
    "corticosteroid_use": 0,
    "cigarettes_per_day": 0,
    "congestive_heart_failure": 0,
    "prior_stroke_tia": 0,
    "vascular_disease": 0,
    "physical_activity_level": "active",
    "family_history_diabetes": "none",
    "history_high_glucose": 0,
    "daily_fruit_veg": 0,
    "daily_activity_30min": 0,
    "loud_snoring": 0,
    "prior_fragility_fracture": 0,
    "family_history_osteoporosis": 0,
    "falls_last_year": 0,
    "alcohol_intake_level": "none",
    "care_home": 0,
    "dementia": 0,
    "cancer": 0,
    "asthma_copd": 0,
    "chronic_liver_disease": 0,
    "advanced_ckd_stage45": 0,
    "epilepsy": 0,
    "parkinsons": 0,
    "malabsorption": 0,
    "endocrine_bone_disorder": 0,
    "antidepressant_use": 0,
    "hrt_estrogen_only": 0,
}


def get_profile(user_id: int) -> dict | None:
    """Return the user's clinical profile, or None if not set."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM user_clinical_profile WHERE user_id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def save_profile(user_id: int, data: dict):
    """Create or update the user's clinical profile."""
    conn = get_connection()
    try:
        values = [data.get(field, PROFILE_DEFAULTS.get(field)) for field in PROFILE_FIELDS]
        columns = ", ".join(["user_id"] + PROFILE_FIELDS + ["updated_at"])
        placeholders = ", ".join(["?"] * (len(PROFILE_FIELDS) + 1) + ["datetime('now')"])
        updates = ", ".join(f"{field} = excluded.{field}" for field in PROFILE_FIELDS)
        conn.execute(
            f"""INSERT INTO user_clinical_profile
               ({columns})
               VALUES ({placeholders})
               ON CONFLICT(user_id)
               DO UPDATE SET
                   {updates},
                   updated_at = datetime('now')""",
            (user_id, *values),
        )
        conn.commit()
    finally:
        conn.close()


def get_age(user_id: int) -> float | None:
    """Calculate user's age in years from date_of_birth, or None if not set."""
    profile = get_profile(user_id)
    if not profile or not profile.get("date_of_birth"):
        return None
    try:
        dob = datetime.strptime(profile["date_of_birth"], "%Y-%m-%d").date()
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return float(age)
    except (ValueError, TypeError):
        return None


def get_bmi(user_id: int) -> float | None:
    """Calculate BMI from height_cm and weight_kg, or None if not set."""
    profile = get_profile(user_id)
    height = (profile or {}).get("height_cm")
    weight = (profile or {}).get("weight_kg")
    if (height is None or weight is None) and user_id:
        try:
            from services.body_metrics_service import get_latest_metrics
            latest = get_latest_metrics(user_id) or {}
            height = height or latest.get("height_cm")
            weight = weight or latest.get("weight_kg")
        except Exception:
            pass
    if not height or not weight or height <= 0:
        return None
    height_m = height / 100.0
    return round(weight / (height_m ** 2), 1)
