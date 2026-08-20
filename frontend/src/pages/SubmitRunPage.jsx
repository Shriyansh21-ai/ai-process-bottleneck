/**
 * Agent task submission (Phase 15). Submits to the existing POST /run endpoint,
 * which executes synchronously server-side and returns the finished run. We show
 * an honest "executing" state while awaiting the response — no fake streaming or
 * fabricated real-time progress — then surface the outcome and a link to the
 * full execution trace.
 */

import { useState, useRef } from "react";
import { PlayCircle, ArrowRight, Sparkles, AlertCircle } from "lucide-react";
import PageHeader from "../components/ui/PageHeader.jsx";
import { Card } from "../components/ui/Card.jsx";
import StatusBadge from "../components/ui/StatusBadge.jsx";
import { Spinner } from "../components/ui/Spinner.jsx";
import { Link } from "../lib/router.jsx";
import * as runsService from "../services/runsService.js";

const EXAMPLES = [
  "Analyze manufacturing bottlenecks in production lines",
  "Predict rework probability for the assembly stage",
  "Recommend resource allocation to reduce waiting time",
];

function newSessionId() {
  try {
    if (crypto?.randomUUID) return `web-${crypto.randomUUID().slice(0, 8)}`;
  } catch {
    /* fall through */
  }
  return `web-${Date.now().toString(36)}`;
}

export default function SubmitRunPage() {
  const [query, setQuery] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const sessionIdRef = useRef(newSessionId());

  const submit = async (e) => {
    e.preventDefault();
    const q = query.trim();
    if (!q || submitting) return;

    setSubmitting(true);
    setError(null);
    setResult(null);
    const sessionId = sessionIdRef.current;

    try {
      const res = await runsService.submitRun(q, sessionId);
      let runId = res && typeof res === "object" ? res.run_id : null;

      // Some terminal branches omit run_id — fall back to the newest run for
      // this (fresh) session so we can still link to the trace.
      if (!runId) {
        try {
          const page = await runsService.listRuns({ session_id: sessionId, page: 1, page_size: 1 });
          runId = page?.items?.[0]?.run_id ?? null;
        } catch {
          /* best-effort */
        }
      }

      setResult({ res, runId });
      // Rotate the session id so the next submission is a fresh conversation.
      sessionIdRef.current = newSessionId();
    } catch (err) {
      setError(err);
    } finally {
      setSubmitting(false);
    }
  };

  const finalText = (() => {
    const r = result?.res;
    if (!r || typeof r !== "object") return null;
    return r.message || r.verification?.summary || r.execution?.goal || null;
  })();

  return (
    <>
      <PageHeader title="Submit Task" description="Run an agent task and inspect the resulting execution trace." />

      <div className="grid-2">
        <Card title="New agent task">
          <form onSubmit={submit}>
            <label className="field-label" htmlFor="task-query">Task</label>
            <textarea
              id="task-query"
              className="textarea"
              rows={5}
              placeholder="Describe the analysis you want the agent to perform…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={submitting}
              style={{ resize: "vertical" }}
            />

            <div style={{ margin: "0.75rem 0" }}>
              <div className="faint" style={{ fontSize: "0.76rem", marginBottom: "0.4rem", display: "flex", alignItems: "center", gap: "0.35rem" }}>
                <Sparkles size={13} /> Examples
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem" }}>
                {EXAMPLES.map((ex) => (
                  <button key={ex} type="button" className="btn btn-sm" onClick={() => setQuery(ex)} disabled={submitting} style={{ fontWeight: 500 }}>
                    {ex}
                  </button>
                ))}
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "1rem", marginTop: "0.5rem" }}>
              <span className="faint mono" style={{ fontSize: "0.72rem" }}>session: {sessionIdRef.current}</span>
              <button type="submit" className="btn btn-primary" disabled={submitting || !query.trim()}>
                {submitting ? <Spinner size={16} /> : <PlayCircle size={16} />}
                {submitting ? "Executing…" : "Run task"}
              </button>
            </div>
          </form>
        </Card>

        <Card title="Result">
          {submitting ? (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "0.75rem", padding: "2rem 1rem", textAlign: "center" }}>
              <Spinner size={26} />
              <div style={{ fontWeight: 600 }}>Agent is working…</div>
              <p className="muted" style={{ margin: 0, fontSize: "0.85rem", maxWidth: 320 }}>
                The task runs to completion on the server. This can take a moment for multi-step plans.
              </p>
            </div>
          ) : error ? (
            <div role="alert" style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
              <div className="badge-danger" style={{ display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.7rem 0.85rem", borderRadius: 9, fontSize: "0.88rem", fontWeight: 500 }}>
                <AlertCircle size={16} aria-hidden="true" />
                {error.status === 429
                  ? "Rate limit reached — please wait a moment before submitting again."
                  : error.message || "The task could not be completed."}
              </div>
            </div>
          ) : result ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
                <StatusBadge status={result.res?.status || "completed"} />
                {result.res?.attempts != null && (
                  <span className="faint" style={{ fontSize: "0.8rem" }}>{result.res.attempts} attempt{result.res.attempts === 1 ? "" : "s"}</span>
                )}
              </div>
              {finalText && (
                <div>
                  <div className="field-label">Summary</div>
                  <div className="prose-block" style={{ whiteSpace: "pre-wrap" }}>{finalText}</div>
                </div>
              )}
              {result.runId ? (
                <Link to={`/runs/${result.runId}`} className="btn btn-primary" style={{ alignSelf: "flex-start" }}>
                  View execution trace <ArrowRight size={15} />
                </Link>
              ) : (
                <Link to="/runs" className="btn btn-sm" style={{ alignSelf: "flex-start" }}>
                  View runs <ArrowRight size={15} />
                </Link>
              )}
            </div>
          ) : (
            <div className="muted" style={{ padding: "2rem 1rem", textAlign: "center", fontSize: "0.9rem" }}>
              Submit a task to see its result and a link to the full trace here.
            </div>
          )}
        </Card>
      </div>
    </>
  );
}
