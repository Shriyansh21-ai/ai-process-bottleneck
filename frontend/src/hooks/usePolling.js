/**
 * Controlled polling (Phase 14). Deliberately conservative: polling is opt-in,
 * pauses when the browser tab is hidden, and the interval is configurable. We do
 * NOT poll aggressively and there is no fake real-time/streaming.
 */

import { useEffect, useRef, useState, useCallback } from "react";

export const REFRESH_INTERVALS = [
  { label: "Off", value: 0 },
  { label: "10s", value: 10000 },
  { label: "30s", value: 30000 },
  { label: "1m", value: 60000 },
  { label: "5m", value: 300000 },
];

/**
 * Invoke `callback` every `intervalMs` (0 disables). Skips ticks while the tab
 * is hidden so background tabs don't hammer the API.
 * @returns {{lastRun: number|null}}
 */
export function usePolling(callback, intervalMs) {
  const cbRef = useRef(callback);
  const [lastRun, setLastRun] = useState(null);

  // Keep the latest callback without re-arming the interval each render.
  useEffect(() => {
    cbRef.current = callback;
  }, [callback]);

  useEffect(() => {
    if (!intervalMs || intervalMs <= 0) return;
    const id = setInterval(() => {
      if (document.visibilityState === "visible") {
        cbRef.current();
        setLastRun(Date.now());
      }
    }, intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);

  return { lastRun };
}

/** Small helper for a persisted, user-selectable refresh interval. */
export function useRefreshInterval(defaultMs = 30000, storageKey = "aiops.refresh") {
  const [interval, setIntervalMs] = useState(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      return saved !== null ? Number(saved) : defaultMs;
    } catch {
      return defaultMs;
    }
  });
  const set = useCallback(
    (ms) => {
      setIntervalMs(ms);
      try {
        localStorage.setItem(storageKey, String(ms));
      } catch {
        /* ignore */
      }
    },
    [storageKey]
  );
  return [interval, set];
}
