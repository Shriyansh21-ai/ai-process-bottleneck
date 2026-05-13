from sqlalchemy import (
    Column,
    Integer,
    ForeignKey,
    Text
)

from sqlalchemy.orm import relationship

from sqlalchemy import JSON

from src.db.base import Base


class DocumentChunk(Base):

    __tablename__ = "document_chunks"

    id = Column(
        Integer,
        primary_key=True
    )

    document_id = Column(
        Integer,
        ForeignKey(
            "documents.id",
            ondelete="CASCADE"
        )
    )

    content = Column(
        Text,
        nullable=False
    )

    embedding = Column(JSON)

    # ==========================================
    # SOURCE METADATA
    # ==========================================

    section = Column(
        Text,
        nullable=True
    )

    page_number = Column(
        Integer,
        nullable=True
    )

    # ==========================================
    # RELATIONSHIP
    # ==========================================

    document = relationship(
        "Document",
        backref="chunks"
    )