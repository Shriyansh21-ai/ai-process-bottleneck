from src.db.models.agent_task import (
    AgentTask
)


def create_task(
    db,
    task: str
):

    obj = AgentTask(
        task=task,
        status="pending"
    )

    db.add(obj)

    db.commit()

    db.refresh(obj)

    return obj


def complete_task(
    db,
    task_id: int,
    result: str
):

    task = db.query(
        AgentTask
    ).filter(
        AgentTask.id == task_id
    ).first()

    if task:

        task.status = "completed"

        task.result = result

        db.commit()


def get_pending_tasks(db):

    return db.query(
        AgentTask
    ).filter(
        AgentTask.status == "pending"
    ).all()