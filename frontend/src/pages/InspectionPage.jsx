/**
 * MRPL Inspection Intelligence (Phase 4 demo experience).
 *
 * Upload an inspection report and run it through the REAL agent pipeline
 * (extract/OCR -> RAG -> Planner -> Executor -> Verifier), then present the
 * structured, evidence-backed findings with page provenance, a verification
 * verdict and the real agent trace. Additive: reuses DashboardLayout, the API
 * client, auth, routing and the existing design-system tokens.
 *
 * The findings ALWAYS come from the backend (POST /inspection/analyze) — nothing
 * on this page is fabricated.
 */

import { useState } from "react";
import {
  Upload,
  AlertCircle,
  ShieldCheck,
  ShieldAlert,
  FileText,
  FileSearch,
  Cpu,
  Download,
  RotateCcw,
} from "lucide-react";
import PageHeader from "../components/ui/PageHeader.jsx";
import { Card } from "../components/ui/Card.jsx";
import { Spinner } from "../components/ui/Spinner.jsx";
import { EmptyState } from "../components/ui/StateViews.jsx";
import FindingCard from "../components/inspection/FindingCard.jsx";
import PipelineStages from "../components/inspection/PipelineStages.jsx";
import AgentTrace from "../components/inspection/AgentTrace.jsx";
import * as inspectionService from "../services/inspectionService.js";

const DEFAULT_QUERY =
  "Identify safety-critical findings and defects that require maintenance attention.";

const PAGE_DESCRIPTION =
  "Analyze industrial inspection reports using sovereign AI: document intelligence, retrieval, agentic reasoning and verification.";

// Keep in sync with the backend upload limits (UPLOAD_MAX_REQUEST_BYTES /
// document config). Client-side check gives instant feedback before upload.
const MAX_UPLOAD_BYTES = 20 * 1024 * 1024;
const ALLOWED_EXT = ["pdf", "png", "jpg", "jpeg", "tif", "tiff", "bmp", "webp"];

const STAGE_DEFS = [
  { key: "extract", label: "Document Extraction" },
  { key: "ocr", label: "OCR / Text" },
  { key: "retrieval", label: "Knowledge Retrieval" },
  { key: "analysis", label: "Agent Analysis" },
  { key: "verify", label: "Verification" },
];

