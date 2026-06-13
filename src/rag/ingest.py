from sqlalchemy.orm import Session

from qdrant_client.models import (
    PointStruct
)

from src.rag.chunker import TextChunker
from src.rag.embeddings import embed_text

from src.db.models.document import Document

from src.models.document_chunk import (
    DocumentChunk
)

from src.db.qdrant import client
import hashlib


chunker = TextChunker()


def ingest_document(
    db: Session,
    title: str,
    source: str,
    doc_type: str,
    text: str
):

    # ==========================================
    # CREATE DOCUMENT
    # ==========================================
    doc_hash = hashlib.md5(
    text.encode()
    ).hexdigest()

    existing = db.query(Document).filter(
    Document.content_hash == doc_hash
    ).first()

    if existing:

        return {

            "status": "duplicate",

            "message": "Document already exists",

            "document_id": existing.id
        }

    document = Document(

        title=title,

        source=source,

        doc_type=doc_type,

        content=text,

        content_hash=doc_hash
    )

    db.add(document)

    # ==========================================
    # GENERATE DOCUMENT ID
    # ==========================================

    db.flush()

    # ==========================================
    # CHUNK DOCUMENT
    # ==========================================

    chunks = chunker.chunk_text(text)

    qdrant_points = []

    # ==========================================
    # PROCESS CHUNKS
    # ==========================================

    for index, chunk in enumerate(chunks):

        embedding = embed_text(chunk)

        # ==========================================
        # STORE CHUNK IN POSTGRESQL
        # ==========================================

        db_chunk = DocumentChunk(

            document_id=document.id,

            content=chunk,

            chunk_index=index
        )

        db.add(db_chunk)

        # ==========================================
        # UNIQUE QDRANT POINT ID
        # ==========================================

        qdrant_id = int(
            f"{document.id}{index}"
        )

        # ==========================================
        # STORE VECTOR IN QDRANT
        # ==========================================

        qdrant_points.append(

            PointStruct(

                id=qdrant_id,

                vector=embedding,

                payload={

                    "document_id": document.id,

                    "content": chunk,

                    "title": title,

                    "source": source,

                    "doc_type": doc_type,

                    "chunk_index": index
                }
            )
        )

    # ==========================================
    # SAVE POSTGRESQL DATA
    # ==========================================

    db.commit()

    # ==========================================
    # SAVE TO QDRANT
    # ==========================================

    client.upsert(

        collection_name="documents",

        points=qdrant_points
    )

    return {

        "document_id": document.id,

        "chunks_created": len(chunks),

        "vector_store": "qdrant"
    }