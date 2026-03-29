from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from db.base import Base

class AgentJob(Base):
    __tablename__ = "agent_jobs"

    id = Column(Integer, primary_key=True)
    status = Column(String(20), default="pending")  
    query = Column(Text, nullable=False)
    result = Column(Text)
    error = Column(Text)
    metadata = Column(JSON)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
