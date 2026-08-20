"""
Agent Run management & reporting API.

ADDITIVE, read-only endpoints for inspecting AgentRun records produced by the
core execution flow. These endpoints do NOT create or mutate runs and do not
touch the agent execution engine.

Route order note: literal paths (``/statistics``, ``/search``) are declared
before the ``/{run_id}`` path parameter so they are never shadowed.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy.exc import SQLAlchemyError

from src.core.auth import get_current_active_user
from src.db.models.user import User
from src.db.session import get_db
from typing import List

from src.schemas.agent_run import (
    AgentRunDetail,
    AgentRunStatistics,
    AgentRunStep,
    PaginatedAgentRuns,
)
from src.services.agent_run_service import (
    ALLOWED_STATUSES,
    get_run_by_id,
    get_run_statistics,
    get_steps_for_run,
    list_runs,
)


def _owner_scope(user: User):
    """
    Resolve the ownership filter for the authenticated user.

    Normal users are scoped to their own runs; admins get ``None`` (unscoped,
    i.e. all runs). Authorization is derived from the DB-backed user record,
    never from client input.
    """
    return None if user.is_admin else user.id

router = APIRouter(
    prefix="/runs",
    tags=["Agent Runs"],
)


# ------------------------------------------------------------------
# Shared helpers
# ------------------------------------------------------------------

def _paginated(db, user_id=None, **kwargs) -> PaginatedAgentRuns:
    """Run a filtered/paginated query and wrap it, translating DB errors.

    ``user_id`` scopes the listing to a single owner (None = admin/all).
    """
    page = kwargs.get("page", 1)
    page_size = kwargs.get("page_size", 20)
    try:
        runs, total = list_runs(db, user_id=user_id, **kwargs)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while retrieving runs.",
        )
    return PaginatedAgentRuns.build(runs, total, page, page_size)


# ------------------------------------------------------------------
# LIST (paginated + filtered)
# ------------------------------------------------------------------

@router.get(
    "",
    response_model=PaginatedAgentRuns,
    summary="List agent runs",
    description=(
        "Return a paginated, filterable list of agent-run summaries. "
        "Supports filtering by session, status, creation date range and a "
        "free-text search over the user query. Heavy plan/execution JSON is "
        "intentionally excluded from summaries."
    ),
)
def all_runs(
    db=Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    page: int = Query(1, ge=1, description="1-based page number"),
    page_size: int = Query(
        20, ge=1, le=100, description="Items per page (max 100)"
    ),
    session_id: Optional[str] = Query(None, description="Filter by session id"),
    run_status: Optional[str] = Query(
        None, alias="status", description="Filter by run status"
    ),
    start_date: Optional[datetime] = Query(
        None, description="Only runs created on/after this timestamp"
    ),
    end_date: Optional[datetime] = Query(
        None, description="Only runs created on/before this timestamp"
    ),
    q: Optional[str] = Query(
        None, description="Case-insensitive search on the user query"
    ),
):
    if run_status is not None and run_status not in ALLOWED_STATUSES:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Allowed: {sorted(ALLOWED_STATUSES)}",
        )

    return _paginated(
        db,
        user_id=_owner_scope(current_user),
        page=page,
        page_size=page_size,
        session_id=session_id,
        status=run_status,
        start_date=start_date,
        end_date=end_date,
        search=q,
    )


# Backwards-compatible alias for the trailing-slash form.
@router.get("/", include_in_schema=False)
def all_runs_slash(
    db=Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session_id: Optional[str] = Query(None),
    run_status: Optional[str] = Query(None, alias="status"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    q: Optional[str] = Query(None),
):
    return all_runs(
        db=db,
        current_user=current_user,
        page=page,
        page_size=page_size,
        session_id=session_id,
        run_status=run_status,
        start_date=start_date,
        end_date=end_date,
        q=q,
    )


# ------------------------------------------------------------------
# STATISTICS (must precede /{run_id})
# ------------------------------------------------------------------

@router.get(
    "/statistics",
    response_model=AgentRunStatistics,
    summary="Aggregate run statistics",
    description=(
        "Return dashboard counters (totals per outcome, success/failure "
        "rates and average execution duration) computed in SQL."
    ),
)
def statistics(
    db=Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        return get_run_statistics(db, user_id=_owner_scope(current_user))
    except SQLAlchemyError:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while computing statistics.",
        )


# ------------------------------------------------------------------
# SEARCH (must precede /{run_id})
# ------------------------------------------------------------------

@router.get(
    "/search",
    response_model=PaginatedAgentRuns,
    summary="Search agent runs",
    description=(
        "Case-insensitive search over the user query, combined with optional "
        "session/status/date filters and pagination."
    ),
)
def search_runs(
    q: str = Query(..., min_length=1, max_length=200, description="Search term"),
    db=Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session_id: Optional[str] = Query(None),
    run_status: Optional[str] = Query(None, alias="status"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
):
    if run_status is not None and run_status not in ALLOWED_STATUSES:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Allowed: {sorted(ALLOWED_STATUSES)}",
        )

    return _paginated(
        db,
        user_id=_owner_scope(current_user),
        page=page,
        page_size=page_size,
        session_id=session_id,
        status=run_status,
        start_date=start_date,
        end_date=end_date,
        search=q,
    )


# ------------------------------------------------------------------
# BY SESSION (paginated)
# ------------------------------------------------------------------

@router.get(
    "/session/{session_id}",
    response_model=PaginatedAgentRuns,
    summary="List runs for a session",
    description="Paginated summaries for a single session id.",
)
def session_runs(
    session_id: str,
    db=Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    # session_id is a filter, NOT an authorization boundary — results are always
    # scoped to the authenticated owner so one user cannot read another's
    # session by guessing its id.
    return _paginated(
        db,
        user_id=_owner_scope(current_user),
        page=page,
        page_size=page_size,
        session_id=session_id,
    )


# ------------------------------------------------------------------
# BY STATUS (paginated)
# ------------------------------------------------------------------

@router.get(
    "/status/{run_status}",
    response_model=PaginatedAgentRuns,
    summary="List runs by status",
    description="Paginated summaries filtered by a valid run status.",
)
def status_runs(
    run_status: str,
    db=Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    if run_status not in ALLOWED_STATUSES:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Allowed: {sorted(ALLOWED_STATUSES)}",
        )

    return _paginated(
        db,
        user_id=_owner_scope(current_user),
        page=page,
        page_size=page_size,
        status=run_status,
    )


# ------------------------------------------------------------------
# EXECUTION STEPS (per-run timeline)
# ------------------------------------------------------------------

@router.get(
    "/{run_id}/steps",
    response_model=List[AgentRunStep],
    summary="List execution steps for a run",
    description=(
        "Return the recorded execution steps for a single run, oldest first, "
        "for the step-execution timeline. Tool input/output payloads are "
        "truncated to short summaries. Owner-scoped: a run owned by another "
        "user returns 404."
    ),
    responses={404: {"description": "Run not found"}},
)
def run_steps(
    run_id: int,
    db=Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        # Enforce ownership on the parent run first — an unauthorized run is
        # indistinguishable from a missing one (no IDOR, no step leak).
        run = get_run_by_id(db, run_id, user_id=_owner_scope(current_user))
        if not run:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Run {run_id} not found",
            )
        steps = get_steps_for_run(db, run_id)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while retrieving run steps.",
        )

    return [AgentRunStep.from_step(s) for s in steps]


# ------------------------------------------------------------------
# DETAIL (declared last so literal routes win)
# ------------------------------------------------------------------

@router.get(
    "/{run_id}",
    response_model=AgentRunDetail,
    summary="Get a single run (full detail)",
    description=(
        "Return one run with its parsed plan, execution result and "
        "verification result. Malformed stored JSON is returned as raw text "
        "rather than causing an error."
    ),
    responses={404: {"description": "Run not found"}},
)
def run_details(
    run_id: int,
    db=Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        # Owner-scoped fetch: a run owned by another user is treated exactly
        # like a missing one (404) so existence is never leaked (no IDOR).
        run = get_run_by_id(db, run_id, user_id=_owner_scope(current_user))
    except SQLAlchemyError:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while retrieving the run.",
        )

    if not run:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found",
        )

    return AgentRunDetail.from_run(run)
