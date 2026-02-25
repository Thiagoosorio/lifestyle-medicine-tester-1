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
