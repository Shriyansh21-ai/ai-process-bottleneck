/**
 * Dependency-free horizontal bar chart (SVG-less; uses flex bars) for ranked
 * categorical data such as per-tool execution counts or failure reasons.
 * Accessible: each row has a text label and a numeric value; bar length is a
 * secondary encoding, never the only signal.
 */

export default function BarChart({ data = [], valueFormat = (v) => String(v), color = "var(--accent)", emptyMessage = "No data available." }) {
  if (!data.length) {
    return (
      <div className="muted" style={{ padding: "1.5rem", textAlign: "center", fontSize: "0.9rem" }}>
        {emptyMessage}
      </div>
    );
  }
  const max = Math.max(...data.map((d) => d.value), 1);

  return (
    <div role="list" style={{ display: "flex", flexDirection: "column", gap: "0.7rem" }}>
      {data.map((d) => {
        const pct = (d.value / max) * 100;
        return (
          <div role="listitem" key={d.label} title={`${d.label}: ${valueFormat(d.value)}`}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.82rem", marginBottom: "0.25rem", gap: "0.75rem" }}>
              <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{d.label}</span>
              <span className="muted mono" style={{ flex: "none" }}>{valueFormat(d.value)}</span>
            </div>
            <div style={{ height: 8, background: "var(--surface-2)", borderRadius: 999, overflow: "hidden" }}>
              <div
                style={{
                  width: `${Math.max(2, pct)}%`,
                  height: "100%",
                  background: d.color || color,
                  borderRadius: 999,
                  transition: "width 0.4s ease",
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
