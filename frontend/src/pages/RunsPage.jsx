/**
 * Agent Runs page (Phases 7–9). Server-side pagination, filtering and search —
 * the browser only ever holds one page. All filter/pagination state lives in the
 * URL query string so views are shareable (e.g. /runs?status=failed&page=2).
 */

import { useMemo } from "react";
import PageHeader from "../components/ui/PageHeader.jsx";
import { Card } from "../components/ui/Card.jsx";
import { ErrorState, EmptyState, LoadingBlock } from "../components/ui/StateViews.jsx";
import RunFilters from "../components/runs/RunFilters.jsx";
import RunsTable from "../components/runs/RunsTable.jsx";
import Pagination from "../components/ui/Pagination.jsx";
import { useSearchParams } from "../lib/router.jsx";
import { useAsync } from "../hooks/useAsync.js";
import * as runsService from "../services/runsService.js";

const PAGE_SIZE = 20;

export default function RunsPage() {
  const [params, setSearchParams] = useSearchParams();

  // Read the current filter state from the URL.
  const filters = useMemo(
    () => ({
      page: Number(params.get("page")) || 1,
      status: params.get("status") || undefined,
      q: params.get("q") || undefined,
      session_id: params.get("session_id") || undefined,
      start_date: params.get("start_date") || undefined,
      end_date: params.get("end_date") || undefined,
    }),
    [params]
  );

  const apiParams = useMemo(() => {
    const p = { ...filters, page: filters.page, page_size: PAGE_SIZE };
    // Make the "To" date inclusive of the whole day for the backend's <= filter.
    if (p.end_date && /^\d{4}-\d{2}-\d{2}$/.test(p.end_date)) p.end_date = `${p.end_date}T23:59:59`;
    return p;
  }, [filters]);

  const { data, error, loading, reload } = useAsync(
    (signal) => runsService.listRuns({ ...apiParams, signal }),
    [apiParams]
  );

  const updateFilters = (next) => {
    // Strip empties so the URL stays clean; drop page when it's 1.
    const clean = {};
    Object.entries(next).forEach(([k, v]) => {
      if (v !== undefined && v !== "" && !(k === "page" && v === 1)) clean[k] = v;
    });
    setSearchParams(clean);
  };

  const goPage = (page) => updateFilters({ ...filters, page });

  return (
    <>
      <PageHeader title="Agent Runs" description="Browse, filter and search every run you own." />

      <Card padded>
        <RunFilters value={filters} onChange={updateFilters} />

        {error ? (
          <ErrorState error={error} onRetry={reload} />
        ) : loading ? (
          <LoadingBlock rows={6} height={44} />
        ) : data && data.items.length > 0 ? (
          <>
            <RunsTable runs={data.items} />
            <Pagination
              page={data.page}
              totalPages={data.total_pages}
              total={data.total}
              pageSize={data.page_size}
              onPage={goPage}
            />
          </>
        ) : (
          <EmptyState
            title="No runs match your filters"
            message={
              filters.q || filters.status || filters.start_date
                ? "Try broadening or clearing your filters."
                : "You haven't submitted any agent runs yet."
            }
          />
        )}
      </Card>
    </>
  );
}
