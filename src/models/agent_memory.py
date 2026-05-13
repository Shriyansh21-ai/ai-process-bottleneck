from sqlalchemy import Column, Integer, Text
from sqlalchemy import JSON
from src.db.base import Base

class AgentMemory(Base):
    __tablename__ = "agent_memory"

    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    embedding = Column(JSON)
