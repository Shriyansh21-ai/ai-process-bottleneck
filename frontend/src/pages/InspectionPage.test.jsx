import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import InspectionPage from "./InspectionPage.jsx";
import { ApiError } from "../lib/apiClient.js";

vi.mock("../services/inspectionService.js");
vi.mock("../services/runsService.js");
import * as inspectionService from "../services/inspectionService.js";
import * as runsService from "../services/runsService.js";

const ANALYSIS = {
  analysis_id: "ins-42-7",
  document: { document_id: 42, filename: "report.pdf", page_count: 5, extraction_method: "ocr" },
  overall_status: "action_required",
  findings: [
    {
      finding_id: "42-F1",
      title: "Corrosion detected",
      description: "Significant corrosion observed on the equipment surface.",
      severity: "HIGH",
      evidence: "Visible corrosion is described on the equipment surface near the flange.",
      page_number: 4,
      extraction_method: "ocr",
      recommendation: "Schedule a detailed inspection and maintenance assessment.",
      confidence: 0.91,
    },
    {
      finding_id: "42-F2",
      title: "Equipment wear observed",
      description: "Coating breakdown and aged gasket seating.",
      severity: "MEDIUM",
      evidence: "Pump casing shows moderate surface wear.",
      page_number: 2,
      extraction_method: "text",
      recommendation: "Monitor and re-inspect at the next maintenance window.",
      confidence: 0.82,
    },
  ],
  verification: { approved: true, issues: [], findings_total: 2, findings_valid: 2, findings_rejected: 0 },
  run_id: 7,
};

function pdf(name = "report.pdf") {
  return new File([new Uint8Array([1, 2, 3, 4])], name, { type: "application/pdf" });
}

async function selectFileAndAnalyze(user, name = "report.pdf") {
  await user.upload(screen.getByLabelText(/upload report/i), pdf(name));
  await user.click(screen.getByRole("button", { name: /analyze inspection report/i }));
}

