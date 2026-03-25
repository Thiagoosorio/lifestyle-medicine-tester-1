from datetime import date, datetime, timezone

import services.strava_service as strava_service


class _FixedDate(date):
    @classmethod
    def today(cls):
        return cls(2026, 3, 25)


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
