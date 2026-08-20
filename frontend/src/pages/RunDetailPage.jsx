/**
 * Run detail page (Phases 9 & 10). Consumes /runs/{id} for the full record and
 * /runs/{id}/steps for the execution timeline. Raw plan/execution/verification
 * payloads are shown in collapsed JSON viewers rather than dumped inline.
 */

import { ArrowLeft, Cpu, Clock, GitBranch, Database, Brain, Hash } from "lucide-react";
import PageHeader from "../components/ui/PageHeader.jsx";
import { Card } from "../components/ui/Card.jsx";
import { ErrorState, EmptyState, LoadingBlock, InlineLoading } from "../components/ui/StateViews.jsx";
import StatusBadge, { ApprovalBadge } from "../components/ui/StatusBadge.jsx";
import JsonBlock from "../components/ui/JsonBlock.jsx";
import StepTimeline from "../components/runs/StepTimeline.jsx";
import { Link, useParams, useNavigate } from "../lib/router.jsx";
import { useAsync } from "../hooks/useAsync.js";
import * as runsService from "../services/runsService.js";
import { ApiError } from "../lib/apiClient.js";
import {
  formatDuration, formatDateTime, formatConfidence, formatNumber,
} from "../lib/format.js";

function Meta({ icon: Icon, label, children }) {
  return (
    <div>
      <div className="field-label" style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
        {Icon && <Icon size={13} aria-hidden="true" />} {label}
      </div>
      <div style={{ fontSize: "0.9rem" }}>{children}</div>
    </div>
  );
}

export default function RunDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const run = useAsync((signal) => runsService.getRun(id, { signal }), [id]);
  const steps = useAsync((signal) => runsService.getRunSteps(id, { signal }), [id]);

  // Distinguish 404 (not found / not yours) from other errors for a clear message.
  if (run.error) {
    const notFound = run.error instanceof ApiError && run.error.status === 404;
    return (
      <>
        <PageHeader
          title={`Run #${id}`}
          actions={<button className="btn btn-sm" onClick={() => navigate("/runs")}><ArrowLeft size={15} /> Back to runs</button>}
        />
        <Card>
          {notFound ? (
            <EmptyState
              icon={Hash}
              title="Run not found"
              message="This run does not exist, or it belongs to another account."
              action={<Link to="/runs" className="btn btn-primary btn-sm">Back to runs</Link>}
            />
          ) : (
            <ErrorState error={run.error} onRetry={run.reload} />
          )}
        </Card>
      </>
    );
  }

  const d = run.data;

  return (
    <>
      <PageHeader
        title={
          <span style={{ display: "inline-flex", alignItems: "center", gap: "0.6rem" }}>
            <span className="mono">Run #{id}</span>
            {d && <StatusBadge status={d.status} />}
          </span>
        }
        actions={<button className="btn btn-sm" onClick={() => navigate("/runs")}><ArrowLeft size={15} /> Back to runs</button>}
      />

      {run.loading ? (
        <Card><LoadingBlock rows={4} height={40} /></Card>
      ) : (
        <>
          {/* Query + metadata */}
          <Card title="Overview">
            <div style={{ marginBottom: "1.25rem" }}>
              <div className="field-label">User query</div>
              <p style={{ margin: 0, fontSize: "1rem", lineHeight: 1.5 }}>{d.user_query}</p>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(170px, 1fr))", gap: "1rem" }}>
              <Meta icon={Hash} label="Session">
                <span className="mono muted" title={d.session_id}>{d.session_id}</span>
              </Meta>
              <Meta icon={Clock} label="Created">{formatDateTime(d.created_at)}</Meta>
              <Meta icon={Clock} label="Started">{formatDateTime(d.started_at)}</Meta>
              <Meta icon={Clock} label="Completed">{formatDateTime(d.completed_at)}</Meta>
              <Meta icon={Clock} label="Duration">{formatDuration(d.execution_duration_ms)}</Meta>
              <Meta icon={GitBranch} label="Execution mode">{d.execution_mode || "—"}</Meta>
              <Meta icon={Cpu} label="LLM model">{d.llm_model || "—"}</Meta>
              <Meta icon={Cpu} label="Confidence">{formatConfidence(d.confidence)}</Meta>
              <Meta label="Approval"><ApprovalBadge approved={d.approved} /></Meta>
              <Meta icon={Database} label="RAG used">{d.rag_used == null ? "—" : d.rag_used ? "Yes" : "No"}</Meta>
              <Meta icon={Brain} label="Memory used">{d.memory_used == null ? "—" : d.memory_used ? "Yes" : "No"}</Meta>
              <Meta label="Steps">
                {formatNumber(d.steps_total)}
                {d.steps_failed ? <span style={{ color: "var(--danger)" }}> · {d.steps_failed} failed</span> : null}
              </Meta>
              <Meta label="Retries">{formatNumber(d.retry_count)}</Meta>
            </div>
          </Card>

          {/* Final response */}
          {d.final_response && (
            <Card title="Final Response" className="" >
              <div className="prose-block" style={{ whiteSpace: "pre-wrap" }}>{d.final_response}</div>
            </Card>
          )}

          {/* Execution step timeline */}
          <Card title="Execution Timeline" subtitle={steps.data ? `${steps.data.length} step${steps.data.length === 1 ? "" : "s"}` : undefined} padded>
            {steps.error ? (
              <ErrorState error={steps.error} onRetry={steps.reload} />
            ) : steps.loading ? (
              <InlineLoading label="Loading steps…" />
            ) : steps.data && steps.data.length > 0 ? (
              <StepTimeline steps={steps.data} />
            ) : (
              <EmptyState
                title="No recorded steps"
                message="This run has no individual step records. The plan and execution result below still describe what happened."
              />
            )}
          </Card>

          {/* Plan / Execution / Verification */}
          <Card title="Plan, Execution & Verification">
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              <JsonBlock label="Plan" value={d.plan} />
              <JsonBlock label="Execution result" value={d.execution_result} />
              <JsonBlock label="Verification result" value={d.verification_result} defaultOpen={d.approved === false} />
            </div>
          </Card>
        </>
      )}
    </>
  );
}
