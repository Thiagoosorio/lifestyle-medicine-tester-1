"""Server-authorized account inventory for administrators."""

from __future__ import annotations

from typing import Any

from db.database import get_connection


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
