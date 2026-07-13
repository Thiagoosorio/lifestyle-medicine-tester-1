from urllib.parse import parse_qs, urlparse

import pytest

from config.env_flags import is_demo_mode
from config.runtime_config import RuntimeConfigError, load_admin_bootstrap_config
from services.strava_service import get_strava_auth_url


def test_is_demo_mode_defaults_to_false(monkeypatch):
    monkeypatch.delenv("DEMO_MODE", raising=False)
    assert is_demo_mode() is False


def test_is_demo_mode_truthy_values(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    assert is_demo_mode() is True


def test_admin_bootstrap_config_requires_username_and_password(monkeypatch):
    monkeypatch.setenv("BOOTSTRAP_ADMIN_USERNAME", "TG")
    monkeypatch.delenv("BOOTSTRAP_ADMIN_PASSWORD", raising=False)

    with pytest.raises(RuntimeConfigError, match="must be set together"):
        load_admin_bootstrap_config()


def test_admin_bootstrap_config_does_not_expose_password_in_repr(monkeypatch):
    monkeypatch.setenv("BOOTSTRAP_ADMIN_USERNAME", "TG")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "AdminPass123")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_REVISION", "credential-v1")
    monkeypatch.setenv("ACCOUNT_RESET_REVISION", "reset-v1")

    config = load_admin_bootstrap_config()

    assert config is not None
    assert config.username == "TG"
    assert config.password == "AdminPass123"
    assert config.bootstrap_revision == "credential-v1"
    assert config.account_reset_revision == "reset-v1"
    assert "AdminPass123" not in repr(config)


def test_strava_auth_url_includes_state(monkeypatch):
    monkeypatch.setenv("STRAVA_CLIENT_ID", "12345")
    url = get_strava_auth_url("http://localhost:8501/", state="abc-state")
    assert url is not None

    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    assert params["client_id"] == ["12345"]
    assert params["state"] == ["abc-state"]
    assert params["response_type"] == ["code"]
