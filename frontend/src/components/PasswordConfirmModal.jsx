import { useState, useRef, useEffect } from "react";
import { X, Lock } from "lucide-react";
import { verifyPassword } from "../services/api";

/**
 * PasswordConfirmModal
 *
 * A clean modal that asks the user to enter their CURRENT account password
 * before a sensitive action (e.g. executing a payment).
 *
 * Security:
 * - The password lives ONLY in component state (memory) — never in
 *   localStorage or sessionStorage.
 * - State is cleared on success, failure, or close.
 * - No logging of the password.
 */
export default function PasswordConfirmModal({
  isOpen,
  onClose,
  onConfirmed,
  title = "Confirm your password",
  subtitle = "Please enter your current account password to continue with this payment.",
}) {
  const [password, setPassword] = useState("");
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (verifying || !password) return;
    setVerifying(true);
    setError("");
    try {
      await verifyPassword(password);
      setPassword("");
      setVerifying(false);
      setError("");
      onConfirmed();
    } catch (err) {
      setError(err.message || "Incorrect password. Please try again.");
      setPassword("");
      setVerifying(false);
    }
  };

  const handleClose = () => {
    setPassword("");
    setError("");
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={handleClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3>
            <Lock size={18} style={{ marginRight: "8px", verticalAlign: "middle" }} />
            {title}
          </h3>
          <button className="icon-btn" onClick={handleClose} aria-label="Close" disabled={verifying}>
            <X size={18} />
          </button>
        </div>
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
          <p style={{ color: "var(--muted)", fontSize: "14px", margin: 0 }}>{subtitle}</p>
          <div className="field">
            <label htmlFor="pw-confirm">Current password</label>
            <input
              id="pw-confirm"
              ref={inputRef}
              type="password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                if (error) setError("");
              }}
              placeholder="Enter your password"
              autoComplete="current-password"
              disabled={verifying}
            />
          </div>
          {error && <div className="field-error">{error}</div>}
          <div className="modal-actions" style={{ display: "flex", gap: "10px", marginTop: "8px" }}>
            <button type="button" className="btn btn-ghost" onClick={handleClose} disabled={verifying}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={verifying || !password}>
              {verifying ? "Verifying…" : "Confirm & Continue"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
