from datetime import datetime, timedelta, timezone

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
