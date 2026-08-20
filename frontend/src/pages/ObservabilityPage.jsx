/**
 * Observability & failure analytics (Phases 11–12). Consumes the existing
 * admin-only /observability/overview (health + per-tool performance + grouped
 * failures + trends) in a single call, plus a small owner-scoped list of the
 * most recent failed runs for drill-down. All aggregation is server-side.
 */

import { useCallback } from "react";
import {
  Activity, Gauge, ThumbsUp, Layers, RotateCcw, Wrench, AlertTriangle, ArrowRight, ShieldAlert,
} from "lucide-react";
import PageHeader from "../components/ui/PageHeader.jsx";
import { Card, StatCard } from "../components/ui/Card.jsx";
import { ErrorState, EmptyState, LoadingBlock } from "../components/ui/StateViews.jsx";
import RefreshControl from "../components/ui/RefreshControl.jsx";
import BarChart from "../components/charts/BarChart.jsx";
import LineChart from "../components/charts/LineChart.jsx";
import StatusBadge from "../components/ui/StatusBadge.jsx";
import { Link } from "../lib/router.jsx";
import { useAsync } from "../hooks/useAsync.js";
import { usePolling, useRefreshInterval } from "../hooks/usePolling.js";
import { useAuth } from "../auth/AuthContext.jsx";
import { ApiError } from "../lib/apiClient.js";
import * as obs from "../services/observabilityService.js";
import * as runsService from "../services/runsService.js";
import {
  formatDuration, formatPercent, formatConfidence, formatNumber, formatDate, truncate,
} from "../lib/format.js";

function AdminRequired() {
  return (
    <Card>
      <EmptyState
        icon={ShieldAlert}
        title="Administrator access required"
        message="System-wide observability aggregates data across all users, so it is restricted to administrators."
      />
    </Card>
  );
}

