"""
Milestone 4 — health & readiness endpoint tests.

SQLite-only, no Postgres/OpenAI required. The database dependency is overridden
to simulate both an available and an unavailable database.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.health import router as health_router
from src.db.session import get_db


def _ok_db():
    class _OK:
        def execute(self, *args, **kwargs):
            return 1

    yield _OK()


def _bad_db():
    class _Bad:
        def execute(self, *args, **kwargs):
            raise Exception(
                "could not connect: host=db password=supersecret"
            )

    yield _Bad()


def _client(db_override):
    app = FastAPI()
    app.include_router(health_router)
    app.dependency_overrides[get_db] = db_override
    return TestClient(app)


# ------------------------------------------------------------------
# liveness
# ------------------------------------------------------------------

def test_health_liveness():
    resp = _client(_ok_db).get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


# ------------------------------------------------------------------
# readiness — ready
# ------------------------------------------------------------------

def test_readiness_ready():
    resp = _client(_ok_db).get("/health/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["checks"]["database"] == "available"
    assert body["checks"]["configuration"] == "ok"


# ------------------------------------------------------------------
# readiness — database unavailable -> 503
# ------------------------------------------------------------------

def test_readiness_database_unavailable():
    resp = _client(_bad_db).get("/health/ready")
    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "not_ready"
    assert body["checks"]["database"] == "unavailable"


def test_readiness_never_leaks_db_error():
    """The raw DB error (with the password) must never reach the client."""
    resp = _client(_bad_db).get("/health/ready")
    assert "supersecret" not in resp.text
    assert "password" not in resp.text.lower()
