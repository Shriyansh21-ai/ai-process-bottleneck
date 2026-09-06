"""
Inspection findings synthesis tool (MRPL Phase 3).

This is a REAL tool registered in the ToolRegistry, so the genuine PlannerAgent
can include it in a plan and the genuine ToolExecutor runs it. It turns the
page-tagged evidence retrieved by the ``rag_retrieval`` step into structured,
provenance-carrying inspection findings.

Crucially, it depends ONLY on the provider abstraction
(``src.genai.llm_router.generate_response``): the exact same code path produces
findings whether ``LLM_PROVIDER`` is ``mock`` (deterministic, offline) or
``ollama`` (a real local model on a teammate's machine). There is NO separate
Ollama logic here.

Contract:

  input:
    * ``context``  — injected by the executor: the completed step results, from
      which this tool harvests the ``rag_retrieval`` output (evidence chunks).
    * ``query``    — the analysis instruction (required input).
    * ``evidence`` — OPTIONAL explicit evidence list (used by unit tests to run
      the tool without an upstream retrieval step).

  output:
    {
      "findings": [ { title, description, severity, evidence, page_number,
                      extraction_method, recommendation, confidence }, ... ],
      "evidence": [ { page_number, extraction_method, content }, ... ],
      "degraded": bool,   # True when the LLM was offline/unusable
    }

The tool does NOT enforce the severity enum or the page/evidence guard — that is
the job of the deterministic inspection verifier, which cross-checks findings
against the very evidence returned here.
"""

import json
import logging
from typing import List

from src.genai.llm_router import generate_response

logger = logging.getLogger("tools.inspection")

# Marker in the system prompt the mock provider keys on. Distinct from the
# planner/verifier markers so the mock routes findings prompts correctly.
_FINDINGS_MARKER = "Inspection Findings Synthesizer"

# Bounds so a large document cannot blow up the findings prompt.
_MAX_EVIDENCE_ITEMS = 8
_MAX_EVIDENCE_CHARS = 800

_SYSTEM_PROMPT = f"""You are an Inspection Findings Synthesizer.

You are given evidence chunks extracted from a single inspection report. Each
chunk carries its source page number and how it was extracted (text or ocr).

Your job:
- Identify concrete, safety- or quality-relevant findings SUPPORTED by the
  evidence.
- For every finding, quote or closely paraphrase the supporting evidence and
  cite the page_number it came from. NEVER invent a page number that is not in
  the evidence.
- Assign a severity from EXACTLY this set: LOW, MEDIUM, HIGH, CRITICAL.
- Give a short, actionable recommendation and a confidence between 0 and 1.
- If the evidence does not support any finding, return an empty findings list.

Return STRICT JSON ONLY in this shape:
{{"findings": [{{"title": "...", "description": "...", "severity": "HIGH",
  "evidence": "...", "page_number": 4, "recommendation": "...",
  "confidence": 0.9}}]}}
"""


def _harvest_evidence(input_data: dict) -> List[dict]:
    """Collect page-tagged evidence for this tool.

    Preference order:
      1. an explicit ``evidence`` list on the input (unit tests);
      2. the ``rag_retrieval`` step output found in the injected ``context``.

    Returns a list of ``{page_number, extraction_method, content}`` dicts.
    """
    explicit = input_data.get("evidence")
    if isinstance(explicit, list):
        chunks = explicit
    else:
        chunks = []
        context = input_data.get("context") or {}
        # context is {step_id: {"tool": ..., "output": ...}}; find retrieval.
        for step in (context.values() if isinstance(context, dict) else []):
            if not isinstance(step, dict):
                continue
            if step.get("tool") == "rag_retrieval":
                output = step.get("output")
                if isinstance(output, list):
                    chunks.extend(output)

    evidence = []
    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue
        content = (chunk.get("content") or "").strip()
        if not content:
            continue
        evidence.append(
            {
                "page_number": chunk.get("page_number"),
                "extraction_method": chunk.get("extraction_method"),
                "content": content[:_MAX_EVIDENCE_CHARS],
            }
        )
        if len(evidence) >= _MAX_EVIDENCE_ITEMS:
            break
    return evidence


def _parse_findings(text: str) -> list:
    """Best-effort parse of the model's findings JSON (tolerant of code fences)."""
    if not text:
        return []

    cleaned = text.strip()
    # Strip markdown code fences a real model may add.
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        # Drop an optional leading language tag line (e.g. "json").
        newline = cleaned.find("\n")
        if newline != -1 and cleaned[:newline].strip().lower() in ("json", ""):
            cleaned = cleaned[newline + 1:]

    try:
        payload = json.loads(cleaned)
    except (ValueError, TypeError):
        # Last resort: locate the first '{' ... last '}' block.
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return []
        try:
            payload = json.loads(cleaned[start:end + 1])
        except (ValueError, TypeError):
            return []

    if isinstance(payload, dict):
        findings = payload.get("findings", [])
    elif isinstance(payload, list):
        findings = payload
    else:
        findings = []

    return findings if isinstance(findings, list) else []


def synthesize_inspection_findings(input_data: dict) -> dict:
    """ToolRegistry entry point: evidence -> structured findings (via provider)."""
    query = input_data.get("query", "")
    evidence = _harvest_evidence(input_data)

    if not evidence:
        # No retrieved evidence -> no findings can be grounded. The verifier
        # turns this into a clean "no_findings"/verification-failure decision.
        logger.info("inspection_findings: no evidence available")
        return {"findings": [], "evidence": [], "degraded": False}

    prompt = (
        f"{_SYSTEM_PROMPT}\n"
        f"ANALYSIS INSTRUCTION:\n{query}\n\n"
        f"RETRIEVED EVIDENCE (JSON):\n{json.dumps(evidence)}\nEND EVIDENCE\n"
    )

    raw = generate_response(prompt)

    # Detect the router's fail-closed offline sentinel so we never treat a
    # degraded (unverified) response as real findings.
    degraded = False
    try:
        maybe = json.loads(raw)
        if isinstance(maybe, dict) and maybe.get("degraded") is True:
            degraded = True
    except (ValueError, TypeError):
        degraded = False

    findings = [] if degraded else _parse_findings(raw)

    logger.info(
        "inspection_findings: evidence=%d findings=%d degraded=%s",
        len(evidence), len(findings), degraded,
    )

    return {"findings": findings, "evidence": evidence, "degraded": degraded}
