from sqlalchemy import (
    Column,
    Integer,
    Text,
    DateTime
)

from sqlalchemy.sql import func

from src.db.base import Base


class AgentRun(Base):

    __tablename__ = "agent_runs"

    id = Column(
        Integer,
        primary_key=True
    )

    session_id = Column(
        Text,
        nullable=False
    )

    user_query = Column(
        Text,
        nullable=False
    )

    plan = Column(
        Text
    )

    execution_result = Column(
        Text
    )

    verification_result = Column(
        Text
    )

    status = Column(
        Text,
        nullable=False
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )