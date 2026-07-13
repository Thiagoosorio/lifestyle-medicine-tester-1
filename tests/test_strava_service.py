import sqlite3
from datetime import date, datetime, timezone

import pytest
from cryptography.fernet import Fernet

import services.strava_service as strava_service


class _FixedDate(date):
    @classmethod
    def today(cls):
        return cls(2026, 3, 25)


def _strava_connection_factory(database_path):
    def connect():
        conn = sqlite3.connect(database_path)
        conn.row_factory = sqlite3.Row
        return conn

    conn = connect()
    conn.execute(
        """CREATE TABLE strava_connections (
            user_id INTEGER PRIMARY KEY,
            strava_athlete_id INTEGER,
            access_token TEXT,
            refresh_token TEXT,
            token_expires_at INTEGER,
            last_sync TEXT
        )"""
    )
    conn.commit()
    conn.close()
    return connect


def test_strava_configuration_requires_valid_token_key(monkeypatch):
    monkeypatch.setattr(strava_service, "_get_client_id", lambda: "client-id")
    monkeypatch.setattr(strava_service, "_get_client_secret", lambda: "client-secret")

    monkeypatch.setattr(strava_service, "_get_token_key", lambda: None)
    assert strava_service.is_strava_configured() is False

    monkeypatch.setattr(strava_service, "_get_token_key", lambda: "not-a-fernet-key")
    assert strava_service.is_strava_configured() is False

    valid_key = Fernet.generate_key().decode()
    monkeypatch.setattr(strava_service, "_get_token_key", lambda: valid_key)
    assert strava_service.is_strava_configured() is True


@pytest.mark.parametrize(
    ("token_key", "error_pattern"),
    [
        (None, "STRAVA_TOKEN_KEY is required"),
        ("not-a-fernet-key", "STRAVA_TOKEN_KEY must be a valid Fernet key"),
    ],
)
def test_save_connection_fails_closed_without_valid_key(
    monkeypatch, token_key, error_pattern
):
    monkeypatch.setattr(strava_service, "_get_token_key", lambda: token_key)
    monkeypatch.setattr(
        strava_service,
        "get_connection",
        lambda: pytest.fail("database must not be opened without a valid token key"),
    )

    with pytest.raises(strava_service.StravaTokenConfigurationError, match=error_pattern):
        strava_service._save_connection(1, 2, "access-secret", "refresh-secret", 123)


def test_save_connection_encrypts_tokens_and_reads_them_back(monkeypatch, tmp_path):
    database_path = tmp_path / "strava.db"
    connect = _strava_connection_factory(database_path)
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(strava_service, "_get_token_key", lambda: key)
    monkeypatch.setattr(strava_service, "get_connection", connect)

    strava_service._save_connection(
        7, 42, "access-secret", "refresh-secret", 2_000_000_000
    )

    conn = connect()
    stored = conn.execute(
        "SELECT access_token, refresh_token FROM strava_connections WHERE user_id = 7"
    ).fetchone()
    conn.close()
    assert stored["access_token"].startswith(strava_service._ENC_PREFIX)
    assert stored["refresh_token"].startswith(strava_service._ENC_PREFIX)
    assert "access-secret" not in stored["access_token"]
    assert "refresh-secret" not in stored["refresh_token"]

    connection = strava_service.get_strava_connection(7)
    assert connection["access_token"] == "access-secret"
    assert connection["refresh_token"] == "refresh-secret"


def test_encrypted_tokens_with_wrong_key_require_reconnect(monkeypatch, tmp_path):
    database_path = tmp_path / "strava.db"
    connect = _strava_connection_factory(database_path)
    original_key = Fernet.generate_key().decode()
    monkeypatch.setattr(strava_service, "_get_token_key", lambda: original_key)
    monkeypatch.setattr(strava_service, "get_connection", connect)
    strava_service._save_connection(
        7, 42, "access-secret", "refresh-secret", 2_000_000_000
    )

    wrong_key = Fernet.generate_key().decode()
    monkeypatch.setattr(strava_service, "_get_token_key", lambda: wrong_key)
    connection = strava_service.get_strava_connection(7)

    assert connection["access_token"] is None
    assert connection["refresh_token"] is None
    assert strava_service._get_valid_token(7) is None
    with pytest.raises(ValueError, match=r"No valid Strava token\. Please reconnect\."):
        strava_service.import_strava_activities(7)


