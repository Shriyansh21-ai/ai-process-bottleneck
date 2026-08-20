import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  request,
  api,
  ApiError,
  setToken,
  getToken,
  onUnauthorized,
} from "./apiClient.js";

function mockFetch(status, body, ok = status >= 200 && status < 300) {
  return vi.fn().mockResolvedValue({
    ok,
    status,
    text: async () => (typeof body === "string" ? body : JSON.stringify(body)),
    json: async () => body,
  });
}

describe("apiClient", () => {
  beforeEach(() => {
    setToken(null);
  });

  it("parses a successful JSON response", async () => {
    global.fetch = mockFetch(200, { items: [1, 2, 3] });
    const data = await api.get("/runs");
    expect(data).toEqual({ items: [1, 2, 3] });
  });

  it("attaches the bearer token when authenticated", async () => {
    setToken("abc123");
    global.fetch = mockFetch(200, {});
    await api.get("/auth/me");
    const [, opts] = global.fetch.mock.calls[0];
    expect(opts.headers.Authorization).toBe("Bearer abc123");
  });

  it("throws a normalized ApiError with the backend detail (404)", async () => {
    global.fetch = mockFetch(404, { detail: "Run 5 not found" }, false);
    await expect(api.get("/runs/5")).rejects.toMatchObject({
      status: 404,
      message: "Run 5 not found",
    });
  });

  it("surfaces a friendly message for 403", async () => {
    global.fetch = mockFetch(403, { detail: "Administrative privilege required" }, false);
    const err = await api.get("/observability/tools").catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(403);
  });

  it("flattens FastAPI 422 validation errors", async () => {
    global.fetch = mockFetch(
      422,
      { detail: [{ loc: ["body", "email"], msg: "value is not a valid email address" }] },
      false
    );
    const err = await api.post("/auth/register", {}).catch((e) => e);
    expect(err.message).toContain("email");
  });

  it("clears the token and notifies listeners on 401", async () => {
    setToken("expired");
    const cb = vi.fn();
    const unsub = onUnauthorized(cb);
    global.fetch = mockFetch(401, { detail: "Could not validate credentials" }, false);
    await api.get("/runs").catch(() => {});
    expect(cb).toHaveBeenCalledOnce();
    expect(getToken()).toBeNull();
    unsub();
  });

  it("maps a network failure to status 0", async () => {
    global.fetch = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
    const err = await api.get("/runs").catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(0);
  });

  it("sends OAuth2 form bodies url-encoded", async () => {
    global.fetch = mockFetch(200, { access_token: "t", token_type: "bearer" });
    await request("/auth/login", { method: "POST", auth: false, form: { username: "a@b.com", password: "x" } });
    const [, opts] = global.fetch.mock.calls[0];
    expect(opts.headers["Content-Type"]).toBe("application/x-www-form-urlencoded");
    expect(opts.body).toContain("username=a%40b.com");
  });
});
