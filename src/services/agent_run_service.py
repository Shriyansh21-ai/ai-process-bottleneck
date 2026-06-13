from src.db.models.agent_run import AgentRun


def get_all_runs(db):

    return (

        db.query(
            AgentRun
        )

        .order_by(
            AgentRun.id.desc()
        )

        .all()
    )


def get_run_by_id(
    db,
    run_id
):

    return (

        db.query(
            AgentRun
        )

        .filter(
            AgentRun.id == run_id
        )

        .first()
    )


def get_runs_by_session(
    db,
    session_id
):

    return (

        db.query(
            AgentRun
        )

        .filter(
            AgentRun.session_id == session_id
        )

        .order_by(
            AgentRun.id.desc()
        )

        .all()
    )


def get_runs_by_status(
    db,
    status
):

    return (

        db.query(
            AgentRun
        )

        .filter(
            AgentRun.status == status
        )

        .order_by(
            AgentRun.id.desc()
        )

        .all()
    )