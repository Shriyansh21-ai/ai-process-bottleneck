import "@testing-library/jest-dom/vitest";
import { afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";

// Reset DOM + mocks between tests.
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  localStorage.clear();
});

// jsdom lacks these; the app calls them defensively.
if (!("randomUUID" in crypto)) {
  crypto.randomUUID = () => "test-uuid-0000-0000-0000-000000000000";
}
window.scrollTo = window.scrollTo || (() => {});
