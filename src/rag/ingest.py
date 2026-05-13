import uuid

from sqlalchemy.orm import Session

from src.rag.chunker import TextChunker
from src.rag.embeddings import embed_text

from src.db.models.document import Document
from src.models.document_chunk import (
    DocumentChunk
)


chunker = TextChunker()


def ingest_document(
    db: Session,
    title: str,
    source: str,
    doc_type: str,
    text: str
):

    doc_id = uuid.uuid4()

    document = Document(
        id=doc_id,
        title=title,
        source=source,
        doc_type=doc_type
    )

    db.add(document)

    chunks = chunker.chunk_text(text)

    for index, chunk in enumerate(chunks):

        embedding = embed_text(chunk)

        db_chunk = DocumentChunk(
            id=uuid.uuid4(),
            document_id=doc_id,
            content=chunk,
            chunk_index=index,
            embedding=embedding
        )

        db.add(db_chunk)

    db.commit()

    return {
        "document_id": str(doc_id),
        "chunks_created": len(chunks)
    }