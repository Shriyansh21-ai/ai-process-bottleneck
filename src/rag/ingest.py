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
    text: str,
    pages: list = None,
    extraction_method: str = None,
):
    """Chunk, embed and store a document in PostgreSQL + Qdrant.

    Backward compatible: called with ``text`` only, behaviour is unchanged.

    MRPL Phase 2 (additive): when ``pages`` is provided — a list of
    ``{"page_number": int, "text": str}`` (as produced by
    :class:`~src.documents.representation.ExtractedDocument`) — chunking is done
    PER PAGE so page provenance survives into the vector store. Each
    ``DocumentChunk`` gets its ``page_number`` set (column already exists) and
    each Qdrant point payload carries ``page_number`` + ``extraction_method``.
    The embedding model, chunker and collection are the EXISTING ones — this only
    threads provenance through; it does not add a second RAG implementation.
    """

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
    # Build a flat list of (chunk_text, page_number) pairs. Without page info we
    # chunk the whole document (legacy behaviour, page_number=None). With page
    # info we chunk each page independently so provenance is preserved.

    if pages:

        chunk_records = []

        for page in pages:

            page_number = page.get("page_number")

            page_text = page.get("text") or ""

            for chunk in chunker.chunk_text(page_text):

                chunk_records.append((chunk, page_number))

    else:

        chunk_records = [
            (chunk, None)
            for chunk in chunker.chunk_text(text)
        ]

    qdrant_points = []

    # ==========================================
    # PROCESS CHUNKS
    # ==========================================

    for index, (chunk, page_number) in enumerate(chunk_records):

        embedding = embed_text(chunk)

        # ==========================================
        # STORE CHUNK IN POSTGRESQL
        # ==========================================

        db_chunk = DocumentChunk(

            document_id=document.id,

            content=chunk,

            chunk_index=index,

            page_number=page_number
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

        payload = {

            "document_id": document.id,

            "content": chunk,

            "title": title,

            "source": source,

            "doc_type": doc_type,

            "chunk_index": index
        }

        # Additive provenance — only present when supplied, so legacy payloads
        # are byte-for-byte unchanged.
        if page_number is not None:
            payload["page_number"] = page_number

        if extraction_method is not None:
            payload["extraction_method"] = extraction_method

        qdrant_points.append(

            PointStruct(

                id=qdrant_id,

                vector=embedding,

                payload=payload
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

        "chunks_created": len(chunk_records),

        "vector_store": "qdrant",

        "extraction_method": extraction_method
    }