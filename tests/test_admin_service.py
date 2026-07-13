import bcrypt
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


def test_bootstrap_admin_is_idempotent_for_same_revision(db_conn, monkeypatch):
    monkeypatch.setattr(admin_service, "get_connection", db_conn)

    first = admin_service.ensure_bootstrap_admin(
        "TG",
        "AdminPass123",
        "TG",
        revision="credential-v1",
    )
    conn = db_conn()
    first_row = conn.execute(
        "SELECT * FROM users WHERE username = 'tg'"
    ).fetchone()
    first_hash = first_row["password_hash"]
    conn.close()

    second = admin_service.ensure_bootstrap_admin(
        "TG",
        "AdminPass123",
        "TG",
        revision="credential-v1",
    )
    conn = db_conn()
    second_row = conn.execute(
        "SELECT * FROM users WHERE username = 'tg'"
    ).fetchone()
    conn.close()

    assert first["created"] is True
    assert first["password_updated"] is True
    assert second["created"] is False
    assert second["password_updated"] is False
    assert second_row["password_hash"] == first_hash
    assert second_row["account_role"] == "admin"
    assert bcrypt.checkpw(b"AdminPass123", first_hash.encode("utf-8"))


def test_bootstrap_admin_promotes_and_rotates_existing_account(db_conn, monkeypatch):
    monkeypatch.setattr(admin_service, "get_connection", db_conn)
    user_id = _create_account(db_conn, "tg", "user")

    summary = admin_service.ensure_bootstrap_admin(
        "TG",
        "Replacement123",
        "Test Administrator",
        revision="credential-v2",
    )
    conn = db_conn()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()

    assert summary["created"] is False
    assert summary["role_updated"] is True
    assert summary["password_updated"] is True
    assert row["account_role"] == "admin"
    assert row["display_name"] == "Test Administrator"
    assert bcrypt.checkpw(b"Replacement123", row["password_hash"].encode("utf-8"))


def test_account_reset_preserves_admin_and_canonical_demo_once(db_conn, monkeypatch):
    monkeypatch.setattr(admin_service, "get_connection", db_conn)
    admin_id = _create_account(db_conn, "tg", "admin")
    conn = db_conn()
    cursor = conn.execute(
        """INSERT INTO users
           (username, password_hash, display_name, email, account_role)
           VALUES ('maria.silva', 'hash', 'Maria', 'maria.silva@demo.com', 'user')"""
    )
    demo_id = cursor.lastrowid
    cursor = conn.execute(
        """INSERT INTO users
           (username, password_hash, display_name, account_role)
           VALUES ('remove-me', 'hash', 'Remove Me', 'user')"""
    )
    removed_id = cursor.lastrowid
    conn.execute(
        "INSERT INTO body_metrics (user_id, log_date, weight_kg) VALUES (?, '2026-01-01', 80)",
        (removed_id,),
    )
    conn.commit()
    conn.close()

    first = admin_service.reset_accounts_once("reset-v1", "TG")
    newcomer_id = _create_account(db_conn, "new-after-reset", "user")
    second = admin_service.reset_accounts_once("reset-v1", "TG")

    conn = db_conn()
    remaining_ids = {
        row["id"] for row in conn.execute("SELECT id FROM users").fetchall()
    }
    removed_metrics = conn.execute(
        "SELECT COUNT(*) FROM body_metrics WHERE user_id = ?",
        (removed_id,),
    ).fetchone()[0]
    conn.close()

    assert first["applied"] is True
    assert first["deleted_accounts"] == 1
    assert first["deleted_records"] >= 1
    assert second == {
        "applied": False,
        "deleted_accounts": 0,
        "deleted_records": 0,
    }
    assert remaining_ids == {admin_id, demo_id, newcomer_id}
    assert removed_metrics == 0

    third = admin_service.reset_accounts_once("reset-v2", "TG")
    conn = db_conn()
    final_ids = {row["id"] for row in conn.execute("SELECT id FROM users").fetchall()}
    conn.close()

    assert third["applied"] is True
    assert third["deleted_accounts"] == 1
    assert final_ids == {admin_id, demo_id}
