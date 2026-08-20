import { ChevronLeft, ChevronRight } from "lucide-react";

/**
 * Server-side pagination control. Emits page changes; it never slices data
 * locally. Fully keyboard-accessible with disabled states at the bounds.
 */
export default function Pagination({ page, totalPages, total, pageSize, onPage }) {
  if (!totalPages || totalPages <= 1) {
    return (
      <div className="muted" style={{ fontSize: "0.8rem", padding: "0.75rem 0" }}>
        {total ? `${total} result${total === 1 ? "" : "s"}` : ""}
      </div>
    );
  }

  const from = (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);

  return (
    <nav
      aria-label="Pagination"
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: "1rem",
        padding: "0.75rem 0",
        flexWrap: "wrap",
      }}
    >
      <span className="muted" style={{ fontSize: "0.8rem" }}>
        Showing <strong>{from}</strong>–<strong>{to}</strong> of <strong>{total}</strong>
      </span>
      <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
        <button
          className="btn btn-sm"
          onClick={() => onPage(page - 1)}
          disabled={page <= 1}
          aria-label="Previous page"
        >
          <ChevronLeft size={15} /> Prev
        </button>
        <span className="muted" style={{ fontSize: "0.82rem", padding: "0 0.4rem" }}>
          Page {page} of {totalPages}
        </span>
        <button
          className="btn btn-sm"
          onClick={() => onPage(page + 1)}
          disabled={page >= totalPages}
          aria-label="Next page"
        >
          Next <ChevronRight size={15} />
        </button>
      </div>
    </nav>
  );
}
