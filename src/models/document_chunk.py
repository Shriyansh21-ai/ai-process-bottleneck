from sqlalchemy import (
    Column,
    Integer,
    ForeignKey,
    Text
)

from sqlalchemy.orm import relationship

from src.db.base import Base


class DocumentChunk(Base):

    __tablename__ = "document_chunks"

    # ==========================================
    # PRIMARY KEY
    # ==========================================

    id = Column(
    Integer,
    primary_key=True,
    autoincrement=True
)

    # ==========================================
    # DOCUMENT RELATION
    # ==========================================

    document_id = Column(
        Integer,
        ForeignKey(
            "documents.id",
            ondelete="CASCADE"
        )
    )

    # ==========================================
    # CHUNK CONTENT
    # ==========================================

    content = Column(
        Text,
        nullable=False
    )

    # ==========================================
    # CHUNK POSITION
    # ==========================================

    chunk_index = Column(
        Integer,
        nullable=True
    )

    # ==========================================
    # OPTIONAL SOURCE METADATA
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