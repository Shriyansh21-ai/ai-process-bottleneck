from src.db.models.approval import (
    ApprovalRequest
)
import json


def create_approval_request(
    db,
    task,
    risk_level,
    reason,
    user_query=None,
    tool_name=None,
    session_id=None
):

    obj = ApprovalRequest(

        user_query=user_query or "",

        session_id=session_id,

        tool_name=tool_name or "",

        task=str(task),

        risk_level=risk_level,

        plan_json=json.dumps(task),

        reason=reason
    )

    db.add(obj)

    db.commit()

    db.refresh(obj)

    return obj