import json
import logging
from datetime import datetime, timezone

from sqlalchemy import distinct, func
from sqlalchemy.orm import load_only

from src.db.models.agent_run import AgentRun
from src.db.models.step_execution import StepExecution

logger = logging.getLogger("agent_run_summary")

# Tools whose execution implies a capability was actually used.
RAG_TOOLS = {"rag_retrieval"}
MEMORY_TOOLS = {"memory_tool"}



# ==========================================
# STATUS VOCABULARY
# ==========================================
# The core execution flow (AgentController) writes these statuses.
# Kept here so the reporting layer stays consistent with the engine.

STATUS_RUNNING = "running"
STATUS_PENDING = "pending"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

SUCCESS_STATUSES = {"success", "completed"}
FAILED_STATUSES = {"failed", "planning_failed", "execution_failed"}

# Canonical persisted status: the engine emits "success", we persist
# "completed" (Milestone 2 convention) while still recognising the legacy
# value everywhere in the reporting layer.
_STATUS_NORMALISATION = {"success": STATUS_COMPLETED}

# Terminal outcomes get completed_at / duration_ms stamped.
TERMINAL_STATUSES = SUCCESS_STATUSES | FAILED_STATUSES


def normalize_status(status):
    """Map engine status strings onto the canonical persisted vocabulary."""
    if status is None:
        return STATUS_RUNNING
    return _STATUS_NORMALISATION.get(status, status)

ALLOWED_STATUSES = (
    SUCCESS_STATUSES
    | FAILED_STATUSES
    | {STATUS_RUNNING, STATUS_PENDING, "approval_required"}
)

# Columns that are cheap to load for list/summary views. This deliberately
# excludes the large plan / execution_result / verification_result text so we
# never drag huge JSON blobs through list endpoints.
_SUMMARY_LOAD_COLUMNS = (
    AgentRun.id,
    AgentRun.session_id,
    AgentRun.user_query,
    AgentRun.status,
    AgentRun.created_at,
    AgentRun.started_at,
    AgentRun.completed_at,
    AgentRun.duration_ms,
    AgentRun.steps_total,
    AgentRun.retry_count,
    AgentRun.confidence,
    AgentRun.approved,
)


# ==========================================
# CREATE
# ==========================================

def create_agent_run(
    db,
    session_id,
    user_query,
    status="running",
    plan=None,
    execution_result=None,
    verification_result=None,
    user_id=None
):
    run = AgentRun(
        user_id=user_id,
        session_id=session_id,
        user_query=user_query,
        status=status,
        plan=plan,
        execution_result=execution_result,
        verification_result=verification_result
    )

    db.add(run)
    db.commit()
    db.refresh(run)

    return run


# ==========================================
# UPDATE STATUS
# ==========================================

def update_run_status(
    db,
    run_id,
    status
):
    run = get_run_by_id(db, run_id)

    if not run:
        return None

    run.status = status

    db.commit()
    db.refresh(run)

    return run


# ==========================================
# UPDATE PLAN
# ==========================================

def update_run_plan(
    db,
    run_id,
    plan
):
    run = get_run_by_id(db, run_id)

    if not run:
        return None

    run.plan = plan

    db.commit()
    db.refresh(run)

    return run


# ==========================================
# UPDATE EXECUTION RESULT
# ==========================================

def update_execution_result(
    db,
    run_id,
    execution_result
):
    run = get_run_by_id(db, run_id)

    if not run:
        return None

    run.execution_result = execution_result

    db.commit()
    db.refresh(run)

    return run


# ==========================================
# UPDATE VERIFICATION
# ==========================================

def update_verification_result(
    db,
    run_id,
    verification_result
):
    run = get_run_by_id(db, run_id)

    if not run:
        return None

    run.verification_result = verification_result

    db.commit()
    db.refresh(run)

    return run


# ==========================================
# COMPLETE RUN
# ==========================================

