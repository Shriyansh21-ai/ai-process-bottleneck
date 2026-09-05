"""
MRPL Phase 1 — LLM provider abstraction tests.

Covers:

  1. MockLLMProvider directly (deterministic planner/verifier/generic output).
  2. Provider selection / configuration (LLM_PROVIDER -> providers).
  3. The REAL PlannerAgent driven by the mock provider.
  4. The REAL planner -> executor -> verifier pipeline driven by the mock.
  5. OllamaProvider CONFIGURATION + invocation WITHOUT a running Ollama
     (the ``ollama`` package is faked; no real inference happens here).
  6. OpenAIProvider configuration (injected client; no real API call).

IMPORTANT: No test in this module performs real Ollama or OpenAI inference.
Ollama inference is validated on a capable machine by another team member.
"""

import asyncio
import json

import pytest

from src.llm import (
    MockLLMProvider,
    OllamaProvider,
    OpenAIProvider,
    get_provider,
    select_providers,
)
from src.llm.base import LLMProviderError
from src.llm.config import get_llm_provider_name
from src.llm.mock_provider import build_mock_response
from src.tools.tool_registry import ToolRegistry


# Minimal reproductions of the real system-prompt markers so we can build
# representative prompts without importing the agent modules everywhere.
_PLANNER_PROMPT = (
    "You are an autonomous AI Planner.\n"
    "==========================================\n"
    "USER REQUEST\n"
    "==========================================\n\n"
    "Find the slowest task in the pipeline\n\n"
    "==========================================\n"
    "PREVIOUS FEEDBACK\n"
)
_VERIFIER_PROMPT = "You are a Verification Agent.\nEXECUTION RESULT:\n{}"


# ======================================================================
# 1. MOCK PROVIDER — DIRECT
# ======================================================================

def test_mock_provider_planner_prompt_returns_valid_plan_json():
    provider = MockLLMProvider()
    out = provider.generate(_PLANNER_PROMPT)
    plan = json.loads(out)

    assert plan["goal"] == "Find the slowest task in the pipeline"
    tools = [s["tool"] for s in plan["steps"]]
    assert tools == ["rag_retrieval", "ml_analysis"]
    # rag_retrieval requires a 'query' input — the mock must supply it.
    assert plan["steps"][0]["input"]["query"]


def test_mock_plan_is_valid_against_real_tool_registry():
    """The mock plan must pass the REAL PlanValidator so the pipeline continues."""
    import src.tools.register_tools  # noqa: F401 ensure real tools registered
    from src.agent.plan_validator import PlanValidator

    plan = json.loads(MockLLMProvider().generate(_PLANNER_PROMPT))
    # Raises on any invalidity (unknown tool, missing required input, cycle).
    assert PlanValidator().validate(plan) is True


def test_mock_plan_never_trips_planner_offline_sentinel():
    """Planner treats a '"confidence"' substring as the offline sentinel."""
    out = MockLLMProvider().generate(_PLANNER_PROMPT)
    assert '"confidence"' not in out


def test_mock_provider_verifier_prompt_returns_approval():
    verdict = json.loads(MockLLMProvider().generate(_VERIFIER_PROMPT))
    assert verdict["approved"] is True
    assert verdict["confidence"] >= 0.75
    assert verdict["issues"] == []


def test_mock_provider_generic_prompt_returns_text():
    out = MockLLMProvider().generate("just say something")
    assert isinstance(out, str)
    assert "MOCK LLM" in out


def test_mock_provider_is_deterministic():
    a = build_mock_response(_PLANNER_PROMPT)
    b = build_mock_response(_PLANNER_PROMPT)
    assert a == b


def test_mock_provider_records_model_and_is_available():
    provider = MockLLMProvider()
    provider.generate("hi")
    assert provider.last_model == "mock-model"
    assert provider.is_available() is True
    assert provider.name == "mock"


# ======================================================================
# 2. PROVIDER SELECTION / CONFIGURATION
# ======================================================================

