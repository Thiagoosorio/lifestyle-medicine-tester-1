import services.recovery_service as recovery
from datetime import date, timedelta


def test_recovery_renormalizes_available_components(monkeypatch):
    components = {
        key: {"score": 50, "raw": None, "label": key, "icon": ""}
        for key in recovery.RECOVERY_WEIGHTS
    }
    components["mood"] = {"score": 80, "raw": 8, "label": "Mood", "icon": ""}
    monkeypatch.setattr(recovery, "get_recovery_components", lambda _user_id: components)

    result = recovery.calculate_recovery_score(1)

    assert result["score"] == 80
    assert result["coverage_pct"] == 10
    assert result["zone"]["label"] == "Limited Data"


def test_stress_management_rating_is_not_inverted(monkeypatch):
    class _Connection:
        def execute(self, *_args, **_kwargs):
            return self

        def fetchone(self):
            return {"stress_rating": 10, "checkin_date": date.today().isoformat()}

        def close(self):
            pass

    monkeypatch.setattr(recovery, "get_connection", _Connection)

    component = recovery._get_stress_component(1)

    assert component["score"] == 100
    assert component["label"] == "Stress Management"


def test_stale_sleep_is_not_used_as_current_readiness(monkeypatch):
    class _Connection:
        def execute(self, *_args, **_kwargs):
            return self

        def fetchone(self):
            return {
                "sleep_score": 95,
                "sleep_date": (date.today() - timedelta(days=10)).isoformat(),
            }

        def close(self):
            pass

    monkeypatch.setattr(recovery, "get_connection", _Connection)

    component = recovery._get_sleep_component(1)

    assert component["raw"] is None


def test_stale_checkin_is_not_used_for_mood_or_stress(monkeypatch):
    stale_date = (date.today() - timedelta(days=10)).isoformat()

    class _Connection:
        def execute(self, *_args, **_kwargs):
            return self

        def fetchone(self):
            return {"mood": 9, "stress_rating": 9, "checkin_date": stale_date}

        def close(self):
            pass

    monkeypatch.setattr(recovery, "get_connection", _Connection)

    assert recovery._get_mood_component(1)["raw"] is None
    assert recovery._get_stress_component(1)["raw"] is None
