from sqlalchemy import (
    Column,
    Integer,
    Text,
    DateTime,
    Boolean,
    Float,
    JSON,
    ForeignKey
)

from sqlalchemy.sql import func

from src.db.base import Base


class AgentRun(Base):

    __tablename__ = "agent_runs"

    id = Column(
        Integer,
        primary_key=True
    )

    # Owning user (Milestone 6). Nullable so pre-existing runs created before
    # authentication are preserved as "unowned" (visible only to admins).
    # New runs are always associated with the authenticated user.
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    session_id = Column(
        Text,
        nullable=False,
        index=True
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
        nullable=False,
        index=True
    )

    # -----------------------------
    # Execution Summary
    # -----------------------------

    started_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    completed_at = Column(
        DateTime(timezone=True)
    )

    duration_ms = Column(
        Integer,
        default=0
    )

    steps_total = Column(
        Integer,
        default=0
    )

    steps_success = Column(
        Integer,
        default=0
    )

    steps_failed = Column(
        Integer,
        default=0
    )

    retry_count = Column(
        Integer,
        default=0
    )

    tools_used = Column(
        JSON
    )

    execution_mode = Column(
        Text,
        default="parallel"
    )

    memory_used = Column(
        Boolean,
        default=False
    )

    rag_used = Column(
        Boolean,
        default=False
    )

    confidence = Column(
        Float
    )

    approved = Column(
        Boolean
    )

    llm_model = Column(
        Text
    )

    final_response = Column(
        Text
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True
    )