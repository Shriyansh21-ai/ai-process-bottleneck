from sqlalchemy import Column, String, TIMESTAMP
from sqlalchemy.sql import func
from src.db.base import Base
import uuid

class GenAISession(Base):
    __tablename__ = "genai_sessions"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(TIMESTAMP, server_default=func.now())
    last_active_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
