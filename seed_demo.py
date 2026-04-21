"""
Seed script: Maria's Lifestyle Medicine Transformation
======================================================
Maria, 43, mother of two. Over 12 months she:
- Lost 27 kg (started at 105 kg, now 78 kg)
- Went from sedentary to running a 21K half-marathon
- Transformed her diet from processed/fast food to whole-food plant-predominant
- Fixed her sleep from 4-5h fragmented to 7-8h restorative
- Started daily meditation practice
- Rebuilt relationships with family and friends
- Quit smoking, reduced alcohol to occasional wine
- Still carries active cardiometabolic risk diagnoses on treatment
"""

import random
import uuid
import json
from datetime import date, datetime, timedelta
from db.database import init_db, get_connection
from models.user import create_user
from models.clinical_profile import get_profile, save_profile

# ── Configuration ───────────────────────────────────────────────────────────
USERNAME = "maria.silva"
PASSWORD = "demo123456"
DISPLAY_NAME = "Maria Silva"
EMAIL = "maria.silva@demo.com"
START_DATE = date(2025, 2, 1)   # Journey starts Feb 2025
END_DATE = date(2026, 2, 1)     # One full year

random.seed(42)  # Reproducible data

MARIA_CLINICAL_PROFILE = {
    "date_of_birth": "1982-10-12",  # 43y during demo timeline
    "sex": "female",
    "height_cm": 167.0,
    "weight_kg": 78.0,
    "smoking_status": "former",
    "diabetes_status": 0,
    "systolic_bp": 134.0,
    "diastolic_bp": 84.0,
    "on_bp_medication": 1,
    "on_statin": 1,
    "ethnicity": "other",
    "diabetes_type": "none",
    "family_history_chd": 1,
    "atrial_fibrillation": 0,
    "rheumatoid_arthritis": 0,
    "chronic_kidney_disease": 0,
    "migraine": 0,
    "sle": 0,
    "severe_mental_illness": 0,
    "erectile_dysfunction": 0,
    "atypical_antipsychotic": 0,
    "corticosteroid_use": 0,
    "sbp_variability": 8.0,
    "cigarettes_per_day": 0,
    "congestive_heart_failure": 0,
    "prior_stroke_tia": 0,
    "vascular_disease": 0,
    "education_years": 16,
    "physical_activity_level": "active",
    "family_history_diabetes": "first_degree",
    "history_high_glucose": 1,
    "daily_fruit_veg": 0,
    "daily_activity_30min": 1,
    "neck_circumference_cm": 37.0,
    "loud_snoring": 1,
    "grip_strength_kg": 26.0,
    "chair_stand_time_s": 11.2,
    "gait_speed_m_per_s": 1.05,
    "prior_fragility_fracture": 0,
    "family_history_osteoporosis": 0,
    "falls_last_year": 0,
    "alcohol_intake_level": "light",
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

# Latest follow-up panel values used to backfill legacy demo databases.
MARIA_ORGAN_SCORE_BIOMARKERS = {
    "hba1c": 5.9,
    "fasting_glucose": 108.0,
    "fasting_insulin": 13.2,
    "hs_crp": 2.4,
    "ldl_cholesterol": 154.0,
    "hdl_cholesterol": 45.0,
    "triglycerides": 186.0,
    "apob": 132.0,
    "ggt": 42.0,
    "total_cholesterol": 248.0,
    "lpa": 42.0,
    "homocysteine": 11.8,
    "vitamin_d": 24.0,
    "tsh": 2.6,
    "free_t4": 1.02,
    "free_t3": 3.0,
    "alt": 36.0,
    "ast": 31.0,
    "albumin": 4.2,
    "total_bilirubin": 0.7,
    "platelets": 258.0,
    "creatinine": 0.84,
    "uacr": 22.0,
    "hemoglobin": 13.6,
    "wbc": 6.8,
    "neutrophils_abs": 4.0,
    "lymphocytes_abs": 2.0,
    "mcv": 90.0,
    "rdw": 13.9,
    "ferritin": 48.0,
    "iron": 74.0,
    "tibc": 366.0,
    "transferrin_sat": 20.0,
}
MARIA_ORGAN_SCORE_BODY_METRICS = {
    "weight_kg": 78.0,
    "height_cm": 167.0,
    "waist_cm": 92.0,
    "hip_cm": 103.0,
    "body_fat_pct": 31.0,
}
# Realistic DEXA values for a 43-year-old overweight woman. T-score -1.3 lands
# in the osteopenia band so the DXA WHO/ISCD score surfaces a "low bone mass /
# osteopenia" card -- clinically consistent with Maria's other metabolic-risk
# profile and gives the demo something actionable to discuss on Reveal Day.
MARIA_DEXA_SCAN = {
    "scan_date": "2026-02-15",
    "lab_name": "Demo Imaging Center",
    "scanner_model": "Hologic Horizon W (demo)",
    "weight_kg": 78.0,
    "total_fat_pct": 36.0,
    "total_fat_g": 28080.0,
    "lean_mass_g": 47500.0,
    "bone_mass_g": 2420.0,
    "bmi": 27.9,
    "bmd_g_cm2": 0.98,
    "t_score": -1.3,
    "z_score": -0.5,
    "vat_mass_g": 850.0,
    "vat_volume_cm3": 900.0,
    "vat_area_cm2": 120.0,
    "android_fat_pct": 42.0,
    "gynoid_fat_pct": 38.0,
    "ag_ratio": 1.10,
    "left_arm_fat_pct": 34.0,
    "right_arm_fat_pct": 34.5,
    "trunk_fat_pct": 39.5,
    "left_leg_fat_pct": 35.0,
    "right_leg_fat_pct": 35.2,
    "left_arm_lean_g": 2400.0,
    "right_arm_lean_g": 2500.0,
    "trunk_lean_g": 22000.0,
    "left_leg_lean_g": 7800.0,
    "right_leg_lean_g": 7900.0,
    "source": "demo",
    "notes": "Seeded demo DEXA scan for organ-score dashboard.",
}
MARIA_WEARABLE_METRICS = {
    # Heart & Metabolism
    "resting_heart_rate_bpm": 67.0,
    "heart_rate_variability_ms": 31.0,
    "steps_count": 6400.0,
    "respiratory_rate_bpm": 17.1,
    "arrhythmia_alert_afib": 0.0,
    "kilojoule_expended": 1850.0,
    "systolic_bp_mmhg": 136.0,
    "diastolic_bp_mmhg": 86.0,
    "cgm_avg_glucose_mgdl": 112.0,
    "cgm_time_in_range_pct": 78.0,
    "body_weight_kg": 78.0,
    # System Wide
    "overnight_spo2_avg_pct": 93.8,
    "overnight_spo2_nadir_pct": 86.0,
    "body_temperature_deviation_c": 0.3,
    "recovery_score": 58.0,
    "spo2_pct": 94.5,
    # Brain Health
    "sleep_efficiency_pct": 81.0,
    "sleep_consistency_pct": 69.0,
    "total_slow_wave_sleep_time_min": 62.0,
    "total_rem_sleep_time_min": 74.0,
    "sleep_debt_hours": 2.6,
    "sleep_disturbance_count": 9.0,
    "total_awake_time_min": 61.0,
    "sleep_latency_min": 28.0,
    "sleep_cycle_count": 4.0,
    "sleep_performance_pct": 72.0,
}
MARIA_DIAGNOSES = [
    {
        "diagnosis_name": "Hypertension (Essential)",
        "status": "active",
        "confirmed_date": "2025-02-01",
        "confirming_clinician": "Dr. Yasmin Rahman",
        "source": "Primary care evaluation",
        "notes": "Persistent stage-1 to stage-2 range blood pressure; treated with ARB.",
    },
    {
        "diagnosis_name": "Prediabetes",
        "status": "active",
        "confirmed_date": "2025-02-01",
        "confirming_clinician": "Dr. Yasmin Rahman",
        "source": "ADA criteria (HbA1c + fasting glucose)",
        "notes": "Persistent dysglycemia despite lifestyle changes; managed with metformin XR.",
    },
    {
        "diagnosis_name": "Hypercholesterolemia",
        "status": "active",
        "confirmed_date": "2025-02-01",
        "confirming_clinician": "Dr. Yasmin Rahman",
        "source": "Fasting lipid profile + ApoB",
        "notes": "LDL-C and ApoB remain above target; statin therapy started.",
    },
    {
        "diagnosis_name": "Obstructive Sleep Apnea (moderate)",
        "status": "active",
        "confirmed_date": "2025-05-20",
        "confirming_clinician": "Dr. Thomas Klein",
        "source": "Home sleep apnea test (HSAT)",
        "notes": "Moderate OSA with nocturnal desaturation; nightly CPAP prescribed.",
    },
]
MARIA_INTERVENTIONS = [
    {
        "intervention_type": "medication",
        "name": "Losartan",
        "dose": "50 mg",
        "schedule": "Nightly",
        "start_date": "2025-02-03",
        "end_date": None,
        "status": "active",
        "prescriber": "Dr. Yasmin Rahman",
        "notes": "For hypertension control.",
    },
    {
        "intervention_type": "medication",
        "name": "Rosuvastatin",
        "dose": "10 mg",
        "schedule": "Nightly",
        "start_date": "2025-02-10",
        "end_date": None,
        "status": "active",
        "prescriber": "Dr. Yasmin Rahman",
        "notes": "For LDL-C/ApoB lowering.",
    },
    {
        "intervention_type": "medication",
        "name": "Metformin XR",
        "dose": "500 mg",
        "schedule": "Twice daily with meals",
        "start_date": "2025-03-01",
        "end_date": None,
        "status": "active",
        "prescriber": "Dr. Yasmin Rahman",
        "notes": "For prediabetes and insulin resistance.",
    },
    {
        "intervention_type": "other",
        "name": "CPAP therapy",
        "dose": "Auto-CPAP 6-12 cm H2O",
        "schedule": "Nightly during sleep",
        "start_date": "2025-05-25",
        "end_date": None,
        "status": "active",
        "prescriber": "Dr. Thomas Klein",
        "notes": "For moderate obstructive sleep apnea.",
    },
    {
        "intervention_type": "supplement",
        "name": "Vitamin D3 (cholecalciferol)",
        "dose": "4000 IU",
        "schedule": "Daily with a meal",
        "start_date": "2025-02-05",
        "end_date": None,
        "status": "active",
        "prescriber": "Dr. Yasmin Rahman",
        "notes": "Started for prior 25-OH vitamin D deficiency.",
    },
]
MARIA_TEST_RESULTS = [
    {
        "test_type": "Home Sleep Apnea Test",
        "test_date": "2025-05-20",
        "status": "confirmed",
        "summary": "Moderate obstructive sleep apnea with recurrent oxygen desaturation.",
        "key_metrics": {"ahi_events_per_hour": 18.4, "spo2_nadir_pct": 84, "odi_events_per_hour": 16.2},
        "source_ref": "Sleep lab report",
        "risk_flag": "high",
    },
    {
        "test_type": "24h Ambulatory Blood Pressure Monitoring",
        "test_date": "2025-02-08",
        "status": "confirmed",
        "summary": "Elevated daytime blood pressure with reduced nocturnal dipping.",
        "key_metrics": {"daytime_avg_bp_mmhg": "138/86", "night_avg_bp_mmhg": "130/80", "nocturnal_dip_pct": 5.8},
        "source_ref": "Cardiology outpatient ABPM",
        "risk_flag": "moderate",
    },
    {
        "test_type": "Carotid Ultrasound",
        "test_date": "2025-09-12",
        "status": "confirmed",
        "summary": "Mild bilateral carotid plaque, no hemodynamically significant stenosis.",
        "key_metrics": {"max_ica_stenosis_pct": 25, "mean_imt_mm": 0.86},
        "source_ref": "Vascular imaging",
        "risk_flag": "moderate",
    },
    {
        "test_type": "CPET",
        "test_date": "2026-01-20",
        "status": "confirmed",
        "summary": "Reduced cardiorespiratory fitness with early anaerobic threshold.",
        "key_metrics": {"vo2_peak_ml_kg_min": 24.1, "ve_vco2_slope": 33.4, "anaerobic_threshold_ml_kg_min": 14.7},
        "source_ref": "Exercise physiology lab",
        "risk_flag": "moderate",
    },
    {
        "test_type": "CGM 14-day profile",
        "test_date": "2026-01-26",
        "status": "confirmed",
        "summary": "Prediabetes pattern with elevated mean glucose and reduced time-in-range.",
        "key_metrics": {"mean_glucose_mgdl": 112, "time_in_range_pct": 78, "gmi_pct": 5.9},
        "source_ref": "Freestyle Libre 14-day AGP",
        "risk_flag": "moderate",
    },
]
MARIA_BACKFILL_LAB_DATE = "2026-02-01"
MARIA_BACKFILL_LAB_NAME = "Quest Diagnostics"


def lerp(start: float, end: float, t: float) -> float:
    """Linear interpolation with some noise."""
    base = start + (end - start) * t
    noise = random.gauss(0, 0.3)
    return max(1, min(10, round(base + noise)))


def lerp_smooth(start: float, end: float, t: float) -> float:
    """Smooth S-curve interpolation (slow start, fast middle, slow end)."""
    # Sigmoid-like curve
    import math
    s = 1 / (1 + math.exp(-10 * (t - 0.4)))  # Shifted sigmoid
    base = start + (end - start) * s
    noise = random.gauss(0, 0.25)
    return max(1, min(10, round(base + noise)))


def _seed_maria_clinical_profile(user_id: int):
    """Seed the canonical demo clinical profile for Maria."""
    save_profile(user_id, dict(MARIA_CLINICAL_PROFILE))


def _seed_maria_clinical_registry(conn, user_id: int, force_replace: bool = False) -> dict:
    """Seed clinician-facing diagnoses, interventions, and tests for Maria."""
    inserted_diagnoses = 0
    inserted_interventions = 0
    inserted_tests = 0

    for diag in MARIA_DIAGNOSES:
        before = conn.execute(
            "SELECT id FROM clinical_diagnoses WHERE user_id = ? AND diagnosis_name = ?",
            (user_id, diag["diagnosis_name"]),
        ).fetchone()
        conn.execute(
            """INSERT INTO clinical_diagnoses
               (user_id, diagnosis_name, status, confirmed_date, confirming_clinician, source, notes, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
               ON CONFLICT(user_id, diagnosis_name) DO UPDATE SET
                 status = excluded.status,
                 confirmed_date = excluded.confirmed_date,
                 confirming_clinician = excluded.confirming_clinician,
                 source = excluded.source,
                 notes = excluded.notes,
                 updated_at = datetime('now')""",
            (
                user_id,
                diag["diagnosis_name"],
                diag["status"],
                diag["confirmed_date"],
                diag["confirming_clinician"],
                diag["source"],
                diag["notes"],
            ),
        )
        if before is None:
            inserted_diagnoses += 1

    if force_replace:
        conn.execute("DELETE FROM clinical_interventions WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM clinical_test_results WHERE user_id = ?", (user_id,))

    for iv in MARIA_INTERVENTIONS:
        exists = conn.execute(
            """SELECT 1 FROM clinical_interventions
               WHERE user_id = ? AND intervention_type = ? AND name = ? AND COALESCE(start_date, '') = COALESCE(?, '')
               LIMIT 1""",
            (user_id, iv["intervention_type"], iv["name"], iv.get("start_date")),
        ).fetchone()
        if exists and not force_replace:
            continue
        conn.execute(
            """INSERT INTO clinical_interventions
               (user_id, intervention_type, name, dose, schedule, start_date, end_date,
                status, prescriber, notes, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
            (
                user_id,
                iv["intervention_type"],
                iv["name"],
                iv["dose"],
                iv["schedule"],
                iv["start_date"],
                iv["end_date"],
                iv["status"],
                iv["prescriber"],
                iv["notes"],
            ),
        )
        inserted_interventions += 1

    for test in MARIA_TEST_RESULTS:
        exists = conn.execute(
            """SELECT 1 FROM clinical_test_results
               WHERE user_id = ? AND test_type = ? AND COALESCE(test_date, '') = COALESCE(?, '') AND status = ?
               LIMIT 1""",
            (user_id, test["test_type"], test.get("test_date"), test.get("status", "confirmed")),
        ).fetchone()
        if exists and not force_replace:
            continue
        conn.execute(
            """INSERT INTO clinical_test_results
               (user_id, test_type, test_date, status, summary, key_metrics_json, source_ref, risk_flag, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
            (
                user_id,
                test["test_type"],
                test.get("test_date"),
                test.get("status", "confirmed"),
                test.get("summary"),
                json.dumps(test.get("key_metrics", {})),
                test.get("source_ref"),
                test.get("risk_flag", "unknown"),
            ),
        )
        inserted_tests += 1

    return {
        "inserted_diagnoses": inserted_diagnoses,
        "inserted_interventions": inserted_interventions,
        "inserted_tests": inserted_tests,
    }


def ensure_demo_organ_score_prereqs(
    user_id: int,
    force_profile: bool = False,
    force_registry: bool = False,
) -> dict:
    """Backfill Maria's clinical profile + core labs for organ score computation.

    Safe to run repeatedly on existing demo databases.
    """
    existing_profile = get_profile(user_id) or {}
    if force_profile:
        profile_backfilled = True
        merged_profile = dict(MARIA_CLINICAL_PROFILE)
    else:
        profile_backfilled = not existing_profile or any(
            existing_profile.get(key) in (None, "")
            for key in MARIA_CLINICAL_PROFILE
        )
        merged_profile = dict(MARIA_CLINICAL_PROFILE)
        for key in MARIA_CLINICAL_PROFILE:
            current_value = existing_profile.get(key)
            if current_value is not None and current_value != "":
                merged_profile[key] = current_value
    save_profile(user_id, merged_profile)

    inserted_biomarkers = 0
    updated_biomarkers = 0
    inserted_body_metrics = 0
    inserted_wearable_measurements = 0
    registry_summary = {"inserted_diagnoses": 0, "inserted_interventions": 0, "inserted_tests": 0}
    missing_definitions = []
    conn = get_connection()
    try:
        biomarker_ids = {
            row["code"]: row["id"]
            for row in conn.execute("SELECT id, code FROM biomarker_definitions").fetchall()
        }
        for code, value in MARIA_ORGAN_SCORE_BIOMARKERS.items():
            biomarker_id = biomarker_ids.get(code)
            if biomarker_id is None:
                missing_definitions.append(code)
                continue
            existing_row = conn.execute(
                """SELECT id FROM biomarker_results
                   WHERE user_id = ? AND biomarker_id = ? AND lab_date = ?
                   ORDER BY id DESC LIMIT 1""",
                (user_id, biomarker_id, MARIA_BACKFILL_LAB_DATE),
            ).fetchone()
            if existing_row:
                conn.execute(
                    """UPDATE biomarker_results
                       SET value = ?, lab_name = ?
                       WHERE id = ?""",
                    (float(value), MARIA_BACKFILL_LAB_NAME, existing_row["id"]),
                )
                updated_biomarkers += 1
            else:
                any_row = conn.execute(
                    """SELECT id FROM biomarker_results
                       WHERE user_id = ? AND biomarker_id = ?
                       ORDER BY COALESCE(lab_date, ''), id DESC
                       LIMIT 1""",
                    (user_id, biomarker_id),
                ).fetchone()
                if any_row:
                    conn.execute(
                        """UPDATE biomarker_results
                           SET value = ?, lab_date = ?, lab_name = ?
                           WHERE id = ?""",
                        (float(value), MARIA_BACKFILL_LAB_DATE, MARIA_BACKFILL_LAB_NAME, any_row["id"]),
                    )
                    updated_biomarkers += 1
                else:
                    conn.execute(
                        """INSERT OR IGNORE INTO biomarker_results
                           (user_id, biomarker_id, value, lab_date, lab_name)
                           VALUES (?, ?, ?, ?, ?)""",
                        (user_id, biomarker_id, float(value), MARIA_BACKFILL_LAB_DATE, MARIA_BACKFILL_LAB_NAME),
                    )
                    inserted_biomarkers += 1

        existing_metrics = conn.execute(
            "SELECT 1 FROM body_metrics WHERE user_id = ? LIMIT 1",
            (user_id,),
        ).fetchone()
        backfill_metric_row = conn.execute(
            "SELECT id FROM body_metrics WHERE user_id = ? AND log_date = ? LIMIT 1",
            (user_id, MARIA_BACKFILL_LAB_DATE),
        ).fetchone()
        if backfill_metric_row:
            conn.execute(
                """UPDATE body_metrics
                   SET weight_kg = ?, height_cm = ?, waist_cm = ?, hip_cm = ?, body_fat_pct = ?,
                       notes = ?, created_at = ?
                   WHERE id = ?""",
                (
                    MARIA_ORGAN_SCORE_BODY_METRICS["weight_kg"],
                    MARIA_ORGAN_SCORE_BODY_METRICS["height_cm"],
                    MARIA_ORGAN_SCORE_BODY_METRICS["waist_cm"],
                    MARIA_ORGAN_SCORE_BODY_METRICS["hip_cm"],
                    MARIA_ORGAN_SCORE_BODY_METRICS["body_fat_pct"],
                    "Backfilled for organ score prerequisites",
                    MARIA_BACKFILL_LAB_DATE,
                    backfill_metric_row["id"],
                ),
            )
        elif force_profile or not existing_metrics:
            conn.execute(
                """INSERT OR IGNORE INTO body_metrics
                   (user_id, log_date, weight_kg, height_cm, waist_cm, hip_cm, body_fat_pct, notes, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    user_id,
                    MARIA_BACKFILL_LAB_DATE,
                    MARIA_ORGAN_SCORE_BODY_METRICS["weight_kg"],
                    MARIA_ORGAN_SCORE_BODY_METRICS["height_cm"],
                    MARIA_ORGAN_SCORE_BODY_METRICS["waist_cm"],
                    MARIA_ORGAN_SCORE_BODY_METRICS["hip_cm"],
                    MARIA_ORGAN_SCORE_BODY_METRICS["body_fat_pct"],
                    "Backfilled for organ score prerequisites",
                    MARIA_BACKFILL_LAB_DATE,
                ),
            )
            inserted_body_metrics = 1

        # DEXA scan — inserted fresh, or refreshed when force_profile is set,
        # so the DXA osteoporosis / fragility-fracture score has real inputs.
        # Older or isolated test databases may not yet have the dexa_scans
        # table, so silently skip in that case.
        dexa_table_present = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='dexa_scans'"
        ).fetchone()
        if dexa_table_present:
            existing_dexa = conn.execute(
                "SELECT 1 FROM dexa_scans WHERE user_id = ? LIMIT 1",
                (user_id,),
            ).fetchone()
            if force_profile or not existing_dexa:
                # save_dexa_scan opens its own connection so we must flush ours
                # first to avoid "database is locked" on SQLite.
                conn.commit()
                from services.body_metrics_service import save_dexa_scan
                dexa_payload = {k: v for k, v in MARIA_DEXA_SCAN.items() if k != "scan_date"}
                save_dexa_scan(user_id, MARIA_DEXA_SCAN["scan_date"], **dexa_payload)

        # Check if wearable data exists with recent dates (last 7 days)
        from config.wearable_wheel_data import WEARABLE_METRIC_SPECS as _WMS
        recent_cutoff = (date.today() - timedelta(days=7)).isoformat()
        recent_wearable = conn.execute(
            "SELECT COUNT(*) as cnt FROM wearable_measurements WHERE user_id = ? AND measured_at >= ?",
            (user_id, recent_cutoff),
        ).fetchone()
        has_recent_wearable = (recent_wearable and recent_wearable["cnt"] > 50) and (not force_profile)

        if not has_recent_wearable:
            # Seed 30 days of wearable data with realistic variance
            _wb = {
                "resting_heart_rate_bpm": (67, 6, "Whoop Band"),
                "heart_rate_variability_ms": (31, 9, "Whoop Band"),
                "average_heart_rate_bpm": (76, 7, "Whoop Band"),
                "respiratory_rate_bpm": (17.1, 1.2, "Oura Ring"),
                "steps_count": (6400, 2100, "Whoop Band"),
                "kilojoule_expended": (1850, 320, "Whoop Band"),
                "arrhythmia_alert_afib": (0, 0, "Whoop Band"),
                "recovery_score": (58, 12, "Whoop Band"),
                "spo2_pct": (94.5, 1.2, "Oura Ring"),
                "overnight_spo2_avg_pct": (93.8, 1.4, "Oura Ring"),
                "skin_temperature_c": (33.0, 0.5, "Oura Ring"),
                "body_temperature_deviation_c": (0.30, 0.14, "Oura Ring"),
                "sleep_efficiency_pct": (81, 6, "Oura Ring"),
                "sleep_consistency_pct": (69, 9, "Oura Ring"),
                "sleep_performance_pct": (72, 8, "Whoop Band"),
                "sleep_debt_hours": (2.6, 0.9, "Whoop Band"),
                "total_rem_sleep_time_min": (74, 16, "Oura Ring"),
                "total_slow_wave_sleep_time_min": (62, 14, "Oura Ring"),
                "total_light_sleep_time_min": (248, 36, "Oura Ring"),
                "total_time_spent_in_bed_min": (488, 24, "Oura Ring"),
                "sleep_latency_min": (28, 8, "Oura Ring"),
                "sleep_disturbance_count": (9, 3, "Oura Ring"),
                "total_awake_time_min": (61, 18, "Oura Ring"),
                "sleep_cycle_count": (4, 1, "Oura Ring"),
            }
            _wo = {
                "systolic_bp_mmhg": (136, 8, "Withings BPM Connect Pro"),
                "diastolic_bp_mmhg": (86, 6, "Withings BPM Connect Pro"),
                "body_weight_kg": (78.0, 0.7, "InBody H40 Home Scale"),
                "cgm_avg_glucose_mgdl": (112, 8, "CGM FreeStyle Libre"),
                "cgm_time_in_range_pct": (78, 8, "CGM FreeStyle Libre"),
            }
            for _doff in range(30):
                _md = (date.today() - timedelta(days=29 - _doff))
                _mts = f"{_md.isoformat()}T07:00:00"
                for _mc, (_base, _noise, _src) in _wb.items():
                    _val = _base + random.gauss(0, _noise)
                    if _mc == "arrhythmia_alert_afib":
                        _val = 0
                    elif "pct" in _mc:
                        _val = max(0, min(100, _val))
                    elif _mc == "steps_count":
                        _val = max(1000, round(_val))
                    elif _mc == "sleep_debt_hours":
                        _val = max(0, _val)
                    elif _mc.endswith("_count"):
                        _val = max(0, round(_val))
                    elif _mc.endswith("_min") and "time" in _mc:
                        _val = max(0, round(_val))
                    _unit = _WMS.get(_mc, {}).get("unit", "")
                    try:
                        conn.execute(
                            """INSERT OR REPLACE INTO wearable_measurements
                               (user_id, metric_code, metric_name, value, unit, measured_at, source)
                               VALUES (?, ?, ?, ?, ?, ?, ?)""",
                            (user_id, _mc, _WMS.get(_mc, {}).get("label", _mc),
                             round(_val, 2), _unit, _mts, _src),
                        )
                        inserted_wearable_measurements += 1
                    except Exception:
                        pass
                if _doff % 3 == 0:
                    for _mc, (_base, _noise, _src) in _wo.items():
                        _val = _base + random.gauss(0, _noise)
                        _unit = _WMS.get(_mc, {}).get("unit", "")
                        try:
                            conn.execute(
                                """INSERT OR REPLACE INTO wearable_measurements
                                   (user_id, metric_code, metric_name, value, unit, measured_at, source)
                                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                (user_id, _mc, _WMS.get(_mc, {}).get("label", _mc),
                                 round(_val, 2), _unit, _mts, _src),
                            )
                            inserted_wearable_measurements += 1
                        except Exception:
                            pass

        registry_summary = _seed_maria_clinical_registry(conn, user_id, force_replace=force_registry)
        conn.commit()
    finally:
        conn.close()

    return {
        "profile_backfilled": profile_backfilled,
        "inserted_biomarkers": inserted_biomarkers,
        "updated_biomarkers": updated_biomarkers,
        "inserted_body_metrics": inserted_body_metrics,
        "inserted_wearable_measurements": inserted_wearable_measurements,
        "inserted_diagnoses": registry_summary["inserted_diagnoses"],
        "inserted_interventions": registry_summary["inserted_interventions"],
        "inserted_tests": registry_summary["inserted_tests"],
        "missing_definitions": missing_definitions,
    }


def main():
    print("Initializing database...")
    init_db()

    # Clean any existing demo data
    conn = get_connection()
    existing = conn.execute("SELECT id FROM users WHERE username = ?", (USERNAME,)).fetchone()
    if existing:
        uid = existing["id"]
        # Delete child tables before parent tables to avoid FK violations
        for table in ["goal_progress", "habit_log", "habit_celebrations",
                       "wheel_assessments", "stage_of_change", "goals",
                       "habits", "daily_checkins", "weekly_reviews",
                       "coaching_messages", "comb_assessments",
                       "coin_transactions", "daily_insights", "thought_checks",
                       "user_journey", "user_lesson_progress", "future_self_letters",
                       "auto_weekly_reports",
                       "body_metrics", "weekly_challenges",
                       "protocol_log", "user_protocols",
                       "biomarker_results", "biomarker_ai_analysis",
                       "chronotype_assessments",
                       "sleep_logs", "fasting_sessions",
                       "meal_logs", "nutrition_daily_summary",
                       "food_log_items", "calorie_daily_summary",
                       "calorie_targets", "diet_assessments",
                       "meditation_sessions", "quote_interactions",
                       "nudge_shown", "daily_growth_state",
                       "exercise_logs", "exercise_programs", "exercise_weekly_summary",
                       "workout_sets",
                       "cycling_plan", "cycling_profile", "cycling_ride_logs",
                       "dexa_scans", "organ_score_results",
                       "clinical_diagnoses", "clinical_interventions", "clinical_test_results",
                       "sibo_fodmap_phase", "sibo_food_logs",
                       "sibo_reintro_challenges", "sibo_symptom_logs", "sibo_user_state",
                       "garmin_connections", "strava_connections",
                       "wearable_measurements",
                       "user_clinical_profile", "user_settings"]:
            try:
                conn.execute(f"DELETE FROM {table} WHERE user_id = ?", (uid,))
            except Exception:
                pass  # Table may not exist yet
        conn.commit()
        conn.execute("DELETE FROM users WHERE id = ?", (uid,))
        conn.commit()
    # Reset shared tables
    conn.execute("DELETE FROM micro_lessons")
    conn.commit()
    conn.close()

    # Create Maria's account
    user_id = create_user(USERNAME, PASSWORD, DISPLAY_NAME, EMAIL)
    print(f"Created user: {DISPLAY_NAME} (id={user_id})")

    print("Seeding Maria's clinical profile for organ score computation...")
    _seed_maria_clinical_profile(user_id)

    conn = get_connection()
    registry_seeded = _seed_maria_clinical_registry(conn, user_id, force_replace=True)
    print(
        "Seeding Maria's clinical registry..."
        f" diagnoses={registry_seeded['inserted_diagnoses']},"
        f" interventions={registry_seeded['inserted_interventions']},"
        f" tests={registry_seeded['inserted_tests']}"
    )
    conn.commit()

    # ════════════════════════════════════════════════════════════════════════
    # MARIA'S STORY — The Journey Arc
    # ════════════════════════════════════════════════════════════════════════
    #
    # PHASE 1 (Month 1-2): Rock Bottom & Wake-Up Call
    #   - Doctor visit: pre-diabetic, high BP, 105 kg
    #   - Smoking half a pack/day, drinking wine most nights
    #   - Sleeping 4-5h, stressed, isolated from friends
    #   - Eating fast food and processed meals
    #   - No exercise at all
    #
    # PHASE 2 (Month 3-4): First Steps
    #   - Quit smoking (with patches), cut alcohol to weekends
    #   - Started walking 15-20 min/day
    #   - Began cooking simple meals, added vegetables
    #   - Downloaded sleep hygiene tips, trying to sleep by 11pm
    #   - Reconnected with one old friend
    #
    # PHASE 3 (Month 5-7): Building Momentum
    #   - Walking 30-45 min/day, started Couch-to-5K
    #   - Plant-predominant meals 4-5 days/week
    #   - Lost 15 kg, energy improving
    #   - Started meditation app (5 min/day)
    #   - Joined a running group — new friends
    #   - Sleeping 6-7h, quality improving
    #
    # PHASE 4 (Month 8-10): Thriving
    #   - Running 5K regularly, training for 10K
    #   - Whole-food diet is now default
    #   - Lost 30 kg total, blood work normalized
    #   - Meditating 15-20 min daily
    #   - Family relationships transformed
    #   - Alcohol: only occasional wine at social events
    #
    # PHASE 5 (Month 11-12): Half-Marathon & Maintenance
    #   - Completed first 10K, training for 21K
    #   - Ran 21K half-marathon in month 12!
    #   - Total weight loss: 40 kg (105→65 kg)
    #   - Sleeping 7-8h consistently
    #   - Meditation is non-negotiable daily habit
    #   - Role model for her kids and friends
    #   - Only "substance": occasional glass of wine (1-2/month)

    # ── Pillar progression curves ───────────────────────────────────────────
    # (start_score, end_score) for each pillar over the year
    pillar_arcs = {
        1: (1, 9),   # Nutrition: junk food addict → whole-food plant-predominant
        2: (1, 9),   # Physical Activity: completely sedentary → 21K runner
        3: (2, 9),   # Sleep: 4h fragmented, phone addiction → 7-8h restorative
        4: (1, 8),   # Stress Management: panic attacks, overwhelmed → daily meditation
        5: (2, 9),   # Social Connection: deeply isolated, ashamed → strong community
        6: (2, 8),   # Substance Avoidance: smoker+daily drinker → clean (occasional wine)
    }

    # ── Stage of Change progression per pillar ──────────────────────────────
    # {pillar_id: [(month, stage)]}
    stage_progression = {
        1: [(1, "contemplation"), (3, "preparation"), (4, "action"), (9, "maintenance")],
        2: [(1, "precontemplation"), (2, "contemplation"), (3, "preparation"), (4, "action"), (10, "maintenance")],
        3: [(1, "contemplation"), (3, "action"), (7, "maintenance")],
        4: [(1, "precontemplation"), (4, "contemplation"), (5, "preparation"), (6, "action"), (10, "maintenance")],
        5: [(1, "contemplation"), (3, "preparation"), (5, "action"), (9, "maintenance")],
        6: [(1, "contemplation"), (2, "preparation"), (3, "action"), (8, "maintenance")],
    }

    # ── Wheel Assessments (monthly) ─────────────────────────────────────────
    print("Creating wheel assessments...")
    total_days = (END_DATE - START_DATE).days

    for month_offset in range(13):  # 0 through 12
        assess_date = START_DATE + timedelta(days=month_offset * 30)
        if assess_date > END_DATE:
            assess_date = END_DATE
        t = month_offset / 12.0  # 0.0 to 1.0

        session_id = str(uuid.uuid4())
        for pid, (start, end) in pillar_arcs.items():
            score = lerp_smooth(start, end, t)
            note = _get_pillar_note(pid, month_offset)
            conn.execute(
                "INSERT INTO wheel_assessments (user_id, pillar_id, score, notes, session_id, assessed_at) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, pid, score, note, session_id, assess_date.isoformat()),
            )

        # Stage of change entries for this month
        for pid, stages in stage_progression.items():
            for stage_month, stage in stages:
                if stage_month == month_offset + 1:
                    conn.execute(
                        "INSERT INTO stage_of_change (user_id, pillar_id, stage, assessed_at) VALUES (?, ?, ?, ?)",
                        (user_id, pid, stage, assess_date.isoformat()),
                    )

    # ── Habits ──────────────────────────────────────────────────────────────
    print("Creating habits...")
    habits = [
        # (pillar_id, name, start_month, description)
        (1, "Eat 5+ servings fruits/vegetables", 1, "Track daily fruit and vegetable intake"),
        (1, "Cook a whole-food meal", 2, "Prepare at least one meal from scratch"),
        (1, "Drink 8 glasses of water", 1, "Stay hydrated throughout the day"),
        (2, "Morning walk/run", 2, "Started with 15min walks, now running"),
        (2, "Stretching routine", 4, "10-minute morning stretch"),
        (2, "Strength training", 6, "Bodyweight exercises 2x/week"),
        (3, "In bed by 10:30 PM", 2, "Consistent bedtime routine"),
        (3, "No screens after 10 PM", 3, "Blue light cutoff for better sleep"),
        (3, "7+ hours of sleep", 3, "Track sleep duration"),
        (4, "Morning meditation", 5, "Started at 5min, now 15-20min"),
        (4, "Gratitude journaling", 4, "Write 3 things grateful for"),
        (4, "Deep breathing (3x daily)", 3, "Box breathing during stress"),
        (5, "Call/text a friend", 3, "Maintain social connections"),
        (5, "Family dinner (no phones)", 4, "Quality time with kids"),
        (5, "Running group meetup", 6, "Weekly group run Saturdays"),
        (6, "Tobacco-free day", 2, "Quit smoking journey"),
        (6, "Alcohol-free day", 2, "Mindful drinking choices"),
        (6, "Mindful substance check", 3, "Daily awareness moment"),
    ]

    habit_ids = {}
    for pid, name, start_month, desc in habits:
        cursor = conn.execute(
            "INSERT INTO habits (user_id, pillar_id, name, description) VALUES (?, ?, ?, ?)",
            (user_id, pid, name, desc),
        )
        habit_ids[(pid, name)] = (cursor.lastrowid, start_month)

    # ── Daily Check-ins & Habit Logs ────────────────────────────────────────
    print("Creating daily check-ins and habit logs (365 days)...")

    # Mood/energy arcs — she starts in a very dark place
    mood_arc = (1, 9)      # Deeply depressed, hopeless → vibrant, joyful
    energy_arc = (1, 9)    # Completely drained, can barely function → energetic, alive

    # Special events for journal entries
    special_events = {
        3: ("Cried in the car after the doctor's appointment. Pre-diabetic. 105 kg. She said if I don't change, I could be on insulin within a year. My kids need me.", "I made the appointment", "Everything feels impossible"),
        7: ("Told my husband about the diagnosis. He was silent. I don't think he knows how to help. I feel so alone in this.", "I told someone", "Husband doesn't understand"),
        14: ("Day 1 without cigarettes. Used the patch. Hands are shaking. Ate an entire bag of chips. I feel like I'm crawling out of my skin.", "Started the quit", "Withdrawal is unbearable"),
        18: ("Almost bought a pack today. Stood in the store for 10 minutes holding them. Put them back. Went home and cried.", "Didn't buy the cigarettes", "I wanted to smoke so badly"),
        21: ("Walked for 10 minutes today. That's it. 10 minutes and I was out of breath. I used to be athletic in school. What happened to me?", "Walked for 10 minutes", "Got winded in 10 minutes"),
        30: ("First 5K walk completed! Took 55 minutes but I did it. My knees hurt. But I did it.", "Finished my first 5K walk!", "Knees were sore, very slow"),
        42: ("Bad week. Weight hasn't moved in 10 days. What's the point? Ate pizza last night and hated myself after.", "Didn't smoke", "Binge ate pizza, weight plateau"),
        45: ("One month smoke-free today. Using patches less. The cravings are quieter now. Still there, but quieter.", "One month without cigarettes!", "Cravings still hit at night"),
        60: ("Lost first 5 kg! Doctor says blood pressure is improving. She smiled. First time I've felt hopeful in months.", "5 kg down! BP improving!", "Weekend eating is still hard"),
        82: ("My sister said something cruel about my weight at a family dinner. I almost smoked. Went to my car and did the breathing exercise instead. Shaking but smoke-free.", "Didn't relapse after trigger", "Sister's comment devastated me"),
        85: ("Still hurting from what my sister said. Didn't walk for 3 days. Today I forced myself out. Walked and cried. But I walked.", "Got back to walking", "Depression hit hard this week"),
        90: ("Started Couch-to-5K program. Running for 1 minute felt impossible. Literally 60 seconds and I thought I would die.", "Began C25K program", "Running is SO hard, felt humiliated"),
        120: ("Ran 5 minutes without stopping for the first time in decades! I was so shocked I stopped and looked at my watch twice.", "5 minutes of running non-stop!", "Wanted to quit at 3 min but pushed through"),
        148: ("Knee pain. Doctor says rest for a week. No running. I'm terrified I'll lose all my progress. What if I can't go back?", "Went to the doctor instead of ignoring it", "Injury scare — forced to rest"),
        153: ("First run after the knee rest. Slow, careful, but I'm back. I'm not the person who gives up anymore.", "Back to running after injury", "Fear of re-injury"),
        150: ("Lost 15 kg! Friends are noticing. Ana said 'you look like a different person.' I don't feel different yet inside.", "15 kg lost, people noticing!", "Plateau was frustrating, body image still hard"),
        180: ("Completed Couch-to-5K! I can run 30 minutes straight! 4 months ago I couldn't run for ONE minute!", "Finished C25K program!! 30 min run!", "Weather was terrible but I did it anyway"),
        210: ("Joined a running group. Was terrified — thought they'd judge the slow, chubby woman. Instead they high-fived me. Made 3 new friends.", "First running group meetup!", "Felt slow compared to everyone, but they were so kind"),
        237: ("Anniversary of Papa's death. Miss him so much. He never got to see me like this. Meditated for 30 min and let myself cry.", "Honored my father's memory", "Grief is heavy today"),
        240: ("Ran my first 5K race! 32 minutes! My kids were at the finish line with a sign. I ugly-cried.", "FIRST 5K RACE — 32 minutes!!", "Nothing. Everything was perfect."),
        270: ("Lost 30 kg total. Blood work is completely normal. Doctor literally hugged me. She said 'you reversed it.' No more pre-diabetes.", "30 kg lost! Blood work NORMAL! Pre-diabetes reversed!", "Loose skin bothers me sometimes"),
        300: ("Completed my first 10K race! 1:05:00. My running group all ran it together.", "10K DONE! 1:05:00!", "Legs were dead after but heart was full"),
        330: ("Training for the half-marathon. 15K long run today. A year ago I was 105 kg eating pizza on the couch. Now I run 15K for fun.", "15K training run completed", "Nutrition timing is tricky for long runs"),
        355: ("Last long training run before the half-marathon. 18K. I'm ready. I can't believe I'm saying that.", "18K — I am ready", "Taper anxiety, worried about race day"),
        360: ("RAN MY FIRST HALF-MARATHON! 21.1 KM! 2:15:00. I crossed that line and SOBBED. My kids, my husband, Ana, my running group — they were all there. One year ago I was 105 kg and couldn't walk 10 minutes. Today I ran 21.1 km. I am not the same person.", "21K HALF-MARATHON COMPLETED!! 2:15:00!!", "My feet hurt but my heart is FULL"),
    }

    current_date = START_DATE
    day_count = 0

    while current_date <= END_DATE:
        day_count += 1
        t = day_count / total_days  # 0.0 to 1.0
        month = ((current_date - START_DATE).days // 30) + 1
        weekday = current_date.weekday()  # 0=Mon, 6=Sun

        # Skip some days early on (less consistent), fewer skips later
        skip_chance = max(0.02, 0.25 * (1 - t))
        if random.random() < skip_chance:
            current_date += timedelta(days=1)
            continue

        mood = lerp_smooth(mood_arc[0], mood_arc[1], t)
        energy = lerp_smooth(energy_arc[0], energy_arc[1], t)

        # ── Setback periods (realistic dips) ──────────────────────────────
        # Week 3: Nicotine withdrawal crash
        if 14 <= day_count <= 24:
            mood = max(1, mood - random.randint(1, 3))
            energy = max(1, energy - random.randint(1, 2))
        # Week 6-7: First plateau, doubt creeps in
        if 38 <= day_count <= 50:
            mood = max(1, mood - random.randint(0, 2))
        # Month 3: Stressful family event, almost relapsed smoking
        if 80 <= day_count <= 88:
            mood = max(1, mood - random.randint(1, 3))
            energy = max(1, energy - random.randint(1, 2))
        # Month 5: Running injury scare, had to rest a week
        if 145 <= day_count <= 152:
            mood = max(1, mood - random.randint(1, 2))
            energy = max(1, energy - random.randint(2, 3))
        # Month 8: Emotional week — anniversary of her father's passing
        if 235 <= day_count <= 242:
            mood = max(1, mood - random.randint(2, 3))

        # Pillar daily ratings
        ratings = {}
        for pid, (start, end) in pillar_arcs.items():
            base = lerp_smooth(start, end, t)

            # ── Setback dips per pillar ───────────────────────────────
            # Early weeks: substance cravings hit hard
            if pid == 6 and day_count <= 60:
                base = max(1, base - random.randint(0, 2))
            # Nicotine withdrawal tanks stress management
            if pid == 4 and 14 <= day_count <= 30:
                base = max(1, base - random.randint(1, 2))
            # Sleep gets WORSE before better (withdrawal + anxiety)
            if pid == 3 and day_count <= 40:
                base = max(1, base - random.randint(0, 1))
            # Running injury week — activity drops
            if pid == 2 and 145 <= day_count <= 155:
                base = max(1, base - random.randint(2, 4))
            # Stressful family event impacts social + stress
            if pid in [4, 5] and 80 <= day_count <= 88:
                base = max(1, base - random.randint(1, 3))
            # Father's anniversary — everything dips
            if 235 <= day_count <= 242:
                base = max(1, base - random.randint(0, 2))

            # Weekends slightly different
            if weekday >= 5:
                if pid == 5:  # Social better on weekends
                    base = min(10, base + 1)
                if pid == 6:  # Substance slightly harder on weekends (wine)
                    base = max(1, base - 1) if t > 0.3 else base
            ratings[pid] = base

        # Journal and reflections
        journal = ""
        win = ""
        challenge = ""
        gratitude = ""

        event = special_events.get(day_count)
        if event:
            journal, win, challenge = event[0], event[1], event[2]
        else:
            # Regular day journal entries based on phase
            journal, win, challenge, gratitude = _get_daily_entry(month, t, weekday)

        conn.execute(
            """INSERT OR REPLACE INTO daily_checkins
               (user_id, checkin_date, mood, energy,
                nutrition_rating, activity_rating, sleep_rating,
                stress_rating, connection_rating, substance_rating,
                journal_entry, gratitude, win_of_day, challenge)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, current_date.isoformat(), mood, energy,
             ratings[1], ratings[2], ratings[3],
             ratings[4], ratings[5], ratings[6],
             journal, gratitude, win, challenge),
        )

        # Habit logs
        for (pid, name), (habit_id, start_month) in habit_ids.items():
            if month < start_month:
                continue

            # Completion probability increases over time
            months_active = month - start_month + 1
            base_prob = min(0.95, 0.4 + months_active * 0.08)

            # Some habits are harder on weekends
            if weekday >= 5 and pid in [3, 4]:  # Sleep/stress harder on weekends
                base_prob -= 0.1

            # Occasional wine on weekends (substance avoidance not perfect)
            if pid == 6 and "Alcohol" in name and weekday >= 4:
                if t > 0.5:  # After month 6, occasional wine is OK
                    base_prob = 0.75  # Not always alcohol-free on weekends

            completed = 1 if random.random() < base_prob else 0
            if completed:
                conn.execute(
                    "INSERT OR REPLACE INTO habit_log (habit_id, user_id, log_date, completed_count) VALUES (?, ?, ?, ?)",
                    (habit_id, user_id, current_date.isoformat(), 1),
                )

        current_date += timedelta(days=1)

    # ── SMART-EST Goals ─────────────────────────────────────────────────────
    print("Creating SMART-EST goals...")

    goals = [
        # Phase 1-2 Goals
        {
            "pillar_id": 6, "title": "Quit smoking completely",
            "specific": "Stop smoking cigarettes entirely, using nicotine patches for the first 8 weeks",
            "measurable": "Zero cigarettes per day, tracked daily",
            "achievable": "Using nicotine replacement therapy and support from my doctor",
            "relevant": "My doctor warned about pre-diabetes and high blood pressure; smoking makes both worse",
            "time_bound": "Completely smoke-free within 3 months",
            "evidence_base": "NRT doubles quit rates (Cochrane review). Combining behavioral support with NRT further improves outcomes.",
            "strategic": "Substance avoidance is my most urgent pillar — it affects all others",
            "tailored": "I chose patches because I need something to manage the physical cravings while I build new habits",
            "start_date": "2025-02-15", "target_date": "2025-05-15",
            "status": "completed", "progress_pct": 100, "completed_at": "2025-04-30",
        },
        {
            "pillar_id": 2, "title": "Walk 30 minutes every day",
            "specific": "Take a brisk 30-minute walk every morning before the kids wake up",
            "measurable": "30 minutes tracked with phone timer, at least 5 days per week",
            "achievable": "I can wake up 30 minutes earlier; walking requires no equipment or skill",
            "relevant": "Physical activity is my lowest-scoring pillar and will help with weight loss",
            "time_bound": "Consistent daily walking habit within 6 weeks",
            "evidence_base": "150 min/week moderate walking reduces cardiovascular risk by 30% (AHA guidelines)",
            "strategic": "Walking is the foundation before I can progress to running",
            "tailored": "Morning works best before my kids need me; the park is 2 minutes from home",
            "start_date": "2025-03-01", "target_date": "2025-04-15",
            "status": "completed", "progress_pct": 100, "completed_at": "2025-04-10",
        },
        # Phase 3 Goals
        {
            "pillar_id": 1, "title": "Eat plant-predominant meals 5 days/week",
            "specific": "Cook whole-food, plant-based meals for lunch and dinner at least 5 days per week",
            "measurable": "Track meals daily; target 10+ plant-predominant meals per week",
            "achievable": "I've learned 15 simple recipes; grocery delivery makes ingredients accessible",
            "relevant": "Nutrition is central to my weight loss and reversing pre-diabetes",
            "time_bound": "Achieve this consistently for 8 weeks",
            "evidence_base": "Plant-predominant diets reduce T2D risk by 23% and support sustainable weight loss (ACLM position statement)",
            "strategic": "Good nutrition fuels my running and improves sleep quality",
            "tailored": "I still include fish on weekends and allow flexibility for social meals",
            "start_date": "2025-04-01", "target_date": "2025-06-01",
            "status": "completed", "progress_pct": 100, "completed_at": "2025-05-28",
        },
        {
            "pillar_id": 2, "title": "Complete Couch-to-5K program",
            "specific": "Follow the C25K program 3 times per week, progressing from run/walk intervals to continuous 30-minute runs",
            "measurable": "Complete all 9 weeks of the program; track each session with a running app",
            "achievable": "I can now walk 30 minutes easily; C25K is designed for beginners",
            "relevant": "Running will accelerate my fitness and give me a concrete achievement to work toward",
            "time_bound": "Complete the program in 9-10 weeks",
            "evidence_base": "Gradual progression reduces injury risk; C25K has high adherence rates for new runners",
            "strategic": "Builds on my walking habit; stepping stone to longer races",
            "tailored": "I run on the same morning schedule; my new running shoes fit well",
            "start_date": "2025-05-01", "target_date": "2025-07-15",
            "status": "completed", "progress_pct": 100, "completed_at": "2025-07-10",
        },
        {
            "pillar_id": 4, "title": "Establish daily meditation practice",
            "specific": "Meditate for 10+ minutes every morning using a guided meditation app",
            "measurable": "Track daily: minutes meditated, streak days",
            "achievable": "Starting with 5 minutes and building up; I already wake up early for running",
            "relevant": "Stress management is critical — chronic stress contributed to my emotional eating and poor sleep",
            "time_bound": "Consistent 10+ minute daily practice within 6 weeks",
            "evidence_base": "Mindfulness meditation reduces cortisol levels and improves emotional regulation (JAMA Internal Medicine meta-analysis)",
            "strategic": "Meditation before running helps me start the day centered",
            "tailored": "I prefer body scan meditations; mornings are my quiet time before the kids wake",
            "start_date": "2025-05-15", "target_date": "2025-07-01",
            "status": "completed", "progress_pct": 100, "completed_at": "2025-07-05",
        },
        # Phase 4 Goals
        {
            "pillar_id": 5, "title": "Join a running community",
            "specific": "Attend a local running group's Saturday morning runs every week",
            "measurable": "Attend at least 3 out of 4 Saturday runs per month",
            "achievable": "There's a group that meets at my local park; they welcome all levels",
            "relevant": "Social connection through shared activity — combines two pillars I need to improve",
            "time_bound": "Become a regular member within 2 months",
            "evidence_base": "Social exercise groups improve adherence by 25%+ and reduce loneliness (British Journal of Sports Medicine)",
            "strategic": "Running group addresses both physical activity and social connection pillars simultaneously",
            "tailored": "Saturday mornings work because my husband watches the kids",
            "start_date": "2025-07-01", "target_date": "2025-09-01",
            "status": "completed", "progress_pct": 100, "completed_at": "2025-08-25",
        },
        {
            "pillar_id": 2, "title": "Run first 5K race",
            "specific": "Register for and complete a 5K race event",
            "measurable": "Cross the finish line; target time: under 35 minutes",
            "achievable": "I can run 30 minutes continuously; 5K is within my current ability",
            "relevant": "A concrete race goal keeps me motivated and marks my transformation",
            "time_bound": "Complete by end of September 2025",
            "evidence_base": "Goal-setting with specific events improves training adherence (Sports Psychology research)",
            "strategic": "5K is a stepping stone to 10K and eventually half-marathon",
            "tailored": "The local charity 5K is perfect — low pressure, good cause, friends joining",
            "start_date": "2025-08-01", "target_date": "2025-09-30",
            "status": "completed", "progress_pct": 100, "completed_at": "2025-09-15",
            "target_value": 5.0, "unit": "km",
        },
        # Phase 5 Goals
        {
            "pillar_id": 2, "title": "Complete 10K race",
            "specific": "Train for and complete a 10K race",
            "measurable": "Finish the race; target time: under 1:10:00",
            "achievable": "I've been running 7-8K in training; 10K is the next step",
            "relevant": "Continuing to push my limits and prove what my body can do",
            "time_bound": "Complete by end of November 2025",
            "evidence_base": "Progressive distance increase of 10% per week minimizes injury risk",
            "strategic": "10K is the bridge to half-marathon training",
            "tailored": "I love the feeling of race day; registered for the autumn city run",
            "start_date": "2025-09-15", "target_date": "2025-11-30",
            "status": "completed", "progress_pct": 100, "completed_at": "2025-11-15",
            "target_value": 10.0, "unit": "km",
        },
        {
            "pillar_id": 2, "title": "Run 21K half-marathon",
            "specific": "Train for and complete a 21.1K half-marathon",
            "measurable": "Cross the finish line; target time: under 2:20:00",
            "achievable": "12-week training plan; currently running 12-15K in long runs",
            "relevant": "This is my ultimate goal — proof of complete transformation from sedentary to athlete",
            "time_bound": "Race day: February 1, 2026",
            "evidence_base": "Hal Higdon's Novice HM plan is evidence-based for first-time half-marathoners",
            "strategic": "The capstone of my first year of lifestyle medicine",
            "tailored": "My running group has 4 others training for the same race — built-in support",
            "start_date": "2025-11-01", "target_date": "2026-02-01",
            "status": "completed", "progress_pct": 100, "completed_at": "2026-02-01",
            "target_value": 21.1, "unit": "km",
        },
        # Active goal (current)
        {
            "pillar_id": 3, "title": "Maintain 7.5+ hours sleep average",
            "specific": "Maintain an average of 7.5+ hours of quality sleep per night",
            "measurable": "Track nightly with sleep app; weekly average must be 7.5h+",
            "achievable": "I've been sleeping 7-8h for 4 months; this is about consistency",
            "relevant": "Sleep quality directly affects my running recovery and mood",
            "time_bound": "Ongoing — maintain through spring 2026",
            "evidence_base": "7-9h sleep recommended by AASM; critical for athletic recovery and metabolic health",
            "strategic": "Sleep is the foundation that makes all other pillars possible",
            "tailored": "My 10:30 PM bedtime routine is well-established; just need to protect it",
            "start_date": "2026-01-01", "target_date": "2026-04-01",
            "status": "active", "progress_pct": 65,
        },
        {
            "pillar_id": 2, "title": "Train for full marathon",
            "specific": "Follow an 18-week marathon training plan targeting a spring marathon",
            "measurable": "Complete weekly mileage targets; long run progression to 32K",
            "achievable": "I completed a half-marathon; marathon is the natural next challenge",
            "relevant": "Continuing my running journey and pushing new boundaries",
            "time_bound": "Marathon in May 2026",
            "evidence_base": "Gradual mileage build-up following the 10% rule minimizes overtraining risk",
            "strategic": "This is my next big milestone after the half-marathon",
            "tailored": "My coach from running group is helping me with the plan",
            "start_date": "2026-01-15", "target_date": "2026-05-15",
            "status": "active", "progress_pct": 20,
        },
    ]

    for g in goals:
        cursor = conn.execute(
            """INSERT INTO goals (user_id, pillar_id, title, specific, measurable, achievable,
               relevant, time_bound, evidence_base, strategic, tailored,
               status, progress_pct, target_value, unit,
               start_date, target_date, completed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, g["pillar_id"], g["title"], g["specific"], g["measurable"],
             g["achievable"], g["relevant"], g["time_bound"],
             g.get("evidence_base", ""), g.get("strategic", ""), g.get("tailored", ""),
             g["status"], g["progress_pct"],
             g.get("target_value"), g.get("unit", ""),
             g["start_date"], g["target_date"], g.get("completed_at")),
        )

        # Add progress history for completed goals
        if g["status"] == "completed":
            goal_id = cursor.lastrowid
            start = date.fromisoformat(g["start_date"])
            end = date.fromisoformat(g["completed_at"])
            total = (end - start).days
            for step in range(0, total + 1, max(7, total // 8)):
                prog = min(100, int((step / total) * 100)) if total > 0 else 100
                log_date = start + timedelta(days=step)
                conn.execute(
                    "INSERT INTO goal_progress (goal_id, user_id, progress_pct, logged_at) VALUES (?, ?, ?, ?)",
                    (goal_id, user_id, prog, log_date.isoformat()),
                )
            # Final 100%
            conn.execute(
                "INSERT INTO goal_progress (goal_id, user_id, progress_pct, logged_at) VALUES (?, ?, ?, ?)",
                (goal_id, user_id, 100, g["completed_at"]),
            )

    # ── Weekly Reviews ──────────────────────────────────────────────────────
    print("Creating weekly reviews...")

    weekly_insights = [
        (1, "First week tracking. Everything feels overwhelming. Doctor's words keep echoing.", "Decided to make a change", "Don't know where to start"),
        (4, "Started walking this week. Only 15 minutes but it felt huge.", "Three walks completed!", "Legs are sore, motivation is fragile"),
        (8, "Two weeks smoke-free! The patches help but evenings are tough.", "Smoke-free for 14 days", "Cravings after dinner"),
        (12, "Cooking more at home. The kids actually liked the stir-fry!", "Family enjoyed a healthy dinner", "Weekend takeout temptation"),
        (16, "Lost 8 kg so far. Starting to feel lighter and more energetic.", "Consistent 5-day walking streak", "Rain made me skip two days"),
        (20, "Started Couch-to-5K. Running for 1 minute is harder than I thought.", "Completed W1D1 of C25K", "Self-doubt is real"),
        (24, "Can run 8 minutes now! Also started 5-min meditations.", "Running improving weekly!", "Meditation is hard to focus on"),
        (28, "The combination of running and meditation is magical for my mood.", "15 minutes running non-stop", "Sleep still inconsistent"),
        (32, "Lost 20 kg! Running group starts next week.", "20 kg milestone!", "Loose skin makes me self-conscious"),
        (36, "Running with the group is the highlight of my week.", "First group run — felt amazing", "Comparing myself to faster runners"),
        (40, "Completed Couch-to-5K! I can run 30 minutes without stopping!", "C25K COMPLETE!", "Nothing — pure joy this week"),
        (44, "Signed up for my first 5K race. Nervous but excited.", "Training going well, 35 min runs", "Pre-race anxiety"),
        (48, "RAN MY FIRST 5K RACE! 32 minutes! Cried at the finish.", "5K RACE DONE!!", "Post-race blues — what's next?"),
        (52, "One year ago I couldn't walk 15 minutes. Now I'm training for a half-marathon.", "21K half-marathon completed — 2:15:00!!", "Bittersweet — the journey continues"),
    ]

    for week_num, reflection, highlight, challenge in weekly_insights:
        week_date = START_DATE + timedelta(weeks=week_num - 1)
        week_start = week_date - timedelta(days=week_date.weekday())
        conn.execute(
            """INSERT OR REPLACE INTO weekly_reviews
               (user_id, week_start, reflection, highlights, challenges)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, week_start.isoformat(), reflection, highlight, challenge),
        )

    # ── Coaching Messages (key conversations) ───────────────────────────────
    print("Creating coaching conversation highlights...")

    coaching_conversations = [
        ("2025-02-15", "user", "I just came from the doctor. She said I'm pre-diabetic and need to lose weight urgently. I weigh 105 kg. I don't know where to start. I feel like a failure as a mother.", "general"),
        ("2025-02-15", "assistant", "Thank you for sharing that with me, Maria. First, I want you to know that coming here and being willing to talk about this takes real courage — you are not a failure. A diagnosis like pre-diabetes can feel scary, but here's the powerful truth: lifestyle medicine research shows that pre-diabetes is often reversible through lifestyle changes.\n\nLet's not try to change everything at once. Looking at your Wheel of Life, I'd suggest we start with just two things: one small step for physical activity (your lowest pillar) and one for substance avoidance. What feels most doable to you right now?", "general"),
        ("2025-04-30", "user", "I haven't smoked in 45 days! And I've been walking every morning. I lost 8 kg. But I'm scared I'll relapse.", "general"),
        ("2025-04-30", "assistant", "Maria, 45 days smoke-free and 8 kg lost — that is extraordinary! Let me reflect back what I'm hearing: you've made incredible progress, AND you're feeling vulnerable about sustaining it. That fear is actually healthy — it means you care deeply about this change.\n\nYou're in the Action stage for substance avoidance and physical activity. Here's what the research tells us: the biggest relapse risk is during moments of stress. Let's build your toolkit: What has helped you most when cravings hit? And would you be open to trying a brief stress management technique — even just 3 deep breaths — for those tough moments?", "general"),
        ("2025-07-10", "user", "I FINISHED COUCH TO 5K!! I can run for 30 minutes! A few months ago I couldn't run for ONE minute!!", "general"),
        ("2025-07-10", "assistant", "MARIA!! This is absolutely incredible — I'm so proud of you! From not being able to run for one minute to running for thirty. That is not just physical transformation — that is proof of what you're capable of when you commit to yourself.\n\nLet's take a moment to really feel this: You set a SMART goal. You showed up on hard days. You pushed through doubt. And you did it. Your Wheel of Life has shifted dramatically — Physical Activity went from a 1 to a 7!\n\nWhat would you like your next challenge to be? Many runners at your stage start thinking about a 5K race. No pressure — just curiosity. What feels exciting to you?", "general"),
        ("2025-11-15", "user", "10K done! 1:05:00. I'm training for the half-marathon now. I can't believe this is my life.", "general"),
        ("2025-11-15", "assistant", "Maria, look at how far you've come. From 105 kg and pre-diabetic to a 10K runner with normalized blood work. You've lost 30 kg. You meditate daily. You have a running community. Your kids see a mother who transforms challenges into achievements.\n\nYour Wheel of Life is remarkable — most pillars are at 8-9. Your Stage of Change shows Maintenance across nearly every pillar. You've moved from surviving to thriving.\n\nFor the half-marathon: let's make sure your nutrition supports the increased training load. Long runs over 15K require fueling strategies. And let's protect your sleep — recovery is where the magic happens. What does your current training plan look like?", "general"),
        ("2026-02-01", "user", "I DID IT. 21.1 KM. 2 hours 15 minutes. I crossed that finish line and I cried. My kids were there cheering. One year ago I was 105 kg, pre-diabetic, smoking, and couldn't walk 15 minutes. Today I'm 65 kg and I just ran a half-marathon.", "general"),
        ("2026-02-01", "assistant", "Maria. I am so deeply moved. Read that back to yourself:\n\n*One year ago: 105 kg, pre-diabetic, smoking, couldn't walk 15 minutes.*\n*Today: 65 kg, completely healthy, half-marathon finisher.*\n\nThis is what lifestyle medicine looks like when someone commits fully. You didn't just lose 40 kg — you gained a life. You gained:\n- A body that carries you 21.1 km\n- Lungs free of smoke for almost a year\n- A mind calmed by daily meditation\n- Sleep that truly restores you\n- A community of runners who are now friends\n- Children who watched their mother become unstoppable\n\nYour Wheel of Life is nearly complete — every pillar is strong. The only thing to watch is your occasional wine, and honestly, a glass shared with friends once or twice a month is part of a joyful life.\n\nWhat's next for you, Maria? Because I have a feeling you're already thinking about that full marathon... 🏃‍♀️", "general"),
    ]

    for msg_date, role, content, ctx in coaching_conversations:
        conn.execute(
            "INSERT INTO coaching_messages (user_id, role, content, context_type, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, role, content, ctx, msg_date),
        )

    # ── LifeCoins (engagement reward history) ────────────────────────────────
    print("Creating LifeCoin transaction history...")

    total_days = (END_DATE - START_DATE).days
    for day_offset in range(total_days + 1):
        current = START_DATE + timedelta(days=day_offset)
        t = day_offset / total_days
        current_str = current.isoformat()

        # Check-in coins (1 per day with check-in)
        has_checkin = conn.execute(
            "SELECT id FROM daily_checkins WHERE user_id = ? AND checkin_date = ?",
            (user_id, current_str),
        ).fetchone()
        if has_checkin:
            conn.execute(
                "INSERT OR IGNORE INTO coin_transactions (user_id, amount, reason, ref_date, created_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, 1, "checkin", current_str, current_str),
            )

        # All-habits coins (2 per day when all habits done - more likely later in journey)
        if t > 0.3 and random.random() < min(0.8, t):
            conn.execute(
                "INSERT OR IGNORE INTO coin_transactions (user_id, amount, reason, ref_date, created_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, 2, "all_habits", current_str, current_str),
            )

    # Streak milestone bonuses
    streak_milestones = [
        ("2025-02-08", "streak_7"), ("2025-02-15", "streak_14"), ("2025-02-22", "streak_21"),
        ("2025-03-03", "streak_30"), ("2025-04-02", "streak_60"), ("2025-05-02", "streak_90"),
        ("2025-08-01", "streak_180"), ("2026-02-01", "streak_365"),
    ]
    for milestone_date, reason in streak_milestones:
        conn.execute(
            "INSERT OR IGNORE INTO coin_transactions (user_id, amount, reason, ref_date, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, 5, reason, milestone_date, milestone_date),
        )

    # ── Daily Insights (sample cached insights) ─────────────────────────────
    print("Creating sample daily insights...")

    sample_insights = [
        ("2025-03-15", "Your sleep rating has been climbing this week (4 -> 6). On days with better sleep, your energy averages 1.5 points higher. Keep protecting that bedtime routine!"),
        ("2025-05-10", "Pattern spotted: on days you rate Activity 7+, your mood averages 6.8 vs 4.2 on inactive days. Movement is your mood booster!"),
        ("2025-07-20", "You've checked in 12 of the last 14 days. Great consistency! Your Nutrition ratings jumped 2 points this week."),
        ("2025-09-05", "Your Stress Management has been your biggest improver this month (+2.3 points). The meditation practice is paying off!"),
        ("2025-11-01", "Sleep and Energy are strongly correlated in your data (r=0.78). Last night's 8/10 sleep is fueling today's high energy."),
        ("2026-01-15", "All six pillars are above 7 this week. You're in the top zone across the board!"),
    ]
    for insight_date, insight_text in sample_insights:
        conn.execute(
            "INSERT OR IGNORE INTO daily_insights (user_id, insight_date, insight_text, created_at) VALUES (?, ?, ?, ?)",
            (user_id, insight_date, insight_text, insight_date),
        )

    # ── User Journey (progressive unlocking) ─────────────────────────────────
    print("Creating user journey data...")
    conn.execute(
        "INSERT OR IGNORE INTO user_journey (user_id, max_habits, consistency_days, level) VALUES (?, ?, ?, ?)",
        (user_id, 999, 330, 7),  # Maria is at max level — Lifestyle Master
    )

    # ── Implementation Intentions for some habits ─────────────────────────────
    print("Adding implementation intentions to habits...")
    ii_updates = [
        ("Morning walk/run", "After I finish my morning coffee, I will go for a run at the park near my house"),
        ("Morning meditation", "After I finish my run, I will meditate at my reading corner"),
        ("Eat 5+ servings fruits/vegetables", "After I get home from the grocery store, I will prep vegetables at the kitchen counter"),
        ("In bed by 10:30 PM", "After I finish brushing my teeth, I will get into bed at 10:30 PM"),
        ("Call/text a friend", "After I eat lunch, I will send a message to a friend at my desk"),
    ]
    for habit_name, ii_text in ii_updates:
        conn.execute(
            "UPDATE habits SET implementation_intention = ? WHERE user_id = ? AND name = ?",
            (ii_text, user_id, habit_name),
        )

    # ── Future Self Letters ──────────────────────────────────────────────────
    print("Creating future self letters...")
    letters = [
        ("Dear Future Me,\n\nI'm writing this from the darkest place I've ever been. 105 kg. Pre-diabetic. Smoking. Drinking alone. I can barely walk up the stairs without getting winded.\n\nBut today I made a decision. I'm going to change. I don't know how yet, and I'm terrified I'll fail. But I need you to know that I tried.\n\nIf you're reading this, it means some time has passed. I hope you're lighter — not just in weight, but in spirit. I hope you can run. I hope you can breathe without that rattle in your chest.\n\nMost of all, I hope you're proud of me for starting.\n\nWith hope,\nMaria (Day 1)",
         "2025-05-01", 1, "2025-02-01"),
        ("Dear Future Me,\n\nThree months in and I'm writing this after my first 5K walk. My legs hurt, my feet are blistered, and I'm sitting on a park bench crying happy tears.\n\nI quit smoking 45 days ago. I lost 8 kg. I cooked a real meal for my kids last night.\n\nYou probably don't remember how impossible this felt at the beginning. So I'm telling you: it was HARD. Every single day was a battle. But you're winning.\n\nKeep going. Don't you dare stop.\n\nLove,\nMaria (Month 3)",
         "2025-08-01", 1, "2025-05-01"),
        ("Dear Future Me,\n\nI just ran my first 5K RACE. 32 minutes. My kids were at the finish line with a handmade sign that said 'GO MAMA GO.' I ugly-cried in front of 200 strangers and I don't care.\n\nRemember when you couldn't run for ONE minute? Remember when 10 minutes of walking made you wheeze?\n\nYou're proof that people can change. If anyone ever tells you it's too late, show them this letter.\n\nYour blood work is normal. Your doctor hugged you. You reversed the pre-diabetes.\n\nI am so, so proud of us.\n\nLove,\nMaria (Month 8, 30 kg down, 5K finisher)",
         "2026-02-01", 1, "2025-09-15"),
    ]
    for text, delivery, delivered, created in letters:
        conn.execute(
            "INSERT INTO future_self_letters (user_id, letter_text, delivery_date, delivered, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, text, delivery, delivered, created),
        )

    # ── Body Metrics (weight journey) ───────────────────────────────────────
    print("Creating body metrics data...")
    conn.execute("""CREATE TABLE IF NOT EXISTS body_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        log_date TEXT NOT NULL,
        weight_kg REAL,
        height_cm REAL,
        waist_cm REAL,
        hip_cm REAL,
        body_fat_pct REAL,
        notes TEXT,
        photo_note TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(user_id, log_date)
    )""")

    # Maria's weight: 105 kg → 65 kg over 12 months (sigmoid curve)
    import math
    for week in range(53):
        log_date = START_DATE + timedelta(weeks=week)
        if log_date > END_DATE:
            break
        t = week / 52.0
        # Sigmoid weight loss curve
        s = 1 / (1 + math.exp(-10 * (t - 0.4)))
        weight = 105 - (27 * s) + random.gauss(0, 0.5)
        weight = round(max(76, min(106, weight)), 1)
        # Waist: 110cm → 72cm
        waist = round(110 - (18 * s) + random.gauss(0, 0.5), 1)
        waist = max(90, min(112, waist))
        # Hip: 120cm → 95cm
        hip = round(120 - (17 * s) + random.gauss(0, 0.5), 1)
        hip = max(101, min(122, hip))
        # Body fat: 42% → 22%
        bf = round(42 - (11 * s) + random.gauss(0, 0.3), 1)
        bf = max(30, min(43, bf))
        # Height constant
        height = 167.0

        note = ""
        if week == 0:
            note = "Starting measurements. Doctor visit day."
        elif week == 8:
            note = "First 5kg lost! Clothes are looser."
        elif week == 20:
            note = "15kg down. Had to buy new running clothes."
        elif week == 36:
            note = "22kg down. Blood pressure and lipids still need active treatment."
        elif week == 52:
            note = "27kg lost. Running capacity improved; maintaining meds and CPAP."

        conn.execute(
            """INSERT OR IGNORE INTO body_metrics
               (user_id, log_date, weight_kg, height_cm, waist_cm, hip_cm, body_fat_pct, notes, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, log_date.isoformat(), weight, height, waist, hip, bf, note, log_date.isoformat()),
        )

    # ── Weekly Challenges (sample completed challenges) ───────────────────
    print("Creating weekly challenges data...")
    conn.execute("""CREATE TABLE IF NOT EXISTS weekly_challenges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        week_start TEXT NOT NULL,
        pillar_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        target_count INTEGER NOT NULL DEFAULT 5,
        current_count INTEGER NOT NULL DEFAULT 0,
        difficulty TEXT NOT NULL DEFAULT 'medium',
        coin_reward INTEGER NOT NULL DEFAULT 10,
        status TEXT NOT NULL DEFAULT 'active',
        completed_at TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(user_id, week_start, title)
    )""")

    # Create 8 weeks of past challenges (some completed, some not)
    challenge_templates = [
        (1, "5-a-Day Champion", "Eat 5+ servings of fruits and vegetables", 5, "medium", 10),
        (2, "Step It Up", "Hit 8000+ steps in a day", 5, "medium", 10),
        (3, "Early Bird", "In bed by 10:30 PM", 5, "medium", 10),
        (4, "Breathe Easy", "Complete a breathing exercise", 5, "easy", 5),
        (5, "Connection Call", "Have a meaningful conversation", 4, "medium", 10),
        (6, "Clean Days", "Stay substance-free all day", 5, "easy", 5),
        (1, "Hydration Hero", "Drink 8 glasses of water", 5, "easy", 5),
        (2, "Morning Mover", "Exercise before 9 AM", 4, "hard", 15),
        (4, "Mindful Minutes", "Meditate for 10+ minutes", 4, "medium", 10),
        (3, "Screen Sunset", "No screens 30min before bed", 5, "medium", 10),
    ]

    for i in range(8):
        week_date = END_DATE - timedelta(weeks=8 - i)
        week_start = week_date - timedelta(days=week_date.weekday())
        # Pick 3 challenges for this week
        week_challenges = random.sample(challenge_templates, 3)
        for pid, title, desc, target, diff, reward in week_challenges:
            # More recent weeks have higher completion
            completion_prob = 0.6 + (i / 8) * 0.3
            current = target if random.random() < completion_prob else random.randint(1, target - 1)
            status = "completed" if current >= target else "expired"
            completed_at = (week_start + timedelta(days=6)).isoformat() if status == "completed" else None
            conn.execute(
                """INSERT OR IGNORE INTO weekly_challenges
                   (user_id, week_start, pillar_id, title, description, target_count, current_count, difficulty, coin_reward, status, completed_at, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, week_start.isoformat(), pid, title, desc, target, current, diff, reward, status, completed_at, week_start.isoformat()),
            )

    # ── Protocol Adoption & Completion Logs ─────────────────────────────────
    print("Creating protocol adoption and completion logs...")
    # Maria adopted 5 protocols at various points in her journey
    _proto_adoptions = [
        ("Morning Sunlight Walk", "2025-06-01"),
        ("Post-Meal Walk (10 min)", "2025-05-01"),
        ("Morning Mindfulness (10 min)", "2025-05-15"),
        ("Consistent Sleep Schedule", "2025-04-01"),
        ("Mediterranean Meal Template", "2025-04-15"),
    ]
    for proto_name, adopted_date in _proto_adoptions:
        _proto_row = conn.execute(
            "SELECT id FROM protocols WHERE name = ?", (proto_name,)
        ).fetchone()
        if not _proto_row:
            continue
        _proto_id = _proto_row["id"]
        conn.execute(
            "INSERT OR IGNORE INTO user_protocols (user_id, protocol_id, started_at, status) VALUES (?, ?, ?, 'active')",
            (user_id, _proto_id, adopted_date),
        )
        # Generate completion logs from adoption date to END_DATE
        _adopt_d = date.fromisoformat(adopted_date)
        _days_active = (END_DATE - _adopt_d).days
        for _day_off in range(_days_active + 1):
            _log_d = _adopt_d + timedelta(days=_day_off)
            _months_in = _day_off / 30.0
            # Adherence improves over time: starts ~60%, reaches ~90%
            _adh_prob = min(0.95, 0.55 + _months_in * 0.04)
            # Weekends slightly lower adherence
            if _log_d.weekday() >= 5:
                _adh_prob -= 0.08
            _completed = 1 if random.random() < _adh_prob else 0
            if _completed:
                conn.execute(
                    "INSERT OR IGNORE INTO protocol_log (user_id, protocol_id, log_date, completed) VALUES (?, ?, ?, 1)",
                    (user_id, _proto_id, _log_d.isoformat()),
                )

    # ════════════════════════════════════════════════════════════════════════
    # EXERCISE LOGS — Running, Walking, Strength, Yoga progression
    # ════════════════════════════════════════════════════════════════════════
    print("Creating exercise logs (running, walking, strength, yoga)...")
    import math as _math_ex

    # Maria's running progression:
    # Month 1-2: walking only (15-20 min)
    # Month 3-4: walk/jog mix (20-30 min, some with short run segments)
    # Month 5-7: Couch-to-5K, running 3-5K (30-40 min)
    # Month 8-10: Running 5-10K regularly (40-60 min)
    # Month 11-12: Half-marathon training, long runs 12-21K

    _exercise_count = 0
    for day_offset in range(total_days + 1):
        _ex_date = START_DATE + timedelta(days=day_offset)
        _month = day_offset / 30.0
        _t = day_offset / total_days  # 0.0 → 1.0
        _dow = _ex_date.weekday()  # 0=Mon

        # Skip some days randomly (more rest early, fewer later)
        _active_prob = 0.25 + _t * 0.50  # 25% → 75% chance of any exercise
        if random.random() > _active_prob:
            continue

        # ── Running / Walking ──
        if _month < 2:
            # Walking only
            _type = "walk"
            _dur = random.randint(15, 25)
            _dist = round(_dur * 0.08 + random.gauss(0, 0.2), 1)  # ~5 km/h
            _intensity = "light"
            _rpe = random.randint(3, 5)
        elif _month < 4:
            # Walk/jog mix
            _type = random.choice(["walk", "walk", "run"])
            _dur = random.randint(20, 35)
            if _type == "run":
                _dist = round(_dur * 0.10 + random.gauss(0, 0.3), 1)  # ~6 km/h
                _intensity = "moderate"
                _rpe = random.randint(5, 7)
            else:
                _dist = round(_dur * 0.085 + random.gauss(0, 0.2), 1)
                _intensity = "light"
                _rpe = random.randint(3, 5)
        elif _month < 7:
            # C25K → regular 5K runner
            _type = random.choice(["run", "run", "run", "walk"])
            if _type == "run":
                _dur = random.randint(25, 45)
                _pace = 7.5 - _t * 2.0 + random.gauss(0, 0.3)  # min/km improving
                _pace = max(5.5, min(8.0, _pace))
                _dist = round(_dur / _pace, 1)
                _intensity = random.choice(["moderate", "moderate", "vigorous"])
                _rpe = random.randint(5, 8)
            else:
                _dur = random.randint(20, 30)
                _dist = round(_dur * 0.09, 1)
                _intensity = "light"
                _rpe = random.randint(3, 4)
        elif _month < 10:
            # Regular 5-10K runner, some strength
            _type = random.choice(["run", "run", "run", "strength", "yoga"])
            if _type == "run":
                _dur = random.randint(30, 55)
                _pace = 6.5 - _t * 1.0 + random.gauss(0, 0.3)
                _pace = max(5.2, min(7.0, _pace))
                _dist = round(_dur / _pace, 1)
                # Saturday = long run
                if _dow == 5:
                    _dur = random.randint(50, 70)
                    _dist = round(_dur / _pace, 1)
                _intensity = random.choice(["moderate", "vigorous"])
                _rpe = random.randint(5, 8)
            elif _type == "strength":
                _dur = random.randint(30, 45)
                _dist = None
                _intensity = "moderate"
                _rpe = random.randint(6, 8)
            else:
                _dur = random.randint(30, 45)
                _dist = None
                _intensity = "light"
                _rpe = random.randint(3, 5)
        else:
            # Half-marathon training
            _type = random.choice(["run", "run", "run", "run", "strength", "yoga"])
            if _type == "run":
                _dur = random.randint(35, 60)
                _pace = 6.0 - _t * 0.5 + random.gauss(0, 0.25)
                _pace = max(5.0, min(6.8, _pace))
                _dist = round(_dur / _pace, 1)
                # Saturday = long run (progressive: 12→21K)
                if _dow == 5:
                    _long_km = 12.0 + (_month - 10) * 3.0 + random.gauss(0, 1)
                    _long_km = min(21.5, max(12.0, _long_km))
                    _dist = round(_long_km, 1)
                    _dur = round(_dist * _pace)
                _intensity = random.choice(["moderate", "moderate", "vigorous"])
                _rpe = random.randint(5, 9)
            elif _type == "strength":
                _dur = random.randint(35, 50)
                _dist = None
                _intensity = "moderate"
                _rpe = random.randint(6, 8)
            else:
                _dur = random.randint(30, 50)
                _dist = None
                _intensity = "light"
                _rpe = random.randint(3, 5)

        # Ensure positive distance
        if _dist is not None and _dist <= 0:
            _dist = round(random.uniform(1.0, 3.0), 1)

        # Calculate approximate calories (MET-based)
        _weight_at_time = 105 - 40 * _t  # linear weight loss
        _met = {"walk": 3.5, "run": 8.0, "strength": 5.0, "yoga": 3.0}.get(_type, 5.0)
        if _intensity == "vigorous":
            _met *= 1.3
        _cals = round(_met * _weight_at_time * (_dur / 60.0))

        # Estimated heart rate
        _max_hr = 220 - 43  # Maria is 43
        _hr_pct = {"light": 0.60, "moderate": 0.72, "vigorous": 0.85}.get(_intensity, 0.70)
        _avg_hr = round(_max_hr * _hr_pct + random.gauss(0, 3))
        _peak_hr = round(_avg_hr + random.randint(10, 25))

        _ext_id = f"seed_{_ex_date.isoformat()}_{_type}_{_dur}"
        _cat = {"walk": "cardio", "run": "cardio", "strength": "strength", "yoga": "flexibility"}.get(_type, "mixed")
        conn.execute(
            """INSERT OR IGNORE INTO exercise_logs
               (user_id, exercise_date, exercise_type, category, duration_min,
                intensity, distance_km, calories, avg_hr, max_hr, rpe,
                notes, source, external_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'manual', ?)""",
            (user_id, _ex_date.isoformat(), _type, _cat, _dur,
             _intensity, _dist, _cals, _avg_hr, _peak_hr, _rpe,
             None, _ext_id),
        )
        _exercise_count += 1

    conn.commit()
    print(f"  Created {_exercise_count} exercise log entries")

    # ── Update weekly summaries for exercise score ────────────────────────
    print("Updating exercise weekly summaries...")
    from services.exercise_service import update_weekly_summary as _update_ws
    _ws_date = START_DATE
    while _ws_date <= END_DATE:
        _ws_mon = _ws_date - timedelta(days=_ws_date.weekday())
        try:
            _update_ws(user_id, _ws_mon.isoformat())
        except Exception:
            pass
        _ws_date += timedelta(days=7)

    # ════════════════════════════════════════════════════════════════════════
    # PHASE 2: ADVANCED TRACKING DATA
    # ════════════════════════════════════════════════════════════════════════

    # ── Biomarker Results (4 lab panels across Maria's journey) ────────────
    print("Creating biomarker lab results...")
    import math as _math

    # Get biomarker definition IDs by code
    _bm_defs = {}
    for _row in conn.execute("SELECT id, code FROM biomarker_definitions").fetchall():
        _bm_defs[_row["code"]] = _row["id"]

    # Maria's biomarker story: pre-diabetic baseline → optimal at 12 months
    # (biomarker_code, month0, month4, month8, month12)
    _biomarker_panels = [
        ("hba1c", 6.3, 6.1, 6.0, 5.9),
        ("fasting_glucose", 124, 118, 112, 108),
        ("fasting_insulin", 24.0, 19.0, 15.0, 13.2),
        ("hs_crp", 5.8, 4.1, 3.1, 2.4),
        ("ldl_cholesterol", 186, 172, 161, 154),
        ("hdl_cholesterol", 35, 39, 42, 45),
        ("triglycerides", 298, 245, 208, 186),
        ("apob", 165, 152, 141, 132),
        ("ggt", 72, 58, 48, 42),
        ("total_cholesterol", 284, 270, 258, 248),
        ("lpa", 46, 44, 43, 42),
        ("homocysteine", 14.2, 13.1, 12.4, 11.8),
        ("vitamin_d", 12, 16, 20, 24),
        ("tsh", 3.4, 3.1, 2.8, 2.6),
        ("free_t4", 0.92, 0.96, 0.99, 1.02),
        ("free_t3", 2.5, 2.7, 2.9, 3.0),
        ("alt", 58, 49, 41, 36),
        ("ast", 46, 40, 35, 31),
        ("albumin", 3.9, 4.0, 4.1, 4.2),
        ("total_bilirubin", 0.5, 0.6, 0.6, 0.7),
        ("platelets", 272, 268, 262, 258),
        ("creatinine", 0.96, 0.92, 0.88, 0.84),
        ("uacr", 48, 35, 27, 22),
        ("hemoglobin", 12.6, 12.9, 13.2, 13.6),
        ("wbc", 8.9, 7.8, 7.1, 6.8),
        ("neutrophils_abs", 5.8, 4.9, 4.4, 4.0),
        ("lymphocytes_abs", 1.4, 1.6, 1.8, 2.0),
        ("mcv", 89.0, 89.5, 89.8, 90.0),
        ("rdw", 15.2, 14.6, 14.1, 13.9),
        ("ferritin", 22, 28, 37, 48),
        ("iron", 48, 56, 65, 74),
        ("tibc", 420, 402, 384, 366),
        ("transferrin_sat", 11, 14, 17, 20),
    ]

    _panel_dates = [
        ("2025-02-01", 0),   # baseline
        ("2025-06-01", 1),   # month 4
        ("2025-10-01", 2),   # month 8
        ("2026-02-01", 3),   # month 12
    ]
    _lab_names = ["City Hospital Lab", "City Hospital Lab", "Quest Diagnostics", "Quest Diagnostics"]

    for _code, *_values in _biomarker_panels:
        if _code not in _bm_defs:
            continue
        _bm_id = _bm_defs[_code]
        for (_pdate, _idx), _lab in zip(_panel_dates, _lab_names):
            if _idx == 3:
                # Keep latest panel deterministic so demo diagnoses stay aligned.
                _val = round(_values[_idx], 1)
            else:
                _val = round(_values[_idx] + random.gauss(0, 0.2), 1)
            conn.execute(
                """INSERT OR IGNORE INTO biomarker_results
                   (user_id, biomarker_id, value, lab_date, lab_name)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, _bm_id, _val, _pdate, _lab),
            )

    # ── Sleep Logs (~250 entries from Month 3 onward) ─────────────────────
    print("Creating sleep logs (250+ entries)...")

    _sleep_start = START_DATE + timedelta(days=60)  # month 3
    _sleep_date = _sleep_start
    _sleep_total_days = (END_DATE - _sleep_start).days

    while _sleep_date <= END_DATE:
        _st = (_sleep_date - _sleep_start).days / max(1, _sleep_total_days)

        # Skip some days early on (less consistent logging)
        if random.random() < max(0.02, 0.15 * (1 - _st)):
            _sleep_date += timedelta(days=1)
            continue

        # Bedtime: 00:30-01:30 early → 22:15-22:45 late (sigmoid)
        _s = 1 / (1 + _math.exp(-10 * (_st - 0.35)))
        _bed_h = 24 + 0.5 + (1 - _s) * 1.0  # late: 00:30-01:30
        _bed_h = _bed_h - _s * 2.25  # shifts to ~22:15-22:45
        _bed_h += random.gauss(0, 0.25)
        _bed_h = max(21.5, min(25.5, _bed_h))
        _bed_hour = int(_bed_h) % 24
        _bed_min = int((_bed_h % 1) * 60)
        _bedtime = f"{_bed_hour:02d}:{_bed_min:02d}"

        # Wake time: 06:00-07:00 early → 06:00-06:30 late
        _wake_h = 6 + random.gauss(0.25, 0.25) if _st < 0.5 else 6 + random.gauss(0.15, 0.15)
        _wake_h = max(5.5, min(7.5, _wake_h))
        _wake_hour = int(_wake_h)
        _wake_min = int((_wake_h % 1) * 60)
        _waketime = f"{_wake_hour:02d}:{_wake_min:02d}"

        # Latency: 30-60min early → 5-15min late
        _latency = round(lerp_smooth(45, 10, _st) + random.gauss(0, 5))
        _latency = max(2, min(90, _latency))

        # Awakenings: 3-4 early → 0-1 late
        _awakenings = max(0, round(lerp_smooth(3.5, 0.5, _st) + random.gauss(0, 0.5)))
        _wake_dur = max(0, _awakenings * random.randint(3, 10))

        # Quality: 1-2 early → 4-5 late
        _quality = max(1, min(5, round(lerp_smooth(1.5, 4.5, _st))))

        # Setback periods mirror main arc
        _day_in = (_sleep_date - START_DATE).days
        if 145 <= _day_in <= 155:  # injury
            _quality = max(1, _quality - 1)
            _awakenings += 1
        if 235 <= _day_in <= 242:  # grief
            _latency = min(90, _latency + 15)
            _quality = max(1, _quality - 1)

        # Hygiene factors
        _alcohol = 1 if (random.random() < 0.1 and _sleep_date.weekday() >= 4) else 0
        _exercise = 1 if random.random() < min(0.9, 0.4 + _st * 0.5) else 0

        # Compute derived fields
        _bed_dt = datetime.strptime(_bedtime, "%H:%M")
        _wake_dt = datetime.strptime(_waketime, "%H:%M")
        if _wake_dt <= _bed_dt:
            _wake_dt += timedelta(days=1)
        _tib = (_wake_dt - _bed_dt).total_seconds() / 60
        _total_sleep = max(0, _tib - _latency - _wake_dur)
        _efficiency = round((_total_sleep / _tib) * 100, 1) if _tib > 0 else 0

        # Score (simplified — full algo runs in service)
        _hours = _total_sleep / 60
        _dur_sc = 1.0 if 7 <= _hours <= 9 else (0.7 if 6 <= _hours < 7 else 0.4)
        _lat_sc = 1.0 if _latency <= 15 else (0.7 if _latency <= 30 else 0.4)
        _eff_sc = 1.0 if _efficiency >= 90 else (0.7 if _efficiency >= 85 else 0.4)
        _dst_sc = 1.0 if _awakenings <= 1 else (0.7 if _awakenings <= 3 else 0.4)
        _qua_sc = max(0, (_quality - 1) / 4)
        _score = round((_dur_sc * 0.30 + _lat_sc * 0.15 + _eff_sc * 0.20 + _dst_sc * 0.15 + _qua_sc * 0.10 + 0.7 * 0.10) * 100)
        _score = max(0, min(100, _score))

        conn.execute(
            """INSERT OR IGNORE INTO sleep_logs
               (user_id, sleep_date, bedtime, wake_time, sleep_latency_min,
                awakenings, wake_duration_min, sleep_quality,
                alcohol, exercise_today,
                total_sleep_min, sleep_efficiency, sleep_score)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (user_id, _sleep_date.isoformat(), _bedtime, _waketime, _latency,
             _awakenings, _wake_dur, _quality,
             _alcohol, _exercise,
             round(_total_sleep), round(_efficiency, 1), _score),
        )
        _sleep_date += timedelta(days=1)

    # ── Chronotype Assessment (Bear, MEQ ~50) ─────────────────────────────
    print("Setting chronotype (Bear)...")
    conn.execute(
        """INSERT OR IGNORE INTO chronotype_assessments
           (user_id, meq_score, chronotype, ideal_bedtime, ideal_waketime)
           VALUES (?, 50, 'bear', '22:30-23:00', '06:30-07:00')""",
        (user_id,),
    )

    # ── Fasting Sessions (~80 from Month 6 onward) ────────────────────────
    print("Creating fasting sessions...")

    _fast_start = START_DATE + timedelta(days=150)  # month 6
    _fast_date = _fast_start
    _fast_total_days = (END_DATE - _fast_start).days

    while _fast_date <= END_DATE:
        _ft = (_fast_date - _fast_start).days / max(1, _fast_total_days)

        # Frequency: 3-4/week early → 5-6/week late
        _skip = random.random() > min(0.85, 0.5 + _ft * 0.35)
        if _skip:
            _fast_date += timedelta(days=1)
            continue

        # Type progression: 12:12 → 14:10 → 16:8
        if _ft < 0.3:
            _ftype = "12:12"
            _target = 12
        elif _ft < 0.65:
            _ftype = "14:10"
            _target = 14
        else:
            _ftype = "16:8"
            _target = 16

        # Start time: evening of previous day
        _start_h = random.randint(19, 21)
        _start_dt = datetime(_fast_date.year, _fast_date.month, _fast_date.day, _start_h, random.randint(0, 59))
        _start_str = _start_dt.strftime("%Y-%m-%d %H:%M:%S")

        # Actual hours: sometimes they break early
        _completed = 1 if random.random() < min(0.9, 0.65 + _ft * 0.25) else 0
        if _completed:
            _actual = _target + random.gauss(0, 0.5)
        else:
            _actual = _target * random.uniform(0.5, 0.85)
        _actual = round(max(4, _actual), 1)

        _end_dt = _start_dt + timedelta(hours=_actual)
        _end_str = _end_dt.strftime("%Y-%m-%d %H:%M:%S")

        conn.execute(
            """INSERT INTO fasting_sessions
               (user_id, start_time, end_time, target_hours, actual_hours,
                fasting_type, completed)
               VALUES (?,?,?,?,?,?,?)""",
            (user_id, _start_str, _end_str, _target, _actual, _ftype, _completed),
        )
        _fast_date += timedelta(days=1)

    # ── Meal Logs (~500 from Month 2 onward) ──────────────────────────────
    print("Creating meal logs and nutrition summaries...")

    _meal_start = START_DATE + timedelta(days=30)  # month 2
    _meal_date = _meal_start
    _meal_total_days = (END_DATE - _meal_start).days

    _green_meals = [
        "Quinoa grain bowl with roasted chickpeas and veggies",
        "Mixed green salad with lentils and tahini dressing",
        "Oatmeal with berries, flax seeds, and walnuts",
        "Sweet potato and black bean tacos",
        "Smoothie bowl with spinach, banana, chia seeds",
        "Brown rice stir-fry with tofu and vegetables",
        "Mediterranean salad with hummus and whole wheat pita",
        "Vegetable curry with brown rice",
        "Bean and vegetable soup with whole grain bread",
        "Avocado toast on whole grain with cherry tomatoes",
    ]
    _yellow_meals = [
        "Grilled chicken breast with steamed broccoli",
        "Salmon fillet with quinoa and asparagus",
        "Turkey sandwich on whole wheat with mixed greens",
        "Greek yogurt with granola and fruit",
        "Pasta with marinara sauce and side salad",
        "Egg white omelet with vegetables and cheese",
        "Rice bowl with grilled fish and vegetables",
        "Chicken stir-fry with white rice",
    ]
    _red_meals = [
        "Pizza delivery with garlic bread",
        "Burger and fries from fast food",
        "Chocolate cake slice and ice cream",
        "Fried chicken with mashed potatoes",
        "Pasta with cream sauce and garlic bread",
        "Chips and dip while watching TV",
        "Takeout Chinese food with fried rice",
    ]

    while _meal_date <= END_DATE:
        _mt = (_meal_date - _meal_start).days / max(1, _meal_total_days)

        # Green probability increases: 0.15 → 0.75
        _s = 1 / (1 + _math.exp(-10 * (_mt - 0.35)))
        _green_prob = 0.15 + 0.60 * _s
        _red_prob = max(0.05, 0.40 * (1 - _s))
        _yellow_prob = 1 - _green_prob - _red_prob

        # 2-4 meals per day
        _num_meals = random.choice([2, 3, 3, 3, 4])
        _meal_types = ["breakfast", "lunch", "dinner", "snack"][:_num_meals]

        for _mtype in _meal_types:
            _r = random.random()
            if _r < _green_prob:
                _color = "green"
                _desc = random.choice(_green_meals)
                _plant = random.randint(2, 5)
                _fruit = random.randint(0, 2)
                _veg = random.randint(1, 3)
                _grains = random.randint(0, 2)
                _legumes = random.randint(0, 2)
                _nuts = random.randint(0, 1)
                _fiber = random.randint(5, 12)
            elif _r < _green_prob + _yellow_prob:
                _color = "yellow"
                _desc = random.choice(_yellow_meals)
                _plant = random.randint(0, 2)
                _fruit = random.randint(0, 1)
                _veg = random.randint(0, 2)
                _grains = random.randint(0, 1)
                _legumes = 0
                _nuts = 0
                _fiber = random.randint(2, 6)
            else:
                _color = "red"
                _desc = random.choice(_red_meals)
                _plant = 0
                _fruit = 0
                _veg = random.randint(0, 1)
                _grains = 0
                _legumes = 0
                _nuts = 0
                _fiber = random.randint(0, 2)

            _water = random.randint(0, 2)
            _total_plant = _plant

            conn.execute(
                """INSERT INTO meal_logs
                   (user_id, log_date, meal_type, description, color_category,
                    plant_servings, fruit_servings, vegetable_servings,
                    whole_grain_servings, legume_servings, nut_seed_servings,
                    fiber_grams, water_glasses)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (user_id, _meal_date.isoformat(), _mtype, _desc, _color,
                 _total_plant, _fruit, _veg, _grains, _legumes, _nuts,
                 _fiber, _water),
            )

        # Compute daily summary for this date
        _day_meals = conn.execute(
            "SELECT * FROM meal_logs WHERE user_id = ? AND log_date = ?",
            (user_id, _meal_date.isoformat()),
        ).fetchall()
        _d_total = len(_day_meals)
        _d_green = sum(1 for m in _day_meals if m["color_category"] == "green")
        _d_yellow = sum(1 for m in _day_meals if m["color_category"] == "yellow")
        _d_red = sum(1 for m in _day_meals if m["color_category"] == "red")
        _d_plants = sum(m["plant_servings"] or 0 for m in _day_meals)
        _d_fiber = sum(m["fiber_grams"] or 0 for m in _day_meals)
        _d_water = sum(m["water_glasses"] or 0 for m in _day_meals)
        _d_fv = sum((m["fruit_servings"] or 0) + (m["vegetable_servings"] or 0) for m in _day_meals)

        # Plant score
        _ps_plant = min(40, (_d_plants / 10) * 40)
        _ps_fv = min(30, (_d_fv / 5) * 30)
        _ps_fiber = min(20, (_d_fiber / 30) * 20)
        _ps_color = (_d_green / _d_total * 10) if _d_total > 0 else 0
        _plant_score = round(min(100, _ps_plant + _ps_fv + _ps_fiber + _ps_color))
        _color_ratio = _d_green / _d_total if _d_total > 0 else 0
        _nut_score = round(_plant_score * 0.7 + _color_ratio * 100 * 0.3)

        conn.execute(
            """INSERT OR IGNORE INTO nutrition_daily_summary
               (user_id, summary_date, total_meals, green_count, yellow_count, red_count,
                total_plant_servings, total_fiber_grams, total_water_glasses,
                plant_score, nutrition_score)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (user_id, _meal_date.isoformat(), _d_total, _d_green, _d_yellow, _d_red,
             _d_plants, _d_fiber, _d_water, _plant_score, _nut_score),
        )

        _meal_date += timedelta(days=1)

    # ════════════════════════════════════════════════════════════════════════
    # PHASE 3: CALORIE TRACKING & DIET ASSESSMENT DATA
    # ════════════════════════════════════════════════════════════════════════

    # ── Food Log Items (from food_database) ──────────────────────────────
    print("Creating calorie tracking food log data...")

    _food_rows = conn.execute(
        "SELECT id, name, category, calories, protein_g, carbs_g, fat_g, fiber_g, color_category FROM food_database"
    ).fetchall()
    _foods_by_cat = {}
    for _fr in _food_rows:
        cat = _fr["category"]
        if cat not in _foods_by_cat:
            _foods_by_cat[cat] = []
        _foods_by_cat[cat].append(dict(_fr))

    # Last 60 days of calorie tracking (Month 10-12)
    _cal_start = END_DATE - timedelta(days=60)
    _cal_date = _cal_start

    while _cal_date <= END_DATE:
        _ct = (_cal_date - _cal_start).days / 60.0

        if random.random() > min(0.95, 0.85 + _ct * 0.1):
            _cal_date += timedelta(days=1)
            continue

        _day_cal = 0
        _day_pro = 0
        _day_carb = 0
        _day_fat = 0
        _day_fiber = 0
        _day_items = 0

        for _mtype in ["breakfast", "lunch", "dinner", "snack"]:
            if _mtype == "snack" and random.random() < 0.3:
                continue

            if _mtype == "breakfast":
                _picks = random.sample(_foods_by_cat.get("fruits", [])[:5], min(1, len(_foods_by_cat.get("fruits", [])[:5])))
                _picks += random.sample(_foods_by_cat.get("grains", [])[:5], min(1, len(_foods_by_cat.get("grains", [])[:5])))
            elif _mtype == "lunch":
                _picks = random.sample(_foods_by_cat.get("vegetables", [])[:8], min(2, len(_foods_by_cat.get("vegetables", [])[:8])))
                _picks += random.sample(_foods_by_cat.get("legumes", [])[:5], min(1, len(_foods_by_cat.get("legumes", [])[:5])))
            elif _mtype == "dinner":
                _picks = random.sample(_foods_by_cat.get("vegetables", [])[:8], min(1, len(_foods_by_cat.get("vegetables", [])[:8])))
                if random.random() < 0.5:
                    _picks += random.sample(_foods_by_cat.get("fish_seafood", [])[:5], min(1, len(_foods_by_cat.get("fish_seafood", [])[:5])))
                else:
                    _picks += random.sample(_foods_by_cat.get("meat", [])[:5], min(1, len(_foods_by_cat.get("meat", [])[:5])))
                _picks += random.sample(_foods_by_cat.get("grains", [])[:5], min(1, len(_foods_by_cat.get("grains", [])[:5])))
            else:
                _cat_choice = random.choice(["fruits", "nuts_seeds", "dairy"])
                _picks = random.sample(_foods_by_cat.get(_cat_choice, [])[:5], min(1, len(_foods_by_cat.get(_cat_choice, [])[:5])))

            for _food in _picks:
                _srv = round(random.choice([0.5, 1.0, 1.0, 1.0, 1.5, 2.0]), 1)
                _item_cal = round(_food["calories"] * _srv, 1)
                _item_pro = round(_food["protein_g"] * _srv, 1)
                _item_carb = round(_food["carbs_g"] * _srv, 1)
                _item_fat = round(_food["fat_g"] * _srv, 1)
                _item_fib = round(_food["fiber_g"] * _srv, 1)

                conn.execute(
                    """INSERT INTO food_log_items
                       (user_id, food_id, log_date, meal_type, servings,
                        calories, protein_g, carbs_g, fat_g, fiber_g)
                       VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (user_id, _food["id"], _cal_date.isoformat(), _mtype, _srv,
                     _item_cal, _item_pro, _item_carb, _item_fat, _item_fib),
                )

                _day_cal += _item_cal
                _day_pro += _item_pro
                _day_carb += _item_carb
                _day_fat += _item_fat
                _day_fiber += _item_fib
                _day_items += 1

        if _day_items > 0:
            conn.execute(
                """INSERT OR IGNORE INTO calorie_daily_summary
                   (user_id, summary_date, total_calories, total_protein_g,
                    total_carbs_g, total_fat_g, total_fiber_g, total_items)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (user_id, _cal_date.isoformat(), round(_day_cal, 1),
                 round(_day_pro, 1), round(_day_carb, 1), round(_day_fat, 1),
                 round(_day_fiber, 1), _day_items),
            )

        _cal_date += timedelta(days=1)

    # ── Diet Assessments (2 assessments) ─────────────────────────────────
    print("Creating diet assessments...")
    import json as _json

    # Early: Standard American Diet, HEI ~31
    _early_components = {
        "total_fruits": 2, "whole_fruits": 1, "total_vegetables": 2,
        "greens_beans": 1, "whole_grains": 1, "dairy": 5,
        "total_protein": 4, "seafood_plant_protein": 1, "fatty_acids": 2,
        "refined_grains": 3, "sodium": 2, "added_sugars": 4, "saturated_fats": 3,
    }
    conn.execute(
        """INSERT OR IGNORE INTO diet_assessments
           (user_id, assessment_date, diet_type, hei_score, component_scores, answers)
           VALUES (?,?,?,?,?,?)""",
        (user_id, "2025-05-01", "standard_american", 31,
         _json.dumps(_early_components), _json.dumps([2, 2, 2, 0, 3, 3, 1, 2, 1, 2, 2, 3])),
    )

    # Late: Flexitarian, HEI ~72
    _late_components = {
        "total_fruits": 4, "whole_fruits": 4, "total_vegetables": 4,
        "greens_beans": 4, "whole_grains": 8, "dairy": 7,
        "total_protein": 5, "seafood_plant_protein": 4, "fatty_acids": 8,
        "refined_grains": 6, "sodium": 5, "added_sugars": 7, "saturated_fats": 6,
    }
    conn.execute(
        """INSERT OR IGNORE INTO diet_assessments
           (user_id, assessment_date, diet_type, hei_score, component_scores, answers)
           VALUES (?,?,?,?,?,?)""",
        (user_id, "2026-01-15", "flexitarian", 72,
         _json.dumps(_late_components), _json.dumps([0, 0, 0, 2, 1, 0, 0, 0, 3, 0, 0, 1])),
    )

    # ════════════════════════════════════════════════════════════════════════
    # PHASE 4: Daily Growth — Meditation, Quotes & Mindfulness
    # ════════════════════════════════════════════════════════════════════════
    print("Phase 4: Daily Growth...")

    # Meditation sessions — ~40 sessions over last 60 days
    # Maria started meditating around month 5, became consistent by month 8+
    _med_types = ["guided", "unguided", "breathing", "body_scan", "walking"]
    _med_sessions = 0
    for day_offset in range(60, -1, -1):
        d = date.today() - timedelta(days=day_offset)
        # ~65% probability of meditating on any given day in recent months
        if random.random() < 0.65:
            med_type = random.choice(_med_types[:3]) if day_offset > 30 else random.choice(_med_types)
            duration = random.choice([5, 5, 10, 10, 10, 15, 15, 20, 20, 25, 30])
            # Mood generally improves after meditation
            mood_before = random.choice([1, 2, 2, 3, 3, 3, 4])
            mood_after = min(5, mood_before + random.choice([0, 1, 1, 1, 2]))
            notes_pool = [
                None, None, None,  # most sessions no notes
                "Felt restless at first, then settled",
                "Good session, mind was clear",
                "Difficult to focus today",
                "Deep calm after",
                "Short but effective",
                "Morning sunlight meditation on the balcony",
            ]
            conn.execute(
                """INSERT INTO meditation_sessions
                   (user_id, session_date, duration_minutes, meditation_type,
                    mood_before, mood_after, notes)
                   VALUES (?,?,?,?,?,?,?)""",
                (user_id, d.isoformat(), duration, med_type,
                 mood_before, mood_after, random.choice(notes_pool)),
            )
            _med_sessions += 1
    print(f"  - {_med_sessions} meditation sessions (60 days)")

    # Quote interactions — ~20 shown quotes, some with reflections and favorites
    _quote_count = 0
    _fav_count = 0
    _refl_count = 0
    for day_offset in range(25, -1, -1):
        d = date.today() - timedelta(days=day_offset)
        if random.random() < 0.80:  # 80% of days she views the quote
            qi = random.randint(0, 59)
            is_fav = 1 if random.random() < 0.15 else 0
            refl = None
            if random.random() < 0.25:
                reflections = [
                    "This resonates deeply with where I am right now.",
                    "I need to remember this on hard days.",
                    "Simple but powerful. I wrote this in my journal too.",
                    "This is exactly what I needed to hear today.",
                    "I shared this with my running group.",
                ]
                refl = random.choice(reflections)
                _refl_count += 1
            conn.execute(
                """INSERT OR IGNORE INTO quote_interactions
                   (user_id, quote_index, shown_date, is_favorite, reflection_text)
                   VALUES (?,?,?,?,?)""",
                (user_id, qi, d.isoformat(), is_fav, refl),
            )
            _quote_count += 1
            if is_fav:
                _fav_count += 1
    print(f"  - {_quote_count} quote interactions ({_fav_count} favorites, {_refl_count} reflections)")

    # Nudge shown — ~25 acknowledged nudges
    _nudge_count = 0
    for day_offset in range(30, -1, -1):
        d = date.today() - timedelta(days=day_offset)
        if random.random() < 0.80:
            ni = random.randint(0, 34)
            ack = 1 if random.random() < 0.85 else 0
            conn.execute(
                """INSERT OR IGNORE INTO nudge_shown
                   (user_id, nudge_index, shown_date, acknowledged)
                   VALUES (?,?,?,?)""",
                (user_id, ni, d.isoformat(), ack),
            )
            _nudge_count += 1
    print(f"  - {_nudge_count} mindfulness nudges shown")

    # Daily growth state — set for today
    from services.growth_service import get_meditation_streak as _get_streak
    _streak = _get_streak(user_id)
    conn.execute(
        """INSERT OR REPLACE INTO daily_growth_state
           (user_id, current_quote_index, current_nudge_index,
            state_date, meditation_streak)
           VALUES (?,?,?,?,?)""",
        (user_id, random.randint(0, 59), random.randint(0, 34),
         date.today().isoformat(), _streak),
    )

    # ════════════════════════════════════════════════════════════════════════
    # PHASE 5: SIBO & FODMAP Tracker
    # ════════════════════════════════════════════════════════════════════════
    print("Phase 5: SIBO & FODMAP Tracker...")

    import json as _sjson

    # ── Symptom logs: ~45 days over last 60 days ──
    # Maria has IBS-like symptoms; they improve over time with Low-FODMAP diet
    _sym_count = 0
    for day_offset in range(60, -1, -1):
        d = date.today() - timedelta(days=day_offset)
        if random.random() < 0.75:  # ~75% logging rate
            # Symptoms improve over time (higher early, lower later)
            t = 1.0 - (day_offset / 60.0)  # 0=60 days ago, 1=today
            base_reduction = t * 3  # up to 3 points improvement
            bloating = max(0, min(10, round(random.gauss(6 - base_reduction, 1.5))))
            pain = max(0, min(10, round(random.gauss(4.5 - base_reduction * 0.8, 1.5))))
            gas = max(0, min(10, round(random.gauss(5.5 - base_reduction, 1.2))))
            diarrhea = max(0, min(3, round(random.gauss(1.5 - base_reduction * 0.3, 0.6))))
            constipation = max(0, min(3, round(random.gauss(0.8 - base_reduction * 0.1, 0.4))))
            nausea = max(0, min(10, round(random.gauss(3 - base_reduction * 0.6, 1.2))))
            fatigue = max(0, min(10, round(random.gauss(5 - base_reduction * 0.7, 1.5))))
            # Normalize 0-3 scale to 0-10 for overall
            norm_vals = [bloating, pain, gas, diarrhea * 10 / 3, constipation * 10 / 3, nausea, fatigue]
            overall = max(0, min(10, round(sum(norm_vals) / len(norm_vals))))
            sym_notes = random.choice([
                None, None, None, None,
                "Worse after lunch", "Better morning", "Ate late last night",
                "Stressful day at work", "Slept poorly", "Good day overall",
            ])
            conn.execute(
                """INSERT OR REPLACE INTO sibo_symptom_logs
                   (user_id, log_date, bloating, abdominal_pain, gas, diarrhea,
                    constipation, nausea, fatigue, overall_score, notes)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (user_id, d.isoformat(), bloating, pain, gas, diarrhea,
                 constipation, nausea, fatigue, overall, sym_notes),
            )
            _sym_count += 1
    print(f"  - {_sym_count} symptom logs (60 days)")

    # ── Food logs: ~120 entries over last 60 days ──
    _food_count = 0
    _low_foods = [
        ("Rice, white", "grains", 190, "g cooked", "low", "[]"),
        ("Chicken breast", "protein", 120, "g", "low", "[]"),
        ("Carrot", "vegetables", 75, "g", "low", "[]"),
        ("Banana, firm (unripe)", "fruits", 1, "medium", "low", "[]"),
        ("Eggs", "protein", 2, "large", "low", "[]"),
        ("Spinach", "vegetables", 75, "g", "low", "[]"),
        ("Salmon", "protein", 120, "g", "low", "[]"),
        ("Potato", "vegetables", 1, "medium", "low", "[]"),
        ("Oats", "grains", 52, "g dry", "low", "[]"),
        ("Blueberries", "fruits", 40, "g", "low", "[]"),
        ("Lactose-free milk", "dairy", 250, "mL", "low", "[]"),
        ("Tofu (firm)", "protein", 170, "g", "low", "[]"),
        ("Quinoa", "grains", 155, "g cooked", "low", "[]"),
        ("Orange", "fruits", 1, "medium", "low", "[]"),
    ]
    _high_foods = [
        ("Garlic", "vegetables", 1, "clove", "high", '["fructans"]'),
        ("Onion", "vegetables", 30, "g", "high", '["fructans"]'),
        ("Wheat bread", "grains", 1, "slice", "high", '["fructans"]'),
        ("Apple", "fruits", 1, "medium", "high", '["fructose","sorbitol"]'),
        ("Cow's milk", "dairy", 250, "mL", "high", '["lactose"]'),
        ("Honey", "condiments", 7, "g", "high", '["fructose"]'),
        ("Mushrooms", "vegetables", 75, "g", "high", '["mannitol"]'),
        ("Wheat pasta", "grains", 145, "g cooked", "high", '["fructans"]'),
    ]
    _meals = ["breakfast", "lunch", "dinner", "snack"]
    for day_offset in range(60, -1, -1):
        d = date.today() - timedelta(days=day_offset)
        # Log 2-3 meals per day with ~80% probability
        if random.random() < 0.80:
            n_meals = random.choice([2, 2, 3, 3])
            chosen_meals = random.sample(_meals[:3], min(n_meals, 3))
            if n_meals > 3:
                chosen_meals.append("snack")
            for meal in chosen_meals:
                # Early days: mix of high/low; later: mostly low FODMAP
                t = 1.0 - (day_offset / 60.0)
                if random.random() < (0.15 + 0.6 * t):  # more low-FODMAP over time
                    food = random.choice(_low_foods)
                else:
                    food = random.choice(_high_foods)
                name, cat, srv, unit, rating, groups = food
                conn.execute(
                    """INSERT INTO sibo_food_logs
                       (user_id, log_date, meal_type, food_name, food_category,
                        serving_size, serving_unit, fodmap_rating, fodmap_groups)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (user_id, d.isoformat(), meal, name, cat, srv, unit, rating, groups),
                )
                _food_count += 1
    print(f"  - {_food_count} food log entries (60 days)")

    # ── Phase history: 3 phases ──
    # Elimination started 45 days ago, reintroduction started 14 days ago
    elim_start = (date.today() - timedelta(days=45)).isoformat()
    elim_end = (date.today() - timedelta(days=14)).isoformat()
    reintro_start = (date.today() - timedelta(days=14)).isoformat()

    conn.execute(
        """INSERT INTO sibo_fodmap_phase (user_id, phase, started_date, ended_date)
           VALUES (?,?,?,?)""",
        (user_id, "elimination", elim_start, elim_end),
    )
    conn.execute(
        """INSERT INTO sibo_fodmap_phase (user_id, phase, started_date)
           VALUES (?,?,?)""",
        (user_id, "reintroduction", reintro_start),
    )
    print("  - 2 phase records (elimination + reintroduction)")

    # ── Reintroduction challenges: 3 completed ──
    _challenge_data = [
        ("fructans", "Wheat bread", 10, "not_tolerated",
         '{"bloating":3,"abdominal_pain":2,"gas":4}',
         '{"bloating":5,"abdominal_pain":4,"gas":6}',
         '{"bloating":7,"abdominal_pain":5,"gas":7}'),
        ("lactose", "Cow's milk", 7, "partial",
         '{"bloating":2,"abdominal_pain":1,"gas":2}',
         '{"bloating":3,"abdominal_pain":2,"gas":3}',
         '{"bloating":4,"abdominal_pain":3,"gas":4}'),
        ("fructose", "Honey", 4, "tolerated",
         '{"bloating":1,"abdominal_pain":0,"gas":1}',
         '{"bloating":1,"abdominal_pain":1,"gas":1}',
         '{"bloating":2,"abdominal_pain":1,"gas":2}'),
    ]
    for group, food, days_ago, tolerance, d1, d2, d3 in _challenge_data:
        c_start = (date.today() - timedelta(days=days_ago)).isoformat()
        c_end = (date.today() - timedelta(days=days_ago - 3)).isoformat()
        c_washout = (date.today() - timedelta(days=days_ago - 6)).isoformat()
        conn.execute(
            """INSERT INTO sibo_reintro_challenges
               (user_id, fodmap_group, challenge_food, start_date, end_date,
                day1_symptoms, day2_symptoms, day3_symptoms, washout_end, tolerance)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (user_id, group, food, c_start, c_end, d1, d2, d3, c_washout, tolerance),
        )
    print("  - 3 reintroduction challenges (fructans=not_tolerated, lactose=partial, fructose=tolerated)")

    # ── User state ──
    conn.execute(
        """INSERT OR REPLACE INTO sibo_user_state
           (user_id, active_diet, current_phase, phase_start,
            total_symptom_logs, total_food_logs)
           VALUES (?,?,?,?,?,?)""",
        (user_id, "low_fodmap", "reintroduction", reintro_start,
         _sym_count, _food_count),
    )
    print(f"  - User state: low_fodmap diet, reintroduction phase")

    conn.commit()

    # ════════════════════════════════════════════════════════════════════════
    # WEARABLE WHEEL — 30 days of simulated wearable measurements
    # ════════════════════════════════════════════════════════════════════════
    print("Phase 6: Wearable Wheel measurements...")
    from datetime import datetime as _dt
    from config.wearable_wheel_data import WEARABLE_METRIC_SPECS
    _wearable_count = 0

    # Maria's wearable data: Whoop Band + Oura Ring + manual BP/weight/CGM
    # 30 days with cardiometabolic + sleep risk patterns
    _wearable_base = {
        # Heart & Metabolism
        "resting_heart_rate_bpm": (67, 6, "Whoop Band"),
        "heart_rate_variability_ms": (31, 9, "Whoop Band"),
        "steps_count": (6400, 2100, "Whoop Band"),
        "respiratory_rate_bpm": (17.1, 1.2, "Oura Ring"),
        "arrhythmia_alert_afib": (0, 0, "Whoop Band"),
        "kilojoule_expended": (1850, 320, "Whoop Band"),
        # System Wide
        "overnight_spo2_avg_pct": (93.8, 1.4, "Oura Ring"),
        "overnight_spo2_nadir_pct": (86.0, 2.0, "Oura Ring"),
        "body_temperature_deviation_c": (0.30, 0.14, "Oura Ring"),
        "recovery_score": (58, 12, "Whoop Band"),
        "spo2_pct": (94.5, 1.2, "Oura Ring"),
        # Brain Health
        "sleep_efficiency_pct": (81, 6, "Oura Ring"),
        "sleep_consistency_pct": (69, 9, "Oura Ring"),
        "total_slow_wave_sleep_time_min": (62, 14, "Oura Ring"),
        "total_rem_sleep_time_min": (74, 16, "Oura Ring"),
        "sleep_debt_hours": (2.6, 0.9, "Whoop Band"),
        "sleep_disturbance_count": (9, 3, "Oura Ring"),
        "total_awake_time_min": (61, 18, "Oura Ring"),
        "sleep_latency_min": (28, 8, "Oura Ring"),
        "sleep_cycle_count": (4, 1, "Oura Ring"),
        "sleep_performance_pct": (72, 8, "Whoop Band"),
    }
    # Optional metrics (every few days)
    _wearable_optional = {
        "systolic_bp_mmhg": (136, 8, "Withings BPM Connect Pro"),
        "diastolic_bp_mmhg": (86, 6, "Withings BPM Connect Pro"),
        "body_weight_kg": (78.0, 0.7, "InBody H40 Home Scale"),
        "cgm_avg_glucose_mgdl": (112, 8, "CGM FreeStyle Libre"),
        "cgm_time_in_range_pct": (78, 8, "CGM FreeStyle Libre"),
    }

    for _day_off in range(30):
        _meas_date = (date.today() - timedelta(days=29 - _day_off))
        _meas_ts = f"{_meas_date.isoformat()}T07:00:00"

        for _mc, (_base, _noise, _src) in _wearable_base.items():
            _val = _base + random.gauss(0, _noise)
            # Clamp to reasonable ranges
            if _mc == "arrhythmia_alert_afib":
                _val = 0
            elif "pct" in _mc:
                _val = max(0, min(100, _val))
            elif _mc == "steps_count":
                _val = max(1000, round(_val))
            elif _mc == "sleep_debt_hours":
                _val = max(0, _val)
            elif _mc.endswith("_count"):
                _val = max(0, round(_val))
            elif _mc.endswith("_min") and "time" in _mc:
                _val = max(0, round(_val))

            _unit = WEARABLE_METRIC_SPECS.get(_mc, {}).get("unit", "")
            try:
                conn.execute(
                    """INSERT OR REPLACE INTO wearable_measurements
                       (user_id, metric_code, metric_name, value, unit, measured_at, source)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (user_id, _mc, WEARABLE_METRIC_SPECS.get(_mc, {}).get("label", _mc),
                     round(_val, 2), _unit, _meas_ts, _src),
                )
                _wearable_count += 1
            except Exception:
                pass

        # Optional metrics every 3 days
        if _day_off % 3 == 0:
            for _mc, (_base, _noise, _src) in _wearable_optional.items():
                _val = _base + random.gauss(0, _noise)
                _unit = WEARABLE_METRIC_SPECS.get(_mc, {}).get("unit", "")
                try:
                    conn.execute(
                        """INSERT OR REPLACE INTO wearable_measurements
                           (user_id, metric_code, metric_name, value, unit, measured_at, source)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (user_id, _mc, WEARABLE_METRIC_SPECS.get(_mc, {}).get("label", _mc),
                         round(_val, 2), _unit, _meas_ts, _src),
                    )
                    _wearable_count += 1
                except Exception:
                    pass

    conn.commit()
    print(f"  - {_wearable_count} wearable measurements (30 days, Whoop + Oura + manual)")

    conn.close()

    # Seed a realistic DEXA scan so the DXA osteoporosis / fragility-fracture
    # score renders with real data on the organ-health dashboard.
    try:
        from services.body_metrics_service import save_dexa_scan
        dexa_payload = {k: v for k, v in MARIA_DEXA_SCAN.items() if k != "scan_date"}
        save_dexa_scan(user_id, MARIA_DEXA_SCAN["scan_date"], **dexa_payload)
        print(f"  - 1 DEXA scan (T-score {MARIA_DEXA_SCAN['t_score']}, osteopenia band)")
    except Exception as exc:
        print(f"  - DEXA scan seed skipped: {exc}")

    print("")
    print("=" * 60)
    print("  DEMO DATA SEEDED SUCCESSFULLY")
    print("=" * 60)
    print("")
    print("  Patient: Maria Silva, 43")
    print("  Username: maria.silva")
    print("  Password: demo123456")
    print("")
    print("  Journey: Feb 2025 - Feb 2026 (12 months)")
    print("  Weight: 105 kg - 78 kg (-27 kg)")
    print("  Milestone: 21K Half-Marathon completed!")
    print("")
    print("  Data created:")
    print("  - 13 wheel assessments (monthly)")
    print("  - 18 habits with daily logs + implementation intentions")
    print("  - ~330 daily check-ins with journals")
    print("  - 11 SMART-EST goals (9 completed, 2 active)")
    print("  - 14 weekly reviews")
    print("  - 8 coaching conversation messages")
    print("  - Stage of Change progression per pillar")
    print("  - LifeCoin transaction history")
    print("  - 6 sample daily AI insights")
    print("  - User journey (Level 7 — Lifestyle Master)")
    print("  - 3 future self letters (delivered)")
    print("  - 53 body metrics entries (weight/waist/hip/bf%)")
    print("  - 24 weekly challenges (8 weeks)")
    print("  - 5 adopted protocols with completion logs")
    print(f"  - ~{_exercise_count} exercise logs (running, walking, strength, yoga)")
    print("  - Weekly exercise summaries with scores")
    print("  - ~130 biomarker results (33 markers x 4 panels, organ-score ready)")
    print("  - Clinical registry: 4 active diagnoses, 5 active interventions, 5 confirmed tests")
    print("  - ~250 sleep logs with scores")
    print("  - 1 chronotype assessment (Bear)")
    print("  - ~80 fasting sessions (12:12 -> 16:8)")
    print("  - ~500 meal logs with nutrition summaries")
    print("")
    print("  PHASE 3 FEATURES:")
    print("  - ~200 calorie tracking food log entries (60 days)")
    print("  - ~55 calorie daily summaries")
    print("  - 2 diet pattern assessments (Standard American -> Flexitarian)")
    print("")
    print("  PHASE 4 FEATURES:")
    print("  - ~40 meditation sessions (60 days, 5 types)")
    print("  - ~20 quote interactions with reflections and favorites")
    print("  - ~25 mindfulness nudges shown")
    print("")
    print("  PHASE 5 FEATURES:")
    print("  - ~45 SIBO symptom logs (60 days, improving over time)")
    print("  - ~120 FODMAP food log entries (low/high FODMAP mix)")
    print("  - 2 FODMAP phase records (elimination + reintroduction)")
    print("  - 3 reintroduction challenges (fructans, lactose, fructose)")
    print("  - SIBO user state (low_fodmap diet, reintroduction phase)")
    print("")
    print("  ALL PHASES:")
    print("  - Biomarker Dashboard (40 markers, reference + critical threshold classification)")
    print("  - Sleep Tracker (PSQI scoring, chronotype quiz)")
    print("  - Fasting Tracker (metabolic zones, timer)")
    print("  - Nutrition Logger (plant score, Noom-style colors)")
    print("  - Recovery Dashboard (composite score)")
    print("  - Calorie Tracker (USDA food database, macro tracking)")
    print("  - Diet Pattern Assessment (HEI-2020, Diet ID)")
    print("  - Daily Growth (meditation, quotes, mindfulness nudges)")
    print("  - SIBO & FODMAP Tracker (symptom log, food diary, phases, correlations)")
    print("")
    print("  Login at http://localhost:8501 to explore!")
    print("")
    print("  NOTE: Only the demo account (maria.silva) was reset.")
    print("  Any other accounts you created are preserved.")
    print("=" * 60)


# ── Helper: Pillar-specific notes for assessments ───────────────────────────
def _get_pillar_note(pillar_id: int, month: int) -> str:
    notes = {
        1: {
            0: "McDonald's, pizza, chips, soda. Can't remember the last time I ate a vegetable. Eating is emotional, not nutritional. Binge at night.",
            2: "Started adding salads to lunch. Still struggling with dinner — kids want pizza.",
            4: "Cooking 3-4 times a week now. Discovered I love stir-fry and grain bowls.",
            6: "Plant-predominant most days. Lost my craving for fast food. Energy is noticeably better.",
            8: "Whole-food diet feels natural now. Learning about fueling for long runs.",
            10: "Nutrition is dialed in. Meal prep on Sundays. Kids are eating better too.",
            12: "Fueling a half-marathon with whole foods. My relationship with food has completely transformed.",
        },
        2: {
            0: "Zero movement. Get winded walking up stairs. Haven't exercised in 15 years. 105 kg. Body feels like a prison.",
            2: "Walking 15-20 min daily. Legs are sore but I'm showing up.",
            4: "Started Couch-to-5K! Can run 1-2 min intervals. Lost 12 kg.",
            6: "Running 20-25 min continuously! Completed C25K. -20 kg.",
            8: "First 5K race: 32 minutes! Now training for 10K. -28 kg.",
            10: "Completed 10K in 1:05:00. Training for half-marathon. -35 kg.",
            12: "HALF-MARATHON COMPLETED! 21.1 km in 2:15:00. -40 kg. I am a runner.",
        },
        3: {
            0: "3-4 hours of broken sleep. Scrolling phone until 2 AM. Night anxiety. Wake up exhausted. Coffee all day just to function.",
            2: "Trying to get to bed by 11 PM. Screen cutoff helping. 5-6 hours now.",
            4: "Consistent 6-6.5 hours. Morning runs make me tired in a good way.",
            6: "7 hours most nights. Sleep quality improving. Fewer wake-ups.",
            8: "7-8 hours consistently. Bedtime routine is solid. Wake up feeling rested.",
            10: "Sleep is excellent. 7.5-8 hours. Recovery after long runs is great.",
            12: "Sleep is my superpower now. 10:30 PM lights out, 6 AM wake up. Consistent.",
        },
        4: {
            0: "Constant anxiety. Panic attacks at night. Overwhelmed by everything. Cry in the shower. Only coping tools are food, wine, and cigarettes.",
            2: "Started deep breathing exercises. Helps a little during cravings.",
            5: "Began meditation app. 5 minutes feels hard but I'm trying.",
            7: "Meditating 10-15 min daily. Running is incredible stress relief too.",
            9: "15-20 min meditation every morning. Stress feels manageable now. Therapy helped.",
            11: "Meditation is non-negotiable. I handle stress without food, cigarettes, or wine.",
            12: "Inner peace I never thought possible. Gratitude practice changed my perspective on everything.",
        },
        5: {
            0: "Completely isolated. Haven't seen friends in months. Ashamed of my body. Avoid social events. Husband and I barely talk. Kids see a sad mother.",
            3: "Reconnected with my friend Ana. We walk together sometimes.",
            5: "Joined the running group! Made 3 new friends. Ana runs with me too.",
            7: "Running community is my second family. Family dinners are phone-free now.",
            9: "Husband started running too! Kids are proud of me. Deep friendships.",
            11: "My support network is incredible. I'm now encouraging others to start their journey.",
            12: "My kids cheered at the finish line. Husband ran the last km with me. Friendships are deep and real.",
        },
        6: {
            0: "Half a pack of cigarettes daily. Wine every evening, sometimes a full bottle alone. 6+ coffees a day. Using substances to survive, not live.",
            2: "Using nicotine patches. Cut to 2-3 cigarettes/day. Wine only on weekends.",
            4: "Smoke-free for 6 weeks! Alcohol only on weekends, 1-2 glasses.",
            6: "3 months smoke-free. Alcohol reduced to 1-2 times per month.",
            8: "No smoking at all. Occasional glass of wine at social events — that's it.",
            10: "Clean living feels amazing. Wine once or twice a month with friends. Zero tobacco.",
            12: "Almost a year smoke-free. Occasional wine is a choice, not a need. Total freedom.",
        },
    }

    pillar_notes = notes.get(pillar_id, {})
    # Find the closest month note
    closest_month = max((m for m in pillar_notes if m <= month), default=0)
    return pillar_notes.get(closest_month, "")


# ── Helper: Generate daily journal entries based on phase ────────────────────
def _get_daily_entry(month: int, t: float, weekday: int) -> tuple:
    # Phase 0: Rock bottom (month 1)
    journals_rock_bottom = [
        "Couldn't get out of bed until noon. Smoked on the balcony while the kids were at school. Hate myself.",
        "Ate McDonald's for the third time this week. Couldn't even look at myself in the mirror after.",
        "Woke up at 3 AM with heart racing. Anxiety. Googled 'can pre-diabetes kill you.' Couldn't go back to sleep.",
        "My daughter asked me to play at the park. I said I was tired. I saw the disappointment in her eyes.",
        "Drank a bottle of wine alone watching TV. Smoked half a pack. This is not who I want to be.",
        "Weighed myself. 105.2 kg. Stepped off and cried in the bathroom so the kids wouldn't hear.",
        "Another day of doing nothing. Fast food for lunch and dinner. 4 hours of sleep. I'm drowning.",
        "My husband tried to talk to me about my health. I snapped at him. Slept on the couch. Feel terrible.",
    ]
    # Phase 1: First painful steps (month 2-3)
    journals_early = [
        "Withdrawal is hell. Hands shaking. Ate everything in the fridge. But I didn't smoke.",
        "Forced myself to walk 10 minutes. Came home sweating and out of breath. This is humiliating.",
        "Made a salad. It was terrible. But I ate it instead of ordering pizza. That counts, right?",
        "Kids asked why I'm cooking more. Told them we're getting healthy together. They looked confused.",
        "Cravings hit at 9 PM. Drank tea, did breathing exercises, paced the kitchen. Didn't smoke. Barely.",
        "Went to bed at 11. Stared at the ceiling. Mind racing. But at least the phone wasn't in my hand.",
        "Walked in the rain. Cold, wet, miserable. But I showed up. That's more than yesterday me would do.",
        "Scale moved down 0.5 kg. Cried. Every gram matters right now.",
        "Terrible sleep. Maybe 4 hours. But I still walked this morning. Exhausted but present.",
        "Ate well all day then binged on chips at midnight. Two steps forward, one step back.",
    ]
    journals_mid = [
        "Great run this morning! Getting faster. Can't believe I'm saying the word 'run' about myself.",
        "Meditation was peaceful today. 10 minutes flew by. My mind is getting quieter.",
        "Cooked an amazing grain bowl. Who am I becoming? I don't recognize myself in the best way.",
        "Running group Saturday was the highlight of my week. These people don't know the old me.",
        "Lost another kg. Blood pressure is dropping too. The numbers are finally moving.",
        "Slept 7 hours straight! First time in years. Woke up and didn't feel like death.",
        "My friend Ana told me I'm inspiring her to start walking. Me. Inspiring someone.",
        "Practiced gratitude today. 3 months ago I had nothing to write. Now I can't stop.",
        "Long run felt strong. 8K done! My legs know what to do now.",
        "Kids joined me for a walk after school. My son said 'Mom, you're fast now.' My heart.",
    ]
    journals_late = [
        "Amazing run today. Training for the half-marathon is going great. I am an athlete.",
        "15 minutes of meditation. Felt completely present. The noise in my head is gone.",
        "Recovery day. Stretching, healthy food, early bed. Self-care is not selfish. It took me 43 years to learn that.",
        "Running group did 12K together. We laughed the whole time. These are my people.",
        "My doctor said my blood work is 'textbook perfect.' She hugged me. We both cried.",
        "Family movie night. Present, healthy, happy. This is what I almost lost.",
        "Long run 16K. Hard but I finished strong. Half-marathon here I come.",
        "Looked at photos from a year ago. 105 kg, dead eyes, cigarette in hand. I want to hug that woman.",
        "Taught my daughter about whole foods. She made a smoothie bowl! The cycle is breaking.",
        "Quiet morning meditation by the window. I'm grateful for every single breath.",
    ]

    wins_rock_bottom = ["I got out of bed", "I ate something", "I didn't give up completely", "I'm still here"]
    wins_early = ["Didn't smoke today", "Walked even though I didn't want to", "Ate one healthy meal", "Went to bed before midnight", "Drank water instead of wine"]
    wins_mid = ["Ran 20+ minutes", "Meditated without falling asleep", "Cooked from scratch", "Connected with a friend", "7h sleep"]
    wins_late = ["Strong training run", "Deep meditation", "Whole-food day", "Quality time with family", "I feel alive"]

    challenges_rock_bottom = ["Everything", "Getting out of bed", "Not smoking", "Self-hatred", "Feeling hopeless"]
    challenges_early = ["Cravings are brutal", "No motivation", "Body aches from walking", "Can't sleep", "Emotional eating", "Withdrawal symptoms"]
    challenges_mid = ["Tired after run", "Busy schedule", "Weekend temptation", "Self-doubt creeps back", "Weather disrupted plans"]
    challenges_late = ["Muscle soreness from training", "Balancing training with family", "Rest day guilt", "Pre-race nerves", "Wanting to do too much too fast"]

    gratitudes_rock_bottom = ["My kids exist", "I woke up today", "The doctor was honest with me", "I still have a chance"]
    gratitudes_early = ["My kids", "Another day to try", "The patch is working", "My legs can still walk", "Hot tea"]
    gratitudes_mid = ["My running shoes", "Morning sunlight", "Meditation practice", "My running friends", "Feeling strong"]
    gratitudes_late = ["My strong body", "My community", "My family", "This incredible journey", "Being alive and healthy and FREE"]

    if month <= 1:
        journal = random.choice(journals_rock_bottom)
        win = random.choice(wins_rock_bottom)
        challenge = random.choice(challenges_rock_bottom)
        gratitude = random.choice(gratitudes_rock_bottom)
    elif month <= 3:
        journal = random.choice(journals_early)
        win = random.choice(wins_early)
        challenge = random.choice(challenges_early)
        gratitude = random.choice(gratitudes_early)
    elif month <= 8:
        journal = random.choice(journals_mid)
        win = random.choice(wins_mid)
        challenge = random.choice(challenges_mid)
        gratitude = random.choice(gratitudes_mid)
    else:
        journal = random.choice(journals_late)
        win = random.choice(wins_late)
        challenge = random.choice(challenges_late)
        gratitude = random.choice(gratitudes_late)

    return journal, win, challenge, gratitude


if __name__ == "__main__":
    main()
