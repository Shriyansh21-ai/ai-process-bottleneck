from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.db.base import Base

class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)
    case_code = Column(String(50), nullable=False)
    process_id = Column(Integer, ForeignKey("processes.id"))
    created_at = Column(DateTime, server_default=func.now())

    process = relationship("Process")
