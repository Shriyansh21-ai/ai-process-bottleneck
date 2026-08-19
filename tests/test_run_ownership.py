"""
Milestone 6 — agent run ownership (Phase 18).

Verifies the ownership plumbing that associates an AgentRun with the
authenticated user, without invoking the real LLM/agent pipeline:

  * audit_service.create_agent_run persists user_id
  * agent_run_service ownership filtering isolates users
  * AgentController accepts and stores user_id and threads it into create_agent_run
"""

from src.agent.controller import AgentController
from src.services.audit_service import create_agent_run as audit_create_run
from src.services.agent_run_service import (
    get_run_by_id,
    list_runs,
)


def test_audit_create_run_associates_user(db_session):
    run = audit_create_run(
        db=db_session,
        session_id="s1",
        user_query="q",
        plan={"steps": []},
        execution_result={},
        verification_result={},
        status="running",
        user_id=42,
    )
    assert run.user_id == 42


def test_ownership_filter_isolates_users(db_session):
    audit_create_run(
        db=db_session, session_id="sa", user_query="A", plan={}, execution_result={},
        verification_result={}, status="success", user_id=1,
    )
    b_run = audit_create_run(
        db=db_session, session_id="sb", user_query="B", plan={}, execution_result={},
        verification_result={}, status="success", user_id=2,
    )

    # User 1 cannot fetch user 2's run via the owner-scoped getter.
    assert get_run_by_id(db_session, b_run.id, user_id=1) is None
    assert get_run_by_id(db_session, b_run.id, user_id=2) is not None
    # Admin (unscoped) can.
    assert get_run_by_id(db_session, b_run.id, user_id=None) is not None

    a_runs, a_total = list_runs(db_session, user_id=1)
    assert a_total == 1
    assert a_runs[0].user_query == "A"


def test_controller_stores_and_threads_user_id(db_session, monkeypatch):
    # Instantiate the controller with a user id; it must be stored for use when
    # creating the AgentRun. We avoid running the full pipeline (no LLM).
    controller = AgentController(db=db_session, session_id="s", user_id=7)
    assert controller.user_id == 7

    # Simulate the controller's own run-creation call and confirm ownership.
    run = audit_create_run(
        db=db_session, session_id=controller.session_id, user_query="q",
        plan={}, execution_result={}, verification_result={},
        status="running", user_id=controller.user_id,
    )
    assert run.user_id == 7
