/**
 * Execution step timeline (Phase 10). Renders each recorded step as an
 * expandable card connected vertically, with the tool, status, duration and
 * retry count always visible and the (already truncated) input/output/error
 * summaries revealed on expand — never dumped by default.
 */

import { useState } from "react";
import { ChevronDown, ArrowDown, AlertTriangle } from "lucide-react";
import StatusBadge from "../ui/StatusBadge.jsx";
import { formatDuration } from "../../lib/format.js";
import { statusTone } from "../../lib/format.js";

function StepCard({ step, index }) {
  const [open, setOpen] = useState(false);
  const tone = statusTone(step.status);
  const accent = {
    ok: "var(--ok)", danger: "var(--danger)", info: "var(--info)", warn: "var(--warn)", neutral: "var(--neutral)",
  }[tone];
  const hasDetail = step.input_summary || step.output_summary || step.error;

  return (
    <div className="card" style={{ borderLeft: `3px solid ${accent}` }}>
      <button
        onClick={() => hasDetail && setOpen((o) => !o)}
        aria-expanded={hasDetail ? open : undefined}
        disabled={!hasDetail}
        style={{
          width: "100%", display: "flex", alignItems: "center", gap: "0.75rem",
          background: "transparent", border: "none", color: "var(--text)", font: "inherit",
          padding: "0.8rem 1rem", cursor: hasDetail ? "pointer" : "default", textAlign: "left",
        }}
      >
        <div
          aria-hidden="true"
          style={{
            width: 30, height: 30, borderRadius: 8, flex: "none", display: "grid", placeItems: "center",
            background: "var(--surface-2)", border: "1px solid var(--border)", fontSize: "0.8rem", fontWeight: 700,
          }}
        >
          {step.step_id ?? index + 1}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 600, fontSize: "0.9rem" }} className="mono">
            {step.tool_name || "unknown tool"}
          </div>
          <div className="faint" style={{ fontSize: "0.75rem" }}>
            {formatDuration(step.execution_time_ms)}
            {step.retry_count ? ` · ${step.retry_count} retr${step.retry_count === 1 ? "y" : "ies"}` : ""}
          </div>
        </div>
        <StatusBadge status={step.status} />
        {hasDetail && (
          <ChevronDown size={16} style={{ transition: "transform 0.15s", transform: open ? "rotate(180deg)" : "none", color: "var(--text-faint)", flex: "none" }} aria-hidden="true" />
        )}
      </button>

      {open && hasDetail && (
        <div style={{ padding: "0 1rem 1rem", display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {step.error && (
            <div className="badge-danger" style={{ display: "flex", gap: "0.5rem", padding: "0.6rem 0.75rem", borderRadius: 8, fontSize: "0.82rem", alignItems: "flex-start" }}>
              <AlertTriangle size={15} style={{ flex: "none", marginTop: 1 }} aria-hidden="true" />
              <span style={{ overflowWrap: "anywhere" }}>{step.error}</span>
            </div>
          )}
          {step.input_summary && (
            <div>
              <div className="field-label">Input</div>
              <pre className="mono card-2" style={{ margin: 0, padding: "0.6rem 0.75rem", fontSize: "0.76rem", overflow: "auto", maxHeight: 200, whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{step.input_summary}</pre>
            </div>
          )}
          {step.output_summary && (
            <div>
              <div className="field-label">Output</div>
              <pre className="mono card-2" style={{ margin: 0, padding: "0.6rem 0.75rem", fontSize: "0.76rem", overflow: "auto", maxHeight: 200, whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{step.output_summary}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function StepTimeline({ steps }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
      {steps.map((step, i) => (
        <div key={step.id ?? i}>
          <StepCard step={step} index={i} />
          {i < steps.length - 1 && (
            <div style={{ display: "flex", justifyContent: "center", padding: "0.15rem 0" }} aria-hidden="true">
              <ArrowDown size={16} className="faint" />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
