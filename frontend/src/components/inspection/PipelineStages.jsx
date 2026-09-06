/**
 * Pipeline stage indicator (MRPL Phase 4).
 *
 * Visualizes the real processing pipeline a report goes through:
 *   Document Extraction -> OCR / Text -> Knowledge Retrieval -> Agent Analysis
 *   -> Verification
 *
 * State per stage is DERIVED from real API state (see InspectionPage), not from
 * fabricated timers: while the single /analyze request is in flight every stage
 * shows "active"; once the response returns each stage reflects what actually
 * happened (done / needs-review).
 */

import { CheckCircle2, AlertTriangle, XCircle, Circle } from "lucide-react";
import { Spinner } from "../ui/Spinner.jsx";

function StageIcon({ state }) {
  if (state === "done") return <CheckCircle2 size={20} style={{ color: "var(--ok)" }} aria-hidden="true" />;
  if (state === "active") return <Spinner size={20} />;
  if (state === "review") return <AlertTriangle size={20} style={{ color: "var(--warn)" }} aria-hidden="true" />;
  if (state === "error") return <XCircle size={20} style={{ color: "var(--danger)" }} aria-hidden="true" />;
  return <Circle size={20} className="faint" aria-hidden="true" />;
}

const STATE_LABEL = {
  idle: "Pending",
  active: "Processing",
  done: "Done",
  review: "Review",
  error: "Failed",
};

export default function PipelineStages({ stages }) {
  return (
    <ol
      style={{
        listStyle: "none",
        margin: 0,
        padding: 0,
        display: "flex",
        flexWrap: "wrap",
        alignItems: "flex-start",
        gap: "0.5rem",
      }}
      aria-label="Processing pipeline"
    >
      {stages.map((s, i) => (
        <li
          key={s.key}
          style={{ display: "flex", alignItems: "center", gap: "0.5rem", flex: "1 1 140px", minWidth: 0 }}
        >
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "0.3rem", textAlign: "center", minWidth: 0, flex: 1 }}>
            <StageIcon state={s.state} />
            <div style={{ fontSize: "0.78rem", fontWeight: 600, lineHeight: 1.2 }}>{s.label}</div>
            <div className="faint" style={{ fontSize: "0.68rem" }}>
              {s.sublabel || STATE_LABEL[s.state] || ""}
            </div>
          </div>
          {i < stages.length - 1 && (
            <div aria-hidden="true" style={{ flex: "0 0 16px", height: 2, background: "var(--border)", alignSelf: "center", marginTop: -14 }} />
          )}
        </li>
      ))}
    </ol>
  );
}
