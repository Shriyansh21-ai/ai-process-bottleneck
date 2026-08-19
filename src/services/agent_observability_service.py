"""
Agent Observability & Execution Analytics service.

Consumes the EXISTING agent_runs and step_executions audit data. Every metric
is computed with SQL-side aggregation (COUNT / SUM / AVG / CASE / GROUP BY) so
we never load rows — or large JSON payloads — into Python just to count them.

All queries are cross-database (SQLite for tests, PostgreSQL in production).
"""

import logging

from sqlalchemy import case, func

from src.db.models.agent_run import AgentRun
from src.db.models.step_execution import StepExecution
from src.services.agent_run_service import (
    FAILED_STATUSES,
    STATUS_RUNNING,
    SUCCESS_STATUSES,
)

logger = logging.getLogger("agent_observability")

# Step-level status literals written by ToolExecutor / step_audit_service.
STEP_SUCCESS = "success"
STEP_FAILED = "failed"


# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------

def _rate(numerator, denominator):
    return round((numerator / denominator) * 100, 2) if denominator else 0.0


def _round(value, ndigits=2):
    return round(float(value), ndigits) if value is not None else None


def _apply_run_filters(query, start_date, end_date, session_id, status):
    if start_date is not None:
        query = query.filter(AgentRun.created_at >= start_date)
    if end_date is not None:
        query = query.filter(AgentRun.created_at <= end_date)
    if session_id:
        query = query.filter(AgentRun.session_id == session_id)
    if status:
        query = query.filter(AgentRun.status == status)
    return query


# ------------------------------------------------------------------
# health score (deterministic, no LLM)
# ------------------------------------------------------------------

def compute_health_score(metrics):
    """
    Deterministic 0-100 health score + status band.

    Weighted blend of run success, approval, verifier confidence, step
    reliability and retry pressure::

        score = 0.35 * success_rate
              + 0.15 * approval_rate
              + 0.20 * confidence_pct        (missing confidence -> neutral 70)
              + 0.15 * step_reliability      (100 - %failed steps)
              + 0.15 * retry_health          (100 - 20 * retries/run, floored 0)

    Empty windows return (0, "no_data"). Bands: <40 unhealthy, 40-69 degraded,
    70-84 healthy, 85-100 excellent.
    """

    total = metrics["total_runs"]
    if total == 0:
        return 0, "no_data"

    confidence = metrics["average_confidence"]
    confidence_pct = (confidence * 100) if confidence is not None else 70.0

    total_steps = metrics["total_steps"]
    failed_step_ratio = (
        metrics["failed_steps"] / total_steps if total_steps else 0.0
    )
    step_reliability = 100.0 - min(failed_step_ratio * 100.0, 100.0)

    retries_per_run = metrics["total_retries"] / total
    retry_health = 100.0 - min(retries_per_run * 20.0, 100.0)

    raw = (
        0.35 * metrics["success_rate"]
        + 0.15 * metrics["approval_rate"]
        + 0.20 * confidence_pct
        + 0.15 * step_reliability
        + 0.15 * retry_health
    )
    score = int(round(max(0.0, min(100.0, raw))))

    if score < 40:
        status = "unhealthy"
    elif score < 70:
        status = "degraded"
    elif score < 85:
        status = "healthy"
    else:
        status = "excellent"

    return score, status


# ------------------------------------------------------------------
# health
# ------------------------------------------------------------------

def get_agent_health(
    db, start_date=None, end_date=None, session_id=None, status=None
):
    """Overall execution health for the filtered window (single query)."""

    success_case = case((AgentRun.status.in_(SUCCESS_STATUSES), 1), else_=0)
    failed_case = case((AgentRun.status.in_(FAILED_STATUSES), 1), else_=0)
    running_case = case((AgentRun.status == STATUS_RUNNING, 1), else_=0)
    approved_true = case((AgentRun.approved.is_(True), 1), else_=0)
    approved_known = case((AgentRun.approved.isnot(None), 1), else_=0)
    duration_positive = case(
        (AgentRun.duration_ms > 0, AgentRun.duration_ms), else_=None
    )

    row = _apply_run_filters(
        db.query(
            func.count(AgentRun.id).label("total"),
            func.sum(success_case).label("succ"),
            func.sum(failed_case).label("failed"),
            func.sum(running_case).label("running"),
            func.avg(duration_positive).label("avg_dur"),
            func.avg(AgentRun.confidence).label("avg_conf"),
            func.sum(approved_true).label("appr_true"),
            func.sum(approved_known).label("appr_known"),
            func.sum(AgentRun.steps_total).label("steps_total"),
            func.sum(AgentRun.steps_success).label("steps_succ"),
            func.sum(AgentRun.steps_failed).label("steps_failed"),
            func.sum(AgentRun.retry_count).label("retries"),
        ),
        start_date,
        end_date,
        session_id,
        status,
    ).one()

    total = int(row.total or 0)
    succ = int(row.succ or 0)
    failed = int(row.failed or 0)

    metrics = {
        "total_runs": total,
        "successful_runs": succ,
        "failed_runs": failed,
        "running_runs": int(row.running or 0),
        "success_rate": _rate(succ, total),
        "failure_rate": _rate(failed, total),
        "approval_rate": _rate(int(row.appr_true or 0), int(row.appr_known or 0)),
        "average_duration_ms": _round(row.avg_dur),
        "average_confidence": _round(row.avg_conf, 4),
        "total_steps": int(row.steps_total or 0),
        "successful_steps": int(row.steps_succ or 0),
        "failed_steps": int(row.steps_failed or 0),
        "total_retries": int(row.retries or 0),
    }

    score, health_status = compute_health_score(metrics)
    metrics["health_score"] = score
    metrics["health_status"] = health_status
    return metrics


