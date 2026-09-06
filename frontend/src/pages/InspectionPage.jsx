/**
 * MRPL Inspection Intelligence (Phase 3 demo vertical slice).
 *
 * Upload an inspection report, run it through the real agent pipeline
 * (extract/OCR -> RAG -> Planner -> Executor -> Verifier) and render the
 * structured, evidence-backed findings with page provenance. Deliberately
 * minimal — one page, additive, reusing the existing dashboard chrome + api
 * client. No new design system.
 */

import { useState, useRef } from "react";
import {
  FileSearch,
  Upload,
  AlertCircle,
  ShieldCheck,
  ShieldAlert,
  FileText,
} from "lucide-react";
import PageHeader from "../components/ui/PageHeader.jsx";
import { Card } from "../components/ui/Card.jsx";
import { Spinner } from "../components/ui/Spinner.jsx";
import { Link } from "../lib/router.jsx";
import * as inspectionService from "../services/inspectionService.js";

const DEFAULT_QUERY =
  "Analyze this inspection report and identify safety-critical findings requiring attention.";

// Severity -> colored dot + label. Maps to the backend Severity enum.
const SEVERITY_STYLE = {
  CRITICAL: { color: "#b91c1c", dot: "🔴", label: "CRITICAL" },
  HIGH: { color: "#dc2626", dot: "🔴", label: "HIGH" },
  MEDIUM: { color: "#d97706", dot: "🟡", label: "MEDIUM" },
  LOW: { color: "#2563eb", dot: "🔵", label: "LOW" },
};

function SeverityTag({ severity }) {
  const s = SEVERITY_STYLE[severity] || { color: "#6b7280", dot: "⚪", label: severity };
  return (
    <span style={{ fontWeight: 700, color: s.color, fontSize: "0.8rem", letterSpacing: "0.02em" }}>
      {s.dot} {s.label}
    </span>
  );
}

function FindingCard({ finding }) {
  return (
    <div
      style={{
        border: "1px solid var(--border, #e5e7eb)",
        borderRadius: 10,
        padding: "0.9rem 1rem",
        display: "flex",
        flexDirection: "column",
        gap: "0.5rem",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "0.75rem" }}>
        <SeverityTag severity={finding.severity} />
        <span className="faint mono" style={{ fontSize: "0.72rem" }}>
          {finding.page_number != null ? `Page ${finding.page_number}` : "Page —"}
          {finding.extraction_method ? ` · ${finding.extraction_method}` : ""}
        </span>
      </div>

      <div style={{ fontWeight: 600 }}>{finding.title}</div>
      {finding.description && (
        <p className="muted" style={{ margin: 0, fontSize: "0.86rem" }}>{finding.description}</p>
      )}

      {finding.evidence && (
        <div>
          <div className="field-label">Evidence</div>
          <blockquote
            style={{
              margin: 0,
              padding: "0.5rem 0.75rem",
              borderLeft: "3px solid var(--border, #e5e7eb)",
              fontStyle: "italic",
              fontSize: "0.84rem",
              whiteSpace: "pre-wrap",
            }}
          >
            {finding.evidence}
          </blockquote>
        </div>
      )}

      {finding.recommendation && (
        <div>
          <div className="field-label">Recommendation</div>
          <div style={{ fontSize: "0.86rem" }}>{finding.recommendation}</div>
        </div>
      )}

      <div className="faint" style={{ fontSize: "0.72rem" }}>
        confidence: {(Number(finding.confidence) * 100).toFixed(0)}%
      </div>
    </div>
  );
}

