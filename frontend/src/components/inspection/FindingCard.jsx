/**
 * A single inspection finding rendered as a distinct, evidence-first card
 * (MRPL Phase 4). Severity drives a left accent border; page provenance and
 * confidence are always shown so a finding is traceable to the source document.
 */

import { FileText, Quote, Wrench } from "lucide-react";
import SeverityBadge, { severityColor } from "./SeverityBadge.jsx";
import { formatConfidence } from "../../lib/format.js";

export default function FindingCard({ finding }) {
  const accent = severityColor(finding.severity);
  const method = finding.extraction_method
    ? finding.extraction_method.toUpperCase()
    : null;

  return (
    <article
      className="card"
      style={{ borderLeft: `4px solid ${accent}`, padding: "1rem 1.15rem" }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "0.75rem",
          flexWrap: "wrap",
        }}
      >
        <SeverityBadge severity={finding.severity} />
        <span
          className="faint"
          style={{ fontSize: "0.75rem", display: "inline-flex", alignItems: "center", gap: "0.4rem" }}
        >
          <FileText size={12} aria-hidden="true" />
          {finding.page_number != null ? `Page ${finding.page_number}` : "Page —"}
          {method ? ` · ${method}` : ""}
          {finding.confidence != null && (
            <> · Confidence {formatConfidence(finding.confidence)}</>
          )}
        </span>
      </div>

      <h3 style={{ margin: "0.6rem 0 0.3rem", fontSize: "1rem", fontWeight: 700 }}>
        {finding.title}
      </h3>
      {finding.description && (
        <p className="muted" style={{ margin: 0, fontSize: "0.88rem", lineHeight: 1.5 }}>
          {finding.description}
        </p>
      )}

      {finding.evidence && (
        <div style={{ marginTop: "0.75rem" }}>
          <div className="field-label" style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
            <Quote size={12} aria-hidden="true" /> Evidence
          </div>
          <blockquote
            className="card-2"
            style={{
              margin: 0,
              padding: "0.6rem 0.8rem",
              borderLeft: `3px solid ${accent}`,
              fontStyle: "italic",
              fontSize: "0.85rem",
              lineHeight: 1.5,
              overflowWrap: "anywhere",
            }}
          >
            {finding.evidence}
          </blockquote>
        </div>
      )}

      {finding.recommendation && (
        <div style={{ marginTop: "0.75rem" }}>
          <div className="field-label" style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
            <Wrench size={12} aria-hidden="true" /> Recommendation
          </div>
          <p style={{ margin: 0, fontSize: "0.88rem", lineHeight: 1.5 }}>
            {finding.recommendation}
          </p>
        </div>
      )}
    </article>
  );
}
