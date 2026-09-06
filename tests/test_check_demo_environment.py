"""
MRPL Phase 5 — demo environment check tests.

Focused, offline tests of the preflight's decision logic. The pure checks
(providers, dependency gate, verdict, report formatting) are exercised without
touching a real database or Qdrant instance.
"""

from scripts.check_demo_environment import (
    Check,
    FAIL,
    OK,
    WARN,
    check_database,
    check_dependencies,
    check_embeddings_provider,
    check_llm_provider,
    format_report,
    is_ready,
)


def test_llm_provider_mock_is_ok(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    c = check_llm_provider()
    assert c.status == OK
    assert "mock" in c.detail


def test_llm_provider_non_mock_warns_but_does_not_block(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    assert check_llm_provider().status == WARN
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    assert check_llm_provider().status == WARN


def test_embeddings_provider_local_is_ok(monkeypatch):
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "local")
    assert check_embeddings_provider().status == OK
    monkeypatch.delenv("EMBEDDINGS_PROVIDER", raising=False)
    assert check_embeddings_provider().status == OK
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "openai")
    assert check_embeddings_provider().status == WARN


def test_dependencies_present_in_this_environment():
    # The test environment installs requirements.txt, so all core deps resolve.
    assert check_dependencies().status == OK


def test_database_missing_url_fails_without_leaking(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    c = check_database()
    assert c.status == FAIL
    assert "DATABASE_URL is not set" in c.detail


def test_database_error_never_echoes_the_url(monkeypatch):
    secret = "postgresql+psycopg2://user:sup3rsecret@db.internal:5432/prod"
    monkeypatch.setenv("DATABASE_URL", secret)

    def boom(url, *a, **k):
        raise RuntimeError("connection refused to db.internal")

    monkeypatch.setattr("sqlalchemy.create_engine", boom)
    c = check_database()
    assert c.status == FAIL
    # scheme is fine to show; credentials/host/password must never appear.
    assert "postgresql" in c.detail
    assert "sup3rsecret" not in c.detail
    assert "user" not in c.detail
    assert "db.internal" not in c.detail


def test_is_ready_only_blocks_on_fail():
    ok_warn = [Check("a", OK, ""), Check("b", WARN, "")]
    assert is_ready(ok_warn) is True
    assert is_ready(ok_warn + [Check("c", FAIL, "")]) is False


def test_format_report_verdict_lines():
    ready = format_report([Check("a", OK, "x"), Check("b", WARN, "y")])
    assert "DEMO ENVIRONMENT READY" in ready
    assert "NOT READY" not in ready

    blocked = format_report([Check("a", FAIL, "x")])
    assert "DEMO ENVIRONMENT NOT READY" in blocked
    assert "Blocking: a" in blocked
