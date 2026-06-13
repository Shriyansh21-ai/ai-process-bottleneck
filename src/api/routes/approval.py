from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException

from src.db.session import get_db

from src.services.approval_management import (
    get_pending_approvals,
    approve_request,
    reject_request
)

from src.services.resume_execution import (
    resume_execution
)

router = APIRouter(
    prefix="/approvals",
    tags=["Approvals"]
)


@router.get("/pending")
def pending_approvals(
    db=Depends(get_db)
):

    approvals = get_pending_approvals(
        db
    )

    return approvals


@router.post("/{approval_id}/approve")
def approve(
    approval_id: int,
    db=Depends(get_db)
):

    obj = approve_request(
        db,
        approval_id
    )

    if not obj:

        raise HTTPException(
            status_code=404,
            detail="Approval request not found"
        )

    return {
        "status": "approved",
        "approval_id": obj.id
    }


@router.post("/{approval_id}/reject")
def reject(
    approval_id: int,
    db=Depends(get_db)
):

    obj = reject_request(
        db,
        approval_id
    )

    if not obj:

        raise HTTPException(
            status_code=404,
            detail="Approval request not found"
        )

    return {
        "status": "rejected",
        "approval_id": obj.id
    }

@router.post("/{approval_id}/resume")
async def resume(

    approval_id: int,

    db=Depends(get_db)
):

    result = await resume_execution(

        db,

        approval_id
    )

    return result