# ------------------------------------------------------------------
# tool performance
# ------------------------------------------------------------------

def get_tool_performance(
    db,
    start_date=None,
    end_date=None,
    session_id=None,
    status=None,
    tool_name=None,
):
    """Per-tool aggregated performance (GROUP BY tool_name, single query)."""

    success_case = case((StepExecution.status == STEP_SUCCESS, 1), else_=0)
    failed_case = case((StepExecution.status == STEP_FAILED, 1), else_=0)
    duration_positive = case(
        (StepExecution.execution_time_ms > 0, StepExecution.execution_time_ms),
        else_=None,
    )

    query = (
        db.query(
            StepExecution.tool_name.label("tool"),
            func.count(StepExecution.id).label("cnt"),
            func.sum(success_case).label("succ"),
            func.sum(failed_case).label("failed"),
            func.avg(duration_positive).label("avg_dur"),
            func.sum(StepExecution.retry_count).label("retries"),
        )
        .join(AgentRun, AgentRun.id == StepExecution.agent_run_id)
    )
    query = _apply_run_filters(query, start_date, end_date, session_id, status)
    if tool_name:
        query = query.filter(StepExecution.tool_name == tool_name)

    rows = (
        query.group_by(StepExecution.tool_name)
        .order_by(func.count(StepExecution.id).desc())
        .all()
    )

    results = []
    for r in rows:
        cnt = int(r.cnt or 0)
        succ = int(r.succ or 0)
        results.append(
            {
                "tool_name": r.tool or "unknown",
                "execution_count": cnt,
                "success_count": succ,
                "failure_count": int(r.failed or 0),
                "success_rate": _rate(succ, cnt),
                "average_duration_ms": _round(r.avg_dur),
                "total_retries": int(r.retries or 0),
            }
        )
    return results


# ------------------------------------------------------------------
# failures
# ------------------------------------------------------------------

def get_failure_summary(
    db, start_date=None, end_date=None, session_id=None, status=None
):
    """
    Aggregate failed step executions by reason.

    Reason = the recorded error message (truncated) or ``"<tool>: unknown
    error"`` when no message was captured. Only the short reason string is
    exposed — never the raw input/output payloads.
    """

    query = (
        db.query(
            StepExecution.error.label("reason"),
            StepExecution.tool_name.label("tool"),
            func.count(StepExecution.id).label("cnt"),
        )
        .join(AgentRun, AgentRun.id == StepExecution.agent_run_id)
        .filter(StepExecution.status == STEP_FAILED)
    )
    query = _apply_run_filters(query, start_date, end_date, session_id, status)

    rows = (
        query.group_by(StepExecution.error, StepExecution.tool_name)
        .order_by(func.count(StepExecution.id).desc())
        .all()
    )

    total = sum(int(r.cnt or 0) for r in rows)

    results = []
    for r in rows:
        reason = r.reason
        if not reason:
            reason = f"{r.tool or 'unknown'}: unknown error"
        reason = str(reason)
        if len(reason) > 160:
            reason = reason[:160] + "…"
        results.append(
            {
                "failure_type": reason,
                "count": int(r.cnt or 0),
                "percentage": _rate(int(r.cnt or 0), total),
            }
        )
    return results


# ------------------------------------------------------------------
# trends
# ------------------------------------------------------------------

def get_execution_trends(
    db, start_date=None, end_date=None, session_id=None, status=None
):
    """Daily execution trend series (GROUP BY date, single query)."""

    bucket = func.date(AgentRun.created_at)
    success_case = case((AgentRun.status.in_(SUCCESS_STATUSES), 1), else_=0)
    failed_case = case((AgentRun.status.in_(FAILED_STATUSES), 1), else_=0)
    duration_positive = case(
        (AgentRun.duration_ms > 0, AgentRun.duration_ms), else_=None
    )

    query = db.query(
        bucket.label("bucket"),
        func.count(AgentRun.id).label("total"),
        func.sum(success_case).label("succ"),
        func.sum(failed_case).label("failed"),
        func.avg(duration_positive).label("avg_dur"),
        func.avg(AgentRun.confidence).label("avg_conf"),
    )
    query = _apply_run_filters(query, start_date, end_date, session_id, status)

    rows = query.group_by(bucket).order_by(bucket).all()

    results = []
    for r in rows:
        results.append(
            {
                "bucket": str(r.bucket),
                "total_runs": int(r.total or 0),
                "successful_runs": int(r.succ or 0),
                "failed_runs": int(r.failed or 0),
                "average_duration_ms": _round(r.avg_dur),
                "average_confidence": _round(r.avg_conf, 4),
            }
        )
    return results


# ------------------------------------------------------------------
# combined overview
# ------------------------------------------------------------------

def get_observability_overview(
    db, start_date=None, end_date=None, session_id=None, status=None
):
    """Combined dashboard payload built from the individual aggregates."""

    return {
        "health": get_agent_health(
            db, start_date, end_date, session_id, status
        ),
        "tools": get_tool_performance(
            db, start_date, end_date, session_id, status
        ),
        "failures": get_failure_summary(
            db, start_date, end_date, session_id, status
        ),
        "trends": get_execution_trends(
            db, start_date, end_date, session_id, status
        ),
    }
