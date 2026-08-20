import { describe, it, expect } from "vitest";
import {
  formatDuration,
  formatPercent,
  formatConfidence,
  formatNumber,
  statusTone,
  statusLabel,
  truncate,
} from "./format.js";

describe("format helpers", () => {
  it("formats durations across ranges", () => {
    expect(formatDuration(null)).toBe("—");
    expect(formatDuration(450)).toBe("450 ms");
    expect(formatDuration(1500)).toBe("1.50 s");
    expect(formatDuration(65000)).toBe("1m 5s");
  });

  it("formats percentages and confidence", () => {
    expect(formatPercent(92.5)).toBe("92.5%");
    expect(formatPercent(null)).toBe("—");
    expect(formatConfidence(0.81)).toBe("81%");
    expect(formatConfidence(null)).toBe("—");
  });

  it("formats numbers with separators", () => {
    expect(formatNumber(1234)).toBe("1,234");
    expect(formatNumber(null)).toBe("—");
  });

  it("maps statuses to accessible tones and labels", () => {
    expect(statusTone("success")).toBe("ok");
    expect(statusTone("failed")).toBe("danger");
    expect(statusTone("running")).toBe("info");
    expect(statusTone("approval_required")).toBe("warn");
    expect(statusLabel("approval_required")).toBe("Approval Required");
  });

  it("truncates long strings", () => {
    expect(truncate("hello world", 5)).toBe("hello…");
    expect(truncate("hi", 5)).toBe("hi");
  });
});
