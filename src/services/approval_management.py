from src.db.models.approval import (
    ApprovalRequest
)


def get_pending_approvals(db):

    return (

        db.query(
            ApprovalRequest
        )

        .filter(
            ApprovalRequest.status == "pending"
        )

        .all()
    )


def approve_request(
    db,
    approval_id
):

    obj = (

        db.query(
            ApprovalRequest
        )

        .filter(
            ApprovalRequest.id == approval_id
        )

        .first()
    )

    if not obj:

        return None

    obj.status = "approved"

    db.commit()

    db.refresh(obj)

    return obj


def reject_request(
    db,
    approval_id
):

    obj = (

        db.query(
            ApprovalRequest
        )

        .filter(
            ApprovalRequest.id == approval_id
        )

        .first()
    )

    if not obj:

        return None

    obj.status = "rejected"

    db.commit()

    db.refresh(obj)

    return obj