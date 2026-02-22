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
    with open(SCHEMA_PATH, "r") as f:
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
