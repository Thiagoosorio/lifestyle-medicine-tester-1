from datetime import datetime, timedelta, timezone
import sqlite3

import services.wearable_wheel_service as wws


def _create_user(db_conn) -> int:
    conn = db_conn()
    cursor = conn.execute(
        "INSERT INTO users (username, password_hash, display_name, email) VALUES (?, ?, ?, ?)",
        ("wearable.user", "fakehash", "Wearable User", "wearable@example.com"),
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return user_id


def test_save_measurements_accepts_known_metrics(db_conn, monkeypatch):
    monkeypatch.setattr(wws, "get_connection", db_conn)
    user_id = _create_user(db_conn)

    summary = wws.save_measurements(
        user_id,
        [
            {"metric_code": "resting_heart_rate_bpm", "value": 54, "measured_at": "2026-03-26T07:00:00"},
            {"metric_code": "unknown_metric", "value": 10, "measured_at": "2026-03-26T07:00:00"},
        ],
    )

    assert summary["inserted"] == 1
    assert summary["skipped_unknown"] == 1
    assert summary["skipped_invalid"] == 0


def test_import_csv_template_and_compute_wheel(db_conn, monkeypatch):
    monkeypatch.setattr(wws, "get_connection", db_conn)
    user_id = _create_user(db_conn)

    template_csv = wws.build_wearable_csv_template()
    import_summary = wws.import_measurements_csv_text(user_id, template_csv)
    assert import_summary["inserted"] >= 3

    # Add a compact but representative metric set.
    wws.save_measurements(
        user_id,
        [
            {"metric_code": "arrhythmia_alert_afib", "value": 0, "measured_at": "2026-03-26T07:00:00"},
            {"metric_code": "heart_rate_variability_ms", "value": 60, "measured_at": "2026-03-26T07:00:00"},
            {"metric_code": "steps_count", "value": 10250, "measured_at": "2026-03-26T07:00:00"},
            {"metric_code": "kilojoule_expended", "value": 2500, "measured_at": "2026-03-26T07:00:00"},
            {"metric_code": "recovery_score", "value": 82, "measured_at": "2026-03-26T07:00:00"},
            {"metric_code": "sleep_efficiency_pct", "value": 92, "measured_at": "2026-03-26T07:00:00"},
            {"metric_code": "sleep_debt_hours", "value": 0.8, "measured_at": "2026-03-26T07:00:00"},
            {"metric_code": "respiratory_rate_bpm", "value": 14.0, "measured_at": "2026-03-26T07:00:00"},
            {"metric_code": "body_temperature_deviation_c", "value": 0.1, "measured_at": "2026-03-26T07:00:00"},
            {"metric_code": "spo2_pct", "value": 97, "measured_at": "2026-03-26T07:00:00"},
        ],
    )

    wheel = wws.compute_wearable_wheel(user_id)

    assert wheel["data_points_used"] >= 10
    assert set(wheel["domains"].keys()) == {
        "heart_metabolism",
        "muscle_bones",
        "gut_digestion",
        "brain_health",
        "system_wide",
    }
    assert wheel["domains"]["heart_metabolism"]["score_10"] > 6
    assert wheel["domains"]["muscle_bones"]["is_proxy"] is True
    assert 0 <= wheel["domains"]["gut_digestion"]["confidence"] <= 0.7
    assert "overall_readiness_10" in wheel
    assert "overall_resilience_10" in wheel


def test_recency_weighting_and_readiness_resilience_split(db_conn, monkeypatch):
    monkeypatch.setattr(wws, "get_connection", db_conn)
    user_id = _create_user(db_conn)

    now_utc = datetime.now(timezone.utc)
    recent_ts = (now_utc - timedelta(days=1)).replace(tzinfo=None).isoformat(timespec="seconds")
    older_ts = (now_utc - timedelta(days=20)).replace(tzinfo=None).isoformat(timespec="seconds")

    # Older value is worse; newer value is better.
    wws.save_measurements(
        user_id,
        [
            {"metric_code": "resting_heart_rate_bpm", "value": 82, "measured_at": older_ts},
            {"metric_code": "resting_heart_rate_bpm", "value": 52, "measured_at": recent_ts},
            {"metric_code": "heart_rate_variability_ms", "value": 60, "measured_at": recent_ts},
            {"metric_code": "steps_count", "value": 9000, "measured_at": recent_ts},
            {"metric_code": "kilojoule_expended", "value": 2300, "measured_at": recent_ts},
            {"metric_code": "arrhythmia_alert_afib", "value": 0, "measured_at": recent_ts},
        ],
    )

    wheel = wws.compute_wearable_wheel(user_id)
    metric = wheel["metrics"]["resting_heart_rate_bpm"]

    # Smoothed current value should lean strongly toward the recent reading.
    assert metric["raw_value"] < 65
    # With older poor readings, long-horizon resilience should not exceed short-horizon readiness.
    assert wheel["overall_readiness_100"] >= wheel["overall_resilience_100"]


def test_optional_bp_and_cgm_do_not_reduce_required_coverage(db_conn, monkeypatch):
    monkeypatch.setattr(wws, "get_connection", db_conn)
    user_id = _create_user(db_conn)

    ts = "2026-03-26T07:00:00"
    # Required HM metrics only; optional BP/CGM/weight are intentionally missing.
    wws.save_measurements(
        user_id,
        [
            {"metric_code": "arrhythmia_alert_afib", "value": 0, "measured_at": ts},
            {"metric_code": "average_heart_rate_bpm", "value": 66, "measured_at": ts},
            {"metric_code": "heart_rate_variability_ms", "value": 58, "measured_at": ts},
            {"metric_code": "maximum_heart_rate_bpm", "value": 170, "measured_at": ts},
            {"metric_code": "respiratory_rate_bpm", "value": 14, "measured_at": ts},
            {"metric_code": "resting_heart_rate_bpm", "value": 53, "measured_at": ts},
            {"metric_code": "steps_count", "value": 10000, "measured_at": ts},
            {"metric_code": "kilojoule_expended", "value": 2400, "measured_at": ts},
        ],
    )

    wheel = wws.compute_wearable_wheel(user_id)
    hm = wheel["domains"]["heart_metabolism"]
    assert hm["available_metrics"] == hm["total_metrics"]
    assert hm["optional_metrics_used"] == 0


def test_weight_and_bp_improvement_contributes_via_trend(db_conn, monkeypatch):
    monkeypatch.setattr(wws, "get_connection", db_conn)
    user_id = _create_user(db_conn)

    conn = db_conn()
    conn.execute(
        "INSERT OR REPLACE INTO user_settings (user_id, goal_weight_kg) VALUES (?, ?)",
        (user_id, 70.0),
    )
    conn.commit()
    conn.close()

    now_utc = datetime.now(timezone.utc)
    recent_ts = (now_utc - timedelta(days=1)).replace(tzinfo=None).isoformat(timespec="seconds")
    older_ts = (now_utc - timedelta(days=25)).replace(tzinfo=None).isoformat(timespec="seconds")

    wws.save_measurements(
        user_id,
        [
            {"metric_code": "systolic_bp_mmhg", "value": 145, "measured_at": older_ts},
            {"metric_code": "systolic_bp_mmhg", "value": 122, "measured_at": recent_ts},
            {"metric_code": "body_weight_kg", "value": 79, "measured_at": older_ts},
            {"metric_code": "body_weight_kg", "value": 74, "measured_at": recent_ts},
            {"metric_code": "cgm_avg_glucose_mgdl", "value": 135, "measured_at": older_ts},
            {"metric_code": "cgm_avg_glucose_mgdl", "value": 104, "measured_at": recent_ts},
            # keep baseline HM required coverage
            {"metric_code": "arrhythmia_alert_afib", "value": 0, "measured_at": recent_ts},
            {"metric_code": "average_heart_rate_bpm", "value": 66, "measured_at": recent_ts},
            {"metric_code": "heart_rate_variability_ms", "value": 56, "measured_at": recent_ts},
            {"metric_code": "maximum_heart_rate_bpm", "value": 168, "measured_at": recent_ts},
            {"metric_code": "respiratory_rate_bpm", "value": 14, "measured_at": recent_ts},
            {"metric_code": "resting_heart_rate_bpm", "value": 54, "measured_at": recent_ts},
            {"metric_code": "steps_count", "value": 9800, "measured_at": recent_ts},
            {"metric_code": "kilojoule_expended", "value": 2350, "measured_at": recent_ts},
        ],
    )

    wheel = wws.compute_wearable_wheel(user_id)
    sbp_metric = wheel["metrics"]["systolic_bp_mmhg"]
    wt_metric = wheel["metrics"]["body_weight_kg"]
    glu_metric = wheel["metrics"]["cgm_avg_glucose_mgdl"]

    assert sbp_metric["trend_adjust_100"] > 0
    assert wt_metric["trend_adjust_100"] > 0
    assert glu_metric["trend_adjust_100"] > 0
    assert wheel["domains"]["heart_metabolism"]["optional_metrics_used"] >= 3


def test_csv_alias_conversion_and_bp_split(db_conn, monkeypatch):
    monkeypatch.setattr(wws, "get_connection", db_conn)
    user_id = _create_user(db_conn)

    csv_text = """metric_code,value,unit,measured_at,source
rhr,52,bpm,2026-03-26T07:00:00,Whoop Band
glucose_avg,5.6,mmol/L,2026-03-26T07:00:00,CGM FreeStyle Libre
weight,176.4,lb,2026-03-26T07:00:00,InBody H40 Home Scale
bp,122/78,mmHg,2026-03-26T07:00:00,Withings BPM Connect Pro
active_energy_kcal,500,kcal,2026-03-26T07:00:00,Whoop Band
"""
    summary = wws.import_measurements_csv_text(user_id, csv_text)
    latest = wws.get_latest_measurements(user_id)

    assert summary["inserted"] == 6
    assert summary["normalized_aliases"] >= 5
    assert summary["unit_converted"] >= 3
    assert summary["bp_split"] == 1
    assert abs(float(latest["cgm_avg_glucose_mgdl"]["value"]) - 100.9) < 0.6
    assert abs(float(latest["body_weight_kg"]["value"]) - 80.0) < 0.2
    assert abs(float(latest["kilojoule_expended"]["value"]) - 2092.0) < 1.0
    assert "systolic_bp_mmhg" in latest
    assert "diastolic_bp_mmhg" in latest


def test_optional_weight_capped_vs_required_metrics(db_conn, monkeypatch):
    monkeypatch.setattr(wws, "get_connection", db_conn)
    user_id = _create_user(db_conn)

    conn = db_conn()
    conn.execute(
        "INSERT OR REPLACE INTO user_settings (user_id, goal_weight_kg) VALUES (?, ?)",
        (user_id, 70.0),
    )
    conn.commit()
    conn.close()

    ts = "2026-03-26T07:00:00"
    # Weak required HM metrics.
    wws.save_measurements(
        user_id,
        [
            {"metric_code": "arrhythmia_alert_afib", "value": 1, "measured_at": ts},
            {"metric_code": "heart_rate_variability_ms", "value": 20, "measured_at": ts},
            {"metric_code": "respiratory_rate_bpm", "value": 23, "measured_at": ts},
            {"metric_code": "resting_heart_rate_bpm", "value": 85, "measured_at": ts},
            {"metric_code": "steps_count", "value": 2500, "measured_at": ts},
            {"metric_code": "kilojoule_expended", "value": 800, "measured_at": ts},
            # Strong optional HM metrics.
            {"metric_code": "systolic_bp_mmhg", "value": 110, "measured_at": ts},
            {"metric_code": "diastolic_bp_mmhg", "value": 70, "measured_at": ts},
            {"metric_code": "cgm_avg_glucose_mgdl", "value": 90, "measured_at": ts},
            {"metric_code": "cgm_time_in_range_pct", "value": 95, "measured_at": ts},
            {"metric_code": "body_weight_kg", "value": 70, "measured_at": ts},
        ],
    )

    wheel = wws.compute_wearable_wheel(user_id)
    hm = wheel["domains"]["heart_metabolism"]
    assert hm["optional_weight_scale"] < 1.0
    assert hm["missing_required_codes"] == []
    assert hm["score_10"] < 5.6


def test_missing_required_codes_are_exposed_for_ui_coaching(db_conn, monkeypatch):
    monkeypatch.setattr(wws, "get_connection", db_conn)
    user_id = _create_user(db_conn)
    ts = "2026-03-26T07:00:00"

    # Only one required HM metric + optional BP.
    wws.save_measurements(
        user_id,
        [
            {"metric_code": "resting_heart_rate_bpm", "value": 55, "measured_at": ts},
            {"metric_code": "systolic_bp_mmhg", "value": 118, "measured_at": ts},
        ],
    )

    wheel = wws.compute_wearable_wheel(user_id)
    hm_missing = set(wheel["domains"]["heart_metabolism"]["missing_required_codes"])
    assert "heart_rate_variability_ms" in hm_missing
    assert "steps_count" in hm_missing


def test_legacy_wearable_table_without_source_is_self_healed(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy_wearable.db"

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, password_hash TEXT NOT NULL)"
    )
    conn.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", ("legacy.user", "hash"))
    conn.execute(
        """
        CREATE TABLE user_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            goal_weight_kg REAL,
            updated_at TEXT
        )
        """
    )
    # Legacy table intentionally omits source/external_id.
    conn.execute(
        """
        CREATE TABLE wearable_measurements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            metric_code TEXT NOT NULL,
            metric_name TEXT,
            value REAL NOT NULL,
            unit TEXT,
            measured_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        INSERT INTO wearable_measurements (user_id, metric_code, metric_name, value, unit, measured_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (1, "resting_heart_rate_bpm", "Resting Heart Rate", 55.0, "bpm", "2026-03-26T07:00:00"),
    )
    conn.commit()
    conn.close()

    def _legacy_conn():
        db = sqlite3.connect(str(db_path))
        db.row_factory = sqlite3.Row
        return db

    monkeypatch.setattr(wws, "get_connection", _legacy_conn)

    wheel = wws.compute_wearable_wheel(1)
    assert wheel["data_points_used"] >= 1

    summary = wws.save_measurements(
        1,
        [
            {
                "metric_code": "steps_count",
                "value": 8000,
                "measured_at": "2026-03-27T07:00:00",
                "source": "Whoop Band",
            }
        ],
    )
    assert summary["inserted"] == 1

    verify_conn = _legacy_conn()
    try:
        columns = {
            row["name"]
            for row in verify_conn.execute("PRAGMA table_info(wearable_measurements)").fetchall()
        }
    finally:
        verify_conn.close()

    assert "source" in columns
