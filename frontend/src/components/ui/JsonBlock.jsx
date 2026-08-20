import { useMemo, useState } from "react";
import { ChevronRight, Copy, Check } from "lucide-react";

/**
 * Collapsible viewer for a structured (or malformed-string) payload. Large blobs
 * are collapsed by default (Phase 9/10: "do not expose huge raw payloads by
 * default") and can be expanded on demand. Renders safely whether the value is
 * an object, array, string or null.
 */
export default function JsonBlock({ value, label, defaultOpen = false, maxHeight = 360 }) {
  const [open, setOpen] = useState(defaultOpen);
  const [copied, setCopied] = useState(false);

  const isEmpty = value === null || value === undefined || (typeof value === "object" && Object.keys(value).length === 0);

  // Serialize once per value change (not on every render). Large plan /
  // execution_result blobs were previously stringified on each render even
  // while collapsed.
  const text = useMemo(
    () => (typeof value === "string" ? value : JSON.stringify(value, null, 2)),
    [value]
  );

  const copy = async (e) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(text || "");
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable */
    }
  };

  if (isEmpty) {
    return (
      <div className="card-2" style={{ padding: "0.9rem 1rem" }}>
        <div style={{ fontSize: "0.85rem", fontWeight: 600, marginBottom: "0.2rem" }}>{label}</div>
        <div className="faint" style={{ fontSize: "0.82rem" }}>Not recorded for this run.</div>
      </div>
    );
  }

  return (
    <div className="card-2">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        style={{
          width: "100%", display: "flex", alignItems: "center", gap: "0.5rem",
          background: "transparent", border: "none", color: "var(--text)", cursor: "pointer",
          padding: "0.75rem 1rem", font: "inherit",
        }}
      >
        <ChevronRight size={16} style={{ transition: "transform 0.15s", transform: open ? "rotate(90deg)" : "none", flex: "none" }} aria-hidden="true" />
        <span style={{ fontWeight: 600, fontSize: "0.85rem" }}>{label}</span>
        <span style={{ marginLeft: "auto", display: "inline-flex", gap: "0.4rem", alignItems: "center" }}>
          <span className="btn btn-ghost btn-sm" onClick={copy} role="button" aria-label={`Copy ${label}`}>
            {copied ? <Check size={13} /> : <Copy size={13} />}
          </span>
        </span>
      </button>
      {open && (
        <pre
          className="mono"
          style={{
            margin: 0, padding: "0 1rem 1rem", fontSize: "0.78rem", lineHeight: 1.5,
            maxHeight, overflow: "auto", color: "var(--text-muted)",
          }}
        >
          {text}
        </pre>
      )}
    </div>
  );
}
