/**
 * Professional dashboard shell (Phase 4): a fixed sidebar (primary navigation),
 * a top bar (current user, environment status, theme + logout) and the routed
 * main content. Responsive: on narrow screens the sidebar collapses into a
 * slide-over drawer (Phase 18) while keeping the desktop ops experience intact.
 */

import { useState } from "react";
import {
  LayoutDashboard,
  ListTree,
  Activity,
  PlayCircle,
  HeartPulse,
  Brain,
  LogOut,
  Sun,
  Moon,
  Menu,
  X,
  ShieldCheck,
} from "lucide-react";
import { Link, useLocation, useNavigate } from "../../lib/router.jsx";
import { useAuth } from "../../auth/AuthContext.jsx";
import { useTheme } from "../../hooks/useTheme.js";
import { API_BASE_URL } from "../../lib/apiClient.js";

const NAV = [
  { to: "/", label: "Overview", icon: LayoutDashboard, exact: true },
  { to: "/runs", label: "Agent Runs", icon: ListTree },
  { to: "/run", label: "Submit Task", icon: PlayCircle },
  { to: "/observability", label: "Observability", icon: Activity, admin: true },
  { to: "/health", label: "System Health", icon: HeartPulse },
];

function isActive(pathname, item) {
  if (item.exact) return pathname === item.to;
  return pathname === item.to || pathname.startsWith(item.to + "/");
}

function SidebarContent({ pathname, onNavigate, isAdmin }) {
  return (
    <>
      <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", padding: "1.25rem 1.1rem" }}>
        <div
          style={{
            width: 34, height: 34, borderRadius: 9, display: "grid", placeItems: "center",
            background: "color-mix(in srgb, var(--accent) 18%, transparent)", color: "var(--accent)",
          }}
        >
          <Brain size={20} />
        </div>
        <div>
          <div style={{ fontWeight: 700, fontSize: "0.95rem", lineHeight: 1.1 }}>Agent Ops</div>
          <div className="faint" style={{ fontSize: "0.72rem" }}>Process Intelligence</div>
        </div>
      </div>

      <nav aria-label="Primary" style={{ display: "flex", flexDirection: "column", gap: "0.25rem", padding: "0 0.6rem" }}>
        {NAV.map((item) => {
          const Icon = item.icon;
          const active = isActive(pathname, item);
          return (
            <Link
              key={item.to}
              to={item.to}
              className={`nav-link ${active ? "active" : ""}`}
              aria-current={active ? "page" : undefined}
              onClick={onNavigate}
            >
              <Icon size={18} aria-hidden="true" />
              <span style={{ flex: 1 }}>{item.label}</span>
              {item.admin && !isAdmin && (
                <span title="Requires admin" className="faint" style={{ display: "inline-flex" }}>
                  <ShieldCheck size={13} />
                </span>
              )}
            </Link>
          );
        })}
      </nav>
    </>
  );
}

export default function DashboardLayout({ children }) {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { user, isAdmin, logout } = useAuth();
  const { theme, toggle } = useTheme();
  const [drawerOpen, setDrawerOpen] = useState(false);

  const apiHost = (() => {
    try {
      return new URL(API_BASE_URL).host;
    } catch {
      return API_BASE_URL;
    }
  })();

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", background: "var(--bg)" }}>
      {/* Desktop sidebar */}
      <aside
        className="dash-sidebar"
        style={{
          width: 244,
          borderRight: "1px solid var(--border)",
          background: "var(--bg-subtle)",
          position: "sticky",
          top: 0,
          height: "100vh",
          overflowY: "auto",
          flex: "none",
        }}
      >
        <SidebarContent pathname={pathname} isAdmin={isAdmin} />
      </aside>

      {/* Mobile drawer */}
      {drawerOpen && (
        <div
          className="dash-drawer"
          style={{ position: "fixed", inset: 0, zIndex: 40 }}
          onClick={() => setDrawerOpen(false)}
        >
          <div style={{ position: "absolute", inset: 0, background: "rgba(0,0,0,0.5)" }} />
          <aside
            onClick={(e) => e.stopPropagation()}
            style={{
              position: "relative", width: 260, height: "100%",
              background: "var(--bg-subtle)", borderRight: "1px solid var(--border)", overflowY: "auto",
            }}
          >
            <div style={{ display: "flex", justifyContent: "flex-end", padding: "0.75rem 0.75rem 0" }}>
              <button className="btn btn-ghost btn-sm" onClick={() => setDrawerOpen(false)} aria-label="Close menu">
                <X size={18} />
              </button>
            </div>
            <SidebarContent pathname={pathname} isAdmin={isAdmin} onNavigate={() => setDrawerOpen(false)} />
          </aside>
        </div>
      )}

      {/* Main column */}
      <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
        <header
          style={{
            display: "flex", alignItems: "center", justifyContent: "space-between", gap: "1rem",
            padding: "0.75rem 1.25rem", borderBottom: "1px solid var(--border)",
            background: "var(--surface)", position: "sticky", top: 0, zIndex: 20,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <button
              className="btn btn-ghost btn-sm dash-menu-btn"
              onClick={() => setDrawerOpen(true)}
              aria-label="Open menu"
              style={{ display: "none" }}
            >
              <Menu size={18} />
            </button>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <span className="dot" style={{ background: "var(--ok)" }} />
              <span className="muted" style={{ fontSize: "0.8rem" }}>
                API <span className="mono" style={{ color: "var(--text)" }}>{apiHost}</span>
              </span>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
            <button className="btn btn-ghost btn-sm" onClick={toggle} aria-label="Toggle theme">
              {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
            </button>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <div style={{ textAlign: "right", lineHeight: 1.15 }} className="dash-user">
                <div style={{ fontSize: "0.82rem", fontWeight: 600, maxWidth: 180, overflow: "hidden", textOverflow: "ellipsis" }}>
                  {user?.email}
                </div>
                <div className="faint" style={{ fontSize: "0.7rem" }}>
                  {isAdmin ? "Administrator" : "Member"}
                </div>
              </div>
              <div
                aria-hidden="true"
                style={{
                  width: 32, height: 32, borderRadius: 999, display: "grid", placeItems: "center",
                  background: "var(--surface-2)", border: "1px solid var(--border)", fontSize: "0.8rem", fontWeight: 700,
                }}
              >
                {(user?.email || "?").charAt(0).toUpperCase()}
              </div>
            </div>
            <button className="btn btn-sm" onClick={handleLogout}>
              <LogOut size={15} /> <span className="dash-logout-label">Logout</span>
            </button>
          </div>
        </header>

        <main style={{ flex: 1, padding: "1.5rem", maxWidth: 1280, width: "100%", margin: "0 auto" }}>
          {children}
        </main>
      </div>
    </div>
  );
}
