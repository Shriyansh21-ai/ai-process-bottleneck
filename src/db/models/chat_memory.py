from sqlalchemy import (
    Column,
    Integer,
    Text,
    DateTime
)

from sqlalchemy.sql import func

from src.db.base import Base


class ChatMemory(Base):

    __tablename__ = "chat_memory"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    role = Column(Text)

    message = Column(Text)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )