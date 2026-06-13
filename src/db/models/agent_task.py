from sqlalchemy import (
    Column,
    Integer,
    Text,
    ForeignKey,
    DateTime
)

from sqlalchemy.sql import func

from src.db.base import Base


class AgentTask(Base):

    __tablename__ = "agent_tasks"

    id = Column(
        Integer,
        primary_key=True
    )

    agent_run_id = Column(
        Integer,
        ForeignKey(
            "agent_runs.id"
        )
    )

    agent_name = Column(
        Text
    )

    task = Column(
        Text
    )

    input_payload = Column(
        Text
    )

    output_payload = Column(
        Text
    )

    status = Column(
        Text
    )

    error = Column(
        Text
    )

    execution_time_ms = Column(
        Integer
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )