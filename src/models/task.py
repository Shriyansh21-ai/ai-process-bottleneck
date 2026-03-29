from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.db.base import Base

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_code = Column(String(50))
    task_name = Column(String)
    case_id = Column(Integer, ForeignKey("cases.id"))
    resource_id = Column(Integer, ForeignKey("resources.id"))

    start_time = Column(DateTime)
    end_time = Column(DateTime)
    duration_minutes = Column(Float)
    status = Column(String(20))
    created_at = Column(DateTime, server_default=func.now())

    case = relationship("Case")
    resource = relationship("Resource")
