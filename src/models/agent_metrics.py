from sqlalchemy import Column, Integer, String, Boolean, Numeric, TIMESTAMP
from sqlalchemy.sql import func
from db.base import Base


class AgentMetric(Base):
    __tablename__ = "agent_metrics"

    id = Column(Integer, primary_key=True, index=True)

    request_id = Column(String, nullable=False, index=True)
    agent_name = Column(String, nullable=False, index=True)

    latency_ms = Column(Integer)

    tokens_in = Column(Integer)
    tokens_out = Column(Integer)

    cost_usd = Column(Numeric(10, 6))
    confidence = Column(Numeric(4, 2))

    success = Column(Boolean, default=True)

    created_at = Column(
        TIMESTAMP(timezone=False),
        server_default=func.now()
    )