describe("InspectionPage", () => {
  beforeEach(() => {
    inspectionService.analyzeInspection.mockReset();
    runsService.getRunSteps.mockReset();
  });

  it("renders the page title, description and initial empty state", () => {
    render(<InspectionPage />);
    expect(screen.getByText("MRPL Inspection Intelligence")).toBeInTheDocument();
    expect(screen.getByText(/sovereign ai/i)).toBeInTheDocument();
    expect(screen.getByText(/no analysis yet/i)).toBeInTheDocument();
  });

  it("has a default analysis instruction that can be edited", async () => {
    const user = userEvent.setup();
    render(<InspectionPage />);
    const textarea = screen.getByLabelText(/analysis instruction/i);
    expect(textarea).toHaveValue(
      "Identify safety-critical findings and defects that require maintenance attention."
    );
    await user.clear(textarea);
    await user.type(textarea, "custom instruction");
    expect(textarea).toHaveValue("custom instruction");
  });

  it("shows the selected file name and enables submit", async () => {
    const user = userEvent.setup();
    render(<InspectionPage />);
    const submit = screen.getByRole("button", { name: /analyze inspection report/i });
    expect(submit).toBeDisabled();
    await user.upload(screen.getByLabelText(/upload report/i), pdf("weld_report.pdf"));
    expect(screen.getByText(/weld_report\.pdf/)).toBeInTheDocument();
    expect(submit).toBeEnabled();
  });

  it("rejects an oversized file client-side (before upload)", async () => {
    const user = userEvent.setup();
    render(<InspectionPage />);
    const big = pdf("huge.pdf");
    // Simulate a >20 MB file without allocating memory.
    Object.defineProperty(big, "size", { value: 25 * 1024 * 1024 });
    await user.upload(screen.getByLabelText(/upload report/i), big);
    expect(await screen.findByText(/too large/i)).toBeInTheDocument();
    expect(inspectionService.analyzeInspection).not.toHaveBeenCalled();
  });

  it("maps a server 415 to a friendly unsupported-file message", async () => {
    const user = userEvent.setup();
    inspectionService.analyzeInspection.mockRejectedValue(
      new ApiError(415, "unsupported", { detail: { code: "unsupported_file_type" } })
    );
    render(<InspectionPage />);
    await selectFileAndAnalyze(user);
    expect(await screen.findByText(/unsupported file type/i)).toBeInTheDocument();
  });

  it("submits and renders findings with severity, provenance and verification", async () => {
    const user = userEvent.setup();
    inspectionService.analyzeInspection.mockResolvedValue(ANALYSIS);
    render(<InspectionPage />);

    await selectFileAndAnalyze(user);

    // findings
    expect(await screen.findByText("Corrosion detected")).toBeInTheDocument();
    expect(screen.getByText("Equipment wear observed")).toBeInTheDocument();
    // severity rendering
    expect(screen.getByText("HIGH")).toBeInTheDocument();
    expect(screen.getByText("MEDIUM")).toBeInTheDocument();
    // page provenance + confidence
    expect(screen.getByText(/Page 4/)).toBeInTheDocument();
    expect(screen.getByText(/91%/)).toBeInTheDocument();
    // evidence + recommendation text
    expect(screen.getByText(/Visible corrosion is described/)).toBeInTheDocument();
    // verification
    expect(screen.getByText(/analysis verified/i)).toBeInTheDocument();
    expect(screen.getByText(/2\/2 findings validated/i)).toBeInTheDocument();

    // the real backend service was called (no frontend fabrication)
    expect(inspectionService.analyzeInspection).toHaveBeenCalledTimes(1);
  });

  it("shows a loading state and disables duplicate submission", async () => {
    const user = userEvent.setup();
    let resolve;
    inspectionService.analyzeInspection.mockReturnValue(
      new Promise((r) => { resolve = r; })
    );
    render(<InspectionPage />);
    await selectFileAndAnalyze(user);

    const btn = await screen.findByRole("button", { name: /analyzing report/i });
    expect(btn).toBeDisabled();
    expect(screen.getByText(/analyzing inspection report/i)).toBeInTheDocument();

    resolve(ANALYSIS); // cleanup
    await screen.findByText("Corrosion detected");
  });

  it("renders review status when verification is not approved", async () => {
    const user = userEvent.setup();
    inspectionService.analyzeInspection.mockResolvedValue({
      ...ANALYSIS,
      overall_status: "verification_failed",
      findings: [],
      verification: { approved: false, issues: ["page 12 was not in the retrieved evidence"], findings_total: 1, findings_valid: 0, findings_rejected: 1 },
    });
    render(<InspectionPage />);
    await selectFileAndAnalyze(user);
    expect(await screen.findByText(/verification requires review/i)).toBeInTheDocument();
    expect(screen.getByText(/not in the retrieved evidence/i)).toBeInTheDocument();
  });

  it("shows a friendly error when the backend is unreachable", async () => {
    const user = userEvent.setup();
    inspectionService.analyzeInspection.mockRejectedValue(new ApiError(0, "network", null));
    render(<InspectionPage />);
    await selectFileAndAnalyze(user);
    expect(await screen.findByText(/cannot reach the backend/i)).toBeInTheDocument();
  });

  it("shows the real agent trace on demand", async () => {
    const user = userEvent.setup();
    inspectionService.analyzeInspection.mockResolvedValue(ANALYSIS);
    runsService.getRunSteps.mockResolvedValue([
      { id: 1, step_id: 1, tool_name: "rag_retrieval", status: "success" },
      { id: 2, step_id: 2, tool_name: "inspection_findings", status: "success" },
    ]);
    render(<InspectionPage />);
    await selectFileAndAnalyze(user);

    await screen.findByText("Corrosion detected");
    await user.click(screen.getByRole("button", { name: /view agent trace/i }));

    expect(await screen.findByText("RAG Retrieval")).toBeInTheDocument();
    expect(screen.getByText("Inspection Findings")).toBeInTheDocument();
    expect(screen.getByText("Planner")).toBeInTheDocument();
    expect(screen.getByText("Verifier")).toBeInTheDocument();
    expect(runsService.getRunSteps).toHaveBeenCalledWith(7, expect.anything());
  });
});
