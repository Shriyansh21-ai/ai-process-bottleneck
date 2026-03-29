import uuid
from sqlalchemy.orm import Session
from rag.chunker import TextChunker
from models.document import Document
from models.document_chunk import DocumentChunk
from rag.embeddings import embed_text

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

    for chunk in chunks:
        embedding = embed_text(chunk)

        db.add(DocumentChunk(
            id=uuid.uuid4(),
            document_id=doc_id,
            content=chunk,
            embedding=embedding
        ))

    db.commit()
