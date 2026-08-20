import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Router } from "../lib/router.jsx";
import RunsPage from "./RunsPage.jsx";

vi.mock("../services/runsService.js");
import * as runsService from "../services/runsService.js";

function page(items, overrides = {}) {
  return {
    items,
    total: overrides.total ?? items.length,
    page: overrides.page ?? 1,
    page_size: 20,
    total_pages: overrides.total_pages ?? 1,
    has_next: overrides.has_next ?? false,
    has_prev: overrides.has_prev ?? false,
  };
}

const RUN = {
  run_id: 7,
  session_id: "s1",
  user_query: "Analyze bottlenecks",
  status: "success",
  created_at: "2026-08-01T10:00:00Z",
  execution_duration_ms: 1200,
  steps_total: 3,
  retry_count: 0,
  confidence: 0.9,
  approved: true,
};

function renderPage(url = "/runs") {
  window.history.pushState({}, "", url);
  return render(<Router><RunsPage /></Router>);
}

describe("RunsPage", () => {
  beforeEach(() => {
    runsService.listRuns.mockReset();
  });

  it("renders a page of runs from the server", async () => {
    runsService.listRuns.mockResolvedValue(page([RUN], { total: 1 }));
    renderPage();
    expect(await screen.findByText("Analyze bottlenecks")).toBeInTheDocument();
    expect(screen.getByText("#7")).toBeInTheDocument();
  });

  it("requests server-side pagination (page_size, not all rows)", async () => {
    runsService.listRuns.mockResolvedValue(page([RUN]));
    renderPage();
    await waitFor(() => expect(runsService.listRuns).toHaveBeenCalled());
    const args = runsService.listRuns.mock.calls[0][0];
    expect(args.page_size).toBe(20);
    expect(args.page).toBe(1);
  });

  it("passes the status filter from the URL to the API", async () => {
    runsService.listRuns.mockResolvedValue(page([]));
    renderPage("/runs?status=failed");
    await waitFor(() => expect(runsService.listRuns).toHaveBeenCalled());
    expect(runsService.listRuns.mock.calls[0][0].status).toBe("failed");
  });

  it("advances the page when Next is clicked", async () => {
    runsService.listRuns.mockResolvedValue(page([RUN], { total: 40, total_pages: 2, has_next: true }));
    renderPage();
    await screen.findByText("Analyze bottlenecks");
    await userEvent.click(screen.getByRole("button", { name: /next/i }));
    await waitFor(() => expect(window.location.search).toContain("page=2"));
  });

  it("shows an empty state when no runs match", async () => {
    runsService.listRuns.mockResolvedValue(page([]));
    renderPage();
    expect(await screen.findByText(/no runs match your filters/i)).toBeInTheDocument();
  });
});
