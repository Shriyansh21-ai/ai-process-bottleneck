from fastapi import (
    APIRouter,
    Depends
)

from pydantic import BaseModel

from sqlalchemy.orm import Session

from src.db.session import SessionLocal

from src.rag.ingest import (
    ingest_document
)
from fastapi import UploadFile, File
import tempfile

from src.rag.pdf_parser import extract_text_from_pdf


router = APIRouter(
    prefix="/ingest",
    tags=["Ingest"]
)


# ==========================================
# DATABASE DEPENDENCY
# ==========================================

def get_db():

    db = SessionLocal()

    try:

        yield db

    finally:

        db.close()


# ==========================================
# REQUEST SCHEMA
# ==========================================

class IngestRequest(BaseModel):

    title: str
    source: str
    doc_type: str
    text: str


# ==========================================
# INGEST ENDPOINT
# ==========================================

@router.post("/")
def ingest_data(
    request: IngestRequest,
    db: Session = Depends(get_db)
):

    result = ingest_document(
        db=db,
        title=request.title,
        source=request.source,
        doc_type=request.doc_type,
        text=request.text
    )

    return {
        "status": "success",
        "message": "Document ingested successfully",
        "data": result
    }

@router.post("/pdf")
async def ingest_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".pdf"
    ) as temp_file:

        content = await file.read()

        temp_file.write(content)

        temp_path = temp_file.name

    extracted_text = extract_text_from_pdf(
        temp_path
    )

    result = ingest_document(
        db=db,
        title=file.filename,
        source="uploaded_pdf",
        doc_type="pdf",
        text=extracted_text
    )

    return {
        "status": "success",
        "message": "PDF ingested successfully",
        "data": result
    }