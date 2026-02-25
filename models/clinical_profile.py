"""CRUD operations for user clinical/demographic profile."""

from datetime import date, datetime
from db.database import get_connection


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
        conn.execute(
            """INSERT INTO user_clinical_profile
               (user_id, date_of_birth, sex, height_cm, weight_kg,
                smoking_status, diabetes_status, systolic_bp, diastolic_bp,
                on_bp_medication, on_statin,
                ethnicity, diabetes_type, family_history_chd,
                atrial_fibrillation, rheumatoid_arthritis,
                chronic_kidney_disease, migraine, sle,
                severe_mental_illness, erectile_dysfunction,
                atypical_antipsychotic, corticosteroid_use,
                sbp_variability, cigarettes_per_day,
                congestive_heart_failure, prior_stroke_tia, vascular_disease,
                education_years, physical_activity_level,
                updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                       ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                       ?, ?, ?, ?, ?,
                       datetime('now'))
               ON CONFLICT(user_id)
               DO UPDATE SET
                   date_of_birth = excluded.date_of_birth,
                   sex = excluded.sex,
                   height_cm = excluded.height_cm,
                   weight_kg = excluded.weight_kg,
                   smoking_status = excluded.smoking_status,
                   diabetes_status = excluded.diabetes_status,
                   systolic_bp = excluded.systolic_bp,
                   diastolic_bp = excluded.diastolic_bp,
                   on_bp_medication = excluded.on_bp_medication,
                   on_statin = excluded.on_statin,
                   ethnicity = excluded.ethnicity,
                   diabetes_type = excluded.diabetes_type,
                   family_history_chd = excluded.family_history_chd,
                   atrial_fibrillation = excluded.atrial_fibrillation,
                   rheumatoid_arthritis = excluded.rheumatoid_arthritis,
                   chronic_kidney_disease = excluded.chronic_kidney_disease,
                   migraine = excluded.migraine,
                   sle = excluded.sle,
                   severe_mental_illness = excluded.severe_mental_illness,
                   erectile_dysfunction = excluded.erectile_dysfunction,
                   atypical_antipsychotic = excluded.atypical_antipsychotic,
                   corticosteroid_use = excluded.corticosteroid_use,
                   sbp_variability = excluded.sbp_variability,
                   cigarettes_per_day = excluded.cigarettes_per_day,
                   congestive_heart_failure = excluded.congestive_heart_failure,
                   prior_stroke_tia = excluded.prior_stroke_tia,
                   vascular_disease = excluded.vascular_disease,
                   education_years = excluded.education_years,
                   physical_activity_level = excluded.physical_activity_level,
                   updated_at = datetime('now')""",
            (user_id,
             data.get("date_of_birth"),
             data.get("sex"),
             data.get("height_cm"),
             data.get("weight_kg"),
             data.get("smoking_status"),
             data.get("diabetes_status", 0),
             data.get("systolic_bp"),
             data.get("diastolic_bp"),
             data.get("on_bp_medication", 0),
             data.get("on_statin", 0),
             data.get("ethnicity", "white"),
             data.get("diabetes_type", "none"),
             data.get("family_history_chd", 0),
             data.get("atrial_fibrillation", 0),
             data.get("rheumatoid_arthritis", 0),
             data.get("chronic_kidney_disease", 0),
             data.get("migraine", 0),
             data.get("sle", 0),
             data.get("severe_mental_illness", 0),
             data.get("erectile_dysfunction", 0),
             data.get("atypical_antipsychotic", 0),
             data.get("corticosteroid_use", 0),
             data.get("sbp_variability"),
             data.get("cigarettes_per_day", 0),
             data.get("congestive_heart_failure", 0),
             data.get("prior_stroke_tia", 0),
             data.get("vascular_disease", 0),
             data.get("education_years"),
             data.get("physical_activity_level", "active")),
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
    if not profile:
        return None
    height = profile.get("height_cm")
    weight = profile.get("weight_kg")
    if not height or not weight or height <= 0:
        return None
    height_m = height / 100.0
    return round(weight / (height_m ** 2), 1)
