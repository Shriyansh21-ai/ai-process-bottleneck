from sqlalchemy import func

from src.db.models.agent_run import (
    AgentRun
)

from src.services.agent_run_service import (
    SUCCESS_STATUSES,
    FAILED_STATUSES,
)

from src.db.models.step_execution import (
    StepExecution
)

from src.db.models.approval import (
    ApprovalRequest
)


# ==========================================
# TOTAL RUNS
# ==========================================

def get_total_runs(db):

    return db.query(
        AgentRun
    ).count()


# ==========================================
# SUCCESS RUNS
# ==========================================

def get_success_runs(db):

    return (

        db.query(
            AgentRun
        )

        .filter(
            AgentRun.status.in_(SUCCESS_STATUSES)
        )

        .count()
    )


# ==========================================
# FAILURE RUNS
# ==========================================

def get_failure_runs(db):

    return (

        db.query(
            AgentRun
        )

        .filter(
            AgentRun.status.in_(FAILED_STATUSES)
        )

        .count()
    )


# ==========================================
# SUCCESS RATE
# ==========================================

def get_success_rate(db):

    total = get_total_runs(db)

    if total == 0:

        return 0

    success = get_success_runs(db)

    return round(
        (success / total) * 100,
        2
    )


# ==========================================
# APPROVALS
# ==========================================

def get_total_approvals(db):

    return db.query(
        ApprovalRequest
    ).count()


def get_pending_approvals_count(db):

    return (

        db.query(
            ApprovalRequest
        )

        .filter(
            ApprovalRequest.status == "pending"
        )

        .count()
    )


# ==========================================
# TOOL EXECUTIONS
# ==========================================

def get_total_tool_executions(db):

    return db.query(
        StepExecution
    ).count()


# ==========================================
# MOST USED TOOL
# ==========================================

def get_most_used_tool(db):

    result = (

        db.query(

            StepExecution.tool_name,

            func.count(
                StepExecution.id
            ).label(
                "count"
            )
        )

        .group_by(
            StepExecution.tool_name
        )

        .order_by(
            func.count(
                StepExecution.id
            ).desc()
        )

        .first()
    )

    if not result:

        return None

    return {

        "tool": result[0],

        "count": result[1]
    }


# ==========================================
# AVG EXECUTION TIME
# ==========================================

def get_average_execution_time(db):

    avg = (

        db.query(

            func.avg(
                StepExecution.execution_time_ms
            )

        ).scalar()
    )

    return round(
        avg or 0,
        2
    )


# ==========================================
# AVG RETRIES
# ==========================================

def get_average_retries(db):

    avg = (

        db.query(

            func.avg(
                StepExecution.retry_count
            )

        ).scalar()
    )

    return round(
        avg or 0,
        2
    )


# ==========================================
# DASHBOARD SUMMARY
# ==========================================

def get_dashboard_metrics(db):

    return {

        "total_runs":
        get_total_runs(db),

        "success_runs":
        get_success_runs(db),

        "failure_runs":
        get_failure_runs(db),

        "success_rate":
        get_success_rate(db),

        "total_approvals":
        get_total_approvals(db),

        "pending_approvals":
        get_pending_approvals_count(db),

        "total_tool_executions":
        get_total_tool_executions(db),

        "average_execution_time_ms":
        get_average_execution_time(db),

        "average_retries":
        get_average_retries(db),

        "most_used_tool":
        get_most_used_tool(db)
    }