def complete_run(
    db,
    run_id,
    execution_result,
    verification_result,
    status="completed"
):
    run = get_run_by_id(db, run_id)

    if not run:
        return None

    run.execution_result = execution_result
    run.verification_result = verification_result
    run.status = status

    db.commit()
    db.refresh(run)

    return run


# ==========================================
# DELETE
# ==========================================

def delete_run(
    db,
    run_id
):
    run = get_run_by_id(db, run_id)

    if not run:
        return False

    db.delete(run)
    db.commit()

    return True


# ==========================================
# GET ALL
# ==========================================

def get_all_runs(db):
    return (
        db.query(AgentRun)
        .order_by(AgentRun.id.desc())
        .all()
    )


# ==========================================
# GET ONE
# ==========================================

def get_run_by_id(
    db,
    run_id,
    user_id=None
):
    """
    Fetch a run by id.

    When ``user_id`` is provided the query is scoped to that owner, so a run
    belonging to another user is indistinguishable from a non-existent one
    (the caller returns 404 — no IDOR leak). Pass ``user_id=None`` for admin /
    unscoped access.
    """
    query = db.query(AgentRun).filter(AgentRun.id == run_id)
    if user_id is not None:
        query = query.filter(AgentRun.user_id == user_id)
    return query.first()


# ==========================================
# GET SESSION
# ==========================================

def get_runs_by_session(
    db,
    session_id
):
    return (
        db.query(AgentRun)
        .filter(AgentRun.session_id == session_id)
        .order_by(AgentRun.id.desc())
        .all()
    )


# ==========================================
# GET STATUS
# ==========================================

def get_runs_by_status(
    db,
    status
):
    return (
        db.query(AgentRun)
        .filter(AgentRun.status == status)
        .order_by(AgentRun.id.desc())
        .all()
    )


# ==========================================
# FILTERED / PAGINATED LISTING
# ==========================================

def _apply_run_filters(
    query,
    session_id=None,
    status=None,
    start_date=None,
    end_date=None,
    search=None,
    user_id=None,
):
    """Attach optional filters to an AgentRun query (shared by list/count)."""

    # Ownership scope first (Milestone 6). When user_id is provided, results
    # are restricted to that owner regardless of any other filter — session_id
    # is NEVER trusted as an authorization boundary.
    if user_id is not None:
        query = query.filter(AgentRun.user_id == user_id)

    if session_id:
        query = query.filter(AgentRun.session_id == session_id)

    if status:
        query = query.filter(AgentRun.status == status)

    if start_date is not None:
        query = query.filter(AgentRun.created_at >= start_date)

    if end_date is not None:
        query = query.filter(AgentRun.created_at <= end_date)

    if search:
        query = query.filter(
            AgentRun.user_query.ilike(f"%{search}%")
        )

    return query


