"""
Deterministic inspection-findings verifier (MRPL Phase 3).

The agent pipeline's generic :class:`~src.agent.verifier.VerifierAgent` runs
first (inside the controller) and vouches for the run as a whole. THIS verifier
adds the domain-specific, deterministic structural checks the demo requires on
top of the produced findings:

  * required fields exist,
  * severity is a valid enum value,
  * evidence exists,
  * confidence is within [0, 1],
  * page_number is valid when supplied AND — the evidence/hallucination guard —
    the page was actually retrieved from the document (findings may not cite a
    page that was never seen),
  * the finding is grounded in retrieved evidence.

It is intentionally NOT ML-based: reliable, explainable, offline. Invalid
findings are DROPPED (never silently returned) and each rejection is reported as
a human-readable issue.
"""

import logging
from typing import Dict, List, Optional, Set, Tuple

from src.schemas.inspection import Severity

logger = logging.getLogger("agent.inspection_verifier")

_VALID_SEVERITIES = {s.value for s in Severity}
_REQUIRED_FIELDS = ("title", "description", "severity", "evidence", "recommendation")


class InspectionVerifier:
    """Validate raw findings against retrieved evidence; drop invalid ones."""

    def verify(
        self,
        raw_findings: list,
        retrieved_pages: Set[int],
        page_method: Dict[int, Optional[str]],
        document_id,
        degraded: bool = False,
    ) -> Tuple[List[dict], dict]:
        """Return ``(valid_findings, verification)``.

        ``valid_findings`` are normalized finding dicts ready for the response
        schema (finding_id assigned, extraction_method resolved from provenance).
        ``verification`` is the structured verdict.
        """
        issues: List[str] = []

        if degraded:
            # The LLM was offline/unusable — we cannot vouch for anything. Fail
            # closed rather than emit unverified findings.
            return [], {
                "approved": False,
                "issues": [
                    "Analysis ran in degraded/offline mode — findings were not "
                    "produced or verified."
                ],
                "findings_total": 0,
                "findings_valid": 0,
                "findings_rejected": 0,
            }

        if not isinstance(raw_findings, list):
            return [], {
                "approved": False,
                "issues": ["Findings payload was not a list."],
                "findings_total": 0,
                "findings_valid": 0,
                "findings_rejected": 0,
            }

        valid: List[dict] = []
        rejected = 0

        for idx, finding in enumerate(raw_findings, start=1):
            ok, normalized, reason = self._validate_one(
                finding, retrieved_pages, page_method, document_id, idx
            )
            if ok:
                valid.append(normalized)
            else:
                rejected += 1
                issues.append(f"Finding {idx} rejected: {reason}")

        total = len(raw_findings)
        approved = rejected == 0  # zero findings (clean report) is approved.

        verification = {
            "approved": approved,
            "issues": issues,
            "findings_total": total,
            "findings_valid": len(valid),
            "findings_rejected": rejected,
        }
        logger.info(
            "inspection verify | total=%d valid=%d rejected=%d approved=%s",
            total, len(valid), rejected, approved,
        )
        return valid, verification

    # -- per-finding validation --------------------------------------------
    def _validate_one(
        self,
        finding,
        retrieved_pages: Set[int],
        page_method: Dict[int, Optional[str]],
        document_id,
        idx: int,
    ):
        if not isinstance(finding, dict):
            return False, None, "not an object"

        # Required textual fields.
        for field in _REQUIRED_FIELDS:
            value = finding.get(field)
            if not isinstance(value, str) or not value.strip():
                return False, None, f"missing/empty field '{field}'"

        # Severity must be a known enum value (case-normalized).
        severity = str(finding.get("severity", "")).strip().upper()
        if severity not in _VALID_SEVERITIES:
            return False, None, f"invalid severity '{finding.get('severity')}'"

        # Confidence must be a number in [0, 1].
        confidence = finding.get("confidence")
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            return False, None, "confidence is not a number"
        if not (0.0 <= confidence <= 1.0):
            return False, None, f"confidence {confidence} out of range [0,1]"

        # Evidence/provenance guard: a finding MUST cite a page that was
        # actually retrieved from the document. This blocks fabricated pages.
        page_number = finding.get("page_number")
        if page_number is None:
            return False, None, "no page_number (cannot establish provenance)"
        try:
            page_number = int(page_number)
        except (TypeError, ValueError):
            return False, None, f"page_number '{page_number}' is not an integer"
        if page_number < 1:
            return False, None, f"page_number {page_number} is not valid (>=1)"
        if page_number not in retrieved_pages:
            return (
                False,
                None,
                f"page {page_number} was not in the retrieved evidence "
                f"{sorted(retrieved_pages)}",
            )

        normalized = {
            "finding_id": f"{document_id}-F{idx}",
            "title": finding["title"].strip(),
            "description": finding["description"].strip(),
            "severity": severity,
            "evidence": finding["evidence"].strip(),
            "page_number": page_number,
            # Resolve extraction_method from the retrieved page's provenance so
            # the value is trustworthy regardless of what the model claimed.
            "extraction_method": page_method.get(page_number),
            "recommendation": finding["recommendation"].strip(),
            "confidence": confidence,
        }
        return True, normalized, None
