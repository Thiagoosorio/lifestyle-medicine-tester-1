import os
import sqlite3

import pytest

import models.user as user_model


_PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
_SCHEMA_PATH = os.path.join(_PROJECT_ROOT, "db", "schema.sql")


@pytest.fixture
def user_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "users.db")

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
    return _get_test_connection


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
