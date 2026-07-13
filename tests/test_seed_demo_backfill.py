import models.clinical_profile as clinical_profile
import seed_demo
import services.biomarker_service as biomarker_service
from datetime import date
import random


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


def test_demo_rng_wrapper_restores_process_random_state():
    random.seed(9876)
    prior_state = random.getstate()

    @seed_demo._with_reproducible_random_state
    def _draw_demo_values():
        return [random.random() for _ in range(3)]

    first = _draw_demo_values()
    second = _draw_demo_values()

    assert first == second
    assert random.getstate() == prior_state


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


def test_ensure_demo_showcase_data_populates_flagship_views_idempotently(
    db_conn,
    monkeypatch,
):
    _patch_db_connections(monkeypatch, db_conn)
    user_id = _create_demo_user(db_conn)
    conn = db_conn()
    conn.executemany(
        "INSERT INTO habits (user_id, pillar_id, name) VALUES (?, ?, ?)",
        [
            (user_id, 2, "Morning walk/run"),
            (user_id, 4, "Morning meditation"),
            (user_id, 1, "Drink 8 glasses of water"),
        ],
    )
    conn.commit()
    conn.close()

    first = seed_demo.ensure_demo_showcase_data(user_id)
    second = seed_demo.ensure_demo_showcase_data(user_id)

    expected = {
        "cpet_reports": 2,
        "inbody_reports": 2,
        "programs": 1,
        "lessons_completed": 12,
        "habit_stacks": 1,
    }
    assert first == expected
    assert second == expected

    conn = db_conn()
    assert conn.execute(
        "SELECT COUNT(*) FROM micro_lessons"
    ).fetchone()[0] == 15
    assert conn.execute(
        "SELECT COUNT(*) FROM habits WHERE user_id = ? AND stack_id IS NOT NULL",
        (user_id,),
    ).fetchone()[0] == 3
    assert conn.execute(
        "SELECT goal_weight_kg FROM user_settings WHERE user_id = ?",
        (user_id,),
    ).fetchone()[0] == 75.0
    assert conn.execute(
        "SELECT COUNT(*) FROM cpet_reports WHERE user_id = ? AND raw_text IS NULL",
        (user_id,),
    ).fetchone()[0] == 2
    assert conn.execute(
        "SELECT COUNT(*) FROM inbody_reports WHERE user_id = ? AND raw_text IS NULL",
        (user_id,),
    ).fetchone()[0] == 2
    conn.close()


def test_ensure_demo_current_window_is_fresh_and_idempotent(db_conn, monkeypatch):
    _patch_db_connections(monkeypatch, db_conn)
    user_id = _create_demo_user(db_conn)
    conn = db_conn()
    conn.execute(
        "INSERT INTO habits (user_id, pillar_id, name) VALUES (?, 2, 'Morning walk/run')",
        (user_id,),
    )
    conn.commit()
    conn.close()
    anchor = date(2026, 7, 13)

    first = seed_demo.ensure_demo_current_window(user_id, anchor)
    second = seed_demo.ensure_demo_current_window(user_id, anchor)

    expected = {
        "anchor_date": "2026-07-13",
        "checkins": 14,
        "sleep_logs": 14,
        "exercise_logs": 7,
        "meal_logs": 42,
    }
    assert first == expected
    assert second == expected

    conn = db_conn()
    assert conn.execute(
        "SELECT MAX(checkin_date) FROM daily_checkins WHERE user_id = ?",
        (user_id,),
    ).fetchone()[0] == anchor.isoformat()
    assert conn.execute(
        "SELECT MAX(sleep_date) FROM sleep_logs WHERE user_id = ?",
        (user_id,),
    ).fetchone()[0] == anchor.isoformat()
    assert conn.execute(
        """SELECT COUNT(*) FROM goals
           WHERE user_id = ? AND title = 'Maintain half-marathon fitness safely'
             AND status = 'active'""",
        (user_id,),
    ).fetchone()[0] == 1
    assert conn.execute(
        "SELECT COUNT(*) FROM wheel_assessments WHERE user_id = ? AND assessed_at = ?",
        (user_id, anchor.isoformat()),
    ).fetchone()[0] == 6
    conn.close()


def test_showcase_backfill_preserves_another_users_lesson_progress(
    db_conn,
    monkeypatch,
):
    _patch_db_connections(monkeypatch, db_conn)
    demo_id = _create_demo_user(db_conn)
    seed_demo.ensure_demo_showcase_data(demo_id)
    conn = db_conn()
    other_id = conn.execute(
        """INSERT INTO users (username, password_hash, display_name)
           VALUES ('other', 'hash', 'Other')"""
    ).lastrowid
    lesson_id = conn.execute("SELECT MIN(id) FROM micro_lessons").fetchone()[0]
    conn.execute(
        """INSERT INTO user_lesson_progress (user_id, lesson_id, quiz_score)
           VALUES (?, ?, 100)""",
        (other_id, lesson_id),
    )
    conn.commit()
    conn.close()

    seed_demo.ensure_demo_showcase_data(demo_id)

    conn = db_conn()
    assert conn.execute(
        "SELECT COUNT(*) FROM user_lesson_progress WHERE user_id = ?",
        (other_id,),
    ).fetchone()[0] == 1
    conn.close()
