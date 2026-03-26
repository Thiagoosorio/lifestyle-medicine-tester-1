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
