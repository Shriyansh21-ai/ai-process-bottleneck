/**
 * Inspection intelligence API (MRPL Phase 3).
 *
 * Wraps POST /inspection/analyze: upload an inspection report + an analysis
 * instruction, receive structured, evidence-backed findings with page
 * provenance. The multipart upload goes through the shared api client so JWT
 * auth + error normalization are handled centrally.
 */

import { api } from "../lib/apiClient.js";

/**
 * Analyze an inspection document and return structured findings.
 * @param {File} file   the inspection report (PDF or image)
 * @param {string} query analysis instruction
 * @param {{signal?:AbortSignal}} [opts]
 * @returns {Promise<import("../lib/apiClient.js").ApiError|object>} InspectionAnalysis
 */
export function analyzeInspection(file, query, opts) {
  const fd = new FormData();
  fd.append("file", file);
  if (query) fd.append("query", query);
  return api.upload("/inspection/analyze", fd, opts);
}
