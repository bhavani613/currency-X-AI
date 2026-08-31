import { useState } from "react";
import { Navigate, Link, useNavigate, useLocation } from "react-router-dom";
import { BarChart3, Eye, EyeOff, Mail, Lock } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login, getStoredUser, isAuthenticated, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from?.pathname || "/dashboard";

  const [form, setForm] = useState({ email: "", password: "", remember: false });
  const [show, setShow] = useState(false);
  const [errors, setErrors] = useState({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // While restoring the persisted session, avoid flashing.
  if (authLoading) return null;

  // Already authenticated? Send them back to the dashboard.
  if (isAuthenticated) {
    return <Navigate to={from} replace />;
  }

  const validate = () => {
    const e = {};
    if (!form.email.trim()) e.email = "Email is required";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) e.email = "Enter a valid email";
    if (!form.password) e.password = "Password is required";
    return e;
  };

  const handleSubmit = (ev) => {
    ev.preventDefault();
    const e = validate();
    setErrors(e);
    setError("");
    if (Object.keys(e).length) return;
    setLoading(true);
    // Mock login — validate against the stored profile (localStorage).
    setTimeout(() => {
      const stored = getStoredUser(form.email);
      if (!stored) {
        setError("No account found. Please sign up first.");
        setLoading(false);
        return;
      }
      if (stored.password && stored.password !== form.password) {
        setError("Incorrect password. Please try again.");
        setLoading(false);
        return;
      }
      login(stored, form.remember);
      navigate(from, { replace: true });
    }, 700);
  };

  const handleGoogle = () => {
    login({ email: "demo@currencyx.app", name: "Demo User" });
    navigate(from, { replace: true });
  };

  return (
    <div className="auth-screen site">
      <div className="auth-layout">
        <div className="auth-panel">
          <Link to="/" className="brand auth-brand">
            <span className="brand-mark"><BarChart3 size={20} /></span>
            <span className="brand-text">Currency<span>X</span> AI</span>
          </Link>

          <div className="auth-intro">
            <h2>Welcome back.</h2>
            <p>Sign in to see the real cost of your international payments.</p>
          </div>

          <form className="auth-form" onSubmit={handleSubmit} noValidate>
            {error && (
              <div className="auth-error" role="alert">
                {error}
              </div>
            )}
            <div className="field">
              <label htmlFor="login-email">Email</label>
              <div className="input-wrap with-icon">
                <Mail size={17} className="field-icon" />
                <input
                  id="login-email"
                  type="email"
                  placeholder="you@example.com"
                  value={form.email}
                  autoComplete="email"
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                />
              </div>
              {errors.email && <span className="field-error">{errors.email}</span>}
            </div>

            <div className="field">
              <label htmlFor="login-password">Password</label>
              <div className="input-wrap with-icon">
                <Lock size={17} className="field-icon" />
                <input
                  id="login-password"
                  type={show ? "text" : "password"}
                  placeholder="••••••••"
                  value={form.password}
                  autoComplete="current-password"
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                />
                <button
                  type="button"
                  className="password-toggle"
                  aria-label="Toggle password visibility"
                  onClick={() => setShow((v) => !v)}
                >
                  {show ? <EyeOff size={17} /> : <Eye size={17} />}
                </button>
              </div>
              {errors.password && <span className="field-error">{errors.password}</span>}
            </div>

            <div className="auth-options">
              <label className="checkbox">
                <input
                  type="checkbox"
                  checked={form.remember}
                  onChange={(e) => setForm({ ...form, remember: e.target.checked })}
                />
                <span>Remember me</span>
              </label>
              <a href="#forgot" className="forgot" onClick={(e) => e.preventDefault()}>
                Forgot password?
              </a>
            </div>

            <button className="btn btn-primary btn-block" disabled={loading}>
              {loading ? "Signing in…" : "Login"}
            </button>
          </form>

          <div className="auth-divider"><span>or</span></div>

          <button className="btn btn-google btn-block" onClick={handleGoogle}>
            <GoogleIcon /> Continue with Google
          </button>

          <p className="auth-switch">
            Don't have an account? <Link to="/signup">Sign up</Link>
          </p>
        </div>
<div className="auth-side">
          <div className="auth-quote card">
            <p>
              "CurrencyX AI showed me I was paying ₹4,000 extra per transfer on
              hidden FX markups. I'll never wire money the old way again."
            </p>
            <span className="quote-meta">— Anjali R., frequent international sender</span>
          </div>
          <div className="auth-side-stats">
            <div><strong>₹4.2K</strong><span>avg. savings per user</span></div>
            <div><strong>200K+</strong><span>transfers analysed</span></div>
          </div>
        </div>
      </div>
    </div>
  );
}

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.27-4.74 3.27-8.1z" />
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A11 11 0 0 0 12 23z" />
      <path fill="#FBBC05" d="M5.84 14.1a6.6 6.6 0 0 1 0-4.2V7.06H2.18a11 11 0 0 0 0 9.88l3.66-2.84z" />
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15A10.96 10.96 0 0 0 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
    </svg>
  );
}