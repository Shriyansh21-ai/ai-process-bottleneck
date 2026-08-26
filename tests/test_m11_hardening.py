"""
Milestone 11 — final hardening regression tests.

Two areas:

  * Phase 4 — tool input-contract validation. The planner used to default every
    step to ``{"query": ...}``; a step selecting ``sql_query`` (which REQUIRES a
    ``table``) then crashed mid-execution. PlanValidator now rejects a plan that
    omits a tool's required inputs, so the planner repairs to a safe plan
    instead of producing a failed run. These tests lock in the contract.

  * Phase 5 — LLM provider fallback. generate_response cascades OpenAI -> Ollama
    -> offline safe fallback, each attempted once (no infinite retry), with a
    bounded timeout, and the offline payload is never a real high-confidence
    success.

External providers are always mocked — no real API calls.
"""

import json

import pytest

import src.tools.register_tools  # noqa: F401  (populate the ToolRegistry)
from src.tools.tool_registry import ToolRegistry
from src.agent.plan_validator import PlanValidator
from src.agent.planner import PlannerAgent
from src.tools.sql_tool import run_sql_query
from src.tools.ml_tool import run_ml_analysis
from src.genai import llm_router


# ======================================================================
# PHASE 4 — TOOL INPUT CONTRACTS
# ======================================================================


def _step(tool, input_data, step_id=1):
    return {
        "steps": [
            {"step_id": step_id, "tool": tool, "input": input_data,
             "depends_on": []}
        ]
    }


def test_registry_declares_required_inputs():
    """sql_query/rag_retrieval declare required inputs; others declare none."""
    assert ToolRegistry.get_tool("sql_query")["required_inputs"] == ["table"]
    assert ToolRegistry.get_tool("rag_retrieval")["required_inputs"] == ["query"]
    assert ToolRegistry.get_tool("ml_analysis")["required_inputs"] == []
    assert ToolRegistry.get_tool("memory_tool")["required_inputs"] == []


def test_register_is_backward_compatible():
    """Registering without required_inputs still works and defaults to []."""
    ToolRegistry.register(
        name="m11_probe", function=lambda x: x, description="probe"
    )
    assert ToolRegistry.get_tool("m11_probe")["required_inputs"] == []


def test_validator_rejects_sql_query_without_table():
    v = PlanValidator()
    with pytest.raises(ValueError) as exc:
        v.validate(_step("sql_query", {"query": "x"}))
    assert "table" in str(exc.value)


def test_validator_accepts_sql_query_with_table():
    v = PlanValidator()
    assert v.validate(_step("sql_query", {"table": "tasks"})) is True


def test_validator_rejects_rag_retrieval_without_query():
    v = PlanValidator()
    with pytest.raises(ValueError) as exc:
        v.validate(_step("rag_retrieval", {}))
    assert "query" in str(exc.value)


def test_validator_allows_ml_analysis_without_durations():
    """ml_analysis degrades gracefully, so it declares no required inputs."""
    v = PlanValidator()
    assert v.validate(_step("ml_analysis", {"query": "x"})) is True


def test_validator_rejects_non_dict_input_for_required_tool():
    v = PlanValidator()
    with pytest.raises(ValueError):
        v.validate(_step("sql_query", ["not", "a", "dict"]))


def test_repair_plan_satisfies_input_contracts():
    """The planner's safety-net plan must itself pass input validation."""
    plan = PlannerAgent().repair_plan("analyze bottlenecks", "unit-test")
    assert PlanValidator().validate(plan) is True


def test_planner_prompt_surfaces_required_inputs():
    """The tool section shown to the LLM must advertise required input keys."""
    section = PlannerAgent().build_tool_section()
    assert "sql_query" in section
    assert "REQUIRED input keys: table" in section
    assert "REQUIRED input keys: query" in section  # rag_retrieval


# --- tool behavior these contracts protect ---------------------------------


def test_sql_query_raises_without_valid_table():
    with pytest.raises(ValueError):
        run_sql_query({"query": "x"})


def test_ml_analysis_no_data_without_durations():
    assert run_ml_analysis({"query": "x"}) == {"status": "no_data"}


def test_ml_analysis_computes_with_durations():
    out = run_ml_analysis({"durations": [1, 1, 1, 10]})
    assert out["bottleneck_count"] == 1
    assert out["average_duration"] == pytest.approx(3.25)


# ======================================================================
# PHASE 5 — LLM PROVIDER FALLBACK
# ======================================================================


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeCompletion:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


