from urllib.parse import parse_qs, urlparse

from config.env_flags import is_demo_mode
from services.strava_service import get_strava_auth_url


def test_is_demo_mode_defaults_to_false(monkeypatch):
    monkeypatch.delenv("DEMO_MODE", raising=False)
    assert is_demo_mode() is False


def test_is_demo_mode_truthy_values(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    assert is_demo_mode() is True


def test_strava_auth_url_includes_state(monkeypatch):
    monkeypatch.setenv("STRAVA_CLIENT_ID", "12345")
    url = get_strava_auth_url("http://localhost:8501/", state="abc-state")
    assert url is not None

    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    assert params["client_id"] == ["12345"]
    assert params["state"] == ["abc-state"]
    assert params["response_type"] == ["code"]
