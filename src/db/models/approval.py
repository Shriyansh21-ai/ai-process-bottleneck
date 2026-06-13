from sqlalchemy import (
    Column,
    Integer,
    Text,
    DateTime,
    Boolean
)

from sqlalchemy.sql import func

from src.db.base import Base


class ApprovalRequest(Base):

    __tablename__ = "approval_requests"

    id = Column(Integer, primary_key=True)

    user_query = Column(Text, nullable=False)

    tool_name = Column(Text, nullable=False)

    task = Column(Text)

    plan_json = Column(Text)

    session_id = Column(Text)

    risk_level = Column(Text)

    status = Column(Text, default="pending")

    reason = Column(Text)

    approved = Column(Boolean, nullable=True)

    executed = Column(Boolean, default=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )