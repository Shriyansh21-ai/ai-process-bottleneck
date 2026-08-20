/**
 * Overview dashboard (Phase 5 & 6). All metrics come from existing backend APIs
 * — nothing is computed in the browser:
 *   - /runs/statistics       (owner-scoped, available to every user)
 *   - /observability/health  (richer KPIs; ADMIN only — gracefully skipped)
 *   - /observability/trends  (trend chart; ADMIN only — falls back to a note)
 *   - /runs?page_size=6      (recent activity)
 */

import { useCallback } from "react";
import {
  Activity, CheckCircle2, XCircle, Timer, Gauge, ThumbsUp, Layers, RotateCcw,
} from "lucide-react";
import PageHeader from "../components/ui/PageHeader.jsx";
import { StatCard, Card } from "../components/ui/Card.jsx";
import { ErrorState, EmptyState, LoadingBlock } from "../components/ui/StateViews.jsx";
import RefreshControl from "../components/ui/RefreshControl.jsx";
import RunsTable from "../components/runs/RunsTable.jsx";
import Donut from "../components/charts/Donut.jsx";
import LineChart from "../components/charts/LineChart.jsx";
import { Link } from "../lib/router.jsx";
import { useAsync } from "../hooks/useAsync.js";
import { usePolling, useRefreshInterval } from "../hooks/usePolling.js";
import { useAuth } from "../auth/AuthContext.jsx";
import { ApiError } from "../lib/apiClient.js";
import * as runsService from "../services/runsService.js";
import * as obs from "../services/observabilityService.js";
import { formatDuration, formatPercent, formatConfidence, formatNumber, formatDate } from "../lib/format.js";

