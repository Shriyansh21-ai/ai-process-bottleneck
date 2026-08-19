"""
Milestone 5 — CORS configuration safety.

Verifies the environment-driven CORS behaviour added for production hardening:
a wildcard origin must NOT be paired with credentials, while an explicit
allow-list enables credentials.
"""

import importlib

import pytest


def _reload_config(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)
    else:
        monkeypatch.setenv("CORS_ALLOW_ORIGINS", value)
    import src.config as config
    importlib.reload(config)
    return config


def test_default_is_wildcard_without_credentials(monkeypatch):
    config = _reload_config(monkeypatch, None)
    assert config.get_cors_origins() == ["*"]
    # Wildcard + credentials is unsafe / browser-invalid -> must be disabled.
    assert config.cors_allow_credentials() is False


def test_explicit_wildcard_disables_credentials(monkeypatch):
    config = _reload_config(monkeypatch, "*")
    assert config.get_cors_origins() == ["*"]
    assert config.cors_allow_credentials() is False


def test_explicit_allowlist_enables_credentials(monkeypatch):
    config = _reload_config(monkeypatch, "https://a.example.com, https://b.example.com")
    assert config.get_cors_origins() == [
        "https://a.example.com",
        "https://b.example.com",
    ]
    assert config.cors_allow_credentials() is True


@pytest.fixture(autouse=True)
def _restore_config():
    """Reload config back to a clean default after each test."""
    yield
    import src.config as config
    importlib.reload(config)
