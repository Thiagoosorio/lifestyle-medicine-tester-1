import sqlite3
import bcrypt
from db.database import get_connection


def _normalize_username(username: str) -> str:
    return username.strip().lower()


def _normalize_email(email: str | None) -> str | None:
    if email is None:
        return None
    value = email.strip()
    return value.lower() if value else None


def create_user(username: str, password: str, display_name: str = None, email: str = None) -> int:
    username_norm = _normalize_username(username)
    email_norm = _normalize_email(email)
    pw_bytes = password.strip().encode("utf-8")
    password_hash = bcrypt.hashpw(pw_bytes, bcrypt.gensalt()).decode("utf-8")
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM users WHERE LOWER(username) = LOWER(?)",
            (username_norm,),
        ).fetchone()
        if existing:
            raise sqlite3.IntegrityError("Username already exists")

        cursor = conn.execute(
            "INSERT INTO users (username, password_hash, display_name, email) VALUES (?, ?, ?, ?)",
            (username_norm, password_hash, (display_name or username).strip(), email_norm),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def verify_user(username_or_email: str, password: str) -> dict | None:
    identifier = username_or_email.strip()
    if not identifier:
        return None
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT * FROM users
               WHERE LOWER(username) = LOWER(?)
                  OR LOWER(COALESCE(email, '')) = LOWER(?)
               LIMIT 1""",
            (identifier, identifier),
        ).fetchone()
        if not row:
            return None
        stored_hash = row["password_hash"]
        # Ensure hash is bytes for bcrypt
        if isinstance(stored_hash, str):
            stored_hash = stored_hash.encode("utf-8")
        if bcrypt.checkpw(password.strip().encode("utf-8"), stored_hash):
            return dict(row)
        return None
    finally:
        conn.close()


def get_user(user_id: int) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_user(user_id: int, display_name: str = None, email: str = None):
    email_norm = _normalize_email(email) if email is not None else None
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE users SET display_name = COALESCE(?, display_name), email = COALESCE(?, email), updated_at = datetime('now') WHERE id = ?",
            (display_name, email_norm, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def change_password(user_id: int, new_password: str):
    password_hash = bcrypt.hashpw(new_password.strip().encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE users SET password_hash = ?, updated_at = datetime('now') WHERE id = ?",
            (password_hash, user_id),
        )
        conn.commit()
    finally:
        conn.close()
