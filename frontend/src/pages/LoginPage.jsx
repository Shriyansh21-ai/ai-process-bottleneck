import { useState } from "react";
import { AlertCircle } from "lucide-react";
import AuthShell from "./AuthShell.jsx";
import { Link, useNavigate, useSearchParams } from "../lib/router.jsx";
import { useAuth } from "../auth/AuthContext.jsx";
import { Spinner } from "../components/ui/Spinner.jsx";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const next = params.get("next") || "/";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email.trim(), password);
      navigate(decodeURIComponent(next), { replace: true });
    } catch (err) {
      setError(err?.message || "Sign in failed. Please try again.");
      setSubmitting(false);
    }
  };

  return (
    <AuthShell
      title="Sign in"
      subtitle="Access your agent operations dashboard."
      footer={
        <>
          Don&apos;t have an account? <Link to="/register" style={{ color: "var(--accent)", fontWeight: 600 }}>Create one</Link>
        </>
      }
    >
      <form onSubmit={onSubmit} noValidate>
        {error && (
          <div role="alert" className="badge-danger" style={{ display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.6rem 0.75rem", borderRadius: 9, fontSize: "0.85rem", marginBottom: "1rem", fontWeight: 500 }}>
            <AlertCircle size={16} aria-hidden="true" /> {error}
          </div>
        )}

        <div style={{ marginBottom: "1rem" }}>
          <label className="field-label" htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            className="input"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            aria-invalid={!!error}
          />
        </div>

        <div style={{ marginBottom: "1.25rem" }}>
          <label className="field-label" htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            className="input"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            aria-invalid={!!error}
          />
        </div>

        <button type="submit" className="btn btn-primary" style={{ width: "100%" }} disabled={submitting || !email || !password}>
          {submitting ? <Spinner size={16} /> : null}
          {submitting ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </AuthShell>
  );
}
