from sqlalchemy import Column, Integer, Text, DateTime
from sqlalchemy.sql import func

from src.db.base import Base


class Document(Base):

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)

    content = Column(Text, nullable=False)

    embedding = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )