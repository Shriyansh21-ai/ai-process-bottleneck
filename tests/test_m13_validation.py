"""Milestone 13 — REAL workflow validation over the HTTP surface.

These tests drive the **actual** production request path end-to-end:

    HTTP POST /run  (real JWT auth)
        -> AgentController
            -> PlannerAgent  -> PlanValidator
            -> ToolExecutor  -> ToolRegistry -> real registered tools
                -> DAG deps / parallel waves / retry engine
            -> VerifierAgent -> RiskEvaluator
            -> step audit (step_executions) + AgentRun summary
        -> PostgreSQL/SQLite persistence
    then read back through the real GET /runs* APIs.

Only the *external* boundaries are mocked, exactly as Milestone 13 Step 13
requires:
  * ``generate_response``   — the OpenAI/Ollama LLM boundary (planner+verifier)
  * ``retrieve_memory`` / ``add_memory`` — the embedding/vector memory boundary
  * ``retrieve_context``    — the RAG vector-store boundary (rag_retrieval tool)

Everything else — the controller loop, planner JSON handling, plan validation,
the DAG executor, the retry engine, the verifier gate, the risk evaluator, the
audit trail and the persistence/readback layer — is the real production code.

The ``/run`` route defined here mirrors ``main.py`` exactly (same
``AgentController`` construction, same ``get_current_active_user`` dependency);
it uses the dependency-injected test DB session instead of ``SessionLocal()``
so the whole flow — auth, execution, audit and readback — shares one database.
"""

import asyncio
import json

import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from tests.conftest import (
    TestingSessionLocal,
    _override_get_db,
    register_and_login,
)

from src.agent import controller as controller_mod
from src.agent import planner as planner_mod
from src.agent import verifier as verifier_mod
from src.agent import executor as executor_mod
from src.agent.controller import AgentController
from src.core.auth import get_current_active_user
from src.db.models.user import User
from src.db.session import get_db as real_get_db
from src.tools import rag_tool as rag_tool_mod
from src.tools.tool_registry import ToolRegistry

from src.api.auth import router as auth_router
from src.api.routes.agent_runs import router as agent_runs_router
from src.api.routes.agent_observability import (
    router as agent_observability_router,
)


# ===========================================================================
# LLM / verifier verdict fixtures (deterministic)
# ===========================================================================

_APPROVED = json.dumps({"approved": True, "confidence": 0.92, "issues": []})
_LOW_CONF = json.dumps({"approved": True, "confidence": 0.10, "issues": ["weak"]})
_REJECTED = json.dumps({"approved": False, "confidence": 0.30, "issues": ["bad"]})
_OFFLINE = json.dumps(
    {"degraded": True, "approved": False, "confidence": 0.0,
     "issues": ["System operating in offline fallback mode"]}
)


def _plan(steps, goal="Analyze the available project information"):
    return json.dumps({"goal": goal, "steps": steps})


def _mock_boundaries(monkeypatch, *, plan, verdict=_APPROVED):
    """Mock ONLY the external boundaries; leave the whole pipeline real."""
    monkeypatch.setattr(planner_mod, "generate_response", lambda prompt: plan)
    monkeypatch.setattr(verifier_mod, "generate_response", lambda prompt: verdict)
    monkeypatch.setattr(controller_mod, "retrieve_memory", lambda **kw: [])
    monkeypatch.setattr(controller_mod, "add_memory", lambda **kw: None)
    # Don't actually sleep between tool retries.
    monkeypatch.setattr(executor_mod, "RETRY_DELAY_SECONDS", 0)


# ===========================================================================
# Deterministic, synthetic tools registered into the REAL ToolRegistry.
# The registry, executor, DAG engine and retry engine are all real; only the
# leaf tool bodies are controlled stubs (Step 8's "controlled failure
# injection"). Real tools (ml_analysis, rag_retrieval) are exercised too.
# ===========================================================================

