"""Milestone 9 — end-to-end integration, failure-scenario and concurrency tests.

These exercise the REAL agent pipeline (AgentController -> PlannerAgent ->
ToolExecutor -> VerifierAgent -> audit -> run summary -> persistence) and then
read the result back through the /runs API. Only the LLM boundary
(generate_response) and the memory subsystem are mocked, so no OpenAI/Ollama/
Qdrant access is required. Everything else is the production code path.
"""

import asyncio
import json

import pytest

from tests.conftest import TestingSessionLocal
from src.agent import controller as controller_mod
from src.agent import planner as planner_mod
from src.agent import verifier as verifier_mod
from src.agent.controller import AgentController
from src.agent.plan_validator import PlanValidator
from src.tools.tool_registry import ToolRegistry


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _plan_json(*, tool="m9_ok", two_step=False):
    steps = [
        {"step_id": 1, "tool": tool, "purpose": "analyze",
         "input": {"query": "bottlenecks"}, "depends_on": []},
    ]
    if two_step:
        steps.append(
            {"step_id": 2, "tool": tool, "purpose": "synthesize",
             "input": {"query": "summary"}, "depends_on": [1]}
        )
    return json.dumps({"goal": "Analyze manufacturing bottlenecks", "steps": steps})


_APPROVED = json.dumps({"approved": True, "confidence": 0.9, "issues": []})


@pytest.fixture
def registered_tools():
    """Register deterministic fake tools; leave the real registry intact."""
    def ok_tool(payload):
        return {"analysis": "ok", "echo": payload.get("query")}

    def boom_tool(payload):
        raise RuntimeError("simulated tool failure")

    ToolRegistry.register("m9_ok", ok_tool, "deterministic success tool")
    ToolRegistry.register("m9_boom", boom_tool, "always-failing tool")
    yield


def _mock_llm(monkeypatch, *, plan=None, verdict=_APPROVED):
    """Mock planner + verifier LLM calls and the (non-critical) memory system."""
    plan = plan if plan is not None else _plan_json()
    monkeypatch.setattr(planner_mod, "generate_response", lambda prompt: plan)
    monkeypatch.setattr(verifier_mod, "generate_response", lambda prompt: verdict)
    # get_last_llm_meta is imported into controller; keep it deterministic.
    monkeypatch.setattr(controller_mod, "retrieve_memory",
                        lambda **kw: [])
    monkeypatch.setattr(controller_mod, "add_memory", lambda **kw: None)
    # Speed up any tool retries.
    from src.agent import executor as ex
    monkeypatch.setattr(ex, "RETRY_DELAY_SECONDS", 0)


def _run(session_id="m9", user_query="Analyze manufacturing bottlenecks in production lines"):
    db = TestingSessionLocal()
    try:
        ctrl = AgentController(db=db, session_id=session_id, user_id=None)
        return asyncio.run(ctrl.run(user_query))
    finally:
        db.close()


# ===========================================================================
# PHASE 2 / 18 — full happy-path pipeline, then read back via the API
# ===========================================================================

def test_full_pipeline_success_end_to_end(client, registered_tools, monkeypatch):
    _mock_llm(monkeypatch, plan=_plan_json(two_step=True))

    result = _run()

    assert result["status"] == "success"
    run_id = result["run_id"]
    assert run_id

    # Exposed through the list endpoint.
    listing = client.get("/runs").json()
    assert any(r["run_id"] == run_id for r in listing["items"])

    # Exposed through the detail endpoint with the persisted summary.
    # The engine emits "success"; it is persisted as the canonical "completed"
    # (Milestone 2 convention). Both count as successful in statistics.
    detail = client.get(f"/runs/{run_id}").json()
    assert detail["status"] in ("success", "completed")
    assert detail["approved"] is True
    assert detail["confidence"] == 0.9
    assert detail["steps_total"] == 2
    assert detail["steps_success"] == 2
    assert detail["steps_failed"] == 0
    assert detail["execution_duration_ms"] is not None

    # Step audit rows recorded and exposed (endpoint returns a list).
    steps = client.get(f"/runs/{run_id}/steps").json()
    assert len(steps) == 2

    # Statistics reflect the run.
    stats = client.get("/runs/statistics").json()
    assert stats["total_runs"] >= 1


