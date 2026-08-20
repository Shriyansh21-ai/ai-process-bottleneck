import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { Router } from "../lib/router.jsx";
import OverviewPage from "./OverviewPage.jsx";
import { ApiError } from "../lib/apiClient.js";

vi.mock("../auth/AuthContext.jsx", () => ({ useAuth: () => ({ isAdmin: false }) }));
vi.mock("../services/runsService.js");
vi.mock("../services/observabilityService.js");

import * as runsService from "../services/runsService.js";

const STATS = {
  total_runs: 42,
  successful_runs: 30,
  failed_runs: 8,
  running_runs: 2,
  pending_runs: 2,
  other_runs: 0,
  success_rate: 71.4,
  failure_rate: 19.0,
  average_duration_ms: 1234,
};

function renderPage() {
  window.history.pushState({}, "", "/");
  return render(<Router><OverviewPage /></Router>);
}

describe("OverviewPage", () => {
  beforeEach(() => {
    runsService.listRuns.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 6, total_pages: 0, has_next: false, has_prev: false });
  });

  it("renders KPI metrics from the statistics API", async () => {
    runsService.getStatistics.mockResolvedValue(STATS);
    renderPage();
    // 71.4% is the unique success-rate KPI; "42" appears in both the total-runs
    // card and the donut center, so assert it renders at least once.
    expect(await screen.findByText("71.4%")).toBeInTheDocument();
    expect(screen.getAllByText("42").length).toBeGreaterThan(0);
  });

  it("shows an empty state when there are no runs", async () => {
    runsService.getStatistics.mockResolvedValue({ ...STATS, total_runs: 0, successful_runs: 0, failed_runs: 0, running_runs: 0, pending_runs: 0 });
    renderPage();
    expect(await screen.findAllByText(/no runs yet/i)).not.toHaveLength(0);
  });

  it("shows an error state when statistics fail to load", async () => {
    runsService.getStatistics.mockRejectedValue(new ApiError(500, "The server encountered an error.", null));
    renderPage();
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    expect(screen.getByText(/server encountered an error/i)).toBeInTheDocument();
  });
});
