/**
 * Severity pill for an inspection finding (MRPL Phase 4).
 *
 * Maps the backend Severity enum (LOW/MEDIUM/HIGH/CRITICAL) to a themed,
 * icon+text badge so severity is understandable at a glance and never
 * color-only (accessibility). Uses the existing design-system CSS variables.
 */

import { AlertTriangle, AlertOctagon, Info, Circle } from "lucide-react";

const META = {
  CRITICAL: { color: "var(--danger)", Icon: AlertOctagon, filled: true },
  HIGH: { color: "var(--danger)", Icon: AlertTriangle, filled: false },
  MEDIUM: { color: "var(--warn)", Icon: AlertTriangle, filled: false },
  LOW: { color: "var(--info)", Icon: Info, filled: false },
};

export default function SeverityBadge({ severity }) {
  const key = String(severity || "").toUpperCase();
  const m = META[key] || { color: "var(--neutral)", Icon: Circle, filled: false };

  const style = m.filled
    ? { background: m.color, color: "#fff", borderColor: m.color }
    : {
        background: `color-mix(in srgb, ${m.color} 14%, transparent)`,
        color: m.color,
        borderColor: `color-mix(in srgb, ${m.color} 35%, transparent)`,
      };

  return (
    <span className="badge" style={style}>
      <m.Icon size={12} aria-hidden="true" />
      {key || "UNKNOWN"}
    </span>
  );
}

/** Severity accent color (for card borders etc.). */
export function severityColor(severity) {
  return (META[String(severity || "").toUpperCase()] || { color: "var(--neutral)" }).color;
}