# Shared, per-test-reset state for the stateful stubs.
_STATE = {
    "flaky_attempts": 0,          # retry-then-success counter
    "parallel_active": 0,         # live count of concurrent async steps
    "parallel_max": 0,            # high-water mark => proves real parallelism
    "seen_context": {},           # step_id -> keys visible to a dependent step
}


def _reset_state():
    _STATE.update(
        flaky_attempts=0, parallel_active=0, parallel_max=0, seen_context={}
    )


def _ok_tool(payload):
    return {"analysis": "ok", "echo": payload.get("query")}


async def _parallel_tool(payload):
    """Async tool that measures real concurrency via a high-water mark."""
    _STATE["parallel_active"] += 1
    _STATE["parallel_max"] = max(_STATE["parallel_max"], _STATE["parallel_active"])
    try:
        await asyncio.sleep(0.05)
        return {"ok": True, "who": payload.get("query")}
    finally:
        _STATE["parallel_active"] -= 1


def _dependent_tool(payload):
    """Records which upstream step outputs are visible in its context."""
    ctx = payload.get("context", {})
    _STATE["seen_context"] = {
        k: ("output" in v if isinstance(v, dict) else None) for k, v in ctx.items()
    }
    return {"combined": sorted(ctx.keys())}


def _flaky_tool(payload):
    """Fails on attempts 1 and 2, succeeds on attempt 3 (retry-then-success)."""
    _STATE["flaky_attempts"] += 1
    if _STATE["flaky_attempts"] < 3:
        raise RuntimeError(f"transient failure #{_STATE['flaky_attempts']}")
    return {"ok": True, "attempt": _STATE["flaky_attempts"]}


def _always_fail_tool(payload):
    raise RuntimeError("permanent tool failure")


@pytest.fixture
def m13_tools():
    ToolRegistry.register("m13_ok", _ok_tool, "deterministic success tool")
    ToolRegistry.register("m13_parallel", _parallel_tool, "async concurrency probe")
    ToolRegistry.register("m13_dependent", _dependent_tool, "context-collecting tool")
    ToolRegistry.register("m13_flaky", _flaky_tool, "fails twice then succeeds")
    ToolRegistry.register("m13_boom", _always_fail_tool, "always-failing tool")
    _reset_state()
    yield
    _reset_state()


# ===========================================================================
# App fixture — mirrors main.py's production /run wiring (real auth + controller)
# ===========================================================================

@pytest.fixture
def app_client(db_session):
    """A TestClient exposing /auth, /run (real controller) and /runs* readback."""
    app = FastAPI()

    @app.post("/run")
    async def run_query(
        req: dict,
        request: Request,
        current_user: User = Depends(get_current_active_user),
        db=Depends(real_get_db),
    ):
        # Mirrors main.py: the authenticated user owns the run; the agent flow
        # itself is unchanged. (Uses the injected test session so auth,
        # execution, audit and readback all share one DB.)
        try:
            controller = AgentController(
                db=db,
                session_id=req["session_id"],
                user_id=current_user.id,
            )
            result = await controller.run(user_query=req["query"])
            return result
        except Exception:
            return JSONResponse(
                status_code=500,
                content={"error": "Internal server error"},
            )

    app.include_router(auth_router)
    app.include_router(agent_runs_router)
    app.include_router(agent_observability_router)
    app.dependency_overrides[real_get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _run_http(client, headers, query, session_id):
    resp = client.post(
        "/run",
        json={"query": query, "session_id": session_id},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


# ===========================================================================
# 1. Normal successful run  (success)
# ===========================================================================

def test_normal_successful_run(app_client, m13_tools, monkeypatch):
    _mock_boundaries(
        monkeypatch,
        plan=_plan([
            {"step_id": 1, "tool": "m13_ok", "purpose": "analyze",
             "input": {"query": "bottleneck"}, "depends_on": []},
        ]),
    )
    headers = register_and_login(app_client, "m13-success@example.com")

    result = _run_http(app_client, headers, "Analyze the main bottleneck.", "s-success")

    assert result["status"] == "success"
    run_id = result["run_id"]

    detail = app_client.get(f"/runs/{run_id}", headers=headers).json()
    assert detail["status"] in ("success", "completed")
    assert detail["approved"] is True
    assert detail["confidence"] == 0.92
    assert detail["steps_total"] == 1
    assert detail["steps_success"] == 1
    assert detail["steps_failed"] == 0
    assert detail["execution_duration_ms"] is not None


# ===========================================================================
# 2. Multi-step dependent run  (A -> B -> C)   (success)
# ===========================================================================

def test_multi_step_dependent_run(app_client, m13_tools, monkeypatch):
    _mock_boundaries(
        monkeypatch,
        plan=_plan([
            {"step_id": 1, "tool": "m13_ok", "purpose": "collect",
             "input": {"query": "a"}, "depends_on": []},
            {"step_id": 2, "tool": "m13_ok", "purpose": "enrich",
             "input": {"query": "b"}, "depends_on": [1]},
            {"step_id": 3, "tool": "m13_dependent", "purpose": "combine",
             "input": {"query": "c"}, "depends_on": [1, 2]},
        ]),
    )
    headers = register_and_login(app_client, "m13-multi@example.com")

    result = _run_http(app_client, headers, "Retrieve and analyze.", "s-multi")
    assert result["status"] == "success"

    # The dependent step must have seen BOTH upstream outputs (deps waited).
    assert set(_STATE["seen_context"].keys()) == {1, 2}
    assert all(_STATE["seen_context"].values())  # both were successful outputs

    run_id = result["run_id"]
    steps = app_client.get(f"/runs/{run_id}/steps", headers=headers).json()
    assert len(steps) == 3


# ===========================================================================
# 3. Parallel independent steps  (A | B -> C)   (success + real concurrency)
# ===========================================================================

def test_parallel_independent_steps(app_client, m13_tools, monkeypatch):
    _mock_boundaries(
        monkeypatch,
        plan=_plan([
            {"step_id": 1, "tool": "m13_parallel", "purpose": "left",
             "input": {"query": "L"}, "depends_on": []},
            {"step_id": 2, "tool": "m13_parallel", "purpose": "right",
             "input": {"query": "R"}, "depends_on": []},
            {"step_id": 3, "tool": "m13_dependent", "purpose": "join",
             "input": {"query": "J"}, "depends_on": [1, 2]},
        ]),
    )
    headers = register_and_login(app_client, "m13-parallel@example.com")

    result = _run_http(app_client, headers, "Compare the available data.", "s-par")
    assert result["status"] == "success"

    # Independent async steps 1 & 2 genuinely overlapped in the same wave.
    assert _STATE["parallel_max"] == 2
    # And the join step waited for both.
    assert set(_STATE["seen_context"].keys()) == {1, 2}


# ===========================================================================
# 4. Retry-then-success   (attempt 1 fail, 2 fail, 3 succeed)  (success)
# ===========================================================================

def test_retry_then_success(app_client, m13_tools, monkeypatch):
    _mock_boundaries(
        monkeypatch,
        plan=_plan([
            {"step_id": 1, "tool": "m13_flaky", "purpose": "resilient",
             "input": {"query": "x"}, "depends_on": []},
        ]),
    )
    headers = register_and_login(app_client, "m13-retry@example.com")

    result = _run_http(app_client, headers, "Determine the most likely issue.", "s-retry")
    assert result["status"] == "success"

    run_id = result["run_id"]
    steps = app_client.get(f"/runs/{run_id}/steps", headers=headers).json()
    assert len(steps) == 1
    assert steps[0]["status"] == "success"
    # Two failed attempts preceded success -> retry_count == 2.
    assert steps[0]["retry_count"] == 2

    detail = app_client.get(f"/runs/{run_id}", headers=headers).json()
    assert detail["retry_count"] == 2


# ===========================================================================
# 5. Retry exhaustion   (fails all 3 attempts)   (failed, safely)
# ===========================================================================

def test_retry_exhaustion_fails_safely(app_client, m13_tools, monkeypatch):
    _mock_boundaries(
        monkeypatch,
        plan=_plan([
            {"step_id": 1, "tool": "m13_boom", "purpose": "doomed",
             "input": {"query": "x"}, "depends_on": []},
        ]),
    )
    headers = register_and_login(app_client, "m13-exhaust@example.com")

    result = _run_http(app_client, headers, "Analyze.", "s-exhaust")

    # Never a success; no orphaned "running" row.
    assert result["status"] != "success"
    runs = app_client.get("/runs/session/s-exhaust", headers=headers).json()
    assert runs["items"]  # at least one attempt persisted
    assert all(r["status"] != "running" for r in runs["items"])

    # The failing step is audited as failed with the full retry budget spent.
    run_id = result["run_id"]
    steps = app_client.get(f"/runs/{run_id}/steps", headers=headers).json()
    assert any(s["status"] == "failed" for s in steps)
    failed = next(s for s in steps if s["status"] == "failed")
    # retry_count == retries performed == MAX_TOOL_RETRIES - 1 (3 attempts,
    # 2 retries). The step-audit row and the run-summary telemetry must agree.
    expected_retries = executor_mod.MAX_TOOL_RETRIES - 1
    assert failed["retry_count"] == expected_retries
    detail = app_client.get(f"/runs/{run_id}", headers=headers).json()
    assert detail["retry_count"] == expected_retries  # no contradiction


# ===========================================================================
# 6. Verifier rejection   (approved=False)  (failed, never success)
# ===========================================================================

def test_verifier_rejection(app_client, m13_tools, monkeypatch):
    _mock_boundaries(
        monkeypatch,
        plan=_plan([
            {"step_id": 1, "tool": "m13_ok", "purpose": "analyze",
             "input": {"query": "x"}, "depends_on": []},
        ]),
        verdict=_REJECTED,
    )
    headers = register_and_login(app_client, "m13-reject@example.com")

    result = _run_http(app_client, headers, "Analyze.", "s-reject")
    assert result["status"] == "failed"

    run_id = result["run_id"]
    detail = app_client.get(f"/runs/{run_id}", headers=headers).json()
    assert detail["approved"] in (False, None)
    assert detail["status"] == "failed"


# ===========================================================================
# 7. Low confidence   (approved but below threshold)  (failed after replan)
# ===========================================================================

def test_low_confidence_triggers_replan_then_fails(app_client, m13_tools, monkeypatch):
    _mock_boundaries(
        monkeypatch,
        plan=_plan([
            {"step_id": 1, "tool": "m13_ok", "purpose": "analyze",
             "input": {"query": "x"}, "depends_on": []},
        ]),
        verdict=_LOW_CONF,
    )
    headers = register_and_login(app_client, "m13-lowconf@example.com")

    result = _run_http(app_client, headers, "Analyze.", "s-lowconf")
    assert result["status"] == "failed"

    # Every superseded attempt is finalized — none orphaned in "running".
    runs = app_client.get("/runs/session/s-lowconf", headers=headers).json()
    assert len(runs["items"]) >= 2  # controller retried
    assert all(r["status"] != "running" for r in runs["items"])


# ===========================================================================
# 8. LLM offline fallback   (degraded, must NOT become a fake success)
# ===========================================================================

def test_llm_fallback_not_fake_success(app_client, m13_tools, monkeypatch):
    _mock_boundaries(
        monkeypatch,
        plan=_plan([
            {"step_id": 1, "tool": "m13_ok", "purpose": "analyze",
             "input": {"query": "x"}, "depends_on": []},
        ]),
        verdict=_OFFLINE,
    )
    headers = register_and_login(app_client, "m13-offline@example.com")

    result = _run_http(app_client, headers, "Analyze.", "s-offline")
    assert result["status"] != "success"

    run_id = result["run_id"]
    detail = app_client.get(f"/runs/{run_id}", headers=headers).json()
    assert detail["approved"] in (False, None)
    assert detail["status"] == "failed"


# ===========================================================================
# 9. Empty RAG retrieval   (real rag_retrieval tool, empty vector store)
# ===========================================================================

def test_empty_rag_retrieval_is_safe(app_client, m13_tools, monkeypatch):
    # Real rag_search tool wrapper runs; only the vector-store boundary is
    # mocked to return no matches.
    monkeypatch.setattr(rag_tool_mod, "retrieve_context", lambda **kw: [])
    _mock_boundaries(
        monkeypatch,
        plan=_plan([
            {"step_id": 1, "tool": "rag_retrieval", "purpose": "retrieve",
             "input": {"query": "nonexistent topic"}, "depends_on": []},
        ]),
    )
    headers = register_and_login(app_client, "m13-emptyrag@example.com")

    result = _run_http(app_client, headers, "Find relevant historical context.", "s-rag")
    # Empty retrieval is a valid, non-crashing result (verifier approves here).
    assert result["status"] == "success"

    run_id = result["run_id"]
    steps = app_client.get(f"/runs/{run_id}/steps", headers=headers).json()
    assert len(steps) == 1
    assert steps[0]["status"] == "success"
    assert steps[0]["tool_name"] == "rag_retrieval"

    detail = app_client.get(f"/runs/{run_id}", headers=headers).json()
    assert detail["rag_used"] is True


# ===========================================================================
# 10. Invalid / unsupported tool selected by planner  (rejected safely)
# ===========================================================================

def test_invalid_tool_is_rejected_safely(app_client, m13_tools, monkeypatch):
    # Planner emits a plan referencing a tool that is NOT registered. The
    # PlanValidator rejects it, so the planner repairs to a safe static plan
    # (rag_retrieval + memory_tool + ml_analysis) rather than executing garbage.
    monkeypatch.setattr(rag_tool_mod, "retrieve_context", lambda **kw: [])
    _mock_boundaries(
        monkeypatch,
        plan=_plan([
            {"step_id": 1, "tool": "totally_unregistered_tool", "purpose": "x",
             "input": {"query": "x"}, "depends_on": []},
        ]),
    )
    headers = register_and_login(app_client, "m13-invalidtool@example.com")

    # Must not raise / 500; the run completes through the repair path.
    result = _run_http(app_client, headers, "Analyze.", "s-invalid")
    assert result["status"] in ("success", "failed")

    run_id = result["run_id"]
    detail = app_client.get(f"/runs/{run_id}", headers=headers).json()
    # None of the executed steps used the bogus tool.
    steps = app_client.get(f"/runs/{run_id}/steps", headers=headers).json()
    assert all(s["tool_name"] != "totally_unregistered_tool" for s in steps)
    assert detail["status"] in ("success", "completed", "failed")


# ===========================================================================
# 11. Session isolation   (two sessions never cross-contaminate)
# ===========================================================================

def test_session_isolation(app_client, m13_tools, monkeypatch):
    _mock_boundaries(
        monkeypatch,
        plan=_plan([
            {"step_id": 1, "tool": "m13_ok", "purpose": "analyze",
             "input": {"query": "x"}, "depends_on": []},
        ]),
    )
    headers = register_and_login(app_client, "m13-iso@example.com")

    r_a = _run_http(app_client, headers, "Analyze session A.", "SESSION_A")
    r_b = _run_http(app_client, headers, "Analyze session B.", "SESSION_B")
    assert r_a["run_id"] != r_b["run_id"]

    a = app_client.get("/runs/session/SESSION_A", headers=headers).json()
    b = app_client.get("/runs/session/SESSION_B", headers=headers).json()
    a_ids = {r["run_id"] for r in a["items"]}
    b_ids = {r["run_id"] for r in b["items"]}
    assert a_ids and b_ids
    assert a_ids.isdisjoint(b_ids)               # no cross-leak
    assert all(r["session_id"] == "SESSION_A" for r in a["items"])
    assert all(r["session_id"] == "SESSION_B" for r in b["items"])


# ===========================================================================
# 12. Concurrent runs   (>=3, isolated, distinct run ids, no orphans)
# ===========================================================================

def test_concurrent_runs_isolated(app_client, m13_tools, monkeypatch):
    _mock_boundaries(
        monkeypatch,
        plan=_plan([
            {"step_id": 1, "tool": "m13_parallel", "purpose": "analyze",
             "input": {"query": "x"}, "depends_on": []},
        ]),
    )

    async def run_one(session_id):
        db = TestingSessionLocal()
        try:
            ctrl = AgentController(db=db, session_id=session_id, user_id=None)
            return await ctrl.run(f"analyze {session_id}")
        finally:
            db.close()

    async def run_all():
        return await asyncio.gather(*[run_one(f"conc-{i}") for i in range(3)])

    results = asyncio.run(run_all())

    run_ids = {r["run_id"] for r in results}
    assert len(run_ids) == 3
    assert all(r["status"] == "success" for r in results)

    headers = register_and_login(app_client, "m13-conc@example.com", is_admin=True)
    for i, r in enumerate(results):
        detail = app_client.get(f"/runs/{r['run_id']}", headers=headers).json()
        assert detail["session_id"] == f"conc-{i}"


# ===========================================================================
# 13. Unauthorized request   (401)
# ===========================================================================

def test_unauthorized_run_is_401(app_client, m13_tools):
    resp = app_client.post(
        "/run", json={"query": "Analyze.", "session_id": "s"},
    )
    assert resp.status_code == 401


def test_unauthorized_runs_readback_is_401(app_client):
    assert app_client.get("/runs").status_code == 401
    assert app_client.get("/runs/statistics").status_code == 401


# ===========================================================================
# 14. Cross-user isolation / IDOR   (one user cannot read another's run)
# ===========================================================================

def test_cross_user_run_is_not_readable(app_client, m13_tools, monkeypatch):
    _mock_boundaries(
        monkeypatch,
        plan=_plan([
            {"step_id": 1, "tool": "m13_ok", "purpose": "analyze",
             "input": {"query": "x"}, "depends_on": []},
        ]),
    )
    owner = register_and_login(app_client, "m13-owner@example.com")
    result = _run_http(app_client, owner, "Analyze.", "s-owner")
    run_id = result["run_id"]

    attacker = register_and_login(app_client, "m13-attacker@example.com")
    # Owned by another user -> indistinguishable from missing (404, no leak).
    assert app_client.get(f"/runs/{run_id}", headers=attacker).status_code == 404
    assert app_client.get(f"/runs/{run_id}/steps", headers=attacker).status_code == 404


# ===========================================================================
# 15. Read-back API surface   (all endpoints reflect persisted reality)
# ===========================================================================

def test_readback_apis_reflect_reality(app_client, m13_tools, monkeypatch):
    _mock_boundaries(
        monkeypatch,
        plan=_plan([
            {"step_id": 1, "tool": "m13_ok", "purpose": "analyze",
             "input": {"query": "x"}, "depends_on": []},
            {"step_id": 2, "tool": "m13_ok", "purpose": "synth",
             "input": {"query": "y"}, "depends_on": [1]},
        ]),
    )
    headers = register_and_login(app_client, "m13-readback@example.com")
    result = _run_http(app_client, headers, "Summarize the main bottleneck.", "s-read")
    run_id = result["run_id"]

    # GET /runs (list + pagination envelope)
    listing = app_client.get("/runs?page=1&page_size=10", headers=headers).json()
    assert listing["page"] == 1 and listing["page_size"] == 10
    assert any(r["run_id"] == run_id for r in listing["items"])

    # GET /runs/{id}
    detail = app_client.get(f"/runs/{run_id}", headers=headers).json()
    assert detail["steps_total"] == 2 and detail["steps_success"] == 2

    # GET /runs/{id}/steps
    steps = app_client.get(f"/runs/{run_id}/steps", headers=headers).json()
    assert len(steps) == 2

    # GET /runs/statistics
    stats = app_client.get("/runs/statistics", headers=headers).json()
    assert stats["total_runs"] >= 1
    assert stats["successful_runs"] >= 1

    # GET /runs/search
    found = app_client.get("/runs/search?q=bottleneck", headers=headers).json()
    assert any(r["run_id"] == run_id for r in found["items"])

    # GET /runs/status/{status}
    completed = app_client.get("/runs/status/completed", headers=headers).json()
    assert any(r["run_id"] == run_id for r in completed["items"])

    # GET /runs/session/{session_id}
    sess = app_client.get("/runs/session/s-read", headers=headers).json()
    assert any(r["run_id"] == run_id for r in sess["items"])

    # Invalid status -> 400
    assert app_client.get("/runs/status/bogus", headers=headers).status_code == 400


# ===========================================================================
# 16. No secret leakage in the audit trail
# ===========================================================================

def test_no_db_handle_or_secret_in_step_audit(app_client, m13_tools, monkeypatch):
    _mock_boundaries(
        monkeypatch,
        plan=_plan([
            {"step_id": 1, "tool": "m13_ok", "purpose": "analyze",
             "input": {"query": "x"}, "depends_on": []},
        ]),
    )
    headers = register_and_login(app_client, "m13-secret@example.com")
    result = _run_http(app_client, headers, "Analyze.", "s-secret")
    run_id = result["run_id"]

    steps = app_client.get(f"/runs/{run_id}/steps", headers=headers).json()
    # The executor injects a live ``db`` handle into every tool input; the audit
    # layer must strip it before persisting the input payload.
    blob = json.dumps(steps).lower()
    assert '"db"' not in blob
    assert "session" not in blob or "session_id" in blob  # no raw Session repr
    assert "password" not in blob


# ===========================================================================
# 17. Regression: verifier must tolerate non-JSON-native tool outputs
# ===========================================================================
# The real ``sql_query`` tool returns rows containing ``datetime`` objects.
# ``VerifierAgent.verify`` serialises the execution result into its prompt; if
# it used a plain ``json.dumps`` (no ``default=str``) it would raise TypeError,
# the controller would treat verification as failed, and EVERY DB-backed
# workflow could never succeed. This locks in the ``default=str`` fix.

def test_verifier_tolerates_datetime_in_execution_result(monkeypatch):
    import datetime as _dt
    from src.agent.verifier import VerifierAgent

    monkeypatch.setattr(
        verifier_mod, "generate_response",
        lambda prompt: json.dumps({"approved": True, "confidence": 0.9, "issues": []}),
    )

    execution_result = {
        "goal": "analyze",
        "results": {
            "1": {
                "step_id": 1, "tool": "sql_query", "retry_count": 0,
                "output": [{"id": 1, "start_time": _dt.datetime(2026, 8, 30, 12, 0, 0)}],
            }
        },
    }

    # Must NOT raise, and must return the (approved) verdict unchanged.
    verdict = VerifierAgent().verify("q", execution_result)
    assert verdict["approved"] is True
    assert verdict["confidence"] == 0.9


def test_datetime_bearing_tool_output_run_succeeds(app_client, m13_tools, monkeypatch):
    """End-to-end analogue: a tool returning datetime output still succeeds."""
    import datetime as _dt

    def _datetime_tool(payload):
        return {"rows": [{"id": 1, "ts": _dt.datetime(2026, 8, 30, 12, 0, 0)}]}

    ToolRegistry.register("m13_datetime", _datetime_tool, "returns datetime output")
    _mock_boundaries(
        monkeypatch,
        plan=_plan([
            {"step_id": 1, "tool": "m13_datetime", "purpose": "read",
             "input": {"query": "x"}, "depends_on": []},
        ]),
    )
    headers = register_and_login(app_client, "m13-datetime@example.com")

    result = _run_http(app_client, headers, "Analyze timestamped data.", "s-dt")
    assert result["status"] == "success"
