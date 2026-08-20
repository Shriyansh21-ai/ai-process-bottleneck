/**
 * Dependency-free responsive line chart (SVG).
 *
 * Handles all required edge cases (Phase 6): empty data (renders a message),
 * a single data point (renders a dot), and large series (points thin out, line
 * still draws). Accessible: role=img with an aria-label summary, plus a hover
 * guide with a readable tooltip. Colors use theme tokens, not hard-coded hues,
 * and each series is labelled so meaning never depends on color alone.
 */

import { useState, useId } from "react";

const PALETTE = ["var(--accent)", "var(--ok)", "var(--warn)", "var(--info)"];

export default function LineChart({
  labels = [],
  series = [],
  height = 220,
  yFormat = (v) => String(v),
  ariaLabel,
}) {
  const [hover, setHover] = useState(null);
  const clipId = useId();

  const n = labels.length;
  if (n === 0 || series.length === 0) {
    return (
      <div className="muted" style={{ padding: "2rem", textAlign: "center", fontSize: "0.9rem" }}>
        No data available for this period.
      </div>
    );
  }

  // Geometry in a fixed viewBox; SVG scales to container width.
  const W = 640;
  const H = height;
  const pad = { top: 16, right: 16, bottom: 30, left: 44 };
  const innerW = W - pad.left - pad.right;
  const innerH = H - pad.top - pad.bottom;

  const allValues = series.flatMap((s) => s.data.filter((v) => v != null));
  const rawMax = allValues.length ? Math.max(...allValues) : 0;
  const maxY = rawMax <= 0 ? 1 : rawMax * 1.1;

  const x = (i) => (n === 1 ? pad.left + innerW / 2 : pad.left + (i / (n - 1)) * innerW);
  const y = (v) => pad.top + innerH - (Math.max(0, v) / maxY) * innerH;

  const yTicks = 4;
  const gridLines = Array.from({ length: yTicks + 1 }, (_, i) => {
    const val = (maxY / yTicks) * i;
    return { val, yPos: y(val) };
  });

  // Show at most ~8 x labels to avoid crowding on large datasets.
  const labelStep = Math.max(1, Math.ceil(n / 8));

  const summary =
    ariaLabel ||
    `Line chart of ${series.map((s) => s.name).join(", ")} across ${n} points.`;

  const onMove = (e) => {
    const svg = e.currentTarget;
    const rect = svg.getBoundingClientRect();
    const px = ((e.clientX - rect.left) / rect.width) * W;
    if (n === 1) return setHover(0);
    const i = Math.round(((px - pad.left) / innerW) * (n - 1));
    setHover(Math.max(0, Math.min(n - 1, i)));
  };

  return (
    <div style={{ width: "100%" }}>
      <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", marginBottom: "0.5rem" }}>
        {series.map((s, si) => (
          <span key={s.name} style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem", fontSize: "0.8rem" }}>
            <span className="dot" style={{ background: s.color || PALETTE[si % PALETTE.length] }} />
            <span className="muted">{s.name}</span>
          </span>
        ))}
      </div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        width="100%"
        height={H}
        role="img"
        aria-label={summary}
        preserveAspectRatio="xMidYMid meet"
        onMouseMove={onMove}
        onMouseLeave={() => setHover(null)}
        style={{ display: "block" }}
      >
        <defs>
          <clipPath id={clipId}>
            <rect x={pad.left} y={pad.top} width={innerW} height={innerH} />
          </clipPath>
        </defs>

        {/* gridlines + y labels */}
        {gridLines.map((g, i) => (
          <g key={i}>
            <line x1={pad.left} x2={W - pad.right} y1={g.yPos} y2={g.yPos} stroke="var(--border)" strokeWidth="1" />
            <text x={pad.left - 8} y={g.yPos + 4} textAnchor="end" fontSize="10" fill="var(--text-faint)">
              {yFormat(g.val)}
            </text>
          </g>
        ))}

        {/* x labels */}
        {labels.map((lb, i) =>
          i % labelStep === 0 || i === n - 1 ? (
            <text key={i} x={x(i)} y={H - 10} textAnchor="middle" fontSize="10" fill="var(--text-faint)">
              {lb}
            </text>
          ) : null
        )}

        {/* series */}
        <g clipPath={`url(#${clipId})`}>
          {series.map((s, si) => {
            const color = s.color || PALETTE[si % PALETTE.length];
            const pts = s.data.map((v, i) => (v == null ? null : [x(i), y(v)])).filter(Boolean);
            if (pts.length === 0) return null;
            if (pts.length === 1) {
              return <circle key={s.name} cx={pts[0][0]} cy={pts[0][1]} r="4" fill={color} />;
            }
            const d = pts.map((p, i) => `${i === 0 ? "M" : "L"}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" ");
            return <path key={s.name} d={d} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" />;
          })}
        </g>

        {/* hover guide */}
        {hover != null && (
          <g>
            <line x1={x(hover)} x2={x(hover)} y1={pad.top} y2={pad.top + innerH} stroke="var(--border-strong)" strokeDasharray="3 3" />
            {series.map((s, si) => {
              const v = s.data[hover];
              if (v == null) return null;
              return (
                <circle
                  key={s.name}
                  cx={x(hover)}
                  cy={y(v)}
                  r="3.5"
                  fill={s.color || PALETTE[si % PALETTE.length]}
                  stroke="var(--surface)"
                  strokeWidth="1.5"
                />
              );
            })}
          </g>
        )}
      </svg>

      {hover != null && (
        <div className="card-2" style={{ marginTop: "0.5rem", padding: "0.5rem 0.75rem", fontSize: "0.8rem" }}>
          <strong>{labels[hover]}</strong>
          {series.map((s) => (
            <span key={s.name} style={{ marginLeft: "0.75rem" }} className="muted">
              {s.name}: <strong style={{ color: "var(--text)" }}>{s.data[hover] == null ? "—" : yFormat(s.data[hover])}</strong>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
