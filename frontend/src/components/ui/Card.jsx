import { Spinner } from "./Spinner.jsx";

export function Card({ title, subtitle, actions, children, className = "", padded = true }) {
  return (
    <section className={`card ${className}`}>
      {(title || actions) && (
        <header
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "1rem",
            padding: "1rem 1.25rem",
            borderBottom: "1px solid var(--border)",
          }}
        >
          <div>
            {title && (
              <h2 style={{ margin: 0, fontSize: "0.95rem", fontWeight: 600 }}>{title}</h2>
            )}
            {subtitle && (
              <p className="muted" style={{ margin: "0.15rem 0 0", fontSize: "0.8rem" }}>
                {subtitle}
              </p>
            )}
          </div>
          {actions && <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>{actions}</div>}
        </header>
      )}
      <div style={padded ? { padding: "1.25rem" } : undefined}>{children}</div>
    </section>
  );
}

/**
 * KPI tile for the overview dashboard. `tone` tints the value; `hint` is a small
 * caption. Values come pre-computed from the backend — no math here.
 */
export function StatCard({ label, value, icon: Icon, tone = "default", hint, loading }) {
  const toneColor = {
    default: "var(--text)",
    ok: "var(--ok)",
    danger: "var(--danger)",
    warn: "var(--warn)",
    info: "var(--info)",
    accent: "var(--accent)",
  }[tone];

  return (
    <div className="card" style={{ padding: "1.1rem 1.25rem" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span
          className="muted"
          style={{ fontSize: "0.78rem", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.03em" }}
        >
          {label}
        </span>
        {Icon && <Icon size={18} className="faint" aria-hidden="true" />}
      </div>
      <div style={{ marginTop: "0.6rem", minHeight: 34, display: "flex", alignItems: "center" }}>
        {loading ? (
          <Spinner size={18} />
        ) : (
          <span style={{ fontSize: "1.7rem", fontWeight: 700, lineHeight: 1, color: toneColor }}>
            {value}
          </span>
        )}
      </div>
      {hint && (
        <div className="faint" style={{ marginTop: "0.35rem", fontSize: "0.76rem" }}>
          {hint}
        </div>
      )}
    </div>
  );
}
