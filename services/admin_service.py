"""Administrator authorization, inventory, and deployment provisioning."""

from __future__ import annotations

from typing import Any

import bcrypt

from db.database import get_connection
from models.user import validate_password


_ACCOUNT_RESET_STATE_KEY = "account_reset_revision"


def _admin_bootstrap_state_key(username: str) -> str:
    return f"admin_bootstrap_revision:{username.strip().lower()}"


def _set_runtime_state(conn, key: str, value: str) -> None:
    conn.execute(
        """INSERT INTO app_runtime_state (state_key, state_value, updated_at)
           VALUES (?, ?, datetime('now'))
           ON CONFLICT(state_key) DO UPDATE SET
               state_value = excluded.state_value,
               updated_at = excluded.updated_at""",
        (key, value),
    )


def _get_runtime_state(conn, key: str) -> str | None:
    row = conn.execute(
        "SELECT state_value FROM app_runtime_state WHERE state_key = ?",
        (key,),
    ).fetchone()
    return str(row["state_value"]) if row else None


def ensure_bootstrap_admin(
    username: str,
    password: str,
    display_name: str,
    *,
    revision: str | None = None,
) -> dict[str, Any]:
    """Create or repair the configured admin, rotating its password once per revision."""
    username_norm = username.strip().lower()
    if not username_norm:
        raise ValueError("Bootstrap admin username is required")
    password_value = validate_password(password)
    display_value = display_name.strip() or username.strip()
    revision_value = revision.strip() if revision else None
    state_key = _admin_bootstrap_state_key(username_norm)

    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, account_role FROM users WHERE LOWER(TRIM(username)) = ?",
            (username_norm,),
        ).fetchone()
        previous_revision = _get_runtime_state(conn, state_key)
        should_set_password = row is None or (
            revision_value is not None and previous_revision != revision_value
        )
        password_hash = None
        if should_set_password:
            password_hash = bcrypt.hashpw(
                password_value.encode("utf-8"),
                bcrypt.gensalt(),
            ).decode("utf-8")

        if row is None:
            cursor = conn.execute(
                """INSERT INTO users
                   (username, password_hash, display_name, account_role)
                   VALUES (?, ?, ?, 'admin')""",
                (username_norm, password_hash, display_value),
            )
            user_id = cursor.lastrowid
            created = True
            role_updated = False
        else:
            user_id = row["id"]
            created = False
            role_updated = row["account_role"] != "admin"
            updates = [
                "display_name = ?",
                "account_role = 'admin'",
                "updated_at = datetime('now')",
            ]
            params: list[Any] = [display_value]
            if password_hash is not None:
                updates.append("password_hash = ?")
                params.append(password_hash)
            params.append(user_id)
            conn.execute(
                f"UPDATE users SET {', '.join(updates)} WHERE id = ?",
                tuple(params),
            )

        if revision_value is not None:
            _set_runtime_state(conn, state_key, revision_value)
        conn.commit()
        return {
            "user_id": user_id,
            "created": created,
            "role_updated": role_updated,
            "password_updated": should_set_password,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def reset_accounts_once(
    revision: str,
    admin_username: str,
    *,
    demo_username: str = "maria.silva",
    demo_email: str = "maria.silva@demo.com",
) -> dict[str, Any]:
    """Delete non-demo/non-admin accounts once for a named deployment revision."""
    revision_value = revision.strip()
    if not revision_value:
        raise ValueError("Account reset revision is required")
    admin_norm = admin_username.strip().lower()

    conn = get_connection()
    try:
        if _get_runtime_state(conn, _ACCOUNT_RESET_STATE_KEY) == revision_value:
            return {"applied": False, "deleted_accounts": 0, "deleted_records": 0}

        removable = conn.execute(
            """SELECT COUNT(*)
               FROM users
               WHERE LOWER(TRIM(username)) <> ?
                 AND NOT (
                     LOWER(TRIM(username)) = ?
                     AND LOWER(TRIM(COALESCE(email, ''))) = ?
                 )""",
            (admin_norm, demo_username.lower(), demo_email.lower()),
        ).fetchone()[0]

        user_tables = []
        for table_row in conn.execute(
            """SELECT name FROM sqlite_master
               WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"""
        ).fetchall():
            table_name = table_row["name"]
            quoted_name = table_name.replace('"', '""')
            columns = {
                column["name"]
                for column in conn.execute(
                    f'PRAGMA table_info("{quoted_name}")'
                ).fetchall()
            }
            if "user_id" in columns:
                user_tables.append(table_name)

        conn.commit()
        conn.execute("PRAGMA foreign_keys = OFF")
        deleted_records = 0
        try:
            for table_name in user_tables:
                quoted_name = table_name.replace('"', '""')
                cursor = conn.execute(
                    f'''DELETE FROM "{quoted_name}"
                        WHERE user_id IN (
                            SELECT id FROM users
                            WHERE LOWER(TRIM(username)) <> ?
                              AND NOT (
                                  LOWER(TRIM(username)) = ?
                                  AND LOWER(TRIM(COALESCE(email, ''))) = ?
                              )
                        )''',
                    (admin_norm, demo_username.lower(), demo_email.lower()),
                )
                deleted_records += max(cursor.rowcount, 0)
            conn.execute(
                """DELETE FROM users
                   WHERE LOWER(TRIM(username)) <> ?
                     AND NOT (
                         LOWER(TRIM(username)) = ?
                         AND LOWER(TRIM(COALESCE(email, ''))) = ?
                     )""",
                (admin_norm, demo_username.lower(), demo_email.lower()),
            )
            _set_runtime_state(conn, _ACCOUNT_RESET_STATE_KEY, revision_value)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.execute("PRAGMA foreign_keys = ON")

        return {
            "applied": True,
            "deleted_accounts": removable,
            "deleted_records": deleted_records,
        }
    finally:
        conn.close()


class AdminAccessError(PermissionError):
    pass


def get_account_inventory(requesting_user_id: int) -> dict[str, Any]:
    """Return account metadata and owned-row counts after verifying admin role."""
    conn = get_connection()
    try:
        requester = conn.execute(
            "SELECT account_role FROM users WHERE id = ?",
            (requesting_user_id,),
        ).fetchone()
        if requester is None or requester["account_role"] != "admin":
            raise AdminAccessError("Administrator access required")

        owned_tables = []
        for row in conn.execute(
            """SELECT name FROM sqlite_master
               WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
               ORDER BY name"""
        ).fetchall():
            table_name = row["name"]
            columns = {
                column["name"]
                for column in conn.execute(
                    f'PRAGMA table_info("{table_name}")'
                ).fetchall()
            }
            if "user_id" in columns:
                owned_tables.append(table_name)

        accounts = []
        rows = conn.execute(
            """SELECT id, username, display_name, email, account_role,
                      created_at, updated_at
               FROM users
               ORDER BY account_role DESC, username"""
        ).fetchall()
        for row in rows:
            account = dict(row)
            account["owned_records"] = sum(
                conn.execute(
                    f'SELECT COUNT(*) FROM "{table}" WHERE user_id = ?',
                    (account["id"],),
                ).fetchone()[0]
                for table in owned_tables
            )
            accounts.append(account)

        return {
            "accounts": accounts,
            "account_count": len(accounts),
            "admin_count": sum(
                account["account_role"] == "admin" for account in accounts
            ),
            "owned_table_count": len(owned_tables),
            "owned_record_count": sum(
                account["owned_records"] for account in accounts
            ),
        }
    finally:
        conn.close()
