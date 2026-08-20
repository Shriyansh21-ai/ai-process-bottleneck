/**
 * Route guard. Unauthenticated users are redirected to /login (Phase 3), with
 * the attempted path preserved in `?next=` so they return after signing in.
 * While the session is bootstrapping we show a neutral loader rather than
 * flashing the login screen.
 */

import { useEffect } from "react";
import { useAuth } from "./AuthContext.jsx";
import { useNavigate, useLocation } from "../lib/router.jsx";
import { FullPageSpinner } from "../components/ui/Spinner.jsx";

export default function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      const next = encodeURIComponent(location.pathname + location.search);
      navigate(`/login?next=${next}`, { replace: true });
    }
  }, [isLoading, isAuthenticated, navigate, location.pathname, location.search]);

  if (isLoading) return <FullPageSpinner label="Restoring your session…" />;
  if (!isAuthenticated) return null;
  return children;
}
