import sqlite3
import re
import bcrypt
from db.database import get_connection


def _normalize_username(username: str) -> str:
    return username.strip().lower()


def _normalize_email(email: str | None) -> str | None:
    if email is None:
        return None
    value = email.strip()
    return value.lower() if value else None


_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_email(email: str | None) -> None:
    if email is None:
        return
    if not _EMAIL_PATTERN.match(email):
        raise ValueError("Invalid email format")


def _validate_password(password: str) -> str:
    value = password.strip()
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters")
    if not any(ch.isalpha() for ch in value) or not any(ch.isdigit() for ch in value):
        raise ValueError("Password must include letters and numbers")
    return value


def create_user(username: str, password: str, display_name: str = None, email: str = None) -> int:
    username_norm = _normalize_username(username)
    if not username_norm:
        raise ValueError("Username is required")
    email_norm = _normalize_email(email)
    _validate_email(email_norm)
    password_value = _validate_password(password)
    pw_bytes = password_value.encode("utf-8")
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
    conn = get_connection()
    try:
        updates = ["updated_at = datetime('now')"]
        params = []

        if display_name is not None:
            display_value = display_name.strip()
            if display_value:
                updates.append("display_name = ?")
                params.append(display_value)

        if email is not None:
            email_raw = email.strip()
            if email_raw:
                email_norm = _normalize_email(email_raw)
                _validate_email(email_norm)
                updates.append("email = ?")
                params.append(email_norm)
            else:
                updates.append("email = NULL")

        params.append(user_id)
        conn.execute(
            f"UPDATE users SET {', '.join(updates)} WHERE id = ?",
            tuple(params),
        )
        conn.commit()
    finally:
        conn.close()


def change_password(user_id: int, new_password: str):
    password_value = _validate_password(new_password)
    password_hash = bcrypt.hashpw(password_value.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE users SET password_hash = ?, updated_at = datetime('now') WHERE id = ?",
            (password_hash, user_id),
        )
        conn.commit()
    finally:
        conn.close()
