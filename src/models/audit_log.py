from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.sql import func
from db.base import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    actor_id = Column(String, nullable=False)
    actor_type = Column(String(20), nullable=False)
    role = Column(String(20))
    action = Column(String(100), nullable=False)
    resource = Column(String(100))
    details = Column(JSON)  # ✅ renamed
    created_at = Column(DateTime, server_default=func.now())
