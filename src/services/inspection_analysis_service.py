"""
Inspection analysis orchestration (MRPL Phase 3).

This is the first complete MRPL demo vertical slice. It wires the EXISTING
building blocks together — it does NOT introduce a new agent architecture, a new
retrieval system, or a document -> LLM shortcut:

    inspection document
        -> DocumentIntelligencePipeline (extract / OCR, page provenance)
        -> ingest_extracted_document       (EXISTING RAG ingestion)
        -> AgentController.run(...)         (REAL Planner -> Executor -> Verifier)
              step 1: rag_retrieval  (scoped to this document_id)
              step 2: inspection_findings (evidence -> findings, via provider)
        -> InspectionVerifier              (deterministic structural + evidence guard)
        -> InspectionAnalysis              (structured, page-provenanced result)

The controller uses the provider abstraction, so the identical flow runs under
``LLM_PROVIDER=mock`` (this machine) and ``LLM_PROVIDER=ollama`` (a teammate's
machine) with no branching here.
"""

import logging

from src.agent.controller import AgentController
from src.agent.inspection_verifier import InspectionVerifier
from src.documents import (
    DocumentIntelligencePipeline,
    ingest_extracted_document,
)
from src.schemas.inspection import (
    Finding,
    InspectionAnalysis,
    InspectionDocumentInfo,
    InspectionVerification,
    STATUS_ACTION_REQUIRED,
    STATUS_ANALYSIS_FAILED,
    STATUS_NO_FINDINGS,
    STATUS_REVIEW,
    STATUS_VERIFICATION_FAILED,
    Severity,
    severity_rank,
)

logger = logging.getLogger("services.inspection_analysis")

# Embedded in the analysis query so the (real) planner produces the
# inspection-specific plan. Kept in sync with the mock provider marker.
_INSPECTION_MARKER = "MRPL_INSPECTION_ANALYSIS"


class InspectionAnalysisService:
    """Produce structured, evidence-backed findings for one inspection document."""

    def __init__(self, db, session_id: str = "inspection", user_id=None):
        self.db = db
        self.session_id = session_id
        self.user_id = user_id
        self.pipeline = DocumentIntelligencePipeline()
        self.findings_verifier = InspectionVerifier()

    async def analyze(self, data: bytes, filename: str, query: str) -> InspectionAnalysis:
        # 1) EXTRACT (may raise DocumentError -> mapped by the route).
        document = self.pipeline.extract(data, filename=filename)

        doc_info = InspectionDocumentInfo(
            document_id=None,
            filename=document.filename,
            page_count=document.page_count,
            extraction_method=document.extraction_method,
        )

        # 2) INGEST into the EXISTING RAG pipeline (chunk + embed + Qdrant),
        #    preserving page provenance. A failure here is reported, not fatal.
        try:
            ingest_result = ingest_extracted_document(self.db, document)
            document_id = ingest_result.get("document_id")
        except Exception as exc:  # noqa: BLE001 — surfaced as a structured result
            logger.warning("RAG ingestion failed during analysis: %s", exc)
            return self._failed(
                doc_info,
                run_id=None,
                issue=f"RAG ingestion failed: {exc}",
            )

        doc_info.document_id = document_id

        # 3) RUN the REAL agent pipeline. The document_id is embedded so the
        #    planner scopes retrieval to this document; the marker selects the
        #    inspection plan shape.
        analysis_query = (
            f"{_INSPECTION_MARKER}\n"
            f"document_id={document_id}\n"
            f"{query}"
        )
        controller = AgentController(
            db=self.db, session_id=self.session_id, user_id=self.user_id
        )
        run = await controller.run(analysis_query)
        run_id = run.get("run_id")

        if run.get("status") != "success":
            issues = self._controller_issues(run)
            return self._failed(doc_info, run_id=run_id, issue=issues)

        # 4) EXTRACT retrieval + findings from the execution result.
        results = ((run.get("execution") or {}).get("results") or {})
        rag_output, findings_output = None, None
        for step in results.values():
            if not isinstance(step, dict):
                continue
            if step.get("tool") == "rag_retrieval":
                rag_output = step.get("output")
            elif step.get("tool") == "inspection_findings":
                findings_output = step.get("output")

        findings_output = findings_output or {}
        raw_findings = findings_output.get("findings", [])
        degraded = bool(findings_output.get("degraded", False))

        # Authoritative retrieved-evidence provenance (prefer the retrieval step
        # output; fall back to the evidence the findings tool actually saw).
        chunks = rag_output if isinstance(rag_output, list) else (
            findings_output.get("evidence") or []
        )
        retrieved_pages = set()
        page_method = {}
        for chunk in chunks:
            if not isinstance(chunk, dict):
                continue
            page = chunk.get("page_number")
            if isinstance(page, int):
                retrieved_pages.add(page)
                page_method.setdefault(page, chunk.get("extraction_method"))

        # 5) DETERMINISTIC structural + evidence verification.
        valid, verification = self.findings_verifier.verify(
            raw_findings,
            retrieved_pages=retrieved_pages,
            page_method=page_method,
            document_id=document_id,
            degraded=degraded,
        )

        findings = [Finding(**f) for f in valid]
        overall_status = self._overall_status(findings, verification, degraded)

        return InspectionAnalysis(
            analysis_id=f"ins-{document_id}-{run_id}",
            document=doc_info,
            overall_status=overall_status,
            findings=findings,
            verification=InspectionVerification(**verification),
            run_id=run_id,
        )

    # -- helpers ------------------------------------------------------------
    @staticmethod
    def _overall_status(findings, verification, degraded) -> str:
        if degraded or not verification.get("approved", False):
            return STATUS_VERIFICATION_FAILED
        if not findings:
            return STATUS_NO_FINDINGS
        worst = max(severity_rank(f.severity) for f in findings)
        if worst >= severity_rank(Severity.HIGH):
            return STATUS_ACTION_REQUIRED
        return STATUS_REVIEW

    @staticmethod
    def _controller_issues(run: dict):
        verification = run.get("verification") or {}
        issues = verification.get("issues") if isinstance(verification, dict) else None
        if issues:
            return issues
        return run.get("message") or run.get("error") or (
            f"Agent run did not succeed (status={run.get('status')})."
        )

    def _failed(self, doc_info, run_id, issue) -> InspectionAnalysis:
        issues = issue if isinstance(issue, list) else [str(issue)]
        return InspectionAnalysis(
            analysis_id=f"ins-{doc_info.document_id}-{run_id}",
            document=doc_info,
            overall_status=STATUS_ANALYSIS_FAILED,
            findings=[],
            verification=InspectionVerification(
                approved=False,
                issues=issues,
                findings_total=0,
                findings_valid=0,
                findings_rejected=0,
            ),
            run_id=run_id,
        )
