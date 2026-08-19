"""
Test fixtures for the AgentRun management + auth APIs.

Everything runs against an in-memory SQLite database so tests are fast,
deterministic and require neither PostgreSQL nor the OpenAI/Ollama stack.

Milestone 6: the /runs and /observability routes now require authentication.
The legacy ``client`` / ``obs_client`` fixtures therefore authenticate as an
ADMIN (owner scope = all runs) so pre-Milestone-6 behaviour/tests are preserved.
Real multi-user auth/authorization tests use the ``auth_client`` fixture, which
performs genuine register/login against the test DB with no dependency overrides.
"""

import json
import os

# src.db.session reads DATABASE_URL at import time. Provide a lazy,
# never-connected URL so importing the router doesn't blow up. The actual
# test database is a separate SQLite engine wired via a dependency override.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg2://test:test@localhost:5432/testdb",
)
# Disable rate limiting for deterministic tests (must be set before the
# rate_limiter module is imported).
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
# Deterministic JWT signing for tests.
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret")

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.db.base import Base
import src.db.models  # noqa: F401 register all tables (users, agent_runs, ...)
from src.db.models.agent_run import AgentRun
from src.db.models.step_execution import StepExecution
from src.db.models.user import User
from src.core.auth import get_current_active_user, get_current_admin_user
from src.core.security import hash_password
from src.db.session import get_db as real_get_db
from src.api.auth import router as auth_router
from src.api.routes.agent_runs import router as agent_runs_router
from src.api.routes.agent_observability import (
    router as agent_observability_router,
)


test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def db_session():
    """Fresh schema + session per test."""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ------------------------------------------------------------------
# Legacy fixtures — authenticated as an admin (owner scope = all runs)
# ------------------------------------------------------------------

_ADMIN_STUB = User(
    id=1, email="admin@test.local", hashed_password="x",
    is_active=True, is_admin=True,
)


@pytest.fixture
def client(db_session):
    app = FastAPI()
    app.include_router(agent_runs_router)
    app.dependency_overrides[real_get_db] = _override_get_db
    # Authenticate every request as an admin so legacy tests see all runs.
    app.dependency_overrides[get_current_active_user] = lambda: _ADMIN_STUB
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def obs_client(db_session):
    app = FastAPI()
    app.include_router(agent_runs_router)
    app.include_router(agent_observability_router)
    app.dependency_overrides[real_get_db] = _override_get_db
    app.dependency_overrides[get_current_active_user] = lambda: _ADMIN_STUB
    app.dependency_overrides[get_current_admin_user] = lambda: _ADMIN_STUB
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ------------------------------------------------------------------
# Real-auth fixture (no overrides) for Milestone 6 auth/authz tests
# ------------------------------------------------------------------

@pytest.fixture
def auth_client(db_session):
    """A client with auth + runs + observability routers and NO auth override."""
    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(agent_runs_router)
    app.include_router(agent_observability_router)
    app.dependency_overrides[real_get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def register_and_login(client, email, password="Password123!", is_admin=False):
    """Register a user (optionally promoting to admin) and return an auth header."""
    resp = client.post("/auth/register", json={"email": email, "password": password})
    assert resp.status_code in (200, 201, 409), resp.text
    if is_admin:
        # Promote directly in the DB — admin is never grantable via the API.
        db = TestingSessionLocal()
        try:
            user = db.query(User).filter(User.email == email.lower()).first()
            user.is_admin = True
            db.commit()
        finally:
            db.close()
    token = client.post(
        "/auth/login", data={"username": email, "password": password}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def user_id_for(email):
    db = TestingSessionLocal()
    try:
        u = db.query(User).filter(User.email == email.lower()).first()
        return u.id if u else None
    finally:
        db.close()


# ------------------------------------------------------------------
# Seed helpers
# ------------------------------------------------------------------

def make_run(
    session_id="s1",
    user_query="Analyze the pipeline bottleneck",
    status="success",
    plan=None,
    execution_result=None,
    verification_result=None,
    confidence=None,
    approved=None,
    duration_ms=None,
    steps_total=None,
    steps_success=None,
    steps_failed=None,
    retry_count=None,
    created_at=None,
    started_at=None,
    completed_at=None,
    user_id=None,
):
    run = AgentRun(
        user_id=user_id,
        session_id=session_id,
        user_query=user_query,
        status=status,
        plan=json.dumps(plan) if plan is not None else None,
        execution_result=(
            json.dumps(execution_result)
            if execution_result is not None
            else None
        ),
        verification_result=(
            json.dumps(verification_result)
            if verification_result is not None
            else None
        ),
        confidence=confidence,
        approved=approved,
        duration_ms=duration_ms,
        steps_total=steps_total,
        steps_success=steps_success,
        steps_failed=steps_failed,
        retry_count=retry_count,
    )
    if created_at is not None:
        run.created_at = created_at
    if started_at is not None:
        run.started_at = started_at
    if completed_at is not None:
        run.completed_at = completed_at
    return run


def make_step(
    agent_run_id,
    step_id=1,
    tool_name="ml_analysis",
    status="success",
    error=None,
    execution_time_ms=100,
    retry_count=0,
):
    return StepExecution(
        agent_run_id=agent_run_id,
        step_id=step_id,
        tool_name=tool_name,
        input_payload="{}",
        output_payload="{}",
        status=status,
        error=error,
        execution_time_ms=execution_time_ms,
        retry_count=retry_count,
    )


@pytest.fixture
def run_factory():
    """Expose the ``make_run`` builder to tests without cross-module imports."""
    return make_run


@pytest.fixture
def step_factory():
    """Expose the ``make_step`` builder to tests."""
    return make_step


@pytest.fixture
def seeded(db_session):
    """A small, deterministic set of runs covering statuses and sessions."""
    runs = [
        make_run(
            session_id="alpha",
            user_query="Find the slowest task",
            status="success",
            plan={"steps": [{"tool": "sql"}, {"tool": "ml"}]},
            execution_result={"results": [1, 2, 3]},
            verification_result={"approved": True, "confidence": 0.9},
            confidence=0.9,
            approved=True,
            duration_ms=1200,
            steps_total=2,
        ),
        make_run(
            session_id="alpha",
            user_query="Predict rework probability",
            status="failed",
            confidence=0.2,
            approved=False,
            duration_ms=800,
            steps_total=1,
        ),
        make_run(
            session_id="beta",
            user_query="Summarize waiting time",
            status="running",
        ),
        make_run(
            session_id="beta",
            user_query="Recommend resource allocation",
            status="approval_required",
        ),
        make_run(
            session_id="gamma",
            user_query="Analyze currency volatility risk",
            status="success",
            duration_ms=400,
            steps_total=3,
            approved=True,
            confidence=0.81,
        ),
    ]
    db_session.add_all(runs)
    db_session.commit()
    return runs
