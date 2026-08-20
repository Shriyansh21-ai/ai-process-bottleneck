/**
 * Presentation helpers — formatting only, no business logic. All aggregate
 * metrics come from the backend; these functions just render values.
 */

/** Format a millisecond duration into a compact human string. */
export function formatDuration(ms) {
  if (ms === null || ms === undefined || Number.isNaN(ms)) return "—";
  if (ms < 1000) return `${Math.round(ms)} ms`;
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(s < 10 ? 2 : 1)} s`;
  const m = Math.floor(s / 60);
  const rem = Math.round(s % 60);
  return `${m}m ${rem}s`;
}

/** Format an ISO timestamp as a readable local date-time. */
export function formatDateTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Short date (no time). */
export function formatDate(value) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString(undefined, {
    month: "short",
    day: "2-digit",
  });
}

/** Relative "time ago" for recent timestamps. */
export function timeAgo(value) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  const diff = Date.now() - d.getTime();
  const sec = Math.round(diff / 1000);
  if (sec < 60) return "just now";
  const min = Math.round(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.round(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const day = Math.round(hr / 24);
  if (day < 30) return `${day}d ago`;
  return formatDate(value);
}

/** Percentage value already in 0–100 from the backend. */
export function formatPercent(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${Number(value).toFixed(digits)}%`;
}

/** Confidence is stored 0–1; show as a percentage. */
export function formatConfidence(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${Math.round(Number(value) * 100)}%`;
}

/** Plain integer with thousands separators; em dash for null. */
export function formatNumber(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return Number(value).toLocaleString();
}

/** Truncate a string for table cells / summaries. */
export function truncate(text, max = 80) {
  if (!text) return "";
  const s = String(text);
  return s.length > max ? s.slice(0, max) + "…" : s;
}

/**
 * Map a run/step status string to a semantic tone used by StatusBadge.
 * Never color-only: the label text is always shown alongside.
 */
export function statusTone(status) {
  if (!status) return "neutral";
  const s = String(status).toLowerCase();
  if (["success", "completed", "passed", "ready", "healthy", "ok", "available", "excellent"].includes(s))
    return "ok";
  if (["failed", "planning_failed", "execution_failed", "error", "unavailable", "not_ready", "unhealthy"].includes(s))
    return "danger";
  if (["running", "pending", "in_progress"].includes(s)) return "info";
  if (["approval_required", "degraded", "warn", "warning", "incomplete", "unknown"].includes(s))
    return "warn";
  return "neutral";
}

/** Human label for a status (title-cased, underscores → spaces). */
export function statusLabel(status) {
  if (!status) return "Unknown";
  return String(status)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
