/**
 * System health API — the existing public /health and /health/ready probes.
 * Readiness returns 503 when a critical dependency is down; we treat that as a
 * valid, informative response (not a hard error) so the UI can show per-check state.
 *
 * @typedef {import("../types/api").HealthResponse} HealthResponse
 * @typedef {import("../types/api").ReadinessResponse} ReadinessResponse
 */

import { API_BASE_URL, ApiError } from "../lib/apiClient.js";

/**
 * Liveness probe.
 * @returns {Promise<HealthResponse>}
 */
export async function getHealth(opts = {}) {
  const res = await fetch(`${API_BASE_URL}/health`, { signal: opts.signal });
  if (!res.ok) throw new ApiError(res.status, "Health probe failed", null);
  return res.json();
}

/**
 * Readiness probe. Returns the parsed body for BOTH 200 and 503 so the caller
 * can render per-dependency checks; only network/parse failures reject.
 * @returns {Promise<{ready: boolean, body: ReadinessResponse}>}
 */
export async function getReadiness(opts = {}) {
  let res;
  try {
    res = await fetch(`${API_BASE_URL}/health/ready`, { signal: opts.signal });
  } catch (err) {
    if (err && err.name === "AbortError") throw err;
    throw new ApiError(0, "Cannot reach the server.", null);
  }
  const body = await res.json().catch(() => ({ status: "not_ready", checks: {} }));
  return { ready: res.ok && body.status === "ready", body };
}
