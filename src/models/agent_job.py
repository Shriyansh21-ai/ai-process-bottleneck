from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from src.db.base import Base

class AgentJob(Base):
    __tablename__ = "agent_jobs"

    id = Column(Integer, primary_key=True)
    status = Column(String(20), default="pending")  
    query = Column(Text, nullable=False)
    result = Column(Text)
    error = Column(Text)
    # NOTE: the Python attribute is `job_metadata` because `metadata` is a
    # reserved name on SQLAlchemy's declarative Base (defining it raises
    # InvalidRequestError, which previously made this whole model — and any
    # module importing it — impossible to import). The DB column stays
    # "metadata" so no schema change is implied.
    job_metadata = Column("metadata", JSON)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
