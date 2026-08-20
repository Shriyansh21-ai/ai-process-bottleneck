import { useState } from "react";
import { AlertCircle } from "lucide-react";
import AuthShell from "./AuthShell.jsx";
import { Link, useNavigate } from "../lib/router.jsx";
import { useAuth } from "../auth/AuthContext.jsx";
import { Spinner } from "../components/ui/Spinner.jsx";

export default function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  // Mirror the backend rule (min 8 chars) so users get instant feedback.
  const passwordTooShort = password.length > 0 && password.length < 8;
  const mismatch = confirm.length > 0 && confirm !== password;
  const canSubmit = email && password.length >= 8 && confirm === password && !submitting;

  const onSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    if (!canSubmit) return;
    setSubmitting(true);
    try {
      await register(email.trim(), password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err?.message || "Registration failed. Please try again.");
      setSubmitting(false);
    }
  };

  return (
    <AuthShell
      title="Create your account"
      subtitle="Register to start monitoring agent operations."
      footer={
        <>
          Already have an account? <Link to="/login" style={{ color: "var(--accent)", fontWeight: 600 }}>Sign in</Link>
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
          <input id="email" type="email" className="input" autoComplete="email" required
            value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
        </div>

        <div style={{ marginBottom: "1rem" }}>
          <label className="field-label" htmlFor="password">Password</label>
          <input id="password" type="password" className="input" autoComplete="new-password" required minLength={8}
            value={password} onChange={(e) => setPassword(e.target.value)} placeholder="At least 8 characters"
            aria-invalid={passwordTooShort} aria-describedby="pw-help" />
          <p id="pw-help" className={passwordTooShort ? "" : "faint"} style={{ margin: "0.35rem 0 0", fontSize: "0.76rem", color: passwordTooShort ? "var(--danger)" : undefined }}>
            {passwordTooShort ? "Password must be at least 8 characters." : "Minimum 8 characters."}
          </p>
        </div>

        <div style={{ marginBottom: "1.25rem" }}>
          <label className="field-label" htmlFor="confirm">Confirm password</label>
          <input id="confirm" type="password" className="input" autoComplete="new-password" required
            value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="Re-enter your password"
            aria-invalid={mismatch} aria-describedby="confirm-help" />
          {mismatch && (
            <p id="confirm-help" style={{ margin: "0.35rem 0 0", fontSize: "0.76rem", color: "var(--danger)" }}>
              Passwords do not match.
            </p>
          )}
        </div>

        <button type="submit" className="btn btn-primary" style={{ width: "100%" }} disabled={!canSubmit}>
          {submitting ? <Spinner size={16} /> : null}
          {submitting ? "Creating account…" : "Create account"}
        </button>
      </form>
    </AuthShell>
  );
}
