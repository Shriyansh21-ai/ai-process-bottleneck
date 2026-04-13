import asyncio
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, UploadFile, File, HTTPException
from src.genai.engine import GenAIEngine
from src.genai.agents.memory_summarizer import MemorySummarizerAgent
from src.db.session import SessionLocal

router = APIRouter()


def run_genai_task(data: dict):
    db = SessionLocal()
    try:
        engine = GenAIEngine(db=db, session_id="bg-task")
        engine.run_task(data)
    finally:
        db.close()


@router.post("/")
def analyze_bottleneck(data: dict, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_genai_task, data)
    return {"status": "processing", "message": "Analysis started"}


@router.post("/summarize")
async def summarize_text(data: dict):
    text = data.get("content") or data.get("text")
    if not text:
        raise HTTPException(status_code=400, detail="Missing content for summarization")

    summarizer = MemorySummarizerAgent()

    try:
        summary = await summarizer.run([text])
    except Exception as e:
        # Fallback graceful path
        words = text.split()
        summary = " ".join(words[:150]) + ("..." if len(words) > 150 else "")

    return {
        "status": "success",
        "summary": summary,
        "source_length": len(text),
        "hint": "Use /analysis/upload-and-summarize for docs",
    }


def _extract_text_from_pdf(raw_bytes: bytes) -> str:
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="PyPDF2 not installed; install it to support PDF summarization",
        )

    import io

    reader = PdfReader(io.BytesIO(raw_bytes))
    text_pages = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        text_pages.append(page_text)

    return "\n".join(text_pages)


def _extract_text_from_docx(raw_bytes: bytes) -> str:
    try:
        import docx
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="python-docx not installed; install it to support DOCX summarization",
        )

    import io

    doc = docx.Document(io.BytesIO(raw_bytes))
    return "\n".join([p.text for p in doc.paragraphs])


@router.post("/upload-and-summarize")
async def upload_and_summarize(file: UploadFile = File(...), max_tokens: Optional[int] = 250):
    content_type = file.content_type or ""
    file_bytes = await file.read()

    if content_type.startswith("text/") or file.filename.endswith((".md", ".txt")):
        text = file_bytes.decode("utf-8", errors="ignore")
    elif file.filename.lower().endswith(".pdf"):
        text = _extract_text_from_pdf(file_bytes)
    elif file.filename.lower().endswith(".docx"):
        text = _extract_text_from_docx(file_bytes)
    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type; only txt, md, pdf, docx supported",
        )

    # Truncate for safe token size
    if len(text) > max_tokens * 10:
        text = text[: max_tokens * 10]

    summarizer = MemorySummarizerAgent()

    try:
        summary = await summarizer.run([text])
    except Exception:
        words = text.split()
        summary = " ".join(words[: max_tokens * 2]) + ("..." if len(words) > max_tokens * 2 else "")

    return {
        "filename": file.filename,
        "content_type": content_type,
        "source_length": len(text),
        "summary": summary,
    }
