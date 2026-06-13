from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException

from src.db.session import get_db

from src.services.agent_run_service import (
    get_all_runs,
    get_run_by_id,
    get_runs_by_session,
    get_runs_by_status
)

router = APIRouter(
    prefix="/runs",
    tags=["Agent Runs"]
)


@router.get("/")
def all_runs(
    db=Depends(get_db)
):

    return get_all_runs(db)


@router.get("/{run_id}")
def run_details(
    run_id: int,
    db=Depends(get_db)
):

    run = get_run_by_id(
        db,
        run_id
    )

    if not run:

        raise HTTPException(
            status_code=404,
            detail="Run not found"
        )

    return run


@router.get("/session/{session_id}")
def session_runs(
    session_id: str,
    db=Depends(get_db)
):

    return get_runs_by_session(
        db,
        session_id
    )


@router.get("/status/{status}")
def status_runs(
    status: str,
    db=Depends(get_db)
):

    return get_runs_by_status(
        db,
        status
    )