/**
 * Dependency-free donut chart (SVG) for outcome splits (e.g. success vs failure).
 * Renders a legend with explicit labels + values so it is readable without color
 * perception. Empty/zero-total shows a neutral ring, not a broken chart.
 */

const PALETTE = ["var(--ok)", "var(--danger)", "var(--info)", "var(--warn)", "var(--neutral)"];

export default function Donut({ segments = [], size = 160, thickness = 20, centerLabel, centerValue }) {
  const total = segments.reduce((s, seg) => s + (seg.value || 0), 0);
  const r = (size - thickness) / 2;
  const c = size / 2;
  const circ = 2 * Math.PI * r;

  let offset = 0;
  const arcs = total > 0
    ? segments.map((seg, i) => {
        const frac = seg.value / total;
        const dash = frac * circ;
        const arc = {
          color: seg.color || PALETTE[i % PALETTE.length],
          dashArray: `${dash} ${circ - dash}`,
          dashOffset: -offset,
        };
        offset += dash;
        return arc;
      })
    : [];

  return (
    <div style={{ display: "flex", gap: "1.25rem", alignItems: "center", flexWrap: "wrap" }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img" aria-label={`Donut chart, total ${total}`}>
        <circle cx={c} cy={c} r={r} fill="none" stroke="var(--surface-2)" strokeWidth={thickness} />
        {arcs.map((a, i) => (
          <circle
            key={i}
            cx={c}
            cy={c}
            r={r}
            fill="none"
            stroke={a.color}
            strokeWidth={thickness}
            strokeDasharray={a.dashArray}
            strokeDashoffset={a.dashOffset}
            transform={`rotate(-90 ${c} ${c})`}
            strokeLinecap="butt"
          />
        ))}
        {(centerValue !== undefined || centerLabel) && (
          <g>
            <text x={c} y={c - 2} textAnchor="middle" fontSize="22" fontWeight="700" fill="var(--text)">
              {centerValue}
            </text>
            <text x={c} y={c + 16} textAnchor="middle" fontSize="10" fill="var(--text-faint)">
              {centerLabel}
            </text>
          </g>
        )}
      </svg>
      <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: "0.5rem" }}>
        {segments.map((seg, i) => (
          <li key={seg.label} style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.85rem" }}>
            <span className="dot" style={{ background: seg.color || PALETTE[i % PALETTE.length] }} />
            <span>{seg.label}</span>
            <strong style={{ marginLeft: "auto" }}>{seg.value}</strong>
            <span className="faint" style={{ minWidth: 42, textAlign: "right" }}>
              {total > 0 ? `${Math.round((seg.value / total) * 100)}%` : "0%"}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
