"""
Milestone 4 — API security hardening regression tests.

Focused on: no secret / credential / stack-trace leakage through error paths,
and step-audit input redaction (the DB handle is never persisted).
"""

import json

from src.services.step_audit_service import create_step_log


def test_step_audit_strips_db_handle(db_session):
    """The live DB session handed to tools must never be persisted."""

    class _FakeDB:
        def __repr__(self):
            return "postgresql://user:password@host/db"

    row = create_step_log(
        db=db_session,
        agent_run_id=1,
        step_id=1,
        tool_name="ml_analysis",
        input_payload={"query": "hello", "db": _FakeDB(), "secret": "x"},
        output_payload={"ok": True},
        status="success",
        execution_time_ms=10,
        retry_count=0,
    )

    stored = json.loads(row.input_payload)
    assert "db" not in stored
    assert "password@host" not in row.input_payload
    # Non-sensitive fields are preserved.
    assert stored["query"] == "hello"


def test_config_error_message_has_no_secret_value(monkeypatch):
    from src.config import ConfigError, validate_config

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-should-not-appear")
    try:
        validate_config(raise_on_error=True)
    except ConfigError as exc:
        assert "sk-should-not-appear" not in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ConfigError")
