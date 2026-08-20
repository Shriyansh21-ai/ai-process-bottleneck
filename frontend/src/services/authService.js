/**
 * Authentication API — wraps the existing backend /auth endpoints.
 * No auth logic is duplicated here; JWT issuance/validation lives on the server.
 *
 * @typedef {import("../types/api").User} User
 * @typedef {import("../types/api").Token} Token
 */

import { api, request, setToken } from "../lib/apiClient.js";

/**
 * Register a new account. Returns the created public user (no secrets).
 * @returns {Promise<User>}
 */
export function register(email, password) {
  return api.post("/auth/register", { email, password }, { auth: false });
}

/**
 * Log in via the OAuth2 password flow (form-encoded; `username` = email),
 * persist the returned JWT, and return the token payload.
 * @returns {Promise<Token>}
 */
export async function login(email, password) {
  const token = await request("/auth/login", {
    method: "POST",
    auth: false,
    form: { username: email, password },
  });
  setToken(token.access_token);
  return token;
}

/**
 * Fetch the currently authenticated user.
 * @returns {Promise<User>}
 */
export function me(opts) {
  return api.get("/auth/me", opts);
}
