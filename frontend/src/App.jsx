/**
 * Application shell for the Agent Operations Dashboard.
 *
 * Wires the router + auth provider and declares the route table. Public routes
 * (login/register) redirect authenticated users to the dashboard; every other
 * route is guarded by <ProtectedRoute> and rendered inside <DashboardLayout>.
 *
 * The previous single-file chat demo has been replaced by this dashboard while
 * preserving the existing stack (Vite + React + Tailwind + lucide-react).
 */

import { Router, Routes, useNavigate } from "./lib/router.jsx";
import { AuthProvider, useAuth } from "./auth/AuthContext.jsx";
import ProtectedRoute from "./auth/ProtectedRoute.jsx";
import DashboardLayout from "./components/layout/DashboardLayout.jsx";
import { FullPageSpinner } from "./components/ui/Spinner.jsx";

import LoginPage from "./pages/LoginPage.jsx";
import RegisterPage from "./pages/RegisterPage.jsx";
import OverviewPage from "./pages/OverviewPage.jsx";
import RunsPage from "./pages/RunsPage.jsx";
import RunDetailPage from "./pages/RunDetailPage.jsx";
import SubmitRunPage from "./pages/SubmitRunPage.jsx";
import ObservabilityPage from "./pages/ObservabilityPage.jsx";
import HealthPage from "./pages/HealthPage.jsx";
import NotFoundPage from "./pages/NotFoundPage.jsx";
import { useEffect } from "react";

/** Redirect already-authenticated users away from auth screens. */
function PublicOnly({ children }) {
  const { isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();
  useEffect(() => {
    if (!isLoading && isAuthenticated) navigate("/", { replace: true });
  }, [isLoading, isAuthenticated, navigate]);
  if (isLoading) return <FullPageSpinner label="Loading…" />;
  return children;
}

/** Wrap a page in the auth guard + dashboard chrome. */
function dash(element) {
  return (
    <ProtectedRoute>
      <DashboardLayout>{element}</DashboardLayout>
    </ProtectedRoute>
  );
}

const routes = [
  { path: "/login", element: <PublicOnly><LoginPage /></PublicOnly> },
  { path: "/register", element: <PublicOnly><RegisterPage /></PublicOnly> },
  { path: "/", element: dash(<OverviewPage />) },
  { path: "/runs", element: dash(<RunsPage />) },
  { path: "/runs/:id", element: dash(<RunDetailPage />) },
  { path: "/run", element: dash(<SubmitRunPage />) },
  { path: "/observability", element: dash(<ObservabilityPage />) },
  { path: "/health", element: dash(<HealthPage />) },
];

export default function App() {
  return (
    <Router>
      <AuthProvider>
        <Routes routes={routes} fallback={dash(<NotFoundPage />)} />
      </AuthProvider>
    </Router>
  );
}