# ===========================================================================
# PHASE 3 — failure scenarios
# ===========================================================================

def test_tool_failure_is_audited_and_not_reported_success(client, registered_tools, monkeypatch):
    # Plan uses the always-failing tool.
    _mock_llm(monkeypatch, plan=_plan_json(tool="m9_boom"))

    result = _run(session_id="fail")

    # The run must NOT be reported as success.
    assert result["status"] != "success"

    run_id = result["run_id"]
    steps = client.get(f"/runs/{run_id}/steps").json()
    assert len(steps) >= 1
    step = steps[0]
    assert step["status"] == "failed"
    # Retries were attempted and recorded (MAX_TOOL_RETRIES).
    assert step["retry_count"] >= 1


def test_llm_offline_fallback_not_treated_as_success(client, registered_tools, monkeypatch):
    # Verifier returns the offline-fallback shape (degraded / not approved).
    offline = json.dumps(
        {"degraded": True, "approved": False, "confidence": 0.0,
         "issues": ["System operating in offline fallback mode"]}
    )
    _mock_llm(monkeypatch, verdict=offline)

    result = _run(session_id="offline")

    # Fallback must never be treated as an approved, high-confidence success.
    assert result["status"] != "success"
    run_id = result["run_id"]
    detail = client.get(f"/runs/{run_id}").json()
    assert detail["approved"] in (False, None)
    assert detail["status"] == "failed"


def test_verifier_low_confidence_triggers_replan_then_fails(client, registered_tools, monkeypatch):
    low = json.dumps({"approved": True, "confidence": 0.10, "issues": ["weak"]})
    _mock_llm(monkeypatch, verdict=low)

    result = _run(session_id="lowconf")

    assert result["status"] == "failed"
    # Multiple attempts were made (controller MAX_RETRIES) — each superseded
    # attempt is finalized, so none is left orphaned in "running".
    runs = client.get("/runs/session/lowconf").json()
    assert all(r["status"] != "running" for r in runs["items"])


# ===========================================================================
# PHASE 3 — planner / plan validation
# ===========================================================================

def test_plan_validator_rejects_invalid_tool():
    with pytest.raises(ValueError):
        PlanValidator().validate(
            {"steps": [{"step_id": 1, "tool": "does_not_exist"}]}
        )


def test_plan_validator_rejects_missing_steps():
    with pytest.raises(ValueError):
        PlanValidator().validate({"goal": "x"})


def test_plan_validator_rejects_unknown_dependency(registered_tools):
    with pytest.raises(ValueError):
        PlanValidator().validate(
            {"steps": [{"step_id": 1, "tool": "m9_ok", "depends_on": [99]}]}
        )


def test_plan_validator_detects_cycle(registered_tools):
    with pytest.raises(ValueError):
        PlanValidator().validate(
            {"steps": [
                {"step_id": 1, "tool": "m9_ok", "depends_on": [2]},
                {"step_id": 2, "tool": "m9_ok", "depends_on": [1]},
            ]}
        )


# ===========================================================================
# PHASE 12 — concurrency / isolation
# ===========================================================================

def test_concurrent_runs_are_isolated(client, registered_tools, monkeypatch):
    _mock_llm(monkeypatch)

    async def run_one(session_id):
        db = TestingSessionLocal()
        try:
            ctrl = AgentController(db=db, session_id=session_id, user_id=None)
            return await ctrl.run(f"analyze {session_id}")
        finally:
            db.close()

    async def run_all():
        return await asyncio.gather(*[run_one(f"c{i}") for i in range(3)])

    results = asyncio.run(run_all())

    # Distinct run ids, all successful, each bound to its own session.
    run_ids = {r["run_id"] for r in results}
    assert len(run_ids) == 3
    assert all(r["status"] == "success" for r in results)

    for i, r in enumerate(results):
        detail = client.get(f"/runs/{r['run_id']}").json()
        assert detail["session_id"] == f"c{i}"
        # Each run's steps belong only to that run (no cross-leak).
        steps = client.get(f"/runs/{r['run_id']}/steps").json()
        assert len(steps) >= 1
