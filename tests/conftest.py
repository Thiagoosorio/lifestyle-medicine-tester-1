"""Shared pytest fixtures for Lifestyle Medicine app tests.

Provides an isolated SQLite database per test function by:
1. Creating a fresh DB from schema.sql + migrations in a tmp directory
2. Monkeypatching db.database.get_connection so all app code uses the test DB
"""

import os
import sqlite3
import pytest

_PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
_SCHEMA_PATH = os.path.join(_PROJECT_ROOT, "db", "schema.sql")


@pytest.fixture
def db_conn(tmp_path, monkeypatch):
    """Yield a factory that returns connections to a fresh, isolated test DB."""
    db_path = str(tmp_path / "test.db")

    def _get_test_connection():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    # Initialize schema
    conn = _get_test_connection()
    with open(_SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()

    # Run the same migrations that database.py runs on startup
    import db.database as db_mod
    _run_test_migrations(conn, db_mod)
    conn.commit()
    conn.close()

    # Monkeypatch so all app code uses our test DB
    monkeypatch.setattr(db_mod, "get_connection", _get_test_connection)

    # Modules that do `from db.database import get_connection` hold a local copy
    # — must patch those too. Keep this list tight (per-test explicit patches
    # for anything not listed); broad auto-patching causes test-ordering drift
    # in modules that also seed per-call state (e.g. microhabit_service).
    import models.habit
    monkeypatch.setattr(models.habit, "get_connection", _get_test_connection)
    import services.microhabit_service
    monkeypatch.setattr(services.microhabit_service, "get_connection", _get_test_connection)
    import models.clinical_profile
    monkeypatch.setattr(models.clinical_profile, "get_connection", _get_test_connection)
    import services.body_metrics_service
    monkeypatch.setattr(services.body_metrics_service, "get_connection", _get_test_connection)
    import services.fracture_risk_service
    monkeypatch.setattr(services.fracture_risk_service, "get_connection", _get_test_connection, raising=False)
    import services.organ_score_service
    monkeypatch.setattr(services.organ_score_service, "get_connection", _get_test_connection, raising=False)
    import models.organ_score
    monkeypatch.setattr(models.organ_score, "get_connection", _get_test_connection, raising=False)
    import seed_demo
    monkeypatch.setattr(seed_demo, "get_connection", _get_test_connection, raising=False)

    yield _get_test_connection


def _run_test_migrations(conn, db_mod):
    """Apply table_migrations from database.py to the test DB."""
    if hasattr(db_mod, "_migrate"):
        db_mod._migrate(conn)
        return
    if hasattr(db_mod, "table_migrations"):
        for sql in db_mod.table_migrations:
            try:
                conn.executescript(sql) if ";" in sql else conn.execute(sql)
            except Exception:
                pass  # Migrations are idempotent, ignore already-applied


@pytest.fixture
def test_user(db_conn):
    """Create a test user and return their user_id."""
    conn = db_conn()
    cursor = conn.execute(
        "INSERT INTO users (username, password_hash, display_name) VALUES (?, ?, ?)",
        ("testuser", "fakehash", "Test User"),
    )
    conn.commit()
    uid = cursor.lastrowid
    conn.close()
    return uid
