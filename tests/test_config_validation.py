"""
Milestone 4 — configuration validation tests (Phase 6).

Confirms required config is enforced, fallback-supported config is optional,
and secret VALUES are never exposed in reports/snapshots.
"""

import pytest

from src.config import (
    ConfigError,
    safe_config_snapshot,
    validate_config,
)


def test_valid_config_passes(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost/db")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-real-key")
    report = validate_config(raise_on_error=True)
    assert report["ok"] is True
    assert report["missing_required"] == []


def test_openai_is_optional_fallback(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost/db")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    # Must NOT raise — OpenAI is fallback-supported (Ollama/offline).
    report = validate_config(raise_on_error=True)
    assert report["ok"] is True
    assert "OPENAI_API_KEY" in report["missing_fallback"]


def test_missing_required_raises(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ConfigError) as exc:
        validate_config(raise_on_error=True)
    assert "DATABASE_URL" in str(exc.value)


def test_missing_required_non_raising(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    report = validate_config(raise_on_error=False)
    assert report["ok"] is False
    assert "DATABASE_URL" in report["missing_required"]


def test_snapshot_redacts_secret_values(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:SECRETPW@host/db")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-SECRETKEY")
    snap = safe_config_snapshot()

    # Secrets are reduced to a presence flag, never their value.
    assert snap["OPENAI_API_KEY"] == {"present": True}
    assert snap["DATABASE_URL"] == {"present": True}

    flat = str(snap)
    assert "SECRETPW" not in flat
    assert "sk-SECRETKEY" not in flat
