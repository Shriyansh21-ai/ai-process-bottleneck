from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime
)

from src.db.base import Base


class GenAIMemory(Base):

    __tablename__ = "genai_memory"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    session_id = Column(
        String,
        nullable=False,
        index=True
    )

    content = Column(
        Text,
        nullable=False
    )

    embedding = Column(
        Text,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )