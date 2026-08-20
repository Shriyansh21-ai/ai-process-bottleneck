import { Loader2 } from "lucide-react";

export function Spinner({ size = 18, className = "" }) {
  return (
    <Loader2
      size={size}
      className={`spin ${className}`}
      style={{ color: "var(--accent)" }}
      aria-hidden="true"
    />
  );
}

export function FullPageSpinner({ label = "Loading…" }) {
  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        minHeight: "60vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: "0.75rem",
      }}
    >
      <Spinner size={28} />
      <span className="muted" style={{ fontSize: "0.9rem" }}>
        {label}
      </span>
    </div>
  );
}
