/**
 * System Health (Phase 13). Reports ONLY dependencies the backend actually
 * exposes — liveness (/health), and DB + configuration readiness (/health/ready),
 * plus agent-execution health from /observability/health for admins. We never
 * claim a dependency (e.g. RAG/LLM) is healthy when the backend does not report
 * it; such components are shown as "Unknown — not reported".
 */

import { useCallback } from "react";
import {
  Server, Database, Settings2, Bot, CheckCircle2, XCircle, AlertTriangle, HelpCircle,
} from "lucide-react";
import PageHeader from "../components/ui/PageHeader.jsx";
import { Card } from "../components/ui/Card.jsx";
import { LoadingBlock } from "../components/ui/StateViews.jsx";
import RefreshControl from "../components/ui/RefreshControl.jsx";
import { useAsync } from "../hooks/useAsync.js";
import { usePolling, useRefreshInterval } from "../hooks/usePolling.js";
import { useAuth } from "../auth/AuthContext.jsx";
import { ApiError } from "../lib/apiClient.js";
import * as health from "../services/healthService.js";
import * as obs from "../services/observabilityService.js";

// state -> presentation. Never color-only: each has an icon + text label.
const STATE_META = {
  healthy: { label: "Healthy", cls: "badge-ok", Icon: CheckCircle2, dot: "var(--ok)" },
  degraded: { label: "Degraded", cls: "badge-warn", Icon: AlertTriangle, dot: "var(--warn)" },
  unavailable: { label: "Unavailable", cls: "badge-danger", Icon: XCircle, dot: "var(--danger)" },
  unknown: { label: "Unknown", cls: "badge-neutral", Icon: HelpCircle, dot: "var(--neutral)" },
};

function HealthItem({ icon: Icon, name, state, detail }) {
  const meta = STATE_META[state] || STATE_META.unknown;
  const Badge = meta.Icon;
  return (
    <div className="card" style={{ padding: "1rem 1.15rem", display: "flex", alignItems: "center", gap: "0.9rem" }}>
      <div style={{ width: 38, height: 38, borderRadius: 9, flex: "none", display: "grid", placeItems: "center", background: "var(--surface-2)", border: "1px solid var(--border)" }}>
        <Icon size={19} className="muted" aria-hidden="true" />
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 600, fontSize: "0.92rem" }}>{name}</div>
        {detail && <div className="faint" style={{ fontSize: "0.76rem" }}>{detail}</div>}
      </div>
      <span className={`badge ${meta.cls}`}>
        <Badge size={12} aria-hidden="true" /> {meta.label}
      </span>
    </div>
  );
}

export default function HealthPage() {
  const { isAdmin } = useAuth();
  const [interval, setInterval] = useRefreshInterval(30000);

  const liveness = useAsync((signal) => health.getHealth({ signal }), []);
  const readiness = useAsync((signal) => health.getReadiness({ signal }), []);
  const agentHealth = useAsync((signal) => obs.getAgentHealth(undefined, { signal }), [], { enabled: isAdmin });

  const refresh = useCallback(() => {
    liveness.reload();
    readiness.reload();
    if (isAdmin) agentHealth.reload();
  }, [liveness, readiness, agentHealth, isAdmin]);

  usePolling(refresh, interval);

  // Derive component states strictly from backend responses.
  const apiState = liveness.loading ? null : liveness.error ? "unavailable" : "healthy";

  const checks = readiness.data?.body?.checks || {};
  const dbState = readiness.loading
    ? null
    : readiness.error
    ? "unknown"
    : checks.database === "available"
    ? "healthy"
    : checks.database === "unavailable"
    ? "unavailable"
    : "unknown";
  const configState = readiness.loading
    ? null
    : readiness.error
    ? "unknown"
    : checks.configuration === "ok"
    ? "healthy"
    : checks.configuration === "incomplete"
    ? "degraded"
    : "unknown";

  const agentState = !isAdmin
    ? "unknown"
    : agentHealth.loading
    ? null
    : agentHealth.error instanceof ApiError && agentHealth.error.status === 403
    ? "unknown"
    : agentHealth.error
    ? "unknown"
    : (() => {
        const s = agentHealth.data?.health_status;
        if (s === "healthy" || s === "excellent") return "healthy";
        if (s === "degraded") return "degraded";
        if (s === "unhealthy") return "unavailable";
        return "unknown"; // no_data
      })();

  const ready = readiness.data?.ready;

  return (
    <>
      <PageHeader
        title="System Health"
        description="Live status of the backend dependencies the API reports on."
        actions={<RefreshControl interval={interval} onIntervalChange={setInterval} onRefresh={refresh} refreshing={liveness.loading || readiness.loading} />}
      />

      {/* Overall readiness banner */}
      <div
        className="card"
        style={{
          padding: "1rem 1.25rem", marginBottom: "1.25rem", display: "flex", alignItems: "center", gap: "0.75rem",
          borderLeft: `4px solid ${ready ? "var(--ok)" : readiness.loading ? "var(--neutral)" : "var(--danger)"}`,
        }}
      >
        {readiness.loading ? (
          <span className="muted">Checking readiness…</span>
        ) : ready ? (
          <>
            <CheckCircle2 size={20} style={{ color: "var(--ok)" }} aria-hidden="true" />
            <div>
              <div style={{ fontWeight: 600 }}>System ready</div>
              <div className="faint" style={{ fontSize: "0.8rem" }}>All critical dependencies are available.</div>
            </div>
          </>
        ) : (
          <>
            <XCircle size={20} style={{ color: "var(--danger)" }} aria-hidden="true" />
            <div>
              <div style={{ fontWeight: 600 }}>Not ready</div>
              <div className="faint" style={{ fontSize: "0.8rem" }}>A critical dependency is unavailable (readiness returned 503).</div>
            </div>
          </>
        )}
      </div>

      {liveness.loading && readiness.loading ? (
        <Card><LoadingBlock rows={4} height={56} /></Card>
      ) : (
        <div className="grid-2">
          <HealthItem icon={Server} name="API" state={apiState} detail={liveness.data?.message || "Liveness probe /health"} />
          <HealthItem icon={Database} name="Database" state={dbState} detail="Readiness probe /health/ready" />
          <HealthItem icon={Settings2} name="Configuration" state={configState} detail={configState === "degraded" ? "Required configuration incomplete" : "Required configuration present"} />
          <HealthItem
            icon={Bot}
            name="Agent Execution"
            state={agentState}
            detail={
              !isAdmin
                ? "Reported to administrators only"
                : agentHealth.data
                ? `Health score ${agentHealth.data.health_score}/100`
                : "From /observability/health"
            }
          />
        </div>
      )}

      <p className="faint" style={{ fontSize: "0.78rem", marginTop: "1rem" }}>
        Only dependencies the backend explicitly reports are shown. Components such as RAG or the
        LLM provider are not surfaced here because the backend does not expose a health signal for
        them — the dashboard never claims a dependency is healthy without backend confirmation.
      </p>
    </>
  );
}