export default function InspectionPage() {
  const [file, setFile] = useState(null);
  const [query, setQuery] = useState(DEFAULT_QUERY);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  const analyze = async (e) => {
    e.preventDefault();
    if (!file || submitting) return;
    setSubmitting(true);
    setError(null);
    setResult(null);
    try {
      const res = await inspectionService.analyzeInspection(file, query.trim() || DEFAULT_QUERY);
      setResult(res);
    } catch (err) {
      setError(err);
    } finally {
      setSubmitting(false);
    }
  };

  const doc = result?.document;
  const approved = result?.verification?.approved;

  return (
    <>
      <PageHeader
        title="MRPL Inspection Intelligence"
        description="Upload an inspection report and extract structured, evidence-backed findings using the agent pipeline."
      />

      <div className="grid-2">
        <Card title="Inspection report">
          <form onSubmit={analyze}>
            <label className="field-label" htmlFor="inspection-file">Upload report (PDF or image)</label>
            <input
              id="inspection-file"
              ref={fileInputRef}
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff,.bmp,.webp"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              disabled={submitting}
              style={{ display: "block", marginBottom: "0.75rem" }}
            />
            {file && (
              <div className="faint" style={{ fontSize: "0.8rem", marginBottom: "0.75rem", display: "flex", alignItems: "center", gap: "0.4rem" }}>
                <FileText size={13} /> {file.name}
              </div>
            )}

            <label className="field-label" htmlFor="inspection-query">Analysis instruction</label>
            <textarea
              id="inspection-query"
              className="textarea"
              rows={3}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={submitting}
              style={{ resize: "vertical", marginBottom: "0.75rem" }}
            />

            <button type="submit" className="btn btn-primary" disabled={submitting || !file}>
              {submitting ? <Spinner size={16} /> : <Upload size={16} />}
              {submitting ? "Analyzing…" : "Analyze inspection"}
            </button>
          </form>
        </Card>

        <Card title="Analysis">
          {submitting ? (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "0.75rem", padding: "2rem 1rem", textAlign: "center" }}>
              <Spinner size={26} />
              <div style={{ fontWeight: 600 }}>Running the inspection pipeline…</div>
              <p className="muted" style={{ margin: 0, fontSize: "0.85rem", maxWidth: 320 }}>
                Extraction → RAG retrieval → Planner → Executor → Verifier. This can take a moment.
              </p>
            </div>
          ) : error ? (
            <div role="alert" className="badge-danger" style={{ display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.7rem 0.85rem", borderRadius: 9, fontSize: "0.88rem", fontWeight: 500 }}>
              <AlertCircle size={16} aria-hidden="true" />
              {error.message || "The analysis could not be completed."}
            </div>
          ) : result ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              {doc && (
                <div className="faint" style={{ fontSize: "0.78rem", display: "flex", flexWrap: "wrap", gap: "0.75rem" }}>
                  <span><FileSearch size={12} /> {doc.filename}</span>
                  <span>Pages: {doc.page_count}</span>
                  <span>Extraction: {doc.extraction_method}</span>
                </div>
              )}

              <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
                {approved ? <ShieldCheck size={16} color="#16a34a" /> : <ShieldAlert size={16} color="#dc2626" />}
                <span style={{ fontWeight: 600 }}>Status: {result.overall_status}</span>
              </div>

              {result.verification?.issues?.length > 0 && (
                <div className="faint" style={{ fontSize: "0.78rem" }}>
                  <div className="field-label">Verification issues</div>
                  <ul style={{ margin: 0, paddingLeft: "1.1rem" }}>
                    {result.verification.issues.map((iss, i) => <li key={i}>{iss}</li>)}
                  </ul>
                </div>
              )}

              <div>
                <div className="field-label">Findings ({result.findings?.length || 0})</div>
                {result.findings?.length ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                    {result.findings.map((f) => <FindingCard key={f.finding_id} finding={f} />)}
                  </div>
                ) : (
                  <div className="muted" style={{ fontSize: "0.86rem" }}>No findings were produced.</div>
                )}
              </div>

              {result.run_id != null && (
                <Link to={`/runs/${result.run_id}`} className="btn btn-sm" style={{ alignSelf: "flex-start" }}>
                  View agent execution trace
                </Link>
              )}
            </div>
          ) : (
            <div className="muted" style={{ padding: "2rem 1rem", textAlign: "center", fontSize: "0.9rem" }}>
              Upload an inspection report and run the analysis to see findings here.
            </div>
          )}
        </Card>
      </div>
    </>
  );
}
