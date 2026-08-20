/**
 * Agent-runs API — the existing owner-scoped /runs endpoints plus run submission.
 * Server-side pagination/filtering/search only; the browser never downloads all
 * runs to filter locally.
 *
 * @typedef {import("../types/api").PaginatedAgentRuns} PaginatedAgentRuns
 * @typedef {import("../types/api").AgentRunDetail} AgentRunDetail
 * @typedef {import("../types/api").AgentRunStep} AgentRunStep
 * @typedef {import("../types/api").AgentRunStatistics} AgentRunStatistics
 */

import { api } from "../lib/apiClient.js";

/**
 * List runs (paginated + filtered). Uses the search endpoint when a query is
 * present so the backend does the searching.
 * @param {{page?:number, page_size?:number, status?:string, session_id?:string,
 *          q?:string, start_date?:string, end_date?:string, signal?:AbortSignal}} [filters]
 * @returns {Promise<PaginatedAgentRuns>}
 */
export function listRuns(filters = {}) {
  const { signal, q, ...rest } = filters;
  const params = { ...rest };
  const trimmed = q && q.trim();
  if (trimmed) {
    // /runs/search requires a non-empty q and applies the same filters.
    return api.get("/runs/search", { params: { ...params, q: trimmed }, signal });
  }
  return api.get("/runs", { params, signal });
}

/**
 * Aggregate run statistics for the current user (admin = system-wide).
 * @returns {Promise<AgentRunStatistics>}
 */
export function getStatistics(opts) {
  return api.get("/runs/statistics", opts);
}

/**
 * Full detail for a single run.
 * @returns {Promise<AgentRunDetail>}
 */
export function getRun(runId, opts) {
  return api.get(`/runs/${encodeURIComponent(runId)}`, opts);
}

/**
 * Execution-step timeline for a run (additive endpoint).
 * @returns {Promise<AgentRunStep[]>}
 */
export function getRunSteps(runId, opts) {
  return api.get(`/runs/${encodeURIComponent(runId)}/steps`, opts);
}

/**
 * Submit a new agent task for execution (existing POST /run). Resolves when the
 * run has completed server-side — the backend does not stream progress, so we
 * do not fake streaming here.
 * @returns {Promise<any>} the raw controller result
 */
export function submitRun(query, sessionId, opts) {
  return api.post("/run", { query, session_id: sessionId }, opts);
}
