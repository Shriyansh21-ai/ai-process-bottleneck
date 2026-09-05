"""
Deterministic mock LLM provider (MRPL Phase 1).

Purpose: let the FULL Neuroflow agent pipeline (planner -> executor ->
verifier) run on hardware that cannot host Ollama, with no external API, no
network, and no OpenAI key — while producing responses in the exact format the
real pipeline expects.

This is deliberately NOT a shortcut that bypasses the planner/executor: it
returns the same JSON contracts the real LLM would, so the genuine
:class:`~src.agent.planner.PlannerAgent`, :class:`~src.agent.plan_validator.PlanValidator`,
:class:`~src.agent.executor.ToolExecutor` and
:class:`~src.agent.verifier.VerifierAgent` all execute normally.

The single entry point the pipeline uses is a prompt string, so the mock
inspects the prompt to decide which contract to satisfy:

  * a planner prompt  -> a STRICT-JSON execution plan using real registered
    tools (rag_retrieval + ml_analysis), so it passes PlanValidator;
  * a verifier prompt -> a STRICT-JSON approval verdict with high confidence;
  * anything else      -> a short deterministic text completion.

Determinism: identical prompts always yield identical output (no randomness,
no timestamps), which is exactly what unit/integration tests need.
"""

import json
from typing import Optional

from src.llm.base import LLMProvider


# Markers taken from the real system prompts (src/agent/planner.py and
# src/agent/verifier.py). Matching on these keeps the mock aligned with the
# actual pipeline rather than guessing.
_PLANNER_MARKER = "autonomous AI Planner"
_VERIFIER_MARKER = "Verification Agent"

_USER_REQUEST_HEADER = "USER REQUEST"
_SECTION_DELIM = "=========================================="

# Default confidence emitted by the mock verifier. Above the controller's
# CONFIDENCE_THRESHOLD (0.75) so a healthy mock run reaches the success path.
_MOCK_CONFIDENCE = 0.9


def _extract_user_query(prompt: str) -> str:
    """Pull the user's request out of a planner prompt.

    The planner formats the query inside a ``USER REQUEST`` section delimited by
    lines of ``=``. We return that block so the mock plan's rag_retrieval step
    carries a meaningful (and deterministic) query. Falls back to a constant
    when the layout is unrecognised — rag_retrieval only needs a non-empty
    string.
    """
    idx = prompt.find(_USER_REQUEST_HEADER)
    if idx == -1:
        return "mock development query"

    rest = prompt[idx + len(_USER_REQUEST_HEADER):]
    for segment in rest.split(_SECTION_DELIM):
        cleaned = segment.strip()
        if cleaned:
            # Cap length: the query is only used as a tool input, not re-parsed.
            return cleaned[:500]
    return "mock development query"


def build_mock_plan(prompt: str) -> str:
    """Return a STRICT-JSON execution plan valid against the real ToolRegistry.

    Uses ``rag_retrieval`` (requires a ``query`` input) followed by a dependent
    ``ml_analysis`` step. Both tools are registered by
    ``src.tools.register_tools``; this shape passes PlanValidator (required
    inputs present, no cycles, known tools) and exercises the executor's
    dependency resolution. MUST NOT contain the substring ``"confidence"`` — the
    planner treats that as the offline-fallback sentinel and would discard the
    plan.
    """
    user_query = _extract_user_query(prompt)

    plan = {
        "goal": user_query,
        "steps": [
            {
                "step_id": 1,
                "tool": "rag_retrieval",
                "purpose": "Retrieve relevant historical context (mock)",
                "input": {"query": user_query},
                "depends_on": [],
            },
            {
                "step_id": 2,
                "tool": "ml_analysis",
                "purpose": "Analyze retrieved context for bottlenecks (mock)",
                "input": {},
                "depends_on": [1],
            },
        ],
    }
    return json.dumps(plan)


def build_mock_verdict() -> str:
    """Return a STRICT-JSON verifier verdict: approved, high confidence."""
    return json.dumps(
        {
            "approved": True,
            "confidence": _MOCK_CONFIDENCE,
            "issues": [],
        }
    )


def build_mock_response(prompt: str) -> str:
    """Route a prompt to the correct deterministic mock contract."""
    if _VERIFIER_MARKER in prompt:
        return build_mock_verdict()
    if _PLANNER_MARKER in prompt:
        return build_mock_plan(prompt)
    # Generic completion for any other caller. Plain text: the only router
    # callers that json.loads() the result are the planner and verifier, both
    # handled above.
    return "[MOCK LLM] deterministic response — no live model was contacted."


class MockLLMProvider(LLMProvider):
    """Deterministic, dependency-free provider for development and tests."""

    name = "mock"

    def __init__(self, model: str = "mock-model") -> None:
        super().__init__()
        self.model = model
        self.last_model = model

    def generate(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        timeout: Optional[float] = None,
    ) -> str:
        # temperature/timeout are accepted for interface parity but ignored —
        # the mock is fully deterministic and never makes a call.
        self.last_model = model or self.model
        return build_mock_response(prompt)

    def is_available(self) -> bool:
        return True
