"""
Milestone 6 — authorization, user isolation and IDOR tests.

Two users (A, B) each own runs. Verifies each user only ever sees their own
runs across every /runs endpoint, that cross-user access returns 404 (no
existence leak / IDOR), that session ids are not an authorization boundary, and
that admins can see everything while /observability is admin-only.
"""

import pytest

from src.db.models.agent_run import AgentRun
from tests.conftest import (
    TestingSessionLocal,
    make_run,
    register_and_login,
    user_id_for,
)


@pytest.fixture
def two_users(auth_client, db_session):
    """Register users A, B (+ an admin) and seed owned runs. Returns context."""
    a = register_and_login(auth_client, "usera@example.com")
    b = register_and_login(auth_client, "userb@example.com")
    admin = register_and_login(auth_client, "admin@example.com", is_admin=True)

    a_id = user_id_for("usera@example.com")
    b_id = user_id_for("userb@example.com")

    db = TestingSessionLocal()
    try:
        db.add_all([
            make_run(session_id="sess-a", user_query="A run one",
                     status="success", user_id=a_id, duration_ms=100),
            make_run(session_id="sess-a", user_query="A run two",
                     status="failed", user_id=a_id, duration_ms=200),
            make_run(session_id="sess-b", user_query="B run one",
                     status="success", user_id=b_id, duration_ms=300),
            # A legacy, unowned run (user_id NULL) — visible only to admins.
            make_run(session_id="sess-legacy", user_query="legacy",
                     status="success", user_id=None),
        ])
        db.commit()
        rows = {r.user_query: r.id for r in db.query(AgentRun).all()}
    finally:
        db.close()

    return {
        "a": a, "b": b, "admin": admin,
        "a_id": a_id, "b_id": b_id, "run_ids": rows,
    }


# ------------------------------------------------------------------
# LIST isolation
# ------------------------------------------------------------------

def test_list_runs_scoped_to_owner(auth_client, two_users):
    a_runs = auth_client.get("/runs", headers=two_users["a"]).json()["items"]
    b_runs = auth_client.get("/runs", headers=two_users["b"]).json()["items"]

    a_queries = {r["user_query"] for r in a_runs}
    b_queries = {r["user_query"] for r in b_runs}

    assert a_queries == {"A run one", "A run two"}
    assert b_queries == {"B run one"}
    # No cross-contamination, no legacy/unowned run leaking to normal users.
    assert "B run one" not in a_queries
    assert "legacy" not in a_queries and "legacy" not in b_queries


def test_admin_sees_all_runs(auth_client, two_users):
    admin_runs = auth_client.get("/runs", headers=two_users["admin"]).json()["items"]
    queries = {r["user_query"] for r in admin_runs}
    assert {"A run one", "A run two", "B run one", "legacy"} <= queries


# ------------------------------------------------------------------
# DETAIL / IDOR
# ------------------------------------------------------------------

def test_owner_can_read_own_run(auth_client, two_users):
    a_run_id = two_users["run_ids"]["A run one"]
    resp = auth_client.get(f"/runs/{a_run_id}", headers=two_users["a"])
    assert resp.status_code == 200
    assert resp.json()["user_query"] == "A run one"


def test_idor_cross_user_detail_returns_404(auth_client, two_users):
    # B tries to read A's run by id -> 404, NOT 200, NOT 403 with details.
    a_run_id = two_users["run_ids"]["A run one"]
    resp = auth_client.get(f"/runs/{a_run_id}", headers=two_users["b"])
    assert resp.status_code == 404
    assert "A run one" not in resp.text


def test_admin_can_read_any_run(auth_client, two_users):
    a_run_id = two_users["run_ids"]["A run one"]
    resp = auth_client.get(f"/runs/{a_run_id}", headers=two_users["admin"])
    assert resp.status_code == 200


# ------------------------------------------------------------------
# SESSION isolation
# ------------------------------------------------------------------

def test_session_endpoint_does_not_leak_across_users(auth_client, two_users):
    # B requests A's session id -> gets nothing (session_id is not authz).
    resp = auth_client.get("/runs/session/sess-a", headers=two_users["b"])
    assert resp.status_code == 200
    assert resp.json()["items"] == []
    # A gets their own session runs.
    a_resp = auth_client.get("/runs/session/sess-a", headers=two_users["a"])
    assert {r["user_query"] for r in a_resp.json()["items"]} == {
        "A run one", "A run two"
    }


# ------------------------------------------------------------------
# SEARCH isolation
# ------------------------------------------------------------------

def test_search_scoped_to_owner(auth_client, two_users):
    # B searches for a term only present in A's runs -> no results.
    resp = auth_client.get("/runs/search", params={"q": "run"}, headers=two_users["b"])
    assert resp.status_code == 200
    assert {r["user_query"] for r in resp.json()["items"]} == {"B run one"}


# ------------------------------------------------------------------
# STATISTICS isolation
# ------------------------------------------------------------------

def test_statistics_scoped_to_owner(auth_client, two_users):
    a_stats = auth_client.get("/runs/statistics", headers=two_users["a"]).json()
    b_stats = auth_client.get("/runs/statistics", headers=two_users["b"]).json()
    assert a_stats["total_runs"] == 2
    assert b_stats["total_runs"] == 1
    # Admin sees system-wide totals (A + B + legacy = 4).
    admin_stats = auth_client.get(
        "/runs/statistics", headers=two_users["admin"]
    ).json()
    assert admin_stats["total_runs"] == 4


# ------------------------------------------------------------------
# UNAUTHENTICATED access
# ------------------------------------------------------------------

@pytest.mark.parametrize("path", [
    "/runs", "/runs/statistics", "/runs/search?q=x",
    "/runs/session/sess-a", "/runs/status/success", "/runs/1",
])
def test_runs_require_authentication(auth_client, path):
    assert auth_client.get(path).status_code == 401


# ------------------------------------------------------------------
# OBSERVABILITY is admin-only
# ------------------------------------------------------------------

def test_observability_forbidden_for_normal_user(auth_client, two_users):
    resp = auth_client.get("/observability/overview", headers=two_users["a"])
    assert resp.status_code == 403


def test_observability_allowed_for_admin(auth_client, two_users):
    resp = auth_client.get("/observability/overview", headers=two_users["admin"])
    assert resp.status_code == 200


def test_observability_requires_auth(auth_client):
    assert auth_client.get("/observability/overview").status_code == 401
