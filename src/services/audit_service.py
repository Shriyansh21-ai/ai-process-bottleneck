import json

from src.db.models.agent_run import AgentRun


def create_agent_run(
    db,
    session_id,
    user_query,
    plan,
    execution_result,
    verification_result,
    status,
    user_id=None
):

    run = AgentRun(

        user_id=user_id,

        session_id=session_id,

        user_query=user_query,

        plan=json.dumps(plan),

        execution_result=json.dumps(
            execution_result
        ),

        verification_result=json.dumps(
            verification_result
        ),

        status=status
    )

    db.add(run)

    db.commit()

    db.refresh(run)

    return run

def update_agent_run(

    db,

    run_id,

    execution_result,

    verification_result,

    status
):

    run = (

        db.query(
            AgentRun
        )

        .filter(
            AgentRun.id == run_id
        )

        .first()
    )

    if not run:

        return None

    run.execution_result = json.dumps(
        execution_result
    )

    run.verification_result = json.dumps(
        verification_result
    )

    run.status = status

    db.commit()

    db.refresh(run)

    return run