export default function ObservabilityPage() {
  const { isAdmin } = useAuth();
  const [interval, setInterval] = useRefreshInterval(60000);

  const overview = useAsync((signal) => obs.getOverview(undefined, { signal }), [], { enabled: isAdmin });
  const recentFailures = useAsync(
    (signal) => runsService.listRuns({ status: "failed", page: 1, page_size: 5, signal }),
    [],
    { enabled: isAdmin }
  );

  const refresh = useCallback(() => {
    overview.reload();
    recentFailures.reload();
  }, [overview, recentFailures]);

  usePolling(refresh, interval);

  if (!isAdmin) {
    return (
      <>
        <PageHeader title="Observability" description="Tool performance and failure analytics across the agent system." />
        <AdminRequired />
      </>
    );
  }

  // A 403 (e.g. admin flag changed) is shown as the admin-required state, not an error.
  if (overview.error instanceof ApiError && overview.error.status === 403) {
    return (
      <>
        <PageHeader title="Observability" />
        <AdminRequired />
      </>
    );
  }

  const data = overview.data;
  const h = data?.health;

  return (
    <>
      <PageHeader
        title="Observability"
        description="Tool performance and failure analytics across the agent system."
        actions={<RefreshControl interval={interval} onIntervalChange={setInterval} onRefresh={refresh} refreshing={overview.loading} />}
      />

      {overview.error ? (
        <Card><ErrorState error={overview.error} onRetry={overview.reload} /></Card>
      ) : overview.loading && !data ? (
        <Card><LoadingBlock rows={4} height={44} /></Card>
      ) : (
        <>
          {/* Health score band */}
          <div className="grid-stats" style={{ marginBottom: "1.25rem" }}>
            <StatCard label="Health Score" value={h ? `${h.health_score}/100` : "—"} icon={Activity}
              tone={h?.health_status === "excellent" || h?.health_status === "healthy" ? "ok" : h?.health_status === "degraded" ? "warn" : h?.health_status === "unhealthy" ? "danger" : "default"}
              hint={h ? h.health_status.replace(/_/g, " ") : undefined} />
            <StatCard label="Success Rate" value={h ? formatPercent(h.success_rate) : "—"} icon={Gauge} tone="ok" />
            <StatCard label="Failure Rate" value={h ? formatPercent(h.failure_rate) : "—"} icon={AlertTriangle} tone="danger" />
            <StatCard label="Approval Rate" value={h ? formatPercent(h.approval_rate) : "—"} icon={ThumbsUp} tone="info" />
            <StatCard label="Avg Duration" value={h ? formatDuration(h.average_duration_ms) : "—"} icon={Activity} />
            <StatCard label="Avg Confidence" value={h ? formatConfidence(h.average_confidence) : "—"} icon={Gauge} />
            <StatCard label="Total Steps" value={h ? formatNumber(h.total_steps) : "—"} icon={Layers} hint={h ? `${formatNumber(h.failed_steps)} failed` : undefined} />
            <StatCard label="Total Retries" value={h ? formatNumber(h.total_retries) : "—"} icon={RotateCcw} tone="warn" />
          </div>

          <div className="grid-2" style={{ marginBottom: "1.25rem" }}>
            {/* Tool usage */}
            <Card title="Most Used Tools" subtitle="Execution count per tool">
              {data?.tools?.length ? (
                <BarChart
                  data={data.tools.slice(0, 8).map((t) => ({ label: t.tool_name, value: t.execution_count }))}
                  valueFormat={formatNumber}
                />
              ) : (
                <EmptyState icon={Wrench} title="No tool activity" message="Tool performance appears once runs execute steps." />
              )}
            </Card>

            {/* Failure reasons */}
            <Card title="Failure Breakdown" subtitle="Grouped failure reasons">
              {data?.failures?.length ? (
                <BarChart
                  data={data.failures.slice(0, 8).map((f) => ({ label: f.failure_type, value: f.count }))}
                  valueFormat={formatNumber}
                  color="var(--danger)"
                  emptyMessage="No failures recorded."
                />
              ) : (
                <EmptyState icon={ThumbsUp} title="No failures recorded" message="Nothing is currently going wrong — no failed steps in this window." />
              )}
            </Card>
          </div>

          {/* Per-tool detail table */}
          <Card title="Tool Performance" subtitle="Success rate, duration and retries per tool" padded={false}>
            {data?.tools?.length ? (
              <div className="table-scroll">
                <table className="tbl">
                  <thead>
                    <tr>
                      <th>Tool</th><th>Executions</th><th>Success</th><th>Failure</th>
                      <th>Success Rate</th><th>Avg Duration</th><th>Retries</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.tools.map((t) => (
                      <tr key={t.tool_name}>
                        <td className="mono" style={{ fontWeight: 600 }}>{t.tool_name}</td>
                        <td className="mono">{formatNumber(t.execution_count)}</td>
                        <td className="mono" style={{ color: "var(--ok)" }}>{formatNumber(t.success_count)}</td>
                        <td className="mono" style={{ color: t.failure_count ? "var(--danger)" : undefined }}>{formatNumber(t.failure_count)}</td>
                        <td className="mono">{formatPercent(t.success_rate)}</td>
                        <td className="mono muted">{formatDuration(t.average_duration_ms)}</td>
                        <td className="mono">{formatNumber(t.total_retries)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div style={{ padding: "1.25rem" }}>
                <EmptyState icon={Wrench} title="No tool data" message="Per-tool analytics will populate as steps are recorded." />
              </div>
            )}
          </Card>

          {/* Trends */}
          <Card title="Execution Trends" subtitle="Daily runs, duration and confidence" className="" >
            {data?.trends?.length ? (
              <LineChart
                labels={data.trends.map((t) => formatDate(t.bucket))}
                series={[
                  { name: "Total", data: data.trends.map((t) => t.total_runs), color: "var(--accent)" },
                  { name: "Successful", data: data.trends.map((t) => t.successful_runs), color: "var(--ok)" },
                  { name: "Failed", data: data.trends.map((t) => t.failed_runs), color: "var(--danger)" },
                ]}
                yFormat={(v) => formatNumber(Math.round(v))}
              />
            ) : (
              <EmptyState title="No trend data" message="Trends appear once runs accumulate over time." />
            )}
          </Card>

          {/* Recent failures drill-down (Phase 12) */}
          <Card title="Recent Failures" subtitle="Jump straight to a failing run" padded={false} className="" >
            {recentFailures.loading ? (
              <div style={{ padding: "1.25rem" }}><LoadingBlock rows={3} height={38} /></div>
            ) : recentFailures.data?.items?.length ? (
              <div className="table-scroll">
                <table className="tbl">
                  <thead><tr><th>Run</th><th>Query</th><th>Status</th><th>When</th><th></th></tr></thead>
                  <tbody>
                    {recentFailures.data.items.map((r) => (
                      <tr key={r.run_id}>
                        <td className="mono" style={{ color: "var(--accent)", fontWeight: 600 }}>#{r.run_id}</td>
                        <td style={{ maxWidth: 320 }}>{truncate(r.user_query, 64)}</td>
                        <td><StatusBadge status={r.status} /></td>
                        <td className="muted" style={{ whiteSpace: "nowrap" }}>{formatDate(r.created_at)}</td>
                        <td><Link to={`/runs/${r.run_id}`} className="btn btn-sm">Inspect <ArrowRight size={13} /></Link></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div style={{ padding: "1.25rem" }}>
                <EmptyState icon={ThumbsUp} title="No recent failures" message="No failed runs to investigate right now." />
              </div>
            )}
          </Card>
        </>
      )}
    </>
  );
}
