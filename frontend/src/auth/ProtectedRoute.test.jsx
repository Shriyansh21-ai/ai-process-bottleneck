import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { Router, Routes } from "../lib/router.jsx";
import ProtectedRoute from "./ProtectedRoute.jsx";

// Control the auth state per test.
let authState;
vi.mock("./AuthContext.jsx", () => ({
  useAuth: () => authState,
}));

function renderAt(path, ui) {
  window.history.pushState({}, "", path);
  return render(<Router>{ui}</Router>);
}

// Mirror the real app: a route table so redirecting to /login unmounts the
// guarded page (exactly as <Routes> does in App), avoiding an isolated
// re-render loop.
function renderWithRoutes(path) {
  window.history.pushState({}, "", path);
  return render(
    <Router>
      <Routes
        routes={[
          { path: "/login", element: <div>login screen</div> },
          { path: "/runs", element: <ProtectedRoute><div>secret</div></ProtectedRoute> },
        ]}
      />
    </Router>
  );
}

describe("ProtectedRoute", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/");
  });

  it("renders children when authenticated", () => {
    authState = { isAuthenticated: true, isLoading: false };
    renderAt("/runs", <ProtectedRoute><div>secret</div></ProtectedRoute>);
    expect(screen.getByText("secret")).toBeInTheDocument();
  });

  it("shows a loader while the session bootstraps", () => {
    authState = { isAuthenticated: false, isLoading: true };
    renderAt("/runs", <ProtectedRoute><div>secret</div></ProtectedRoute>);
    expect(screen.queryByText("secret")).not.toBeInTheDocument();
  });

  it("redirects unauthenticated users to /login with a next param", async () => {
    authState = { isAuthenticated: false, isLoading: false };
    renderWithRoutes("/runs");
    await waitFor(() => expect(window.location.pathname).toBe("/login"));
    expect(window.location.search).toContain("next=");
    expect(await screen.findByText("login screen")).toBeInTheDocument();
    expect(screen.queryByText("secret")).not.toBeInTheDocument();
  });
});
