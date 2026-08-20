import { Brain } from "lucide-react";

/** Centered, branded frame shared by the login and registration screens. */
export default function AuthShell({ title, subtitle, children, footer }) {
  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "1.5rem",
        background:
          "radial-gradient(1200px 600px at 50% -10%, color-mix(in srgb, var(--accent) 12%, transparent), transparent), var(--bg)",
      }}
    >
      <div style={{ width: "100%", maxWidth: 420 }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", justifyContent: "center", marginBottom: "1.25rem" }}>
          <div
            style={{
              width: 38, height: 38, borderRadius: 10, display: "grid", placeItems: "center",
              background: "color-mix(in srgb, var(--accent) 18%, transparent)", color: "var(--accent)",
            }}
          >
            <Brain size={22} />
          </div>
          <div style={{ fontWeight: 700, fontSize: "1.05rem" }}>Agent Operations</div>
        </div>

        <div className="card" style={{ padding: "1.75rem" }}>
          <h1 style={{ margin: 0, fontSize: "1.25rem", fontWeight: 700 }}>{title}</h1>
          {subtitle && (
            <p className="muted" style={{ margin: "0.35rem 0 1.25rem", fontSize: "0.9rem" }}>
              {subtitle}
            </p>
          )}
          {children}
        </div>

        {footer && (
          <p className="muted" style={{ textAlign: "center", marginTop: "1rem", fontSize: "0.88rem" }}>
            {footer}
          </p>
        )}
      </div>
    </div>
  );
}
