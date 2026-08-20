/**
 * Data-fetching hooks that give every consuming component the four required
 * states: loading, error, empty and success (Phase 17). Requests are aborted on
 * unmount / dependency change to avoid setting state on a gone component and to
 * cancel superseded requests.
 */

import { useState, useEffect, useCallback, useRef } from "react";

/**
 * Run an async function and track its lifecycle.
 * @param {(signal: AbortSignal) => Promise<any>} fn
 * @param {Array<any>} deps  re-run when these change
 * @param {{enabled?: boolean}} [options]
 * @returns {{data:any, error:Error|null, loading:boolean, reload:()=>void, setData:Function}}
 */
export function useAsync(fn, deps = [], options = {}) {
  const { enabled = true } = options;
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(enabled);
  const [tick, setTick] = useState(0);
  const fnRef = useRef(fn);

  // Track the latest fn without making it a fetch dependency (the caller passes
  // an inline closure each render). Runs before the fetch effect below.
  useEffect(() => {
    fnRef.current = fn;
  });

  const reload = useCallback(() => setTick((t) => t + 1), []);

  useEffect(() => {
    if (!enabled) {
      setLoading(false);
      return;
    }
    const controller = new AbortController();
    let active = true;
    setLoading(true);
    setError(null);

    fnRef
      .current(controller.signal)
      .then((result) => {
        if (active) {
          setData(result);
          setError(null);
        }
      })
      .catch((err) => {
        if (!active || err.name === "AbortError") return;
        setError(err);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
      controller.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick, enabled]);

  return { data, error, loading, reload, setData };
}
