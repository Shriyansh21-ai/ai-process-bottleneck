"""
Pydantic response schemas for AgentRun management / reporting endpoints.

These schemas are ADDITIVE and read-only. They intentionally expose a
curated view of the AgentRun table so that:

  * summary/list endpoints stay lightweight (no huge plan/execution JSON)
  * detail endpoints return the full, safely-parsed run
  * nullable JSON/text columns never crash serialization

None of the core execution flow depends on this module.
"""

import json
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _safe_json(value: Any) -> Any:
    """
    Safely turn a stored plan / execution_result / verification_result
    value into a JSON-friendly object.

    The core system stores these as ``json.dumps(...)`` text, but older or
    malformed rows may hold plain strings, ``None`` or already-decoded
    objects. We never raise here – worst case we hand back the raw string.
    """
    if value is None:
        return None

    if isinstance(value, (dict, list, int, float, bool)):
        return value

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except (ValueError, TypeError):
            # Malformed JSON – return the raw text instead of exploding.
            return value

    return value


def _count_steps(execution_result: Any) -> Optional[int]:
    """Best-effort step count derived from a decoded execution_result."""
    if isinstance(execution_result, dict):
        for key in ("results", "steps", "step_results"):
            maybe = execution_result.get(key)
            if isinstance(maybe, (list, dict)):
                return len(maybe)
    if isinstance(execution_result, list):
        return len(execution_result)
    return None


# ------------------------------------------------------------------
# Summary (lightweight – used by list / search / filtered endpoints)
# ------------------------------------------------------------------

class AgentRunSummary(BaseModel):
    """Compact representation of a run – safe for large lists."""

    model_config = ConfigDict(from_attributes=True)

    run_id: int = Field(..., description="Unique run identifier")
    session_id: str
    user_query: str
    status: str

    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    steps_total: Optional[int] = Field(
        None, description="Number of execution steps, if recorded"
    )
    execution_duration_ms: Optional[int] = Field(
        None, description="End-to-end execution duration in milliseconds"
    )
    retry_count: Optional[int] = None

    confidence: Optional[float] = Field(
        None, description="Verifier confidence score, if available"
    )
    approved: Optional[bool] = Field(
        None, description="Whether the run passed verification"
    )
    verification_status: Optional[str] = Field(
        None, description="Derived pass/fail label for the run"
    )

    @classmethod
    def from_run(cls, run: Any) -> "AgentRunSummary":
        approved = getattr(run, "approved", None)
        if approved is True:
            verification_status = "passed"
        elif approved is False:
            verification_status = "failed"
        else:
            verification_status = None

        return cls(
            run_id=run.id,
            session_id=run.session_id,
            user_query=run.user_query,
            status=run.status,
            created_at=getattr(run, "created_at", None),
            started_at=getattr(run, "started_at", None),
            completed_at=getattr(run, "completed_at", None),
            steps_total=getattr(run, "steps_total", None),
            execution_duration_ms=getattr(run, "duration_ms", None),
            retry_count=getattr(run, "retry_count", None),
            confidence=getattr(run, "confidence", None),
            approved=approved,
            verification_status=verification_status,
        )


# ------------------------------------------------------------------
# Detail (full – used by single-run endpoint)
# ------------------------------------------------------------------