function formatFileSize(bytes) {
  if (!bytes && bytes !== 0) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

/** Safe, descriptive download filename derived from the analyzed document. */
function reportFilename(result) {
  const raw = result?.document?.filename || "inspection";
  const base = raw.replace(/\.[^.]+$/, "").replace(/[^A-Za-z0-9._-]+/g, "_").replace(/^_+|_+$/g, "");
  return `${base || "inspection"}_inspection_report.pdf`;
}

/** Trigger a browser download of a Blob without navigating away. */
function triggerBlobDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  // Revoke on the next tick so the download has a chance to start.
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

/** Map an API/client error to a clear, non-technical message. */
function friendlyError(err) {
  if (!err) return "The analysis could not be completed. Please try again.";
  const status = err.status;
  const code = err.detail?.detail?.code || err.detail?.code;

  if (status === 0) return "Cannot reach the backend. Make sure the API server is running and try again.";
  if (status === 401) return "Your session has expired. Please sign in again.";
  if (status === 413) return "That file is too large. Please upload a report under 20 MB.";
  if (status === 415 || code === "unsupported_file_type")
    return "Unsupported file type. Upload a PDF or an image (PNG, JPG, or TIFF).";
  if (status === 503 || code === "ocr_unavailable")
    return "This scanned document needs OCR, which is not available on the server right now.";
  if (status === 429) return "Too many requests. Please wait a moment and try again.";
  if (status === 422) {
    if (code === "empty_document") return "No readable text could be extracted from this document.";
    if (code === "corrupted_document" || code === "invalid_image")
      return "The file appears to be corrupted or unreadable.";
    if (code === "invalid_query" || code === "query_too_long")
      return "Please provide a valid analysis instruction.";
    return "The document could not be processed. Please check the file and try again.";
  }
  return err.message || "The analysis could not be completed. Please try again.";
}

function computeStages(phase, result) {
  if (phase === "running") return STAGE_DEFS.map((s) => ({ ...s, state: "active" }));
  if (phase !== "done" || !result) return STAGE_DEFS.map((s) => ({ ...s, state: "idle" }));

  const doc = result.document || {};
  const failed = result.overall_status === "analysis_failed";
  const hasDoc = doc.document_id != null;
  const approved = result.verification?.approved;
  const extractedOk = !!doc.extraction_method;

  return [
    { ...STAGE_DEFS[0], state: extractedOk ? "done" : "error" },
    {
      ...STAGE_DEFS[1],
      state: extractedOk ? "done" : "error",
      sublabel: extractedOk ? doc.extraction_method.toUpperCase() : undefined,
    },
    { ...STAGE_DEFS[2], state: hasDoc ? "done" : "error" },
    { ...STAGE_DEFS[3], state: failed ? "error" : result.run_id != null ? "done" : "review" },
    { ...STAGE_DEFS[4], state: failed ? "idle" : approved ? "done" : "review" },
  ];
}

export default function InspectionPage() {
  const [file, setFile] = useState(null);
  const [query, setQuery] = useState(DEFAULT_QUERY);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState(null);
  // Bump to force-remount the (uncontrolled) file input on reset.
  const [inputKey, setInputKey] = useState(0);

  const phase = submitting ? "running" : error ? "error" : result ? "done" : "idle";

  const onPickFile = (e) => {
    const picked = e.target.files?.[0] || null;
    setError(null);
    setResult(null);
    if (picked) {
      const ext = picked.name.split(".").pop()?.toLowerCase();
      if (!ALLOWED_EXT.includes(ext)) {
        setFile(null);
        setError({ status: 415, message: "Unsupported file type." });
        return;
      }
      if (picked.size > MAX_UPLOAD_BYTES) {
        setFile(null);
        setError({ status: 413, message: "File too large." });
        return;
      }
    }
    setFile(picked);
  };

  const analyze = async (e) => {
    e.preventDefault();
    if (!file || submitting) return;
    setSubmitting(true);
    setError(null);
    setResult(null);
    setDownloadError(null);
    try {
      const res = await inspectionService.analyzeInspection(file, query.trim() || DEFAULT_QUERY);
      setResult(res);
    } catch (err) {
      setError(err);
    } finally {
      setSubmitting(false);
    }
  };

  // Download a PDF report of the CURRENT analysis. This only re-formats the
  // result already on screen — it never re-runs analysis or re-uploads the
  // document (no duplicate records). The page does not reload.
  const downloadReport = async () => {
    if (!result || downloading) return;
    setDownloading(true);
    setDownloadError(null);
    try {
      const blob = await inspectionService.downloadReport(result);
      triggerBlobDownload(blob, reportFilename(result));
    } catch (err) {
      setDownloadError(err);
    } finally {
      setDownloading(false);
    }
  };

  // Reset the UI for a fresh analysis. This is a client-only reset — it does
  // NOT delete any backend/database records.
  const newAnalysis = () => {
    setFile(null);
    setResult(null);
    setError(null);
    setDownloadError(null);
    setQuery(DEFAULT_QUERY);
    setInputKey((k) => k + 1);
  };

  const doc = result?.document;
  const verification = result?.verification;
  const approved = verification?.approved;
  const showPipeline = phase === "running" || phase === "done";

  return (
    <>
      <PageHeader title="MRPL Inspection Intelligence" description={PAGE_DESCRIPTION} />

      {/* Upload / controls */}
      <Card title="Inspection report">
        <form onSubmit={analyze}>
          <div className="grid-2" style={{ gap: "1.25rem" }}>
            <div>
              <label className="field-label" htmlFor="inspection-file">
                Upload report (PDF or image)
              </label>
              <input
                key={inputKey}
                id="inspection-file"
                type="file"
                accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff,.bmp,.webp"
                onChange={onPickFile}
                disabled={submitting}
                style={{ display: "block", width: "100%" }}
              />
              {file && (
                <div
                  className="faint"
                  style={{ fontSize: "0.8rem", marginTop: "0.5rem", display: "flex", alignItems: "center", gap: "0.4rem" }}
                >
                  <FileText size={13} aria-hidden="true" /> {file.name} · {formatFileSize(file.size)}
                </div>
              )}
            </div>

            <div>
              <label className="field-label" htmlFor="inspection-query">
                Analysis instruction
              </label>
              <textarea
                id="inspection-query"
                className="textarea"
                rows={3}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                disabled={submitting}
                style={{ resize: "vertical" }}
              />
            </div>
          </div>

          <div style={{ marginTop: "1rem", display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
            <button type="submit" className="btn btn-primary" disabled={submitting || !file}>
              {submitting ? <Spinner size={16} /> : <Upload size={16} />}
              {submitting ? "Analyzing report…" : "Analyze Inspection Report"}
            </button>
            {!file && !error && (
              <span className="faint" style={{ fontSize: "0.8rem" }}>
                Select a PDF or image to begin.
              </span>
            )}
          </div>
        </form>
      </Card>

      {/* Error banner */}
      {error && (
        <div
          role="alert"
          className="badge-danger"
          style={{
            marginTop: "1.25rem",
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            padding: "0.8rem 1rem",
            borderRadius: 10,
            fontSize: "0.9rem",
            fontWeight: 500,
          }}
        >
          <AlertCircle size={16} aria-hidden="true" />
          {friendlyError(error)}
        </div>
      )}

      {/* Pipeline */}
      {showPipeline && (
        <div style={{ marginTop: "1.25rem" }}>
          <Card title="Processing pipeline">
            <PipelineStages stages={computeStages(phase, result)} />
            {submitting && (
              <div
                aria-live="polite"
                className="muted"
                style={{ marginTop: "0.9rem", textAlign: "center", fontSize: "0.85rem" }}
              >
                Analyzing inspection report — extraction, retrieval, agent analysis and verification…
              </div>
            )}
          </Card>
        </div>
      )}

      {/* Results */}
      {phase === "done" && result && (
        <div style={{ marginTop: "1.25rem", display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          {/* Summary + verification */}
          <Card
            title="Inspection analysis"
            actions={
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
                <AgentTrace runId={result.run_id} approved={approved} />
                <button
                  type="button"
                  className="btn btn-sm btn-primary"
                  onClick={downloadReport}
                  disabled={downloading}
                >
                  {downloading ? <Spinner size={14} /> : <Download size={15} aria-hidden="true" />}
                  {downloading ? "Generating report…" : "Download Inspection Report"}
                </button>
                <button
                  type="button"
                  className="btn btn-sm"
                  onClick={newAnalysis}
                  disabled={downloading}
                >
                  <RotateCcw size={15} aria-hidden="true" />
                  New Analysis
                </button>
              </div>
            }
          >
            {downloadError && (
              <div
                role="alert"
                className="badge-danger"
                style={{
                  marginBottom: "1rem",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.5rem",
                  padding: "0.7rem 0.9rem",
                  borderRadius: 10,
                  fontSize: "0.85rem",
                  fontWeight: 500,
                }}
              >
                <AlertCircle size={15} aria-hidden="true" />
                Could not generate the report. Please try again.
              </div>
            )}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))", gap: "1rem", marginBottom: "1rem" }}>
              <Meta icon={FileSearch} label="Document">{doc?.filename || "—"}</Meta>
              <Meta label="Pages">{doc?.page_count ?? "—"}</Meta>
              <Meta label="Extraction">{doc?.extraction_method ? doc.extraction_method.toUpperCase() : "—"}</Meta>
              <Meta icon={Cpu} label="Findings">{result.findings?.length ?? 0}</Meta>
            </div>

            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.6rem",
                padding: "0.7rem 0.9rem",
                borderRadius: 10,
                background: approved ? "var(--ok-bg)" : "var(--warn-bg)",
                border: `1px solid color-mix(in srgb, ${approved ? "var(--ok)" : "var(--warn)"} 30%, transparent)`,
              }}
            >
              {approved ? (
                <ShieldCheck size={18} style={{ color: "var(--ok)" }} aria-hidden="true" />
              ) : (
                <ShieldAlert size={18} style={{ color: "var(--warn)" }} aria-hidden="true" />
              )}
              <span style={{ fontWeight: 600 }}>
                {approved ? "Analysis verified" : "Verification requires review"}
              </span>
              <span className="faint" style={{ fontSize: "0.82rem" }}>
                {verification?.findings_valid ?? 0}/{verification?.findings_total ?? 0} findings validated
                {verification?.findings_rejected ? ` · ${verification.findings_rejected} rejected` : ""}
              </span>
            </div>

            {verification?.issues?.length > 0 && (
              <div style={{ marginTop: "0.75rem" }}>
                <div className="field-label">Verification notes</div>
                <ul className="muted" style={{ margin: 0, paddingLeft: "1.1rem", fontSize: "0.82rem" }}>
                  {verification.issues.map((iss, i) => (
                    <li key={i} style={{ overflowWrap: "anywhere" }}>{iss}</li>
                  ))}
                </ul>
              </div>
            )}
          </Card>

          {/* Findings */}
          <div>
            <h2 style={{ margin: "0 0 0.75rem", fontSize: "1.05rem", fontWeight: 700 }}>
              Findings ({result.findings?.length || 0})
            </h2>
            {result.findings?.length ? (
              <div className="grid-2">
                {result.findings.map((f) => (
                  <FindingCard key={f.finding_id} finding={f} />
                ))}
              </div>
            ) : (
              <Card>
                <EmptyState
                  icon={FileSearch}
                  title="No findings"
                  message="The analysis did not surface any findings that could be tied to document evidence."
                />
              </Card>
            )}
          </div>
        </div>
      )}

      {/* Initial empty state */}
      {phase === "idle" && (
        <div style={{ marginTop: "1.25rem" }}>
          <Card>
            <EmptyState
              icon={FileSearch}
              title="No analysis yet"
              message="Upload an inspection report and click Analyze to extract evidence-backed findings."
            />
          </Card>
        </div>
      )}
    </>
  );
}

function Meta({ icon: Icon, label, children }) {
  return (
    <div>
      <div className="field-label" style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
        {Icon && <Icon size={13} aria-hidden="true" />} {label}
      </div>
      <div style={{ fontSize: "0.92rem", fontWeight: 600, overflowWrap: "anywhere" }}>{children}</div>
    </div>
  );
}
