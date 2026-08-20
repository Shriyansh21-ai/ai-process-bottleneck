/**
 * Shared Loading / Empty / Error presentational blocks so every page renders the
 * four required states consistently (Phase 17) instead of blank screens.
 */

import { Inbox, AlertCircle, RefreshCw, ShieldAlert } from "lucide-react";
import { Spinner } from "./Spinner.jsx";
import { ApiError } from "../../lib/apiClient.js";

export function EmptyState({ icon: Icon = Inbox, title, message, action }) {
  return (
    <div
      style={{
        textAlign: "center",
        padding: "3rem 1.5rem",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: "0.5rem",
      }}
    >
      <Icon size={40} className="faint" aria-hidden="true" />
      <h3 style={{ margin: "0.25rem 0 0", fontSize: "1rem", fontWeight: 600 }}>
        {title}
      </h3>
      {message && (
        <p className="muted" style={{ margin: 0, maxWidth: 420, fontSize: "0.9rem" }}>
          {message}
        </p>
      )}
      {action && <div style={{ marginTop: "0.75rem" }}>{action}</div>}
    </div>
  );
}

/**
 * Error block that maps common statuses to a friendly message and, for 403,
 * shows an admin-required variant. Never renders raw stack traces.
 */
export function ErrorState({ error, onRetry, title }) {
  const status = error instanceof ApiError ? error.status : null;
  const isForbidden = status === 403;
  const Icon = isForbidden ? ShieldAlert : AlertCircle;
  const heading =
    title || (isForbidden ? "Access restricted" : "Something went wrong");
  const message =
    error?.message || "An unexpected error occurred. Please try again.";

  return (
    <div
      role="alert"
      style={{
        textAlign: "center",
        padding: "2.5rem 1.5rem",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: "0.6rem",
      }}
    >
      <Icon size={38} style={{ color: isForbidden ? "var(--warn)" : "var(--danger)" }} aria-hidden="true" />
      <h3 style={{ margin: 0, fontSize: "1rem", fontWeight: 600 }}>{heading}</h3>
      <p className="muted" style={{ margin: 0, maxWidth: 460, fontSize: "0.9rem" }}>
        {message}
      </p>
      {onRetry && !isForbidden && (
        <button className="btn btn-sm" onClick={onRetry} style={{ marginTop: "0.5rem" }}>
          <RefreshCw size={14} /> Retry
        </button>
      )}
    </div>
  );
}

/** Loading placeholder rows/blocks using the shimmer skeleton. */
export function LoadingBlock({ rows = 3, height = 56 }) {
  return (
    <div
      role="status"
      aria-live="polite"
      aria-busy="true"
      style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}
    >
      <span className="sr-only" style={{ position: "absolute", left: -9999 }}>
        Loading
      </span>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skeleton" style={{ height }} />
      ))}
    </div>
  );
}

export function InlineLoading({ label = "Loading…" }) {
  return (
    <div
      role="status"
      aria-live="polite"
      style={{ display: "flex", alignItems: "center", gap: "0.5rem", padding: "1.5rem" }}
    >
      <Spinner size={16} />
      <span className="muted" style={{ fontSize: "0.875rem" }}>
        {label}
      </span>
    </div>
  );
}
