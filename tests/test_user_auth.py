import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

import pytest

import db.database as database
import models.user as user_model


_PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
_SCHEMA_PATH = os.path.join(_PROJECT_ROOT, "db", "schema.sql")
_TEST_TEMP_ROOT = Path(_PROJECT_ROOT) / ".codex_test_tmp"


@pytest.fixture
def user_db(monkeypatch):
    _TEST_TEMP_ROOT.mkdir(exist_ok=True)
    case_dir = Path(tempfile.mkdtemp(prefix="user-auth-", dir=_TEST_TEMP_ROOT))
    db_path = str(case_dir / "users.db")

    def _get_test_connection():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    conn = _get_test_connection()
    with open(_SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()

    monkeypatch.setattr(user_model, "get_connection", _get_test_connection)
    try:
        yield _get_test_connection
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)


def test_create_user_normalizes_username_and_supports_case_insensitive_login(user_db):
    user_id = user_model.create_user("  John.Doe  ", "Password123", "John", "john@example.com")
    assert user_id > 0

    by_lower = user_model.verify_user("john.doe", "Password123")
    by_upper = user_model.verify_user("JOHN.DOE", "Password123")
    assert by_lower is not None
    assert by_upper is not None
    assert by_lower["id"] == by_upper["id"]


def test_verify_user_accepts_email_case_insensitive(user_db):
    user_model.create_user("maria", "Secret123", "Maria", "Maria@Example.com")
    assert user_model.verify_user("maria@example.com", "Secret123") is not None
    assert user_model.verify_user("MARIA@EXAMPLE.COM", "Secret123") is not None


def test_create_user_blocks_case_variant_duplicates(user_db):
    user_model.create_user("Thiago", "Abc12345", "Thiago", "thiago@example.com")
    with pytest.raises(sqlite3.IntegrityError):
        user_model.create_user("thiago", "Abc12345", "Thiago 2", "thiago2@example.com")


def test_create_user_blocks_case_variant_email_duplicates(user_db):
    user_model.create_user("one", "Abc12345", "One", "Shared@Example.com")

    with pytest.raises(sqlite3.IntegrityError):
        user_model.create_user("two", "Abc12345", "Two", " SHARED@example.com ")


def test_create_user_rejects_cross_namespace_collisions(user_db):
    user_model.create_user("first", "Abc12345", "First", "alias@example.com")
    user_model.create_user("owner@example.com", "Abc12345", "Owner", "owner2@example.com")

    with pytest.raises(sqlite3.IntegrityError):
        user_model.create_user("ALIAS@EXAMPLE.COM", "Abc12345", "Alias", "third@example.com")
    with pytest.raises(sqlite3.IntegrityError):
        user_model.create_user("second", "Abc12345", "Second", "OWNER@EXAMPLE.COM")
    with pytest.raises(sqlite3.IntegrityError):
        user_model.create_user("same@example.com", "Abc12345", "Same", "SAME@example.com")


def test_create_user_rejects_invalid_email(user_db):
    with pytest.raises(ValueError, match="Invalid email format"):
        user_model.create_user("elena", "StrongPass1", "Elena", "invalid-email")


def test_create_user_rejects_weak_password(user_db):
    with pytest.raises(ValueError, match="at least 8 characters"):
        user_model.create_user("sam", "Abc123", "Sam", "sam@example.com")
    with pytest.raises(ValueError, match="include letters and numbers"):
        user_model.create_user("sam2", "12345678", "Sam", "sam2@example.com")


def test_update_user_blank_display_name_keeps_value_and_blank_email_clears(user_db):
    user_id = user_model.create_user("lara", "StrongPass1", "Lara", "lara@example.com")
    user_model.update_user(user_id, display_name="   ", email="   ")

    updated = user_model.get_user(user_id)
    assert updated is not None
    assert updated["display_name"] == "Lara"
    assert updated["email"] is None


def test_update_user_normalizes_email_and_rejects_identity_collisions(user_db):
    first_id = user_model.create_user("first", "StrongPass1", "First", "first@example.com")
    second_id = user_model.create_user(
        "owner@example.com",
        "StrongPass1",
        "Second",
        "second@example.com",
    )

    user_model.update_user(first_id, email="  NEW@Example.com ")
    assert user_model.get_user(first_id)["email"] == "new@example.com"

    with pytest.raises(sqlite3.IntegrityError):
        user_model.update_user(first_id, email="SECOND@EXAMPLE.COM")
    with pytest.raises(sqlite3.IntegrityError):
        user_model.update_user(first_id, email="OWNER@EXAMPLE.COM")

    assert user_model.get_user(first_id)["email"] == "new@example.com"
    assert user_model.get_user(second_id)["email"] == "second@example.com"


def test_verify_user_rejects_ambiguous_legacy_email(user_db):
    password_hash = user_model.bcrypt.hashpw(
        b"StrongPass1",
        user_model.bcrypt.gensalt(),
    ).decode("utf-8")
    conn = user_db()
    conn.execute("DROP TRIGGER users_identity_insert_guard")
    conn.executemany(
        "INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)",
        [
            ("legacy-one", password_hash, "duplicate@example.com"),
            ("legacy-two", password_hash, " DUPLICATE@EXAMPLE.COM "),
        ],
    )
    conn.commit()
    conn.close()

    assert user_model.verify_user("duplicate@example.com", "StrongPass1") is None


def test_verify_user_rejects_legacy_cross_namespace_ambiguity(user_db):
    password_hash = user_model.bcrypt.hashpw(
        b"StrongPass1",
        user_model.bcrypt.gensalt(),
    ).decode("utf-8")
    conn = user_db()
    conn.execute("DROP TRIGGER users_identity_insert_guard")
    conn.executemany(
        "INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)",
        [
            ("shared@example.com", password_hash, None),
            ("legacy-email", password_hash, "shared@example.com"),
        ],
    )
    conn.commit()
    conn.close()

    assert user_model.verify_user("SHARED@EXAMPLE.COM", "StrongPass1") is None


def test_identity_migration_preserves_and_logs_legacy_duplicate_emails(tmp_path, caplog):
    db_path = tmp_path / "legacy-users.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """CREATE TABLE users (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               username TEXT NOT NULL UNIQUE,
               password_hash TEXT NOT NULL,
               email TEXT
           )"""
    )
    conn.executemany(
        "INSERT INTO users (username, password_hash, email) VALUES (?, 'hash', ?)",
        [
            ("legacy-one", "duplicate@example.com"),
            ("legacy-two", " DUPLICATE@EXAMPLE.COM "),
        ],
    )

    with caplog.at_level("WARNING", logger=database.__name__):
        database._migrate_user_identity_integrity(conn)

    assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 2
    assert "Ambiguous legacy email" in caplog.text
    assert conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'index' AND name = 'ux_users_email_normalized'"
    ).fetchone() is None
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO users (username, password_hash, email) VALUES (?, 'hash', ?)",
            ("legacy-three", "duplicate@example.com"),
        )
    conn.close()


def test_change_password_enforces_strength(user_db):
    user_id = user_model.create_user("niko", "StrongPass1", "Niko", "niko@example.com")
    with pytest.raises(ValueError, match="at least 8 characters"):
        user_model.change_password(user_id, "short1")
    with pytest.raises(ValueError, match="include letters and numbers"):
        user_model.change_password(user_id, "abcdefgh")
