import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Router, Routes } from "../lib/router.jsx";
import RunDetailPage from "./RunDetailPage.jsx";
import { ApiError } from "../lib/apiClient.js";

vi.mock("../services/runsService.js");
import * as runsService from "../services/runsService.js";

const DETAIL = {
  run_id: 7,
  session_id: "sess-1",
  user_query: "Analyze manufacturing bottlenecks",
  status: "success",
  created_at: "2026-08-01T10:00:00Z",
  execution_duration_ms: 2200,
  execution_mode: "normal",
  llm_model: "ollama:llama3",
  confidence: 0.88,
  approved: true,
  steps_total: 2,
  steps_failed: 0,
  retry_count: 0,
  final_response: "The main bottleneck is the assembly stage.",
  plan: { steps: [{ tool: "rag_retrieval" }] },
  execution_result: { results: {} },
  verification_result: { approved: true, confidence: 0.88 },
};

const STEPS = [
  { id: 1, step_id: 1, tool_name: "rag_retrieval", status: "success", execution_time_ms: 120, retry_count: 0, input_summary: "{}", output_summary: "docs" },
  { id: 2, step_id: 2, tool_name: "ml_analysis", status: "failed", execution_time_ms: 450, retry_count: 2, error: "model timeout" },
];

function renderDetail(id = 7) {
  window.history.pushState({}, "", `/runs/${id}`);
  return render(
    <Router>
      <Routes routes={[{ path: "/runs/:id", element: <RunDetailPage /> }]} />
    </Router>
  );
}

describe("RunDetailPage", () => {
  beforeEach(() => {
    runsService.getRun.mockReset();
    runsService.getRunSteps.mockReset();
  });

  it("renders run detail with the final response", async () => {
    runsService.getRun.mockResolvedValue(DETAIL);
    runsService.getRunSteps.mockResolvedValue(STEPS);
    renderDetail();
    expect(await screen.findByText("Analyze manufacturing bottlenecks")).toBeInTheDocument();
    expect(screen.getByText(/main bottleneck is the assembly stage/i)).toBeInTheDocument();
    expect(screen.getByText("ollama:llama3")).toBeInTheDocument();
  });

  it("renders the execution step timeline and expands step detail", async () => {
    runsService.getRun.mockResolvedValue(DETAIL);
    runsService.getRunSteps.mockResolvedValue(STEPS);
    renderDetail();
    expect(await screen.findByText("rag_retrieval")).toBeInTheDocument();
    // Expand the failed step to reveal its error.
    await userEvent.click(screen.getByText("ml_analysis"));
    expect(await screen.findByText("model timeout")).toBeInTheDocument();
  });

  it("shows a not-found state for another user's run (authorization / IDOR → 404)", async () => {
    runsService.getRun.mockRejectedValue(new ApiError(404, "Run 7 not found", null));
    runsService.getRunSteps.mockRejectedValue(new ApiError(404, "Run 7 not found", null));
    renderDetail();
    await waitFor(() => expect(screen.getByText(/run not found/i)).toBeInTheDocument());
    expect(screen.getByText(/belongs to another account/i)).toBeInTheDocument();
  });
});
