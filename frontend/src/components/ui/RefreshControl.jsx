import { RefreshCw } from "lucide-react";
import { REFRESH_INTERVALS } from "../../hooks/usePolling.js";

/**
 * Manual refresh button + configurable auto-refresh interval selector (Phase 14).
 * Controlled polling only — no aggressive defaults, and "Off" is always available.
 */
export default function RefreshControl({ interval, onIntervalChange, onRefresh, refreshing }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
      <label className="muted" style={{ fontSize: "0.78rem" }} htmlFor="refresh-interval">
        Auto
      </label>
      <select
        id="refresh-interval"
        className="select"
        style={{ width: "auto", padding: "0.35rem 0.5rem", fontSize: "0.8rem" }}
        value={interval}
        onChange={(e) => onIntervalChange(Number(e.target.value))}
      >
        {REFRESH_INTERVALS.map((r) => (
          <option key={r.value} value={r.value}>
            {r.label}
          </option>
        ))}
      </select>
      <button className="btn btn-sm" onClick={onRefresh} disabled={refreshing} aria-label="Refresh now">
        <RefreshCw size={14} className={refreshing ? "spin" : ""} />
        Refresh
      </button>
    </div>
  );
}