class AgentRunDetail(BaseModel):
    """Full representation of a single run with parsed JSON payloads."""

    model_config = ConfigDict(from_attributes=True)

    run_id: int
    session_id: str
    user_query: str
    status: str

    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_duration_ms: Optional[int] = None

    plan: Optional[Any] = None
    execution_result: Optional[Any] = None
    verification_result: Optional[Any] = None
    final_response: Optional[str] = None

    steps_total: Optional[int] = None
    steps_success: Optional[int] = None
    steps_failed: Optional[int] = None
    retry_count: Optional[int] = None

    tools_used: Optional[Any] = None
    execution_mode: Optional[str] = None
    memory_used: Optional[bool] = None
    rag_used: Optional[bool] = None

    confidence: Optional[float] = None
    approved: Optional[bool] = None
    llm_model: Optional[str] = None

    @classmethod
    def from_run(cls, run: Any) -> "AgentRunDetail":
        execution_result = _safe_json(getattr(run, "execution_result", None))

        steps_total = getattr(run, "steps_total", None)
        if not steps_total:
            steps_total = _count_steps(execution_result)

        return cls(
            run_id=run.id,
            session_id=run.session_id,
            user_query=run.user_query,
            status=run.status,
            created_at=getattr(run, "created_at", None),
            started_at=getattr(run, "started_at", None),
            completed_at=getattr(run, "completed_at", None),
            execution_duration_ms=getattr(run, "duration_ms", None),
            plan=_safe_json(getattr(run, "plan", None)),
            execution_result=execution_result,
            verification_result=_safe_json(
                getattr(run, "verification_result", None)
            ),
            final_response=getattr(run, "final_response", None),
            steps_total=steps_total,
            steps_success=getattr(run, "steps_success", None),
            steps_failed=getattr(run, "steps_failed", None),
            retry_count=getattr(run, "retry_count", None),
            tools_used=getattr(run, "tools_used", None),
            execution_mode=getattr(run, "execution_mode", None),
            memory_used=getattr(run, "memory_used", None),
            rag_used=getattr(run, "rag_used", None),
            confidence=getattr(run, "confidence", None),
            approved=getattr(run, "approved", None),
            llm_model=getattr(run, "llm_model", None),
        )


# ------------------------------------------------------------------
# Execution step (per-step timeline — used by /runs/{id}/steps)
# ------------------------------------------------------------------

# Payload summaries are truncated so the timeline endpoint never streams huge
# raw tool input/output blobs to the dashboard (matches the summary/detail
# split used elsewhere in this module).
_STEP_PAYLOAD_MAX = 600


def _truncate(value: Any, limit: int = _STEP_PAYLOAD_MAX) -> Optional[str]:
    """Return a short, display-safe summary of a stored step payload."""
    if value is None:
        return None
    text = value if isinstance(value, str) else str(value)
    text = text.strip()
    if not text:
        return None
    if len(text) > limit:
        return text[:limit] + "…"
    return text


class AgentRunStep(BaseModel):
    """One recorded execution step (from the step_executions audit table)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    step_id: Optional[int] = Field(None, description="Ordinal within the run")
    tool_name: Optional[str] = None
    status: Optional[str] = None
    execution_time_ms: Optional[int] = None
    retry_count: Optional[int] = None
    input_summary: Optional[str] = Field(
        None, description="Truncated tool input payload"
    )
    output_summary: Optional[str] = Field(
        None, description="Truncated tool output payload"
    )
    error: Optional[str] = Field(None, description="Failure reason, if any")
    created_at: Optional[datetime] = None

    @classmethod
    def from_step(cls, step: Any) -> "AgentRunStep":
        return cls(
            id=step.id,
            step_id=getattr(step, "step_id", None),
            tool_name=getattr(step, "tool_name", None),
            status=getattr(step, "status", None),
            execution_time_ms=getattr(step, "execution_time_ms", None),
            retry_count=getattr(step, "retry_count", None),
            input_summary=_truncate(getattr(step, "input_payload", None)),
            output_summary=_truncate(getattr(step, "output_payload", None)),
            error=_truncate(getattr(step, "error", None)),
            created_at=getattr(step, "created_at", None),
        )


# ------------------------------------------------------------------
# Statistics
# ------------------------------------------------------------------

class AgentRunStatistics(BaseModel):
    """Aggregate counters computed in SQL for the run dashboard."""

    total_runs: int
    successful_runs: int
    failed_runs: int
    running_runs: int
    pending_runs: int
    other_runs: int

    success_rate: float = Field(..., description="Successful runs as a %")
    failure_rate: float = Field(..., description="Failed runs as a %")
    average_duration_ms: Optional[float] = Field(
        None, description="Average execution duration across timed runs"
    )


# ------------------------------------------------------------------
# Pagination envelope
# ------------------------------------------------------------------

class PaginatedAgentRuns(BaseModel):
    """Paginated collection of run summaries."""

    items: List[AgentRunSummary]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool

    @classmethod
    def build(
        cls,
        runs: List[Any],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedAgentRuns":
        total_pages = (total + page_size - 1) // page_size if page_size else 0
        return cls(
            items=[AgentRunSummary.from_run(r) for r in runs],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1 and total_pages > 0,
        )
