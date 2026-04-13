from sqlalchemy import Column, Integer, Text, String
from src.db.base import Base


class GenAIMemory(Base):
    __tablename__ = "genai_memory"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Text, nullable=False)  # pgvector stored as text/array
