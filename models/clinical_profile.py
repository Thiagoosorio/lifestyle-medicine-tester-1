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
    "parent_hip_fracture",
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

# Omitted clinical facts are unknown. Keep this mapping for callers that use
# it to construct a profile without reintroducing risk-lowering assumptions.
PROFILE_DEFAULTS = dict.fromkeys(PROFILE_FIELDS)


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
    """Create or update a profile without inventing omitted clinical values.

    New rows store omitted fields as NULL. For an existing row, omitted fields
    are left unchanged; callers can explicitly clear a value by supplying None.
    """
    conn = get_connection()
    try:
        provided_fields = [field for field in PROFILE_FIELDS if field in data]
        values = [data.get(field, PROFILE_DEFAULTS[field]) for field in PROFILE_FIELDS]
        columns = ", ".join(["user_id"] + PROFILE_FIELDS + ["updated_at"])
        placeholders = ", ".join(["?"] * (len(PROFILE_FIELDS) + 1) + ["datetime('now')"])
        updates = [f"{field} = excluded.{field}" for field in provided_fields]
        updates.append("updated_at = datetime('now')")
        conn.execute(
            f"""INSERT INTO user_clinical_profile
               ({columns})
               VALUES ({placeholders})
               ON CONFLICT(user_id)
               DO UPDATE SET
                   {', '.join(updates)}""",
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
