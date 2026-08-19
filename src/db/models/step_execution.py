from sqlalchemy import (
    Column,
    Integer,
    Text,
    ForeignKey,
    DateTime
)

from sqlalchemy.sql import func

from src.db.base import Base
from sqlalchemy import Integer


class StepExecution(Base):

    __tablename__ = "step_executions"

    id = Column(
        Integer,
        primary_key=True
    )

    agent_run_id = Column(
        Integer,
        ForeignKey(
            "agent_runs.id"
        ),
        index=True
    )

    step_id = Column(
        Integer
    )

    tool_name = Column(
        Text,
        index=True
    )

    input_payload = Column(
        Text
    )

    output_payload = Column(
        Text
    )

    status = Column(
        Text,
        index=True
    )

    error = Column(
        Text
    )

    execution_time_ms = Column(
        Integer
    )

    retry_count = Column(
    Integer,
    default=0
)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )