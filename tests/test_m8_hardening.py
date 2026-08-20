"""Milestone 8 hardening regression tests.

Covers the security / reliability fixes made during production hardening:

* Verifier fails CLOSED on unparseable output (never rubber-stamps a result).
* The offline LLM fallback is marked degraded / not-approved (never presents
  fallback output as an approved verdict).
* The request body-size guard rejects oversized payloads.
* Executor runaway-protection: oversized plans are rejected, per-tool timeouts
  fire, and steps whose dependencies failed are SKIPPED (not run on bad data).
"""

import asyncio
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.agent import executor as executor_mod
from src.agent.executor import ToolExecutor
from src.agent.verifier import VerifierAgent
from src.core.middleware.body_size import BodySizeLimitMiddleware
from src.tools.tool_registry import ToolRegistry


# ---------------------------------------------------------------------------
# Verifier fails closed
# ---------------------------------------------------------------------------

def test_verifier_fails_closed_on_unparseable_output(monkeypatch):
    monkeypatch.setattr(
        "src.agent.verifier.generate_response",
        lambda prompt: "this is not JSON at all",
    )

    verdict = VerifierAgent().verify("q", {"results": {}})

    assert verdict["approved"] is False
    assert verdict["confidence"] == 0.0
    assert verdict["issues"]  # non-empty explanation


# ---------------------------------------------------------------------------
# Offline LLM fallback is degraded / not approved
# ---------------------------------------------------------------------------

def test_offline_fallback_is_not_approved(monkeypatch):
    # Force both providers unavailable so we hit the Tier-3 offline fallback.
    monkeypatch.setattr("src.genai.llm_router.openai_client", None)
    monkeypatch.setattr("src.genai.llm_router.ollama", None)

    from src.genai.llm_router import generate_response

    payload = json.loads(generate_response("anything"))

    assert payload["approved"] is False
    assert payload.get("degraded") is True
    assert payload["confidence"] == 0.0


# ---------------------------------------------------------------------------
# Request body-size guard
# ---------------------------------------------------------------------------

def test_body_size_limit_rejects_oversized_request(monkeypatch):
    monkeypatch.setenv("MAX_REQUEST_BYTES", "100")

    app = FastAPI()
    app.add_middleware(BodySizeLimitMiddleware)

    @app.post("/echo")
    async def echo(payload: dict):
        return payload

    client = TestClient(app)

    # Under the limit: OK.
    assert client.post("/echo", json={"a": 1}).status_code == 200

    # Over the limit: 413.
    big = {"a": "x" * 500}
    assert client.post("/echo", json=big).status_code == 413


# ---------------------------------------------------------------------------
# Executor runaway protection
# ---------------------------------------------------------------------------

def test_executor_rejects_oversized_plan():
    ex = ToolExecutor(db=None)
    plan = {
        "goal": "too big",
        "steps": [
            {"step_id": i, "tool": "noop", "input": {}, "depends_on": []}
            for i in range(executor_mod.MAX_PLAN_STEPS + 1)
        ],
    }
    with pytest.raises(ValueError):
        asyncio.run(ex.execute_plan(plan))


def test_executor_skips_steps_with_failed_dependency(monkeypatch):
    monkeypatch.setattr(executor_mod, "RETRY_DELAY_SECONDS", 0)

    calls = {"dependent": 0}

    def failing_tool(payload):
        raise RuntimeError("boom")

    def dependent_tool(payload):
        calls["dependent"] += 1
        return {"ok": True}

    ToolRegistry.register("m8_fail", failing_tool, "always fails")
    ToolRegistry.register("m8_dep", dependent_tool, "depends on failure")

    ex = ToolExecutor(db=None)
    plan = {
        "goal": "dep test",
        "steps": [
            {"step_id": 1, "tool": "m8_fail", "input": {}, "depends_on": []},
            {"step_id": 2, "tool": "m8_dep", "input": {}, "depends_on": [1]},
        ],
    }

    result = asyncio.run(ex.execute_plan(plan))

    # The dependent must never execute on failed-upstream data.
    assert calls["dependent"] == 0
    assert result["results"][2].get("skipped") is True
    assert "error" in result["results"][1]


def test_executor_tool_timeout_is_recorded_as_failure(monkeypatch):
    monkeypatch.setattr(executor_mod, "RETRY_DELAY_SECONDS", 0)
    monkeypatch.setattr(executor_mod, "TOOL_TIMEOUT_SECONDS", 0.05)

    async def slow_tool(payload):
        await asyncio.sleep(2)
        return {"never": "returned"}

    ToolRegistry.register("m8_slow", slow_tool, "hangs")

    ex = ToolExecutor(db=None)
    plan = {
        "goal": "timeout test",
        "steps": [
            {"step_id": 1, "tool": "m8_slow", "input": {}, "depends_on": []},
        ],
    }

    result = asyncio.run(ex.execute_plan(plan))

    assert "error" in result["results"][1]
