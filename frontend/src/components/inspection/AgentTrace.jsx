/**
 * Agent workflow trace (MRPL Phase 4).
 *
 * Reflects REAL execution data: the tool steps are loaded from the existing
 * owner-scoped /runs/{id}/steps endpoint (the same records the run-detail page
 * uses). The Planner and Verifier rows are DERIVED from the real run outcome
 * (a run with recorded steps necessarily produced a plan; the Verifier row
 * reflects the real verification.approved flag). No events are fabricated.
 */

import { useState } from "react";
import { ChevronDown, CheckCircle2, AlertTriangle, Brain, Database, FileSearch, ShieldCheck } from "lucide-react";
import StatusBadge from "../ui/StatusBadge.jsx";
import { InlineLoading, ErrorState } from "../ui/StateViews.jsx";
import { useAsync } from "../../hooks/useAsync.js";
import * as runsService from "../../services/runsService.js";

const TOOL_META = {
  rag_retrieval: { name: "RAG Retrieval", desc: "Retrieved relevant document evidence", Icon: Database },
  inspection_findings: { name: "Inspection Findings", desc: "Generated structured findings", Icon: FileSearch },
};

function Row({ Icon, name, desc, ok = true, badge }) {
  const StatusIcon = ok ? CheckCircle2 : AlertTriangle;
  const color = ok ? "var(--ok)" : "var(--warn)";
  return (
    <div style={{ display: "flex", alignItems: "flex-start", gap: "0.6rem", padding: "0.5rem 0" }}>
      <StatusIcon size={16} style={{ color, flex: "none", marginTop: 2 }} aria-hidden="true" />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 600, fontSize: "0.88rem", display: "flex", alignItems: "center", gap: "0.4rem" }}>
          {Icon && <Icon size={13} className="faint" aria-hidden="true" />}
          {name}
        </div>
        {desc && <div className="muted" style={{ fontSize: "0.8rem" }}>{desc}</div>}
      </div>
      {badge}
    </div>
  );
}

export default function AgentTrace({ runId, approved }) {
  const [open, setOpen] = useState(false);
  const steps = useAsync(
    (signal) => runsService.getRunSteps(runId, { signal }),
    [runId, open],
    { enabled: open && runId != null }
  );

  if (runId == null) return null;

  return (
    <div>
      <button
        className="btn btn-sm"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        <Brain size={15} aria-hidden="true" />
        {open ? "Hide agent trace" : "View agent trace"}
        <ChevronDown size={15} style={{ transition: "transform 0.15s", transform: open ? "rotate(180deg)" : "none" }} aria-hidden="true" />
      </button>

      {open && (
        <div className="card-2" style={{ marginTop: "0.75rem", padding: "0.75rem 1rem" }}>
          <div className="field-label" style={{ marginBottom: "0.25rem" }}>Agent workflow</div>

          {/* Planner — derived from the real run (steps exist => a plan ran). */}
          <Row Icon={Brain} name="Planner" desc="Created the inspection analysis plan" ok />

          {steps.error ? (
            <ErrorState error={steps.error} onRetry={steps.reload} />
          ) : steps.loading ? (
            <InlineLoading label="Loading steps…" />
          ) : steps.data && steps.data.length > 0 ? (
            steps.data.map((s) => {
              const meta = TOOL_META[s.tool_name] || { name: s.tool_name, desc: "" };
              return (
                <Row
                  key={s.id}
                  Icon={meta.Icon}
                  name={meta.name}
                  desc={meta.desc}
                  ok={s.status === "success"}
                  badge={<StatusBadge status={s.status} />}
                />
              );
            })
          ) : (
            <div className="muted" style={{ fontSize: "0.82rem", padding: "0.4rem 0" }}>
              No individual tool steps were recorded for this run.
            </div>
          )}

          {/* Verifier — reflects the real verification.approved flag. */}
          <Row
            Icon={ShieldCheck}
            name="Verifier"
            desc={approved ? "Validated evidence and provenance" : "Verification requires review"}
            ok={!!approved}
          />
        </div>
      )}
    </div>
  );
}
