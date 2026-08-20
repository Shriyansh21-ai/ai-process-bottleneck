import { useState, useEffect } from "react";
import { Search, X } from "lucide-react";

// Curated subset of the backend's ALLOWED_STATUSES for the filter dropdown.
const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "success", label: "Success" },
  { value: "completed", label: "Completed" },
  { value: "failed", label: "Failed" },
  { value: "running", label: "Running" },
  { value: "pending", label: "Pending" },
  { value: "approval_required", label: "Approval Required" },
];

/**
 * Filter bar for the runs list. Emits changes to the parent, which reflects them
 * into the URL query string (so filters are shareable/bookmarkable). Search is
 * debounced and handed to the backend search endpoint — never a client scan.
 */
export default function RunFilters({ value, onChange }) {
  const [q, setQ] = useState(value.q || "");

  // Keep the local search box in sync if the URL changes externally.
  useEffect(() => {
    setQ(value.q || "");
  }, [value.q]);

  // Debounce free-text search.
  useEffect(() => {
    const t = setTimeout(() => {
      if ((q || "") !== (value.q || "")) onChange({ ...value, q: q || undefined, page: 1 });
    }, 400);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q]);

  const set = (patch) => onChange({ ...value, ...patch, page: 1 });
  const hasFilters = value.q || value.status || value.session_id || value.start_date || value.end_date;

  return (
    <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", alignItems: "flex-end", marginBottom: "1rem" }}>
      <div style={{ flex: "1 1 240px", minWidth: 200 }}>
        <label className="field-label" htmlFor="run-search">Search query</label>
        <div style={{ position: "relative" }}>
          <Search size={15} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--text-faint)" }} aria-hidden="true" />
          <input
            id="run-search"
            className="input"
            style={{ paddingLeft: 32 }}
            placeholder="Search by user query…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
      </div>

      <div style={{ flex: "0 1 190px" }}>
        <label className="field-label" htmlFor="run-status">Status</label>
        <select id="run-status" className="select" value={value.status || ""} onChange={(e) => set({ status: e.target.value || undefined })}>
          {STATUS_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      <div style={{ flex: "0 1 160px" }}>
        <label className="field-label" htmlFor="run-from">From</label>
        <input id="run-from" type="date" className="input" value={value.start_date || ""} onChange={(e) => set({ start_date: e.target.value || undefined })} />
      </div>

      <div style={{ flex: "0 1 160px" }}>
        <label className="field-label" htmlFor="run-to">To</label>
        <input id="run-to" type="date" className="input" value={value.end_date || ""} onChange={(e) => set({ end_date: e.target.value || undefined })} />
      </div>

      {hasFilters && (
        <button
          className="btn btn-sm"
          onClick={() => { setQ(""); onChange({ page: 1 }); }}
          style={{ marginBottom: 1 }}
        >
          <X size={14} /> Clear
        </button>
      )}
    </div>
  );
}
