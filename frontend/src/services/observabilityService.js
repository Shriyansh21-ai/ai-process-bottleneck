/**
 * Agent observability API — the existing /observability/* endpoints.
 * ADMIN-ONLY on the backend: non-admin callers receive 403, which the UI
 * surfaces as a clear "admin required" state rather than an error.
 *
 * All aggregation happens in SQL on the server; nothing is recomputed here.
 *
 * @typedef {import("../types/api").AgentHealthSummary} AgentHealthSummary
 * @typedef {import("../types/api").ToolPerformanceSummary} ToolPerformanceSummary
 * @typedef {import("../types/api").FailureSummary} FailureSummary
 * @typedef {import("../types/api").ExecutionTrendPoint} ExecutionTrendPoint
 * @typedef {import("../types/api").AgentObservabilityResponse} AgentObservabilityResponse
 */

import { api } from "../lib/apiClient.js";

/** @returns {Promise<AgentHealthSummary>} */
export function getAgentHealth(params, opts) {
  return api.get("/observability/health", { ...opts, params });
}

/** @returns {Promise<ToolPerformanceSummary[]>} */
export function getToolPerformance(params, opts) {
  return api.get("/observability/tools", { ...opts, params });
}

/** @returns {Promise<FailureSummary[]>} */
export function getFailures(params, opts) {
  return api.get("/observability/failures", { ...opts, params });
}

/** @returns {Promise<ExecutionTrendPoint[]>} */
export function getTrends(params, opts) {
  return api.get("/observability/trends", { ...opts, params });
}

/** @returns {Promise<AgentObservabilityResponse>} */
export function getOverview(params, opts) {
  return api.get("/observability/overview", { ...opts, params });
}
