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
import re
from typing import Optional

from src.llm.base import LLMProvider


# Markers taken from the real system prompts (src/agent/planner.py and
# src/agent/verifier.py). Matching on these keeps the mock aligned with the
# actual pipeline rather than guessing.
_PLANNER_MARKER = "autonomous AI Planner"
_VERIFIER_MARKER = "Verification Agent"
# Marker from the inspection findings tool (src/tools/inspection_tool.py).
_FINDINGS_MARKER = "Inspection Findings Synthesizer"

_USER_REQUEST_HEADER = "USER REQUEST"
_SECTION_DELIM = "=========================================="

# Marker the inspection workflow embeds in the analysis query so the mock
# planner produces an inspection-specific plan (retrieval -> findings) instead
# of the generic bottleneck plan. Kept distinct so ordinary queries are
# unaffected.
_INSPECTION_MARKER = "MRPL_INSPECTION_ANALYSIS"

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


def _parse_document_id(text: str):
    """Extract ``document_id=<int>`` from an inspection query, or None."""
    match = re.search(r"document_id\s*=\s*(\d+)", text)
    if match:
        try:
            return int(match.group(1))
        except (TypeError, ValueError):
            return None
    return None


def _plain_instruction(user_query: str) -> str:
    """Strip the internal routing lines from an inspection query.

    The service prefixes the query with ``MRPL_INSPECTION_ANALYSIS`` and a
    ``document_id=<id>`` line so the planner selects the inspection plan and
    scopes retrieval. Those tokens must NOT leak into the semantic retrieval
    query (e.g. ``MRPL`` would spuriously match document metadata), so we keep
    only the human instruction lines for the ``query`` fed to rag_retrieval.
    """
    lines = []
    for line in (user_query or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == _INSPECTION_MARKER:
            continue
        if re.match(r"document_id\s*=", stripped):
            continue
        lines.append(stripped)
    plain = " ".join(lines).strip()
    return plain or "identify safety-critical inspection findings"


def build_mock_inspection_plan(user_query: str) -> str:
    """STRICT-JSON plan for the inspection workflow: retrieval -> findings.

    Step 1 scopes ``rag_retrieval`` to the uploaded document (``document_id``)
    so evidence is drawn only from that report; step 2 synthesizes findings from
    that evidence. Both tools are real and registered, so this passes the real
    PlanValidator and runs on the real ToolExecutor. MUST NOT contain the
    substring ``"confidence"`` (planner offline sentinel).
    """
    document_id = _parse_document_id(user_query)
    instruction = _plain_instruction(user_query)

    retrieval_input = {"query": instruction, "top_k": 8}
    if document_id is not None:
        retrieval_input["document_id"] = document_id

    plan = {
        "goal": user_query,
        "steps": [
            {
                "step_id": 1,
                "tool": "rag_retrieval",
                "purpose": "Retrieve page-tagged evidence from the inspection document (mock)",
                "input": retrieval_input,
                "depends_on": [],
            },
            {
                "step_id": 2,
                "tool": "inspection_findings",
                "purpose": "Synthesize structured findings from retrieved evidence (mock)",
                "input": {"query": instruction},
                "depends_on": [1],
            },
        ],
    }
    return json.dumps(plan)


def build_mock_plan(prompt: str) -> str:
    """Return a STRICT-JSON execution plan valid against the real ToolRegistry.

    For an inspection analysis query (carrying ``MRPL_INSPECTION_ANALYSIS``) the
    plan is retrieval -> inspection_findings; otherwise it is the generic
    ``rag_retrieval`` -> ``ml_analysis`` bottleneck plan. Both tools in each plan
    are registered by ``src.tools.register_tools``; the shape passes
    PlanValidator (required inputs present, no cycles, known tools) and exercises
    the executor's dependency resolution. MUST NOT contain the substring
    ``"confidence"`` — the planner treats that as the offline-fallback sentinel
    and would discard the plan.
    """
    user_query = _extract_user_query(prompt)

    if _INSPECTION_MARKER in prompt:
        return build_mock_inspection_plan(user_query)

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


def _parse_evidence(prompt: str) -> list:
    """Extract the JSON evidence array the findings tool embeds in its prompt."""
    header = "RETRIEVED EVIDENCE (JSON):"
    start = prompt.find(header)
    if start == -1:
        return []
    tail = prompt[start + len(header):]
    end = tail.find("END EVIDENCE")
    block = tail[:end] if end != -1 else tail
    try:
        data = json.loads(block.strip())
    except (ValueError, TypeError):
        return []
    return data if isinstance(data, list) else []


# Max findings the mock emits (one per retrieved evidence chunk, capped).
_MAX_MOCK_FINDINGS = 5

# Deterministic keyword -> (severity, title, recommendation) classification. The
# mock is not a real model; this lets a mock run produce varied, content-grounded
# findings so the demo is representative. Order matters: first match wins.
_CLASSIFIERS = [
    (
        ("rupture", "imminent failure", "catastrophic"),
        "CRITICAL",
        "Critical integrity risk identified",
        "Isolate and remediate immediately before returning to service.",
    ),
    (
        ("weld", "joint", "seam", "wall thickness", "pressure containment"),
        "HIGH",
        "Pipe/joint integrity concern",
        "Perform a fitness-for-service assessment of the affected joint.",
    ),
    (
        ("corrosion", "section loss", "material loss"),
        "HIGH",
        "Corrosion / material loss requiring assessment",
        "Schedule a detailed inspection and maintenance assessment.",
    ),
    (
        ("hazard", "handrail", "walkway", "grating", "fire", "emergency", "obstruct"),
        "HIGH",
        "Safety hazard requiring prompt action",
        "Rectify the safety hazard as a priority before the next shift.",
    ),
    (
        ("wear", "coating", "gasket", "aged", "minor", "monitor"),
        "MEDIUM",
        "Equipment wear observed",
        "Monitor and re-inspect at the next scheduled maintenance window.",
    ),
]

_DEFAULT_CLASS = (
    "LOW",
    "General inspection observation",
    "Record for routine follow-up.",
)

_CONFIDENCE_BY_SEVERITY = {
    "CRITICAL": 0.95,
    "HIGH": 0.9,
    "MEDIUM": 0.82,
    "LOW": 0.7,
}


def _classify(content: str):
    """Deterministically map evidence text to (severity, title, recommendation)."""
    lower = (content or "").lower()
    for keywords, severity, title, recommendation in _CLASSIFIERS:
        if any(kw in lower for kw in keywords):
            return severity, title, recommendation
    return _DEFAULT_CLASS


def build_mock_findings(prompt: str) -> str:
    """Return deterministic, evidence-grounded findings JSON.

    One finding is produced per retrieved evidence chunk (capped), with a
    severity/title/recommendation classified deterministically from the chunk
    text. Every finding references ONLY a page number present in the supplied
    evidence, so it passes the deterministic evidence/provenance guard in the
    inspection verifier. This does NOT bypass the pipeline — the tool still calls
    this via the provider abstraction, and the real verifier still validates it.
    """
    evidence = _parse_evidence(prompt)
    if not evidence:
        return json.dumps({"findings": []})

    findings = []
    for item in evidence[:_MAX_MOCK_FINDINGS]:
        content = item.get("content") or ""
        severity, title, recommendation = _classify(content)
        findings.append(
            {
                "title": title,
                "description": (
                    "Identified from the inspection report evidence: the passage "
                    "describes a condition consistent with a "
                    f"{severity.lower()}-severity finding."
                ),
                "severity": severity,
                "evidence": content[:240],
                "page_number": item.get("page_number"),
                "recommendation": recommendation,
                "confidence": _CONFIDENCE_BY_SEVERITY[severity],
            }
        )

    return json.dumps({"findings": findings})


def build_mock_response(prompt: str) -> str:
    """Route a prompt to the correct deterministic mock contract."""
    if _VERIFIER_MARKER in prompt:
        return build_mock_verdict()
    if _FINDINGS_MARKER in prompt:
        return build_mock_findings(prompt)
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