def test_selector_defaults_to_auto_when_unset(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    assert get_llm_provider_name() == "auto"


@pytest.mark.parametrize(
    "value,expected",
    [("mock", "mock"), ("ollama", "ollama"), ("openai", "openai"),
     ("auto", "auto"), ("  MOCK  ", "mock"), ("nonsense", "auto")],
)
def test_selector_normalises_values(monkeypatch, value, expected):
    monkeypatch.setenv("LLM_PROVIDER", value)
    assert get_llm_provider_name() == expected


def test_select_providers_explicit(monkeypatch):
    assert isinstance(select_providers("mock")[0], MockLLMProvider)
    assert isinstance(select_providers("ollama")[0], OllamaProvider)
    assert isinstance(select_providers("openai")[0], OpenAIProvider)


def test_select_providers_auto_skips_unavailable_tiers(monkeypatch):
    # No OpenAI key and no ollama package -> empty chain -> router goes offline.
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("src.llm.ollama_provider.ollama", None)
    assert select_providers("auto") == []


def test_select_providers_auto_includes_openai_when_keyed(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr("src.llm.ollama_provider.ollama", None)
    chain = select_providers("auto")
    assert len(chain) == 1
    assert isinstance(chain[0], OpenAIProvider)


def test_get_provider_by_name_and_unknown():
    assert isinstance(get_provider("mock"), MockLLMProvider)
    with pytest.raises(ValueError):
        get_provider("does-not-exist")


# ======================================================================
# 3. REAL PLANNER DRIVEN BY THE MOCK PROVIDER (via generate_response)
# ======================================================================

def test_real_planner_uses_mock_provider(monkeypatch):
    import src.tools.register_tools  # noqa: F401
    from src.agent.planner import PlannerAgent
    from src.genai.llm_router import get_last_llm_meta

    monkeypatch.setenv("LLM_PROVIDER", "mock")

    plan = PlannerAgent().create_plan(user_query="Where is the bottleneck?")

    assert [s["tool"] for s in plan["steps"]] == ["rag_retrieval", "ml_analysis"]
    assert get_last_llm_meta()["mode"] == "mock"


# ======================================================================
# 4. REAL PIPELINE: planner -> executor -> verifier, all on the mock
# ======================================================================

@pytest.fixture
def stub_tools():
    """Override rag_retrieval + ml_analysis with DB-free stubs, then restore.

    The mock always emits a rag_retrieval -> ml_analysis plan; stubbing those
    two names lets the REAL executor run it with no database, so we exercise the
    genuine planner/executor/verifier code paths end to end.
    """
    saved = dict(ToolRegistry._tools)
    ToolRegistry.register(
        name="rag_retrieval",
        function=lambda payload: {"context": "stub-context"},
        description="stub rag",
        required_inputs=["query"],
    )
    ToolRegistry.register(
        name="ml_analysis",
        function=lambda payload: {"bottleneck": "step-2"},
        description="stub ml",
    )
    try:
        yield
    finally:
        ToolRegistry._tools = saved


def test_full_pipeline_on_mock_provider(monkeypatch, stub_tools):
    from src.agent.planner import PlannerAgent
    from src.agent.executor import ToolExecutor
    from src.agent.verifier import VerifierAgent

    monkeypatch.setenv("LLM_PROVIDER", "mock")

    query = "Find the slowest task"
    plan = PlannerAgent().create_plan(user_query=query)

    executor = ToolExecutor(db=None)  # db-free: stubs need no DB
    result = asyncio.run(executor.execute_plan(plan))

    # Every step produced output, none errored.
    step_results = result["results"]
    assert len(step_results) == 2
    assert all("error" not in r for r in step_results.values())
    assert all("output" in r for r in step_results.values())

    # Verifier (also on the mock) approves with actionable confidence.
    verdict = VerifierAgent().verify(query, result)
    assert verdict["approved"] is True
    assert verdict["confidence"] >= 0.75


# ======================================================================
# 5. OLLAMA PROVIDER — CONFIGURATION + INVOCATION WITHOUT REAL OLLAMA
# ======================================================================

def test_ollama_provider_reads_configuration(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "phi3:mini")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://friend-box:11434")
    monkeypatch.setenv("OLLAMA_TEMPERATURE", "0.3")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "42")

    provider = OllamaProvider()
    assert provider.model == "phi3:mini"
    assert provider.base_url == "http://friend-box:11434"
    assert provider.temperature == 0.3
    assert provider.timeout == 42.0


def test_ollama_unavailable_when_package_absent(monkeypatch):
    monkeypatch.setattr("src.llm.ollama_provider.ollama", None)
    provider = OllamaProvider()
    assert provider.is_available() is False
    with pytest.raises(LLMProviderError):
        provider.generate("hi")


class _FakeOllamaClient:
    def __init__(self, host=None, timeout=None):
        self.host = host
        self.timeout = timeout
        _FakeOllama.last_client = self

    def chat(self, model=None, messages=None, options=None):
        self.model = model
        self.messages = messages
        self.options = options
        return {"message": {"content": "ollama-says-hi"}}


class _FakeOllama:
    """Stand-in for the real ``ollama`` module — records how it was invoked."""
    last_client = None
    Client = _FakeOllamaClient


def test_ollama_provider_invokes_with_configured_values(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "phi3:mini")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://friend-box:11434")
    monkeypatch.setenv("OLLAMA_TEMPERATURE", "0.5")
    monkeypatch.setattr("src.llm.ollama_provider.ollama", _FakeOllama)

    provider = OllamaProvider()
    out = provider.generate("hello")

    assert out == "ollama-says-hi"
    client = _FakeOllama.last_client
    assert client.host == "http://friend-box:11434"
    assert client.model == "phi3:mini"
    assert client.options == {"temperature": 0.5}
    assert provider.last_model == "phi3:mini"


def test_generate_response_ollama_selection_offline_when_unavailable(monkeypatch):
    """LLM_PROVIDER=ollama with no ollama package -> fail-closed offline JSON."""
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setattr("src.llm.ollama_provider.ollama", None)
    from src.genai.llm_router import generate_response, get_last_llm_meta

    payload = json.loads(generate_response("anything"))
    assert payload["degraded"] is True
    assert payload["approved"] is False
    assert get_last_llm_meta()["mode"] == "offline"


def test_generate_response_ollama_selection_uses_fake_ollama(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "phi3:mini")
    monkeypatch.setattr("src.llm.ollama_provider.ollama", _FakeOllama)
    from src.genai.llm_router import generate_response, get_last_llm_meta

    assert generate_response("hi") == "ollama-says-hi"
    meta = get_last_llm_meta()
    assert meta["mode"] == "ollama"
    assert meta["model"] == "phi3:mini"


# ======================================================================
# 6. OPENAI PROVIDER — CONFIGURATION (injected client; no real API call)
# ======================================================================

class _FakeMessage:
    def __init__(self, content):
        self.message = type("M", (), {"content": content})


class _FakeCompletions:
    def __init__(self, content):
        self._content = content
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return type("R", (), {"choices": [_FakeMessage(self._content)]})


class _FakeOpenAIClient:
    def __init__(self, content="openai-hi"):
        self.chat = type("C", (), {"completions": _FakeCompletions(content)})


def test_openai_provider_uses_injected_client_and_config(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")
    client = _FakeOpenAIClient()
    provider = OpenAIProvider(client=client)

    out = provider.generate("hello")
    assert out == "openai-hi"
    assert client.chat.completions.kwargs["model"] == "gpt-4o-mini"
    assert provider.last_model == "gpt-4o-mini"


def test_openai_provider_unavailable_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = OpenAIProvider()
    assert provider.is_available() is False
    with pytest.raises(LLMProviderError):
        provider.generate("hi")


def test_generate_response_openai_selection_offline_without_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from src.genai.llm_router import generate_response, get_last_llm_meta

    payload = json.loads(generate_response("anything"))
    assert payload["degraded"] is True
    assert get_last_llm_meta()["mode"] == "offline"
