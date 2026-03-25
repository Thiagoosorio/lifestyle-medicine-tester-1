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
