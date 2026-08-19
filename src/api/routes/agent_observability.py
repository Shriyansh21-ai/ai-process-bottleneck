"""
Agent Observability & Execution Analytics API.

Read-only, aggregated telemetry over existing agent_runs / step_executions
audit data. No raw execution payloads are exposed and raw DB errors are never
surfaced to clients.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status as http_status,
)
from sqlalchemy.exc import SQLAlchemyError

from src.core.auth import get_current_admin_user
from src.db.session import get_db
from src.schemas.agent_observability import (
    AgentHealthSummary,
    AgentObservabilityResponse,
    ExecutionTrendPoint,
    FailureSummary,
    ToolPerformanceSummary,
)
from src.services.agent_run_service import ALLOWED_STATUSES
from src.services.agent_observability_service import (
    get_agent_health,
    get_execution_trends,
    get_failure_summary,
    get_observability_overview,
    get_tool_performance,
)

# System-wide analytics aggregate across ALL users' runs, so these are
# administrative/operational diagnostics — gated to admins (Milestone 6).
router = APIRouter(
    prefix="/observability",
    tags=["Agent Observability"],
    dependencies=[Depends(get_current_admin_user)],
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Administrative privilege required"},
    },
)


# ------------------------------------------------------------------
# shared filter dependency
# ------------------------------------------------------------------

class ObservabilityFilters:
    def __init__(
        self,
        start_date: Optional[datetime] = Query(
            None, description="Only include runs created on/after this time"
        ),
        end_date: Optional[datetime] = Query(
            None, description="Only include runs created on/before this time"
        ),
        session_id: Optional[str] = Query(
            None, description="Filter by session id"
        ),
        run_status: Optional[str] = Query(
            None, alias="status", description="Filter by run status"
        ),
    ):
        if (
            start_date is not None
            and end_date is not None
            and start_date > end_date
        ):
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="start_date must be before or equal to end_date",
            )
        if run_status is not None and run_status not in ALLOWED_STATUSES:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Allowed: {sorted(ALLOWED_STATUSES)}",
            )

        self.start_date = start_date
        self.end_date = end_date
        self.session_id = session_id
        self.status = run_status


def _guard(fn, *args, **kwargs):
    """Run a service call, translating DB errors into a clean 500."""
    try:
        return fn(*args, **kwargs)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while computing observability data.",
        )


# ------------------------------------------------------------------
# endpoints
# ------------------------------------------------------------------

@router.get(
    "/health",
    response_model=AgentHealthSummary,
    summary="Overall agent execution health",
    description=(
        "Aggregated run/step health for the selected window, including "
        "success/failure/approval rates, average duration & confidence, step "
        "and retry totals, and a deterministic 0-100 health score."
    ),
)
def health(
    filters: ObservabilityFilters = Depends(),
    db=Depends(get_db),
):
    return _guard(
        get_agent_health,
        db,
        filters.start_date,
        filters.end_date,
        filters.session_id,
        filters.status,
    )


@router.get(
    "/tools",
    response_model=List[ToolPerformanceSummary],
    summary="Per-tool performance analytics",
    description=(
        "Execution count, success/failure counts & rate, average duration and "
        "total retries per tool. Ordered by execution count (most used first)."
    ),
)
def tools(
    filters: ObservabilityFilters = Depends(),
    tool_name: Optional[str] = Query(
        None, description="Restrict to a single tool"
    ),
    db=Depends(get_db),
):
    return _guard(
        get_tool_performance,
        db,
        filters.start_date,
        filters.end_date,
        filters.session_id,
        filters.status,
        tool_name,
    )


@router.get(
    "/failures",
    response_model=List[FailureSummary],
    summary="Aggregated failure reasons",
    description=(
        "Failed step executions grouped by (truncated) failure reason with "
        "counts and percentage of all failures."
    ),
)
def failures(
    filters: ObservabilityFilters = Depends(),
    db=Depends(get_db),
):
    return _guard(
        get_failure_summary,
        db,
        filters.start_date,
        filters.end_date,
        filters.session_id,
        filters.status,
    )


@router.get(
    "/trends",
    response_model=List[ExecutionTrendPoint],
    summary="Execution trends over time",
    description=(
        "Daily buckets of total/successful/failed runs with average duration "
        "and confidence, ordered chronologically."
    ),
)
def trends(
    filters: ObservabilityFilters = Depends(),
    db=Depends(get_db),
):
    return _guard(
        get_execution_trends,
        db,
        filters.start_date,
        filters.end_date,
        filters.session_id,
        filters.status,
    )


@router.get(
    "/overview",
    response_model=AgentObservabilityResponse,
    summary="Combined observability dashboard",
    description=(
        "Single payload combining health, tool performance, failure summary "
        "and execution trends for the selected window."
    ),
)
def overview(
    filters: ObservabilityFilters = Depends(),
    db=Depends(get_db),
):
    return _guard(
        get_observability_overview,
        db,
        filters.start_date,
        filters.end_date,
        filters.session_id,
        filters.status,
    )
