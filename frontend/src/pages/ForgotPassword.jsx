import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { BarChart3, Mail, Lock, KeyRound } from "lucide-react";
import { forgotPassword, resetPassword } from "../services/api";

/**
 * ForgotPassword — public page with two modes:
 *
 * 1. Request mode (no ?token= in the URL): asks for the account email and
 *    starts a password reset. The backend always responds with a generic
 *    message so the response cannot reveal whether the email is registered.
 *    In development (EXPOSE_RESET_TOKEN_IN_RESPONSE=true) the backend also
 *    returns a one-time dev token which is shown as a clickable reset link
 *    since SMTP/email delivery is not configured.
 *
 * 2. Reset mode (?token=... in the URL): lets the user choose a new strong
 *    password. The single-use token is invalidated after a successful reset.
 */
export default function ForgotPassword() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const token = params.get("token") || "";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [devLink, setDevLink] = useState("");
  const [loading, setLoading] = useState(false);

  const validatePassword = () => {
    if (password !== confirm) return "Passwords do not match";
    if (
      password.length < 8 ||
      !/[A-Z]/.test(password) ||
      !/[a-z]/.test(password) ||
      !/[0-9]/.test(password) ||
      !/[^A-Za-z0-9]/.test(password)
    ) {
      return "Password must be 8+ chars with upper, lower, number and special character";
    }
    return "";
  };

  const handleRequest = async (ev) => {
    ev.preventDefault();
    setError("");
    setMessage("");
    setDevLink("");
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      setError("Enter a valid email");
      return;
    }
    setLoading(true);
    try {
      const res = await forgotPassword({ email: email.trim() });
      setMessage(res.message || "If an account with that email exists, a reset link has been sent.");
      if (res.dev_reset_token) {
        // Dev-only: SMTP is not configured, so expose the one-time link here.
        setDevLink(`/forgot-password?token=${encodeURIComponent(res.dev_reset_token)}`);
      }
    } catch (err) {
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async (ev) => {
    ev.preventDefault();
    setError("");
    setMessage("");
    const pwError = validatePassword();
    if (pwError) {
      setError(pwError);
      return;
    }
    setLoading(true);
    try {
      await resetPassword({ token, password });
      setMessage("Password reset successfully. You can now log in with your new password.");
      setTimeout(() => navigate("/login", { replace: true }), 2000);
    } catch (err) {
      setError(err.message || "Password reset failed. The link may be expired or already used.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-screen site">
      <div className="auth-layout">
        <div className="auth-panel">
          <Link to="/" className="brand auth-brand">
            <span className="brand-mark"><BarChart3 size={20} /></span>
            <span className="brand-text">Currency<span>X</span> AI</span>
          </Link>

          {token ? (
            <>
              <div className="auth-intro">
                <h2>Choose a new password.</h2>
                <p>Pick a strong password you have not used before.</p>
              </div>

              <form className="auth-form" onSubmit={handleReset} noValidate>
                {error && (
                  <div className="auth-error" role="alert">{error}</div>
                )}
                {message && (
                  <div className="auth-success" role="status">{message}</div>
                )}
                <div className="field">
                  <label htmlFor="reset-password">New password</label>
                  <div className="input-wrap with-icon">
                    <Lock size={17} className="field-icon" />
                    <input
                      id="reset-password"
                      type="password"
                      value={password}
                      onChange={(ev) => setPassword(ev.target.value)}
                      placeholder="New password"
                      autoComplete="new-password"
                      required
                    />
                  </div>
                </div>
                <div className="field">
                  <label htmlFor="reset-confirm">Confirm password</label>
                  <div className="input-wrap with-icon">
                    <Lock size={17} className="field-icon" />
                    <input
                      id="reset-confirm"
                      type="password"
                      value={confirm}
                      onChange={(ev) => setConfirm(ev.target.value)}
                      placeholder="Confirm new password"
                      autoComplete="new-password"
                      required
                    />
                  </div>
                </div>
                <button className="btn btn-primary btn-block" type="submit" disabled={loading}>
                  {loading ? "Resetting…" : "Reset password"}
                </button>
                <p className="auth-alt">
                  <Link to="/login">Back to login</Link>
                </p>
              </form>
            </>
          ) : (
            <>
              <div className="auth-intro">
                <h2>Forgot your password?</h2>
                <p>Enter your account email and we will start a password reset.</p>
              </div>

              <form className="auth-form" onSubmit={handleRequest} noValidate>
                {error && (
                  <div className="auth-error" role="alert">{error}</div>
                )}
                {message && (
                  <div className="auth-success" role="status">{message}</div>
                )}
                {devLink && (
                  <div className="auth-success" role="status">
                    Dev mode (no SMTP configured):{" "}
                    <Link to={devLink}>open your reset link</Link>
                  </div>
                )}
                <div className="field">
                  <label htmlFor="forgot-email">Email</label>
                  <div className="input-wrap with-icon">
                    <Mail size={17} className="field-icon" />
                    <input
                      id="forgot-email"
                      type="email"
                      value={email}
                      onChange={(ev) => setEmail(ev.target.value)}
                      placeholder="you@example.com"
                      autoComplete="email"
                      required
                    />
                  </div>
                </div>
                <button className="btn btn-primary btn-block" type="submit" disabled={loading}>
                  {loading ? "Sending…" : "Send reset link"}
                </button>
                <p className="auth-alt">
                  Remembered it? <Link to="/login">Back to login</Link>
                </p>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