def list_runs(
    db,
    page=1,
    page_size=20,
    session_id=None,
    status=None,
    start_date=None,
    end_date=None,
    search=None,
    user_id=None,
):
    """
    Return ``(runs, total_count)`` for a filtered + paginated query.

    Only the lightweight summary columns are loaded so large plan /
    execution JSON is never pulled for list views. Pagination is enforced
    with LIMIT/OFFSET at the database level. ``user_id`` scopes results to a
    single owner (Milestone 6); pass ``None`` for admin/unscoped listing.
    """

    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 1

    base = _apply_run_filters(
        db.query(AgentRun),
        session_id=session_id,
        status=status,
        start_date=start_date,
        end_date=end_date,
        search=search,
        user_id=user_id,
    )

    total = base.with_entities(func.count(AgentRun.id)).scalar() or 0

    runs = (
        base.options(load_only(*_SUMMARY_LOAD_COLUMNS))
        .order_by(AgentRun.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return runs, total


# ==========================================
# DASHBOARD STATS
# ==========================================

def get_run_statistics(db, user_id=None):
    """
    Compute run statistics entirely in SQL (one GROUP BY + one AVG).

    Returns a dict aligned with the ``AgentRunStatistics`` schema. When
    ``user_id`` is provided the stats cover only that owner's runs (Milestone 6);
    pass ``None`` for admin/system-wide statistics.
    """

    status_query = db.query(
        AgentRun.status,
        func.count(AgentRun.id),
    )
    if user_id is not None:
        status_query = status_query.filter(AgentRun.user_id == user_id)

    rows = status_query.group_by(AgentRun.status).all()

    counts = {status: count for status, count in rows}
    total = sum(counts.values())

    successful = sum(
        c for s, c in counts.items() if s in SUCCESS_STATUSES
    )
    failed = sum(
        c for s, c in counts.items() if s in FAILED_STATUSES
    )
    running = counts.get(STATUS_RUNNING, 0)
    pending = counts.get(STATUS_PENDING, 0)
    other = total - successful - failed - running - pending

    avg_query = (
        db.query(func.avg(AgentRun.duration_ms))
        .filter(AgentRun.duration_ms.isnot(None))
        .filter(AgentRun.duration_ms > 0)
    )
    if user_id is not None:
        avg_query = avg_query.filter(AgentRun.user_id == user_id)
    avg_duration = avg_query.scalar()

    return {
        "total_runs": total,
        "successful_runs": successful,
        "failed_runs": failed,
        "running_runs": running,
        "pending_runs": pending,
        "other_runs": other,
        "success_rate": round((successful / total) * 100, 2) if total else 0.0,
        "failure_rate": round((failed / total) * 100, 2) if total else 0.0,
        "average_duration_ms": round(float(avg_duration), 2)
        if avg_duration is not None
        else None,
    }


# ==========================================
# EXECUTION SUMMARY / TELEMETRY (Milestone 2)
# ==========================================

def _aggregate_step_metrics(db, agent_run_id):
    """
    Derive step counters and the set of tools used from step_executions.

    Uses SQL aggregation (GROUP BY + DISTINCT) so no per-step payloads are
    loaded. Returns a dict with steps_total / steps_success / steps_failed /
    tools_used.
    """

    status_rows = (
        db.query(StepExecution.status, func.count(StepExecution.id))
        .filter(StepExecution.agent_run_id == agent_run_id)
        .group_by(StepExecution.status)
        .all()
    )

    counts = {(status or "unknown"): count for status, count in status_rows}
    steps_total = sum(counts.values())
    steps_success = counts.get("success", 0)
    steps_failed = counts.get("failed", 0)

    tool_rows = (
        db.query(distinct(StepExecution.tool_name))
        .filter(StepExecution.agent_run_id == agent_run_id)
        .all()
    )
    tools_used = sorted({t[0] for t in tool_rows if t[0]})

    return {
        "steps_total": steps_total,
        "steps_success": steps_success,
        "steps_failed": steps_failed,
        "tools_used": tools_used,
    }


def _derive_retry_count(execution_result):
    """
    Sum per-step retry counts from an in-memory execution_result.

    The executor returns ``{"results": {step_id: {"retry_count": n, ...}}}``.
    We never invent retries – if the data is absent we report 0.
    """

    if not isinstance(execution_result, dict):
        return 0

    results = execution_result.get("results")
    if not isinstance(results, dict):
        return 0

    total = 0
    for step in results.values():
        if isinstance(step, dict):
            value = step.get("retry_count")
            if isinstance(value, bool):
                continue
            if isinstance(value, int):
                total += value
    return total


def _extract_confidence(verification_result):
    if not isinstance(verification_result, dict):
        return None
    value = verification_result.get("confidence")
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _extract_approved(verification_result):
    if not isinstance(verification_result, dict):
        return None
    value = verification_result.get("approved")
    if isinstance(value, bool):
        return value
    return None


def _extract_final_response(final_response, execution_result):
    """
    Produce a safe, user-facing final response string.

    Prefers an explicit final_response; otherwise derives a compact summary
    from the execution result. Truncated so we never store huge payloads, and
    never intended to carry credentials/stack traces (the executor already
    strips the db handle from audited payloads).
    """

    if isinstance(final_response, str) and final_response.strip():
        text = final_response
    elif isinstance(execution_result, dict):
        goal = execution_result.get("goal")
        if isinstance(goal, str) and goal.strip():
            text = goal
        else:
            text = json.dumps(execution_result, default=str)
    elif execution_result is not None:
        text = str(execution_result)
    else:
        return None

    text = text.strip()
    max_len = 8000
    if len(text) > max_len:
        text = text[:max_len] + "…"
    return text


def _json_or_none(value):
    if value is None:
        return None
    try:
        return json.dumps(value, default=str)
    except (TypeError, ValueError):
        return json.dumps(str(value))


def finalize_agent_run_summary(
    db,
    agent_run_id,
    status,
    execution_result=None,
    verification_result=None,
    plan=None,
    llm_meta=None,
    final_response=None,
):
    """
    Enrich an existing agent_runs row with execution telemetry in ONE update.

    Derives step counters / tools_used / RAG+memory usage from step_executions
    (SQL aggregation), retry_count from the in-memory execution result, timing
    from started_at→now, and verification confidence/approval from the
    verifier output.

    This function is defensive: it NEVER raises. Any failure is logged and
    ``None`` is returned so optional telemetry can never break an agent run.
    Callers should still treat a ``None`` return as "summary not persisted".
    """

    try:
        run = get_run_by_id(db, agent_run_id)
        if run is None:
            logger.error(
                "finalize_agent_run_summary: run %s not found", agent_run_id
            )
            return None

        canonical_status = normalize_status(status)

        metrics = _aggregate_step_metrics(db, agent_run_id)
        tools_used = metrics["tools_used"]

        # Timing (only stamp completion for terminal outcomes).
        if canonical_status in TERMINAL_STATUSES:
            completed_at = datetime.now(timezone.utc)
            started = run.started_at
            if started is not None:
                if started.tzinfo is None:
                    started = started.replace(tzinfo=timezone.utc)
                duration_ms = int(
                    (completed_at - started).total_seconds() * 1000
                )
                run.duration_ms = max(duration_ms, 0)
            run.completed_at = completed_at

        # Step + capability telemetry.
        run.steps_total = metrics["steps_total"]
        run.steps_success = metrics["steps_success"]
        run.steps_failed = metrics["steps_failed"]
        run.tools_used = tools_used
        run.rag_used = any(t in RAG_TOOLS for t in tools_used)
        run.memory_used = any(t in MEMORY_TOOLS for t in tools_used)
        run.retry_count = _derive_retry_count(execution_result)

        # LLM model / execution mode (best-effort, from router telemetry).
        if llm_meta:
            model = llm_meta.get("model")
            mode = llm_meta.get("mode")
            if model:
                run.llm_model = model
            if mode:
                run.execution_mode = "offline" if mode == "offline" else "normal"

        # Verification outcome.
        run.confidence = _extract_confidence(verification_result)
        run.approved = _extract_approved(verification_result)
        if verification_result is not None:
            run.verification_result = _json_or_none(verification_result)

        # Payloads / final response.
        if execution_result is not None:
            run.execution_result = _json_or_none(execution_result)
        if plan is not None:
            run.plan = _json_or_none(plan)
        run.final_response = _extract_final_response(
            final_response, execution_result
        )

        run.status = canonical_status

        db.commit()
        db.refresh(run)
        return run

    except Exception:
        # Telemetry must never break the agent run – log loudly, roll back.
        logger.exception(
            "finalize_agent_run_summary failed for run %s", agent_run_id
        )
        try:
            db.rollback()
        except Exception:
            logger.exception("rollback failed after summary error")
        return None