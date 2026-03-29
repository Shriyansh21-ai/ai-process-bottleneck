from sqlalchemy import Column, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from db.base import Base

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"))
    content = Column(Text, nullable=False)

    embedding = Column(Vector(1536))  # OpenAI embedding size

    document = relationship("Document", backref="chunks")
