import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "lifestyle_medicine.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db():
    conn = get_connection()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    _migrate(conn)
    conn.close()
    # Seed science foundation data (evidence library + protocols)
    _seed_science_data()


def _migrate(conn):
    """Add columns/tables that may be missing in older databases."""
    migrations = [
        "ALTER TABLE habits ADD COLUMN cue_behavior TEXT",
        "ALTER TABLE habits ADD COLUMN location TEXT",
        "ALTER TABLE habits ADD COLUMN implementation_intention TEXT",
        "ALTER TABLE research_evidence ADD COLUMN journal_tier TEXT",
        "ALTER TABLE research_evidence ADD COLUMN domain TEXT",
        # QRISK3 clinical profile fields
        "ALTER TABLE user_clinical_profile ADD COLUMN ethnicity TEXT DEFAULT 'white'",
        "ALTER TABLE user_clinical_profile ADD COLUMN diabetes_type TEXT DEFAULT 'none'",
        "ALTER TABLE user_clinical_profile ADD COLUMN family_history_chd INTEGER DEFAULT 0",
        "ALTER TABLE user_clinical_profile ADD COLUMN atrial_fibrillation INTEGER DEFAULT 0",
        "ALTER TABLE user_clinical_profile ADD COLUMN rheumatoid_arthritis INTEGER DEFAULT 0",
        "ALTER TABLE user_clinical_profile ADD COLUMN chronic_kidney_disease INTEGER DEFAULT 0",
        "ALTER TABLE user_clinical_profile ADD COLUMN migraine INTEGER DEFAULT 0",
        "ALTER TABLE user_clinical_profile ADD COLUMN sle INTEGER DEFAULT 0",
        "ALTER TABLE user_clinical_profile ADD COLUMN severe_mental_illness INTEGER DEFAULT 0",
        "ALTER TABLE user_clinical_profile ADD COLUMN erectile_dysfunction INTEGER DEFAULT 0",
        "ALTER TABLE user_clinical_profile ADD COLUMN atypical_antipsychotic INTEGER DEFAULT 0",
        "ALTER TABLE user_clinical_profile ADD COLUMN corticosteroid_use INTEGER DEFAULT 0",
        "ALTER TABLE user_clinical_profile ADD COLUMN sbp_variability REAL",
        "ALTER TABLE user_clinical_profile ADD COLUMN cigarettes_per_day INTEGER DEFAULT 0",
        # CHA2DS2-VASc fields
        "ALTER TABLE user_clinical_profile ADD COLUMN congestive_heart_failure INTEGER DEFAULT 0",
        "ALTER TABLE user_clinical_profile ADD COLUMN prior_stroke_tia INTEGER DEFAULT 0",
        "ALTER TABLE user_clinical_profile ADD COLUMN vascular_disease INTEGER DEFAULT 0",
        # CAIDE Dementia Risk fields
        "ALTER TABLE user_clinical_profile ADD COLUMN education_years INTEGER",
        "ALTER TABLE user_clinical_profile ADD COLUMN physical_activity_level TEXT DEFAULT 'active'",
    ]
    # Phase 6: ensure new tables exist for older DBs
    table_migrations = [
        """CREATE TABLE IF NOT EXISTS body_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            log_date TEXT NOT NULL, weight_kg REAL, height_cm REAL,
            waist_cm REAL, hip_cm REAL, body_fat_pct REAL,
            notes TEXT, photo_note TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(user_id, log_date))""",
        """CREATE TABLE IF NOT EXISTS user_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            goal_weight_kg REAL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(user_id))""",
        """CREATE TABLE IF NOT EXISTS garmin_connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            garmin_email TEXT NOT NULL, garmin_token TEXT, last_sync TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(user_id))""",
        # Exercise tracker tables
        """CREATE TABLE IF NOT EXISTS exercise_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            exercise_date TEXT NOT NULL,
            exercise_type TEXT NOT NULL,
            category TEXT NOT NULL,
            duration_min INTEGER NOT NULL CHECK (duration_min > 0),
            intensity TEXT NOT NULL,
            distance_km REAL, calories INTEGER,
            avg_hr INTEGER, max_hr INTEGER,
            rpe INTEGER CHECK (rpe BETWEEN 1 AND 10),
            notes TEXT,
            source TEXT DEFAULT 'manual',
            external_id TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(user_id, exercise_date, external_id))""",
        """CREATE TABLE IF NOT EXISTS exercise_weekly_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            week_start TEXT NOT NULL,
            total_min INTEGER DEFAULT 0, cardio_min INTEGER DEFAULT 0,
            strength_min INTEGER DEFAULT 0, flexibility_min INTEGER DEFAULT 0,
            moderate_min INTEGER DEFAULT 0, vigorous_min INTEGER DEFAULT 0,
            session_count INTEGER DEFAULT 0,
            exercise_score INTEGER CHECK (exercise_score BETWEEN 0 AND 100),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(user_id, week_start))""",
        """CREATE TABLE IF NOT EXISTS strava_connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            strava_athlete_id INTEGER,
            access_token TEXT, refresh_token TEXT,
            token_expires_at INTEGER, last_sync TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(user_id))""",
        # Exercise prescription programs
        """CREATE TABLE IF NOT EXISTS exercise_programs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            level TEXT NOT NULL,
            schedule TEXT NOT NULL,
            goal TEXT NOT NULL DEFAULT 'hypertrophy',
            program_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')))""",
        # Workout set logs (weight, reps, RPE tracking)
        """CREATE TABLE IF NOT EXISTS workout_sets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            workout_date TEXT NOT NULL,
            week_number INTEGER NOT NULL,
            day_number INTEGER NOT NULL,
            split_type TEXT NOT NULL,
            exercise_id TEXT NOT NULL,
            exercise_name TEXT NOT NULL,
            set_number INTEGER NOT NULL,
            prescribed_reps TEXT,
            actual_reps INTEGER,
            weight_kg REAL,
            rpe INTEGER CHECK (rpe BETWEEN 1 AND 10),
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')))""",
        # Cycling training tables (TrainerRoad-style)
        """CREATE TABLE IF NOT EXISTS cycling_profile (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
            ftp_watts INTEGER NOT NULL DEFAULT 200,
            weight_kg REAL,
            athlete_type TEXT DEFAULT 'All-Around',
            goal_event TEXT,
            goal_date TEXT,
            ftp_tested_date TEXT,
            updated_at TEXT NOT NULL DEFAULT (datetime('now')))""",
        """CREATE TABLE IF NOT EXISTS cycling_plan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            phase TEXT NOT NULL,
            start_date TEXT NOT NULL,
            weeks INTEGER NOT NULL,
            days_per_week INTEGER NOT NULL DEFAULT 4,
            tss_per_week INTEGER,
            program_json TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')))""",
        """CREATE TABLE IF NOT EXISTS cycling_ride_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            ride_date TEXT NOT NULL,
            duration_min INTEGER NOT NULL,
            avg_power INTEGER,
            normalized_power INTEGER,
            if_score REAL,
            tss REAL,
            elevation_m INTEGER,
            difficulty_survey INTEGER CHECK (difficulty_survey BETWEEN 1 AND 5),
            workout_id TEXT,
            notes TEXT,
            source TEXT DEFAULT 'manual',
            created_at TEXT NOT NULL DEFAULT (datetime('now')))""",
        """CREATE TABLE IF NOT EXISTS cycling_progression_levels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
            endurance REAL DEFAULT 1.0,
            tempo REAL DEFAULT 1.0,
            sweet_spot REAL DEFAULT 1.0,
            threshold REAL DEFAULT 1.0,
            vo2max REAL DEFAULT 1.0,
            anaerobic REAL DEFAULT 1.0,
            updated_at TEXT NOT NULL DEFAULT (datetime('now')))""",
        "CREATE INDEX IF NOT EXISTS idx_cycling_rides_user ON cycling_ride_logs(user_id, ride_date)",
        "CREATE INDEX IF NOT EXISTS idx_cycling_plan_user ON cycling_plan(user_id, active)",
    ]
    for sql in table_migrations:
        try:
            conn.execute(sql)
        except Exception:
            pass
    for sql in migrations:
        try:
            conn.execute(sql)
        except Exception:
            pass  # Column already exists
    conn.commit()


def _seed_science_data():
    """Seed the evidence library, protocols, and biomarker definitions (idempotent)."""
    try:
        from services.evidence_service import seed_evidence
        from services.protocol_service import seed_protocols
        seed_protocols()
        seed_evidence()
    except Exception:
        pass  # Tables may not exist yet on first run
    try:
        from services.biomarker_service import seed_biomarker_definitions
        seed_biomarker_definitions()
    except Exception:
        pass
    try:
        from services.calorie_service import seed_food_database
        seed_food_database()
    except Exception:
        pass
    try:
        from services.organ_score_service import seed_organ_score_definitions
        seed_organ_score_definitions()
    except Exception:
        pass
