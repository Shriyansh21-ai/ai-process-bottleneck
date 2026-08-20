import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Ensure the classic JSX transform (used by esbuild for test files under
  // rolldown-vite) has React in scope. Harmless for the automatic-runtime app
  // build, which the react plugin handles.
  esbuild: {
    jsxInject: `import React from 'react'`,
  },
  // Vitest configuration (frontend unit/component tests).
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.js"],
    css: false,
    include: ["src/**/*.{test,spec}.{js,jsx}"],
  },
});