class _FakeOpenAI:
    """Minimal stand-in for the OpenAI client used by llm_router."""

    def __init__(self, content=None, exc=None):
        self._content = content
        self._exc = exc
        self.last_kwargs = None

        outer = self

        class _Completions:
            def create(self, **kwargs):
                outer.last_kwargs = kwargs
                if outer._exc:
                    raise outer._exc
                return _FakeCompletion(outer._content)

        class _Chat:
            completions = _Completions()

        self.chat = _Chat()


@pytest.fixture(autouse=True)
def _reset_router(monkeypatch):
    """Isolate llm_router module globals for each test."""
    monkeypatch.setattr(llm_router, "LAST_LLM_META",
                        {"model": None, "mode": None})
    yield


def test_openai_success(monkeypatch):
    monkeypatch.setattr(llm_router, "openai_client", _FakeOpenAI(content="OK"))
    out = llm_router.generate_response("hi")
    assert out == "OK"
    assert llm_router.get_last_llm_meta()["mode"] == "openai"


def test_openai_call_has_bounded_timeout(monkeypatch):
    fake = _FakeOpenAI(content="OK")
    monkeypatch.setattr(llm_router, "openai_client", fake)
    llm_router.generate_response("hi")
    # A timeout MUST be passed so a hung provider cannot stall the request.
    assert "timeout" in fake.last_kwargs
    assert fake.last_kwargs["timeout"] > 0


def test_openai_timeout_falls_back_to_offline(monkeypatch):
    monkeypatch.setattr(
        llm_router, "openai_client",
        _FakeOpenAI(exc=TimeoutError("timed out")),
    )
    monkeypatch.setattr(llm_router, "ollama", None)  # no ollama tier
    out = llm_router.generate_response("hi")
    payload = json.loads(out)
    assert payload["degraded"] is True
    assert payload["approved"] is False
    assert payload["confidence"] == 0.0
    assert llm_router.get_last_llm_meta()["mode"] == "offline"


def test_openai_quota_error_falls_back(monkeypatch):
    monkeypatch.setattr(
        llm_router, "openai_client",
        _FakeOpenAI(exc=RuntimeError("insufficient_quota")),
    )
    monkeypatch.setattr(llm_router, "ollama", None)
    payload = json.loads(llm_router.generate_response("hi"))
    assert payload["approved"] is False


def test_ollama_tier_used_when_openai_absent(monkeypatch):
    monkeypatch.setattr(llm_router, "openai_client", None)

    class _FakeOllama:
        def Client(self, **kwargs):
            outer = self

            class _C:
                def chat(self, model, messages):
                    return {"message": {"content": "ollama-says-hi"}}
            return _C()

        def chat(self, model, messages):  # pragma: no cover - fallback path
            return {"message": {"content": "ollama-says-hi"}}

    monkeypatch.setattr(llm_router, "ollama", _FakeOllama())
    out = llm_router.generate_response("hi")
    assert out == "ollama-says-hi"
    assert llm_router.get_last_llm_meta()["mode"] == "ollama"


def test_ollama_client_signature_fallback(monkeypatch):
    """If Client(timeout=...) is unsupported, we fall back to module chat."""
    monkeypatch.setattr(llm_router, "openai_client", None)

    class _FakeOllama:
        def Client(self, **kwargs):
            raise TypeError("Client() got unexpected kwarg 'timeout'")

        def chat(self, model, messages):
            return {"message": {"content": "fallback-chat"}}

    monkeypatch.setattr(llm_router, "ollama", _FakeOllama())
    assert llm_router.generate_response("hi") == "fallback-chat"


def test_both_providers_unavailable_returns_safe_offline(monkeypatch):
    monkeypatch.setattr(llm_router, "openai_client", None)
    monkeypatch.setattr(llm_router, "ollama", None)
    payload = json.loads(llm_router.generate_response("hi"))
    assert payload["degraded"] is True
    assert payload["approved"] is False
    assert payload["confidence"] == 0.0
    assert llm_router.get_last_llm_meta()["mode"] == "offline"


def test_offline_fallback_not_treated_as_success_by_verifier(monkeypatch):
    """The offline payload parses to a not-approved, zero-confidence verdict."""
    monkeypatch.setattr(llm_router, "openai_client", None)
    monkeypatch.setattr(llm_router, "ollama", None)
    from src.agent.verifier import VerifierAgent
    verdict = VerifierAgent().verify("q", {"results": {}})
    assert verdict.get("approved") is False
    assert float(verdict.get("confidence", 0)) < 0.75
