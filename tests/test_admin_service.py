import pytest

import services.admin_service as admin_service


def _create_account(db_conn, username: str, role: str) -> int:
    conn = db_conn()
    cursor = conn.execute(
        """INSERT INTO users
           (username, password_hash, display_name, account_role)
           VALUES (?, 'hash', ?, ?)""",
        (username, username.upper(), role),
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return user_id


def test_admin_inventory_requires_database_role(db_conn, monkeypatch):
    monkeypatch.setattr(admin_service, "get_connection", db_conn)
    user_id = _create_account(db_conn, "regular", "user")

    with pytest.raises(admin_service.AdminAccessError):
        admin_service.get_account_inventory(user_id)


def test_admin_inventory_excludes_passwords_and_counts_owned_rows(
    db_conn,
    monkeypatch,
):
    monkeypatch.setattr(admin_service, "get_connection", db_conn)
    admin_id = _create_account(db_conn, "tg", "admin")
    user_id = _create_account(db_conn, "maria", "user")
    conn = db_conn()
    conn.execute(
        """INSERT INTO body_metrics (user_id, log_date, weight_kg)
           VALUES (?, '2026-02-01', 78.0)""",
        (user_id,),
    )
    conn.commit()
    conn.close()

    inventory = admin_service.get_account_inventory(admin_id)

    assert inventory["account_count"] == 2
    assert inventory["admin_count"] == 1
    # weekly_challenges is created lazily by its service, so a fresh schema has 62.
    assert inventory["owned_table_count"] >= 62
    maria = next(
        account for account in inventory["accounts"] if account["username"] == "maria"
    )
    assert maria["owned_records"] == 1
    assert "password_hash" not in maria
