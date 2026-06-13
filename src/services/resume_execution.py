import json

from src.agent.executor import ToolExecutor
from src.agent.verifier import VerifierAgent

from src.genai.memory import add_memory

from src.db.models.approval import ApprovalRequest


async def resume_execution(
    db,
    approval_id
):

    approval = (

        db.query(
            ApprovalRequest
        )

        .filter(
            ApprovalRequest.id == approval_id
        )

        .first()
    )

    if not approval:

        raise ValueError(
            "Approval not found"
        )

    if approval.status != "approved":

        raise ValueError(
            "Approval not approved"
        )

    if approval.executed:

        raise ValueError(
            "Execution already completed"
        )

    plan = json.loads(
        approval.plan_json
    )

    executor = ToolExecutor(
        db=db
    )

    execution_result = await executor.execute_plan(
        plan
    )

    verifier = VerifierAgent()

    verification = verifier.verify(

        approval.user_query,

        execution_result
    )

    memory_text = f"""
Goal:
{approval.user_query}

Execution:
{execution_result}

Verification:
{verification}
"""

    add_memory(

        content=memory_text,

        session_id=approval.session_id
    )

    approval.executed = True

    db.commit()

    return {

        "execution": execution_result,

        "verification": verification
    }