def test_legacy_plaintext_tokens_are_migrated_on_read(monkeypatch, tmp_path):
    database_path = tmp_path / "strava.db"
    connect = _strava_connection_factory(database_path)
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(strava_service, "_get_token_key", lambda: key)
    monkeypatch.setattr(strava_service, "get_connection", connect)

    conn = connect()
    conn.execute(
        """INSERT INTO strava_connections
           (user_id, strava_athlete_id, access_token, refresh_token, token_expires_at)
           VALUES (?, ?, ?, ?, ?)""",
        (7, 42, "legacy-access", "legacy-refresh", 2_000_000_000),
    )
    conn.commit()
    conn.close()

    connection = strava_service.get_strava_connection(7)
    assert connection["access_token"] == "legacy-access"
    assert connection["refresh_token"] == "legacy-refresh"

    conn = connect()
    stored = conn.execute(
        "SELECT access_token, refresh_token FROM strava_connections WHERE user_id = 7"
    ).fetchone()
    conn.close()
    assert stored["access_token"].startswith(strava_service._ENC_PREFIX)
    assert stored["refresh_token"].startswith(strava_service._ENC_PREFIX)


def test_days_ago_unix_timestamp_is_deterministic(monkeypatch):
    monkeypatch.setattr(strava_service, "date", _FixedDate)
    ts = strava_service._days_ago_unix_timestamp(30)
    expected = int(datetime(2026, 2, 23, tzinfo=timezone.utc).timestamp())
    assert ts == expected


def test_days_ago_unix_timestamp_clamps_negative_days(monkeypatch):
    monkeypatch.setattr(strava_service, "date", _FixedDate)
    assert strava_service._days_ago_unix_timestamp(-5) == strava_service._days_ago_unix_timestamp(0)


def test_days_ago_unix_timestamp_gets_older_with_larger_day_offset(monkeypatch):
    monkeypatch.setattr(strava_service, "date", _FixedDate)
    assert strava_service._days_ago_unix_timestamp(14) < strava_service._days_ago_unix_timestamp(7)


# ── Activity mapping tests ───────────────────────────────────────────────

def test_map_strava_activity_running():
    """Full pipeline: Strava Run → mapped exercise dict."""
    activity = {
        "type": "Run",
        "moving_time": 1800,  # 30 min
        "start_date_local": "2026-03-20T07:30:00Z",
        "distance": 5000,  # 5 km
        "average_heartrate": 155,
        "max_heartrate": 180,
        "calories": 320,
        "name": "Morning jog",
        "id": 12345,
    }
    result = strava_service._map_strava_activity(activity)
    assert result["exercise_type"] == "run"
    assert result["duration_min"] == 30
    assert result["distance_km"] == 5.0
    assert result["exercise_date"] == "2026-03-20"
    assert result["calories"] == 320
    assert result["avg_hr"] == 155
    assert result["intensity"] == "vigorous"  # 155/180 = 86% > 77%
    assert "Morning jog" in result["notes"]


def test_map_strava_activity_ride_kilojoules():
    """Cycling: kilojoules should convert to kcal."""
    activity = {
        "type": "Ride",
        "moving_time": 3600,
        "start_date_local": "2026-03-20T08:00:00Z",
        "distance": 30000,
        "kilojoules": 600,
        "name": "Evening ride",
        "id": 12346,
    }
    result = strava_service._map_strava_activity(activity)
    assert result["exercise_type"] == "cycle"
    assert result["distance_km"] == 30.0
    assert result["calories"] == round(600 * 0.239)  # kJ → kcal


def test_map_strava_activity_no_hr_uses_type_fallback():
    """Without HR data, intensity is inferred from activity type."""
    walk = {"type": "Walk", "moving_time": 1200, "start_date_local": "2026-03-20T10:00:00Z", "distance": 2000, "name": "", "id": 1}
    run = {"type": "Run", "moving_time": 1200, "start_date_local": "2026-03-20T10:00:00Z", "distance": 3000, "name": "", "id": 2}
    yoga = {"type": "Yoga", "moving_time": 1800, "start_date_local": "2026-03-20T10:00:00Z", "distance": 0, "name": "", "id": 3}

    assert strava_service._map_strava_activity(walk)["intensity"] == "light"
    assert strava_service._map_strava_activity(run)["intensity"] == "vigorous"
    assert strava_service._map_strava_activity(yoga)["intensity"] == "light"


def test_classify_intensity_hr_zones():
    """HR-based classification — 77%+ vigorous, 64-76% moderate, <64% light."""
    assert strava_service._classify_intensity(140, 180, "Run") == "vigorous"  # 77.8%
    assert strava_service._classify_intensity(100, 180, "Run") == "light"  # 55.6%
    assert strava_service._classify_intensity(150, 180, "Run") == "vigorous"  # 83.3%
    assert strava_service._classify_intensity(120, 180, "Run") == "moderate"  # 66.7%


def test_map_strava_activity_minimum_duration():
    """Activities with very short moving_time get clamped to 1 minute."""
    activity = {
        "type": "Run",
        "moving_time": 10,  # 10 seconds
        "start_date_local": "2026-03-20T10:00:00Z",
        "distance": 50,
        "name": "Quick sprint",
        "id": 999,
    }
    result = strava_service._map_strava_activity(activity)
    assert result["duration_min"] >= 1
