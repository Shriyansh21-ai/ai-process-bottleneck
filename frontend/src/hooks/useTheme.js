/**
 * Light/dark theme, persisted and applied via the `data-theme` attribute on
 * <html> (the CSS design tokens in index.css switch on it). Defaults to dark —
 * the primary operations experience — and respects a saved preference.
 */

import { useState, useEffect, useCallback } from "react";

const KEY = "aiops.theme";

function initialTheme() {
  try {
    const saved = localStorage.getItem(KEY);
    if (saved === "light" || saved === "dark") return saved;
  } catch {
    /* ignore */
  }
  return "dark";
}

export function useTheme() {
  const [theme, setTheme] = useState(initialTheme);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem(KEY, theme);
    } catch {
      /* ignore */
    }
  }, [theme]);

  const toggle = useCallback(() => {
    setTheme((t) => (t === "dark" ? "light" : "dark"));
  }, []);

  return { theme, toggle };
}