export default function OverviewPage() {
  const { isAdmin } = useAuth();
  const [interval, setInterval] = useRefreshInterval(30000);

  const stats = useAsync((signal) => runsService.getStatistics({ signal }), []);
  const recent = useAsync((signal) => runsService.listRuns({ page: 1, page_size: 6, signal }), []);
  // Admin-only richer metrics; members simply don't fetch these.
  const health = useAsync(
    (signal) => obs.getAgentHealth(undefined, { signal }),
    [isAdmin],
    { enabled: isAdmin }
  );
  const trends = useAsync(
    (signal) => obs.getTrends(undefined, { signal }),
    [isAdmin],
    { enabled: isAdmin }
  );

  const refreshAll = useCallback(() => {
    stats.reload();
    recent.reload();
    if (isAdmin) {
      health.reload();
      trends.reload();
    }
  }, [stats, recent, health, trends, isAdmin]);

  usePolling(refreshAll, interval);

  const s = stats.data;
  const h = health.data;

  return (
    <>
      <PageHeader
        title="Overview"
        description="Live health and activity across your agent runs."
        actions={
          <RefreshControl
            interval={interval}
            onIntervalChange={setInterval}
            onRefresh={refreshAll}
            refreshing={stats.loading || recent.loading}
          />
        }
      />

      {/* KPI cards */}
      {stats.error ? (
        <Card><ErrorState error={stats.error} onRetry={stats.reload} /></Card>
      ) : (
        <div className="grid-stats" style={{ marginBottom: "1.25rem" }}>
          <StatCard label="Total Runs" value={formatNumber(s?.total_runs)} icon={Activity} loading={stats.loading} />
          <StatCard label="Successful" value={formatNumber(s?.successful_runs)} icon={CheckCircle2} tone="ok" loading={stats.loading} />
          <StatCard label="Failed" value={formatNumber(s?.failed_runs)} icon={XCircle} tone="danger" loading={stats.loading} />
          <StatCard label="Success Rate" value={formatPercent(s?.success_rate)} icon={Gauge} tone="accent" loading={stats.loading} />
          <StatCard label="Avg Duration" value={s ? formatDuration(s.average_duration_ms) : "—"} icon={Timer} loading={stats.loading} />
          {isAdmin && (
            <>
              <StatCard label="Approval Rate" value={h ? formatPercent(h.approval_rate) : "—"} icon={ThumbsUp} tone="info" loading={health.loading} />
              <StatCard label="Avg Confidence" value={h ? formatConfidence(h.average_confidence) : "—"} icon={Gauge} loading={health.loading} />
              <StatCard label="Total Steps" value={h ? formatNumber(h.total_steps) : "—"} icon={Layers} hint={h ? `${formatNumber(h.failed_steps)} failed` : undefined} loading={health.loading} />
              <StatCard label="Retries" value={h ? formatNumber(h.total_retries) : "—"} icon={RotateCcw} tone="warn" loading={health.loading} />
            </>
          )}
        </div>
      )}

      <div className="grid-2" style={{ marginBottom: "1.25rem" }}>
        {/* Outcome breakdown */}
        <Card title="Run Outcomes">
          {stats.loading ? (
            <LoadingBlock rows={2} height={40} />
          ) : s && s.total_runs > 0 ? (
            <Donut
              centerValue={formatNumber(s.total_runs)}
              centerLabel="runs"
              segments={[
                { label: "Successful", value: s.successful_runs, color: "var(--ok)" },
                { label: "Failed", value: s.failed_runs, color: "var(--danger)" },
                { label: "Running", value: s.running_runs, color: "var(--info)" },
                { label: "Pending", value: s.pending_runs, color: "var(--warn)" },
                { label: "Other", value: s.other_runs, color: "var(--neutral)" },
              ].filter((seg) => seg.value > 0)}
            />
          ) : (
            <EmptyState title="No runs yet" message="Submit your first agent task to see outcomes here." action={<Link to="/run" className="btn btn-primary btn-sm">Submit a task</Link>} />
          )}
        </Card>

        {/* Trend chart (admin) */}
        <Card title="Runs Over Time" subtitle={isAdmin ? "Daily execution volume" : undefined}>
          {!isAdmin ? (
            <EmptyState title="Trends are admin-only" message="Execution trend analytics are available to administrators." />
          ) : trends.error ? (
            trends.error instanceof ApiError && trends.error.status === 403 ? (
              <EmptyState title="Trends are admin-only" message="Execution trend analytics require administrator access." />
            ) : (
              <ErrorState error={trends.error} onRetry={trends.reload} />
            )
          ) : trends.loading ? (
            <LoadingBlock rows={2} height={50} />
          ) : trends.data && trends.data.length > 0 ? (
            <LineChart
              labels={trends.data.map((t) => formatDate(t.bucket))}
              series={[
                { name: "Total", data: trends.data.map((t) => t.total_runs), color: "var(--accent)" },
                { name: "Successful", data: trends.data.map((t) => t.successful_runs), color: "var(--ok)" },
                { name: "Failed", data: trends.data.map((t) => t.failed_runs), color: "var(--danger)" },
              ]}
              yFormat={(v) => formatNumber(Math.round(v))}
              ariaLabel="Daily total, successful and failed run counts over time"
            />
          ) : (
            <EmptyState title="No trend data" message="Trend data appears once runs accumulate over multiple days." />
          )}
        </Card>
      </div>

      {/* Recent runs */}
      <Card title="Recent Runs" actions={<Link to="/runs" className="btn btn-sm">View all</Link>} padded={false}>
        {recent.error ? (
          <div style={{ padding: "1rem" }}><ErrorState error={recent.error} onRetry={recent.reload} /></div>
        ) : recent.loading ? (
          <div style={{ padding: "1.25rem" }}><LoadingBlock rows={4} height={40} /></div>
        ) : recent.data && recent.data.items.length > 0 ? (
          <RunsTable runs={recent.data.items} compact />
        ) : (
          <EmptyState title="No runs yet" message="Runs you submit will appear here." action={<Link to="/run" className="btn btn-primary btn-sm">Submit a task</Link>} />
        )}
      </Card>
    </>
  );
}
