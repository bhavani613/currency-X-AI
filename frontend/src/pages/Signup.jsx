import { useState } from "react";
import { Navigate, Link, useNavigate } from "react-router-dom";
import { BarChart3, Eye, EyeOff, Mail, Lock, User, Check } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function Signup() {
  const { signup, isAuthenticated, loading: authLoading } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({
    fullName: "",
    email: "",
    password: "",
    confirm: "",
    agreed: false,
  });
  const [show, setShow] = useState(false);
  const [errors, setErrors] = useState({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // While restoring the persisted session, avoid flashing.
  if (authLoading) return null;

  // Already signed in? Send them to the dashboard.
  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  const validate = () => {
    const e = {};
    if (!form.fullName.trim()) e.fullName = "Full name is required";
    if (!form.email.trim()) e.email = "Email is required";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) e.email = "Enter a valid email";
    if (!form.password) e.password = "Password is required";
    else if (passwordChecks.some((c) => !c.ok)) {
      const failed = passwordChecks.filter((c) => !c.ok).map((c) => c.label.toLowerCase());
      e.password = `Password needs: ${failed.join(", ")}`;
    }
    if (form.confirm !== form.password) e.confirm = "Passwords do not match";
    if (!form.agreed) e.agreed = "You must accept the Terms and Privacy Policy";
    return e;
  };

  const handleSubmit = async (ev) => {
    ev.preventDefault();
    const e = validate();
    setErrors(e);
    setError("");
    if (Object.keys(e).length) return;
    setLoading(true);
    try {
      // Real signup — the account is created in PostgreSQL with a bcrypt
      // password hash. The user is logged in immediately on success.
      await signup({ fullName: form.fullName.trim(), email: form.email.trim(), password: form.password });
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(err.message || "Signup failed. Please try again.");
      setLoading(false);
    }
  };

  // Strong-password requirement checklist (mirrors backend validation).
  const passwordChecks = [
    { label: "At least 8 characters", ok: form.password.length >= 8 },
    { label: "Uppercase letter", ok: /[A-Z]/.test(form.password) },
    { label: "Lowercase letter", ok: /[a-z]/.test(form.password) },
    { label: "Number", ok: /\d/.test(form.password) },
    { label: "Special character", ok: /[^A-Za-z0-9\s]/.test(form.password) },
    { label: "No spaces", ok: form.password.length > 0 && !/\s/.test(form.password) },
  ];
  const passwordOk = passwordChecks.every((c) => c.ok);
  const emailOk = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim());
  const canSubmit =
    !loading &&
    form.fullName.trim().length > 0 &&
    emailOk &&
    passwordOk &&
    form.confirm === form.password &&
    form.confirm.length > 0 &&
    form.agreed;

  return (
    <div className="auth-screen site">
      <div className="auth-layout">
        <div className="auth-panel">
          <Link to="/" className="brand auth-brand">
            <span className="brand-mark"><BarChart3 size={20} /></span>
            <span className="brand-text">Currency<span>X</span> AI</span>
          </Link>

          <div className="auth-intro">
            <h2>Create your account.</h2>
            <p>Start seeing the real cost of every international payment.</p>
          </div>

          <form className="auth-form" onSubmit={handleSubmit} noValidate>
            {error && (
              <div className="auth-error" role="alert">
                {error}
              </div>
            )}
            <div className="field">
              <label htmlFor="su-name">Full Name</label>
              <div className="input-wrap with-icon">
                <User size={17} className="field-icon" />
                <input
                  id="su-name"
                  type="text"
                  placeholder="Alex Kumar"
                  value={form.fullName}
                  autoComplete="name"
                  onChange={(e) => setForm({ ...form, fullName: e.target.value })}
                />
              </div>
              {errors.fullName && <span className="field-error">{errors.fullName}</span>}
            </div>

            <div className="field">
              <label htmlFor="su-email">Email</label>
              <div className="input-wrap with-icon">
                <Mail size={17} className="field-icon" />
                <input
                  id="su-email"
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
              <label htmlFor="su-password">Password</label>
              <div className="input-wrap with-icon">
                <Lock size={17} className="field-icon" />
                <input
                  id="su-password"
                  type={show ? "text" : "password"}
                  placeholder="Min. 8 characters"
                  value={form.password}
                  autoComplete="new-password"
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
              <ul className="password-hints pw-req">
                {passwordChecks.map((c) => (
                  <li key={c.label} className={`hint ${c.ok ? "ok" : "error"}`}>
                    <Check size={12} /> {c.label}
                  </li>
                ))}
              </ul>
            </div>
<div className="field">
              <label htmlFor="su-confirm">Confirm Password</label>
              <div className="input-wrap with-icon">
                <Lock size={17} className="field-icon" />
                <input
                  id="su-confirm"
                  type={show ? "text" : "password"}
                  placeholder="Re-enter password"
                  value={form.confirm}
                  autoComplete="new-password"
                  onChange={(e) => setForm({ ...form, confirm: e.target.value })}
                />
              </div>
              {errors.confirm && <span className="field-error">{errors.confirm}</span>}
            </div>

            <label className="checkbox">
              <input
                type="checkbox"
                checked={form.agreed}
                onChange={(e) => setForm({ ...form, agreed: e.target.checked })}
              />
              <span>
                I agree to the <a href="#terms" onClick={(e) => e.preventDefault()}>Terms</a> and{" "}
                <a href="#privacy" onClick={(e) => e.preventDefault()}>Privacy Policy</a>
              </span>
            </label>
            {errors.agreed && <span className="field-error">{errors.agreed}</span>}

            <button className="btn btn-primary btn-block" disabled={!canSubmit}>
              {loading ? "Creating account…" : "Create Account"}
            </button>
          </form>

          <p className="auth-switch">
            Already have an account? <Link to="/login">Login</Link>
          </p>
        </div>

        <div className="auth-side">
          <div className="auth-perks">
            <h3>Why join CurrencyX AI</h3>
            <ul>
              <li><Check size={16} /><span>Full cost transparency, including hidden FX markups</span></li>
              <li><Check size={16} /><span>AI recommendations to cut your transfer costs</span></li>
              <li><Check size={16} /><span>Compare 4 payment methods side-by-side</span></li>
              <li><Check size={16} /><span>Realistic savings of up to 3% per transfer</span></li>
            </ul>
          </div>
        </div>
</div>
    </div>
  );
}