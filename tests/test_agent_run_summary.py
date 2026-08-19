"""
Milestone 2 tests — agent run execution summary / telemetry.

These exercise ``finalize_agent_run_summary`` directly (fast, deterministic,
no LLM / Postgres / Qdrant) plus the Milestone 1 ``/runs`` endpoints to prove
the enriched summary surfaces through the existing API.
"""

from datetime import datetime, timedelta, timezone

import pytest

from src.services.agent_run_service import (
    finalize_agent_run_summary,
    get_run_by_id,
)


# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------

def _running_run(db, run_factory, started_secs_ago=2, **kwargs):
    run = run_factory(status="running", **kwargs)
    run.started_at = datetime.now(timezone.utc) - timedelta(
        seconds=started_secs_ago
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def _seed_steps(db, step_factory, run_id, specs):
    for i, (tool, status) in enumerate(specs, start=1):
        db.add(step_factory(run_id, step_id=i, tool_name=tool, status=status))
    db.commit()


# ------------------------------------------------------------------
# 1. Successful execution
# ------------------------------------------------------------------

def test_successful_execution_summary(db_session, run_factory, step_factory):
    run = _running_run(db_session, run_factory)
    _seed_steps(
        db_session,
        step_factory,
        run.id,
        [
            ("rag_retrieval", "success"),
            ("memory_tool", "success"),
            ("ml_analysis", "success"),
        ],
    )

    execution_result = {
        "goal": "analyze bottlenecks",
        "results": {
            "1": {"retry_count": 0},
            "2": {"retry_count": 1},
            "3": {"retry_count": 0},
        },
    }
    verification = {"confidence": 0.92, "approved": True, "issues": []}

    finalize_agent_run_summary(
        db=db_session,
        agent_run_id=run.id,
        status="success",
        execution_result=execution_result,
        verification_result=verification,
        plan={"steps": [1, 2, 3]},
        llm_meta={"model": "gpt-4o-mini", "mode": "openai"},
        final_response="Bottleneck is at station 4.",
    )

    r = get_run_by_id(db_session, run.id)
    assert r.status == "completed"
    assert r.started_at is not None
    assert r.completed_at is not None
    assert r.duration_ms is not None and r.duration_ms > 0
    assert r.steps_total == 3
    assert r.steps_success == 3
    assert r.steps_failed == 0
    assert r.retry_count == 1
    assert set(r.tools_used) == {"rag_retrieval", "memory_tool", "ml_analysis"}
    assert r.rag_used is True
    assert r.memory_used is True
    assert r.confidence == 0.92
    assert r.approved is True
    assert r.final_response == "Bottleneck is at station 4."
    assert r.llm_model == "gpt-4o-mini"
    assert r.execution_mode == "normal"


# ------------------------------------------------------------------
# 2. Failed execution
# ------------------------------------------------------------------

def test_failed_execution_summary(db_session, run_factory, step_factory):
    run = _running_run(db_session, run_factory)
    _seed_steps(
        db_session,
        step_factory,
        run.id,
        [("ml_analysis", "success"), ("sql_query", "failed")],
    )

    finalize_agent_run_summary(
        db=db_session,
        agent_run_id=run.id,
        status="failed",
        execution_result={
            "results": {"1": {"retry_count": 0}, "2": {"retry_count": 2}}
        },
        verification_result={"confidence": 0.2, "approved": False},
    )

    r = get_run_by_id(db_session, run.id)
    assert r.status == "failed"
    assert r.steps_total == 2
    assert r.steps_success == 1
    assert r.steps_failed == 1
    assert r.retry_count == 2
    assert r.approved is False
    assert r.confidence == 0.2
    assert r.completed_at is not None  # failed is terminal


# ------------------------------------------------------------------
# 3. Failure safety — telemetry never breaks the run
# ------------------------------------------------------------------

def test_finalize_missing_run_returns_none(db_session):
    # No exception should escape; a missing run is logged and None returned.
    result = finalize_agent_run_summary(
        db=db_session,
        agent_run_id=999999,
        status="success",
        execution_result={"results": {}},
        verification_result={"confidence": 0.9, "approved": True},
    )
    assert result is None


def test_finalize_malformed_verification(db_session, run_factory):
    run = _running_run(db_session, run_factory)
    # verification is a raw string (malformed) — must not crash.
    finalize_agent_run_summary(
        db=db_session,
        agent_run_id=run.id,
        status="success",
        execution_result={"results": {}},
        verification_result="not-a-dict",
    )
    r = get_run_by_id(db_session, run.id)
    assert r.status == "completed"
    assert r.confidence is None
    assert r.approved is None


# ------------------------------------------------------------------
# 4/5. RAG usage detection
# ------------------------------------------------------------------

def test_rag_used_true_when_executed(db_session, run_factory, step_factory):
    run = _running_run(db_session, run_factory)
    _seed_steps(db_session, step_factory, run.id, [("rag_retrieval", "success")])
    finalize_agent_run_summary(
        db=db_session, agent_run_id=run.id, status="success"
    )
    assert get_run_by_id(db_session, run.id).rag_used is True


def test_rag_used_false_when_not_executed(
    db_session, run_factory, step_factory
):
    run = _running_run(db_session, run_factory)
    _seed_steps(db_session, step_factory, run.id, [("ml_analysis", "success")])
    finalize_agent_run_summary(
        db=db_session, agent_run_id=run.id, status="success"
    )
    assert get_run_by_id(db_session, run.id).rag_used is False


# ------------------------------------------------------------------
# 6. Memory usage detection
# ------------------------------------------------------------------

def test_memory_used_true_when_executed(
    db_session, run_factory, step_factory
):
    run = _running_run(db_session, run_factory)
    _seed_steps(db_session, step_factory, run.id, [("memory_tool", "success")])
    finalize_agent_run_summary(
        db=db_session, agent_run_id=run.id, status="success"
    )
    assert get_run_by_id(db_session, run.id).memory_used is True


def test_memory_used_false_when_not_executed(
    db_session, run_factory, step_factory
):
    run = _running_run(db_session, run_factory)
    _seed_steps(db_session, step_factory, run.id, [("sql_query", "success")])
    finalize_agent_run_summary(
        db=db_session, agent_run_id=run.id, status="success"
    )
    assert get_run_by_id(db_session, run.id).memory_used is False


# ------------------------------------------------------------------
# 7. Retry calculation (derived, never invented)
# ------------------------------------------------------------------

def test_retry_count_derivation(db_session, run_factory, step_factory):
    run = _running_run(db_session, run_factory)
    _seed_steps(
        db_session,
        step_factory,
        run.id,
        [("sql_query", "success"), ("ml_analysis", "success")],
    )
    finalize_agent_run_summary(
        db=db_session,
        agent_run_id=run.id,
        status="success",
        execution_result={
            "results": {"1": {"retry_count": 2}, "2": {"retry_count": 3}}
        },
    )
    assert get_run_by_id(db_session, run.id).retry_count == 5


def test_retry_count_zero_when_absent(db_session, run_factory, step_factory):
    run = _running_run(db_session, run_factory)
    _seed_steps(db_session, step_factory, run.id, [("sql_query", "success")])
    finalize_agent_run_summary(
        db=db_session,
        agent_run_id=run.id,
        status="success",
        execution_result={"results": {"1": {}}},
    )
    assert get_run_by_id(db_session, run.id).retry_count == 0


# ------------------------------------------------------------------
# 8. Multiple tools
# ------------------------------------------------------------------

def test_multiple_tools(db_session, run_factory, step_factory):
    run = _running_run(db_session, run_factory)
    _seed_steps(
        db_session,
        step_factory,
        run.id,
        [
            ("rag_retrieval", "success"),
            ("memory_tool", "success"),
            ("ml_analysis", "success"),
        ],
    )
    finalize_agent_run_summary(
        db=db_session,
        agent_run_id=run.id,
        status="success",
        execution_result={"results": {}},
    )
    r = get_run_by_id(db_session, run.id)
    assert r.steps_total == 3
    assert r.steps_success == 3
    assert r.steps_failed == 0
    assert len(r.tools_used) == 3


# ------------------------------------------------------------------
# 9. Verification values
# ------------------------------------------------------------------

def test_verification_values_persisted(db_session, run_factory):
    run = _running_run(db_session, run_factory)
    finalize_agent_run_summary(
        db=db_session,
        agent_run_id=run.id,
        status="success",
        verification_result={"confidence": 0.92, "approved": True},
    )
    r = get_run_by_id(db_session, run.id)
    assert r.confidence == 0.92
    assert r.approved is True


# ------------------------------------------------------------------
# 10. Offline / fallback
# ------------------------------------------------------------------

def test_offline_fallback_summary(db_session, run_factory):
    run = _running_run(db_session, run_factory)
    finalize_agent_run_summary(
        db=db_session,
        agent_run_id=run.id,
        status="success",
        verification_result={
            "confidence": 0.60,
            "approved": True,
            "issues": ["System operating in fallback mode"],
        },
        llm_meta={"model": None, "mode": "offline"},
    )
    r = get_run_by_id(db_session, run.id)
    assert r.execution_mode == "offline"
    assert r.llm_model is None
    assert r.confidence == 0.60


# ------------------------------------------------------------------
# 11. Missing optional fields
# ------------------------------------------------------------------

def test_missing_optional_fields(db_session, run_factory):
    run = _running_run(db_session, run_factory)
    finalize_agent_run_summary(
        db=db_session,
        agent_run_id=run.id,
        status="success",
    )
    r = get_run_by_id(db_session, run.id)
    assert r.status == "completed"
    assert r.confidence is None
    assert r.approved is None
    assert r.retry_count == 0
    assert r.steps_total == 0
    assert r.final_response is None


# ------------------------------------------------------------------
# 12. Enriched summary surfaces through the Milestone 1 API
# ------------------------------------------------------------------

def test_enriched_summary_via_runs_api(
    db_session, run_factory, step_factory, client
):
    run = _running_run(db_session, run_factory, session_id="line-A")
    _seed_steps(
        db_session,
        step_factory,
        run.id,
        [("rag_retrieval", "success"), ("ml_analysis", "success")],
    )
    finalize_agent_run_summary(
        db=db_session,
        agent_run_id=run.id,
        status="success",
        execution_result={"goal": "g", "results": {"1": {"retry_count": 1}}},
        verification_result={"confidence": 0.88, "approved": True},
        llm_meta={"model": "gpt-4o-mini", "mode": "openai"},
        final_response="final answer",
    )

    # Detail endpoint exposes full telemetry.
    detail = client.get(f"/runs/{run.id}").json()
    assert detail["status"] == "completed"
    assert detail["rag_used"] is True
    assert detail["confidence"] == 0.88
    assert detail["approved"] is True
    assert detail["execution_mode"] == "normal"
    assert detail["llm_model"] == "gpt-4o-mini"
    assert sorted(detail["tools_used"]) == ["ml_analysis", "rag_retrieval"]

    # Summary list exposes lightweight telemetry.
    summary = client.get("/runs").json()["items"][0]
    assert summary["status"] == "completed"
    assert summary["steps_total"] == 2
    assert summary["confidence"] == 0.88
    assert summary["verification_status"] == "passed"

    # Statistics count the completed run as successful.
    stats = client.get("/runs/statistics").json()
    assert stats["successful_runs"] == 1
    assert stats["total_runs"] == 1


# ------------------------------------------------------------------
# 13. Controller wiring (integration) — skipped if heavy deps unavailable
# ------------------------------------------------------------------

def test_controller_populates_summary(db_session, monkeypatch):
    """
    Drive AgentController.run end-to-end with fake planner/executor/verifier
    to prove the summary is populated by the real execution flow. Skipped if
    the controller's heavy import chain (torch/qdrant) is unavailable.
    """
    try:
        import src.agent.controller as controller_mod
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"controller import unavailable: {exc}")

    from src.services.step_audit_service import create_step_log

    # Neutralise memory side-effects (Qdrant / embeddings).
    monkeypatch.setattr(controller_mod, "retrieve_memory", lambda **k: [])
    monkeypatch.setattr(controller_mod, "add_memory", lambda **k: None)

    controller = controller_mod.AgentController(db=db_session, session_id="int")

    class FakePlanner:
        def create_plan(self, **kwargs):
            return {
                "goal": "analyze",
                "steps": [
                    {"tool": "rag_retrieval", "step_id": 1},
                    {"tool": "ml_analysis", "step_id": 2},
                ],
            }

    class FakeExecutor:
        def __init__(self):
            self.agent_run_id = None

        def set_agent_run_id(self, rid):
            self.agent_run_id = rid

        async def execute_plan(self, plan):
            for s in plan["steps"]:
                create_step_log(
                    db=db_session,
                    agent_run_id=self.agent_run_id,
                    step_id=s["step_id"],
                    tool_name=s["tool"],
                    input_payload={},
                    output_payload={"ok": True},
                    status="success",
                    execution_time_ms=10,
                )
            return {
                "goal": plan["goal"],
                "results": {
                    "1": {"retry_count": 0},
                    "2": {"retry_count": 0},
                },
            }

    class FakeVerifier:
        def verify(self, query, execution_result):
            return {"confidence": 0.9, "approved": True, "issues": []}

    class FakeRisk:
        def evaluate(self, plan):
            return {"requires_approval": False}

    controller.planner = FakePlanner()
    controller.executor = FakeExecutor()
    controller.verifier = FakeVerifier()
    controller.risk_evaluator = FakeRisk()

    import asyncio

    result = asyncio.run(controller.run(user_query="analyze bottlenecks"))

    assert result["status"] == "success"
    run_id = result["run_id"]

    r = get_run_by_id(db_session, run_id)
    assert r.status == "completed"
    assert r.steps_total == 2
    assert r.steps_success == 2
    assert r.rag_used is True
    assert r.confidence == 0.9
    assert r.approved is True
    assert r.completed_at is not None
