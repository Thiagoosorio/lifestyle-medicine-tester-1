import services.recovery_service as recovery


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
            return {"stress_rating": 10}

        def close(self):
            pass

    monkeypatch.setattr(recovery, "get_connection", _Connection)

    component = recovery._get_stress_component(1)

    assert component["score"] == 100
    assert component["label"] == "Stress Management"
