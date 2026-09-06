"""
Local MRPL inspection demo (LLM_PROVIDER=mock) — no Ollama / OpenAI / internet.

Runs the REAL pipeline end to end on the synthetic demo report:

    demo PDF -> DocumentIntelligencePipeline (real extraction)
             -> ingest_extracted_document   (real embeddings + embedded Qdrant)
             -> AgentController.run          (real Planner/Executor/Verifier)
             -> InspectionVerifier           (real deterministic guard)
             -> InspectionAnalysis (printed)

Only the LLM (mock provider) and the agent memory subsystem are stubbed; the
retrieval, embeddings and Qdrant are REAL. This is the same code path the
`POST /inspection/analyze` endpoint executes.

NOTE: the embedded Qdrant store (./qdrant_data) is single-process — stop any
running dev server before invoking this script.

Usage:
    python scripts/run_inspection_demo.py [pdf_path]
"""

import asyncio
import json
import os
import sys

# Import-safe DB URL (never connected — we use our own SQLite session below).
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://t:t@localhost:5432/t")
os.environ["LLM_PROVIDER"] = "mock"
os.environ.setdefault("EMBEDDINGS_PROVIDER", "local")  # 384-dim, offline
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
# Short demo corpus -> lower similarity floor so page-level evidence is admitted.
os.environ.setdefault("RAG_SIMILARITY_THRESHOLD", "0.3")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.db.base import Base
import src.db.models  # noqa: F401 register core tables (documents, agent_runs, ...)
import src.models  # noqa: F401 register process/case/task/audit models
import src.models.document_chunk  # noqa: F401 register document_chunks table
from src.db.init_qdrant import init_qdrant


def _session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)


def main() -> None:
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        "data", "demo", "mrpl_inspection_report.pdf"
    )
    if not os.path.exists(pdf_path):
        print(f"Demo report not found: {pdf_path}\n"
              f"Generate it first: python scripts/generate_demo_report.py")
        sys.exit(1)

    with open(pdf_path, "rb") as fh:
        data = fh.read()

    # Ensure the (real, embedded) Qdrant collection exists.
    init_qdrant()

    # Memory is orthogonal to the inspection story — stub it to no-ops so the
    # demo needs no memory backend. Everything else is the real pipeline.
    from src.agent import controller as controller_mod
    controller_mod.retrieve_memory = lambda **kw: []
    controller_mod.add_memory = lambda **kw: None

    from src.services.inspection_analysis_service import InspectionAnalysisService

    Session = _session_factory()
    db = Session()
    try:
        service = InspectionAnalysisService(db=db, session_id="cli-demo", user_id=1)
        analysis = asyncio.run(
            service.analyze(
                data,
                filename=os.path.basename(pdf_path),
                query=("Identify safety-critical findings and defects that "
                       "require maintenance attention."),
            )
        )
    finally:
        db.close()

    result = analysis.model_dump()
    print("\n================ INSPECTION ANALYSIS (mock LLM) ================\n")
    print(json.dumps(result, indent=2, default=str))
    print("\n================ SUMMARY ================")
    print(f"Document : {result['document']['filename']} "
          f"({result['document']['page_count']} pages, "
          f"{result['document']['extraction_method']})")
    print(f"Status   : {result['overall_status']}")
    print(f"Verified : {result['verification']['approved']} "
          f"({result['verification']['findings_valid']}/"
          f"{result['verification']['findings_total']} findings valid)")
    for f in result["findings"]:
        print(f"  - [{f['severity']}] {f['title']} "
              f"(page {f['page_number']} · {f['extraction_method']}, "
              f"conf {f['confidence']})")


if __name__ == "__main__":
    main()
