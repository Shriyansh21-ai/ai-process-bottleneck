from sqlalchemy import Column, Integer, String, Text, TIMESTAMP
from sqlalchemy.sql import func
from db.base import Base

class GenAITaskLog(Base):
    __tablename__ = "genai_task_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)

    task = Column(Text)
    status = Column(String)
    response = Column(Text, nullable=True)
    error = Column(Text, nullable=True)

    execution_time_seconds = Column(Integer, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
