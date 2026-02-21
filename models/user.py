import bcrypt
from db.database import get_connection


def create_user(username: str, password: str, display_name: str = None, email: str = None) -> int:
    pw_bytes = password.strip().encode("utf-8")
    password_hash = bcrypt.hashpw(pw_bytes, bcrypt.gensalt()).decode("utf-8")
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO users (username, password_hash, display_name, email) VALUES (?, ?, ?, ?)",
            (username.strip(), password_hash, (display_name or username).strip(), email),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def verify_user(username: str, password: str) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username.strip(),)).fetchone()
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
        conn.execute(
            "UPDATE users SET display_name = COALESCE(?, display_name), email = COALESCE(?, email), updated_at = datetime('now') WHERE id = ?",
            (display_name, email, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def change_password(user_id: int, new_password: str):
    password_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE users SET password_hash = ?, updated_at = datetime('now') WHERE id = ?",
            (password_hash, user_id),
        )
        conn.commit()
    finally:
        conn.close()
