/**
 * Reusable, responsive runs table. Rows are keyboard-accessible links to the
 * run detail page. Wide content scrolls horizontally inside its own container so
 * the page body never scrolls sideways (Phase 18). Data is always a single
 * server page — never a client-side slice of everything (Phase 23).
 */

import { useNavigate } from "../../lib/router.jsx";
import StatusBadge, { ApprovalBadge } from "../ui/StatusBadge.jsx";
import { formatDuration, formatDateTime, formatConfidence, truncate } from "../../lib/format.js";

export default function RunsTable({ runs, compact = false }) {
  const navigate = useNavigate();
  const go = (id) => navigate(`/runs/${id}`);

  return (
    <div className="table-scroll">
      <table className="tbl">
        <thead>
          <tr>
            <th>Run</th>
            <th>Query</th>
            <th>Status</th>
            {!compact && <th>Created</th>}
            <th>Duration</th>
            {!compact && <th>Steps</th>}
            {!compact && <th>Retries</th>}
            <th>Confidence</th>
            {!compact && <th>Approved</th>}
          </tr>
        </thead>
        <tbody>
          {runs.map((r) => (
            <tr
              key={r.run_id}
              className="clickable"
              tabIndex={0}
              role="link"
              aria-label={`Open run ${r.run_id}`}
              onClick={() => go(r.run_id)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  go(r.run_id);
                }
              }}
            >
              <td className="mono" style={{ color: "var(--accent)", fontWeight: 600 }}>#{r.run_id}</td>
              <td style={{ maxWidth: compact ? 240 : 360 }}>
                <span title={r.user_query}>{truncate(r.user_query, compact ? 46 : 70)}</span>
              </td>
              <td><StatusBadge status={r.status} /></td>
              {!compact && <td className="muted" style={{ whiteSpace: "nowrap" }}>{formatDateTime(r.created_at)}</td>}
              <td className="mono muted">{formatDuration(r.execution_duration_ms)}</td>
              {!compact && <td className="mono">{r.steps_total ?? "—"}</td>}
              {!compact && <td className="mono">{r.retry_count ?? "—"}</td>}
              <td className="mono">{formatConfidence(r.confidence)}</td>
              {!compact && <td><ApprovalBadge approved={r.approved} /></td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
