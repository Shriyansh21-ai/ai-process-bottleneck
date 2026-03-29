from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from src.db.base import Base

class Process(Base):
    __tablename__ = "processes"

    id = Column(Integer, primary_key=True, index=True)
    process_code = Column(String(50), unique=True, nullable=False)
    domain = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())
