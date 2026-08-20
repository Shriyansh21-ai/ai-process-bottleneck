import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Router } from "../lib/router.jsx";
import LoginPage from "./LoginPage.jsx";

const login = vi.fn();
vi.mock("../auth/AuthContext.jsx", () => ({
  useAuth: () => ({ login }),
}));

function renderLogin() {
  window.history.pushState({}, "", "/login");
  return render(
    <Router>
      <LoginPage />
    </Router>
  );
}

describe("LoginPage", () => {
  it("submits credentials and redirects on success", async () => {
    login.mockResolvedValueOnce({});
    renderLogin();
    await userEvent.type(screen.getByLabelText(/email/i), "user@example.com");
    await userEvent.type(screen.getByLabelText(/password/i), "Password123!");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => expect(login).toHaveBeenCalledWith("user@example.com", "Password123!"));
    await waitFor(() => expect(window.location.pathname).toBe("/"));
  });

  it("shows a safe error message on invalid credentials", async () => {
    login.mockRejectedValueOnce(Object.assign(new Error("Incorrect email or password"), { status: 401 }));
    renderLogin();
    await userEvent.type(screen.getByLabelText(/email/i), "user@example.com");
    await userEvent.type(screen.getByLabelText(/password/i), "wrongpass");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/incorrect email or password/i);
  });

  it("disables submit until both fields are filled", async () => {
    renderLogin();
    const button = screen.getByRole("button", { name: /sign in/i });
    expect(button).toBeDisabled();
    await userEvent.type(screen.getByLabelText(/email/i), "a@b.com");
    await userEvent.type(screen.getByLabelText(/password/i), "secret12");
    expect(button).toBeEnabled();
  });
});
