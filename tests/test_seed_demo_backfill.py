import models.clinical_profile as clinical_profile
import seed_demo
import services.biomarker_service as biomarker_service


def _patch_db_connections(monkeypatch, db_conn):
    monkeypatch.setattr(seed_demo, "get_connection", db_conn)
    monkeypatch.setattr(clinical_profile, "get_connection", db_conn)
    monkeypatch.setattr(biomarker_service, "get_connection", db_conn)


def _create_demo_user(db_conn) -> int:
    conn = db_conn()
    cursor = conn.execute(
        "INSERT INTO users (username, password_hash, display_name, email) VALUES (?, ?, ?, ?)",
        ("maria.silva", "fakehash", "Maria Silva", "maria.silva@demo.com"),
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return user_id


def test_ensure_demo_organ_score_prereqs_backfills_missing_profile_and_labs(db_conn, monkeypatch):
    _patch_db_connections(monkeypatch, db_conn)
    biomarker_service.seed_biomarker_definitions()
    user_id = _create_demo_user(db_conn)

    clinical_profile.save_profile(user_id, {"sex": "female", "height_cm": 170.0})

    conn = db_conn()
    hba1c_id = conn.execute(
        "SELECT id FROM biomarker_definitions WHERE code = ?",
        ("hba1c",),
    ).fetchone()["id"]
    conn.execute(
        """INSERT INTO biomarker_results (user_id, biomarker_id, value, lab_date, lab_name)
           VALUES (?, ?, ?, ?, ?)""",
        (user_id, hba1c_id, 5.7, "2026-03-10", "Outside Lab"),
    )
    conn.commit()
    conn.close()

    summary = seed_demo.ensure_demo_organ_score_prereqs(user_id)

    assert summary["profile_backfilled"] is True
    assert summary["missing_definitions"] == []
    assert summary["inserted_biomarkers"] == len(seed_demo.MARIA_ORGAN_SCORE_BIOMARKERS) - 1
    assert summary["inserted_body_metrics"] == 1
    # 30 days of wearable data: ~24 daily metrics + ~3 optional every 3rd day
    assert summary["inserted_wearable_measurements"] > 500

    profile = clinical_profile.get_profile(user_id)
    assert profile["date_of_birth"] == "1982-10-12"
    assert profile["height_cm"] == 170.0  # Preserve existing user-edited value.
    assert profile["education_years"] == 16

    conn = db_conn()
    hba1c_count = conn.execute(
        """SELECT COUNT(*) AS cnt
           FROM biomarker_results br
           JOIN biomarker_definitions bd ON bd.id = br.biomarker_id
           WHERE br.user_id = ? AND bd.code = ?""",
        (user_id, "hba1c"),
    ).fetchone()["cnt"]
    ast_latest = conn.execute(
        """SELECT br.lab_date
           FROM biomarker_results br
           JOIN biomarker_definitions bd ON bd.id = br.biomarker_id
           WHERE br.user_id = ? AND bd.code = ?""",
        (user_id, "ast"),
    ).fetchone()
    conn.close()

    assert hba1c_count == 1
    assert ast_latest["lab_date"] == seed_demo.MARIA_BACKFILL_LAB_DATE


def test_ensure_demo_organ_score_prereqs_is_idempotent(db_conn, monkeypatch):
    _patch_db_connections(monkeypatch, db_conn)
    biomarker_service.seed_biomarker_definitions()
    user_id = _create_demo_user(db_conn)

    first = seed_demo.ensure_demo_organ_score_prereqs(user_id)
    second = seed_demo.ensure_demo_organ_score_prereqs(user_id)

    assert first["inserted_biomarkers"] == len(seed_demo.MARIA_ORGAN_SCORE_BIOMARKERS)
    assert first["inserted_body_metrics"] == 1
    assert first["inserted_wearable_measurements"] > 500  # 30 days of multi-metric data
    assert second["inserted_biomarkers"] == 0
    assert second["inserted_body_metrics"] == 0
    assert second["inserted_wearable_measurements"] == 0
    assert second["profile_backfilled"] is False
