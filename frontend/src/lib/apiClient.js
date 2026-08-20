/**
 * Centralized API client for the Agent Operations Dashboard.
 *
 * Single place that knows about: the backend base URL, attaching the JWT
 * Authorization header, JSON (and OAuth2 form) encoding, response parsing and
 * error normalization. No component should call `fetch` directly.
 *
 * 401 handling: on any authenticated request that returns 401 the stored token
 * is cleared and registered listeners are notified so the app can redirect to
 * the login screen (see AuthContext).
 */

const RAW_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
export const API_BASE_URL = RAW_BASE.replace(/\/+$/, "");

const TOKEN_KEY = "aiops.token";

// ---- token storage ---------------------------------------------------------
//
// Token-storage tradeoff (documented, accepted): the JWT is kept in
// localStorage. This is a deliberate choice for an SPA served from a different
// origin than the API, where an httpOnly cookie would require same-site hosting
// and CSRF handling. The XSS risk is bounded because the app never renders raw
// HTML (no dangerouslySetInnerHTML anywhere) and access tokens are short-lived
// (ACCESS_TOKEN_EXPIRE_MINUTES, default 60). For a higher-security deployment,
// move to an httpOnly, Secure, SameSite=strict cookie set by the backend.

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable (private mode) — token stays in-memory only */
  }
}

export function clearToken() {
  setToken(null);
}

// ---- 401 (unauthenticated) subscribers -------------------------------------

const unauthorizedListeners = new Set();

/** Register a callback invoked whenever the API reports 401. Returns unsubscribe. */
export function onUnauthorized(cb) {
  unauthorizedListeners.add(cb);
  return () => unauthorizedListeners.delete(cb);
}

function notifyUnauthorized() {
  clearToken();
  unauthorizedListeners.forEach((cb) => {
    try {
      cb();
    } catch {
      /* ignore listener errors */
    }
  });
}

// ---- error type ------------------------------------------------------------

/**
 * Normalized API error. `status` is the HTTP status (0 for network failures),
 * `message` is a safe, user-presentable string, `detail` is the raw parsed
 * backend payload (may hold FastAPI validation arrays).
 */
export class ApiError extends Error {
  constructor(status, message, detail) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

/** Map a status code to a safe, human-friendly default message. */
export function defaultMessageForStatus(status) {
  switch (status) {
    case 0:
      return "Cannot reach the server. Check your connection and that the API is running.";
    case 400:
      return "The request was invalid.";
    case 401:
      return "Your session has expired. Please sign in again.";
    case 403:
      return "You do not have permission to view this resource.";
    case 404:
      return "The requested resource was not found.";
    case 409:
      return "That resource already exists.";
    case 422:
      return "Some fields are invalid. Please check your input.";
    case 429:
      return "Too many requests. Please slow down and try again shortly.";
    case 503:
      return "The service is temporarily unavailable. Please try again soon.";
    default:
      if (status >= 500) return "The server encountered an error. Please try again later.";
      return "Something went wrong.";
  }
}

/** Extract a readable message from a parsed FastAPI error body. */
function extractDetailMessage(body, status) {
  if (!body || typeof body !== "object") return defaultMessageForStatus(status);
  const d = body.detail ?? body.error ?? body.message;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) {
    // FastAPI 422 validation errors: [{loc, msg, ...}]
    const first = d[0];
    if (first && typeof first.msg === "string") {
      const field = Array.isArray(first.loc) ? first.loc[first.loc.length - 1] : null;
      return field ? `${field}: ${first.msg}` : first.msg;
    }
  }
  return defaultMessageForStatus(status);
}

// ---- core request ----------------------------------------------------------

/**
 * Perform an API request.
 * @param {string} path              Path beginning with "/".
 * @param {object} [opts]
 * @param {string} [opts.method]     HTTP method (default GET).
 * @param {any}    [opts.body]       JSON body (object) — ignored for GET.
 * @param {URLSearchParams|Record<string,string>} [opts.form] OAuth2 form body.
 * @param {Record<string,any>} [opts.params] Query params (skips null/undefined).
 * @param {boolean} [opts.auth]      Attach Authorization header (default true).
 * @param {AbortSignal} [opts.signal]
 * @returns {Promise<any>}           Parsed JSON (or null for 204).
 */
export async function request(path, opts = {}) {
  const {
    method = "GET",
    body,
    form,
    params,
    auth = true,
    signal,
  } = opts;

  let url = API_BASE_URL + path;
  if (params) {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== null && v !== undefined && v !== "") qs.append(k, String(v));
    });
    const q = qs.toString();
    if (q) url += (url.includes("?") ? "&" : "?") + q;
  }

  const headers = {};
  let payload;

  if (form) {
    headers["Content-Type"] = "application/x-www-form-urlencoded";
    payload =
      form instanceof URLSearchParams
        ? form.toString()
        : new URLSearchParams(form).toString();
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  if (auth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  let res;
  try {
    res = await fetch(url, { method, headers, body: payload, signal });
  } catch (err) {
    if (err && err.name === "AbortError") throw err;
    throw new ApiError(0, defaultMessageForStatus(0), null);
  }

  if (res.status === 204) return null;

  // Parse body defensively (may be empty or non-JSON).
  let parsed = null;
  const text = await res.text();
  if (text) {
    try {
      parsed = JSON.parse(text);
    } catch {
      parsed = text;
    }
  }

  if (!res.ok) {
    if (res.status === 401 && auth) notifyUnauthorized();
    // For 5xx, never surface a raw text body — an unhandled server error could
    // carry a stack trace / internal detail. Use the safe generic message.
    const message =
      res.status < 500 && typeof parsed === "string" && parsed
        ? parsed
        : extractDetailMessage(parsed, res.status);
    throw new ApiError(res.status, message, parsed);
  }

  return parsed;
}

export const api = {
  get: (path, opts) => request(path, { ...opts, method: "GET" }),
  post: (path, body, opts) => request(path, { ...opts, method: "POST", body }),
  put: (path, body, opts) => request(path, { ...opts, method: "PUT", body }),
  del: (path, opts) => request(path, { ...opts, method: "DELETE" }),
};
