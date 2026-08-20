/* eslint-disable react-refresh/only-export-components */
/**
 * Minimal History-API router.
 *
 * The dashboard has a small, fixed set of routes, so a ~120-line router keeps
 * us dependency-free (per the milestone's "no unnecessary dependencies" rule)
 * while still supporting path params (`/runs/:id`), query strings, programmatic
 * navigation and active-link styling.
 */

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useMemo,
} from "react";

const RouterContext = createContext(null);
const ParamsContext = createContext({});

function currentLocation() {
  return {
    pathname: window.location.pathname,
    search: window.location.search,
  };
}

export function Router({ children }) {
  const [location, setLocation] = useState(currentLocation);

  useEffect(() => {
    const onPop = () => setLocation(currentLocation());
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const navigate = useCallback((to, { replace = false } = {}) => {
    if (replace) window.history.replaceState({}, "", to);
    else window.history.pushState({}, "", to);
    setLocation(currentLocation());
    window.scrollTo({ top: 0, behavior: "instant" in window ? "instant" : "auto" });
  }, []);

  const value = useMemo(() => ({ location, navigate }), [location, navigate]);
  return <RouterContext.Provider value={value}>{children}</RouterContext.Provider>;
}

export function useRouter() {
  const ctx = useContext(RouterContext);
  if (!ctx) throw new Error("useRouter must be used within <Router>");
  return ctx;
}

export function useLocation() {
  return useRouter().location;
}

export function useNavigate() {
  return useRouter().navigate;
}

export function useParams() {
  return useContext(ParamsContext);
}

/** [URLSearchParams, setSearchParams] — setSearchParams accepts an object. */
export function useSearchParams() {
  const { location, navigate } = useRouter();
  const params = useMemo(
    () => new URLSearchParams(location.search),
    [location.search]
  );
  const setSearchParams = useCallback(
    (next, { replace = true } = {}) => {
      const sp = new URLSearchParams();
      const entries =
        next instanceof URLSearchParams ? next.entries() : Object.entries(next);
      for (const [k, v] of entries) {
        if (v !== null && v !== undefined && v !== "") sp.append(k, String(v));
      }
      const qs = sp.toString();
      navigate(location.pathname + (qs ? `?${qs}` : ""), { replace });
    },
    [location.pathname, navigate]
  );
  return [params, setSearchParams];
}

/** Compile "/runs/:id" into a matcher. */
function matchPath(pattern, pathname) {
  const pSeg = pattern.split("/").filter(Boolean);
  const uSeg = pathname.split("/").filter(Boolean);
  if (pSeg.length !== uSeg.length) return null;
  const params = {};
  for (let i = 0; i < pSeg.length; i++) {
    if (pSeg[i].startsWith(":")) {
      params[pSeg[i].slice(1)] = decodeURIComponent(uSeg[i]);
    } else if (pSeg[i] !== uSeg[i]) {
      return null;
    }
  }
  return params;
}

/**
 * Render the first matching route.
 * @param {Array<{path:string, element:React.ReactNode}>} routes
 * @param {React.ReactNode} [fallback] rendered when nothing matches (404)
 */
export function Routes({ routes, fallback = null }) {
  const { pathname } = useLocation();
  for (const route of routes) {
    const params = matchPath(route.path, pathname);
    if (params) {
      return (
        <ParamsContext.Provider value={params}>
          {route.element}
        </ParamsContext.Provider>
      );
    }
  }
  return fallback;
}

/** Accessible client-side link. */
export function Link({ to, children, className, onClick, ...rest }) {
  const navigate = useNavigate();
  const handle = (e) => {
    if (
      e.defaultPrevented ||
      e.button !== 0 ||
      e.metaKey ||
      e.ctrlKey ||
      e.shiftKey ||
      e.altKey
    ) {
      return; // let the browser handle modified clicks / new tabs
    }
    e.preventDefault();
    onClick?.(e);
    navigate(to);
  };
  return (
    <a href={to} className={className} onClick={handle} {...rest}>
      {children}
    </a>
  );
}
