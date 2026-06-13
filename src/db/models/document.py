from sqlalchemy import (
    Column,
    Integer,
    Text,
    DateTime
)

from sqlalchemy.sql import func

from src.db.base import Base


class Document(Base):

    __tablename__ = "documents"

    # ==========================================
    # PRIMARY KEY
    # ==========================================

    id = Column(
    Integer,
    primary_key=True,
    autoincrement=True
)

    # ==========================================
    # DOCUMENT METADATA
    # ==========================================

    title = Column(
        Text,
        nullable=False
    )

    source = Column(
        Text,
        nullable=True
    )

    doc_type = Column(
        Text,
        nullable=True
    )

    # ==========================================
    # RAW DOCUMENT TEXT
    # ==========================================

    content = Column(
        Text,
        nullable=True
    )
    content_hash = Column(
    Text,
    unique=True,
    nullable=False
    )

    # ==========================================
    # TIMESTAMP
    # ==========================================

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )