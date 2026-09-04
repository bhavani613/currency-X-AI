import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, RefreshCcw, XCircle, CheckCircle2 } from "lucide-react";
import { getRecoveryCase, retryRecoveryCase, completeRecoveryCase, dismissRecoveryCase } from "../services/api";
import { buildRetryPrefill } from "../services/retryPrefill";
import { DashboardShell } from "./Dashboard";

const fmtMoney = (n) =>
  typeof n === "number" ? n.toLocaleString("en-IN", { maximumFractionDigits: 2 }) : "—";

const fmtDate = (iso) => {
  try {
    return new Date(iso).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
  } catch {
    return "—";
  }
};

const riskClass = (level) =>
  ({ LOW: "low", MEDIUM: "medium", HIGH: "high", CRITICAL: "critical" }[level] || "low");

const REC_STATUS_CLASS = {
  PENDING: "pending",
  ACCEPTED: "success",
  DISMISSED: "failed",
  EXECUTED: "success",
};

const ACTION_LABELS = {
  RETRY_LATER: "Retry later",
  RETRY_SOON: "Retry soon",
  RETRY_IMMEDIATELY: "Retry immediately",
  REQUEST_ALTERNATIVE_PAYMENT_METHOD: "Use alternative payment method",
  SEND_RECOVERY_REMINDER: "Send recovery reminder",
};

export default function RecoveryCaseDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [item, setItem] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setItem(await getRecoveryCase(id));
    } catch (err) {
      setError(err.message || "Failed to load the recovery case.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  const handleRetry = async () => {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      const res = await retryRecoveryCase(id);
      setNotice(res.message || "Recommendation accepted.");
      const rp = res.retry_payment || {};
      // Store recovery case ID so Checkout can mark it recovered after verified payment
      sessionStorage.setItem("currencyx_recovery_case_id", res.case_id || id);
      sessionStorage.setItem("currencyx_recovery_amount", String(rp.amount || 0));
      navigate("/analyze", {
        state: {
          amount: rp.amount != null ? String(rp.amount) : "",
          sourceCurrency: rp.currency || "INR",
          destinationCountry: "",
          destinationCurrency: "",
          purpose: "Other",
        },
      });
    } catch (err) {
      setError(err.message || "Failed to accept the recommendation.");
      await load();
    } finally {
      setBusy(false);
    }
  };

  const handleDismiss = async () => {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      const res = await dismissRecoveryCase(id);
      setNotice(res.message || "Recommendation dismissed.");
      await load();
    } catch (err) {
      setError(err.message || "Failed to dismiss the recommendation.");
      await load();
    } finally {
      setBusy(false);
    }
  };

  const actionable = item?.status === "PENDING";

  return (
    <DashboardShell active="/recovery">
      <Link to="/recovery" className="back-link">
        <ArrowLeft size={16} /> Back to Revenue Recovery
      </Link>

      <div className="page-head">
        <div>
          <h1 className="page-title">Recovery Case</h1>
          <p className="page-sub">Case reference: {id}</p>
        </div>
      </div>

      {error && (
        <div className="alert error" role="alert">
          <XCircle size={16} /> {error}{" "}
          <button className="alert-retry" onClick={() => (item ? load() : navigate("/recovery"))}>
            {item ? "Retry" : "Back"}
          </button>
        </div>
      )}
      {notice && (
        <div className="alert success" role="status">
          <CheckCircle2 size={16} /> {notice}
        </div>
      )}

      {loading ? (
        <div className="card results-loading">
          <div className="spinner" /> <p>Loading case…</p>
        </div>
      ) : item ? (
        <div className="card recovery-detail">
          <div className="recovery-case-head">
            <div>
              <span className={`badge risk-${riskClass(item.risk_level)}`}>
                {item.risk_level} RISK
              </span>{" "}
              <span className={`badge ${REC_STATUS_CLASS[item.status] || "pending"}`}>
                {item.status}
              </span>{" "}
              <span className="badge pending">{item.attempt_status}</span>
            </div>
            <span className="recovery-probability">
              {item.recovery_probability}% recovery probability
            </span>
          </div>

          <h2 className="recovery-case-title">
            ₹{fmtMoney(item.amount)} {item.currency} via {item.payment_method}
          </h2>

          <div className="detail-grid">
            <section>
              <h4>Payment Information</h4>
              <dl className="recovery-meta">
                <div>
                  <dt>Payment attempt</dt>
                  <dd>{item.payment_attempt_id}</dd>
                </div>
                <div>
                  <dt>Detected</dt>
                  <dd>{fmtDate(item.created_at)}</dd>
                </div>
                <div>
                  <dt>Attempt status</dt>
                  <dd>{item.attempt_status}</dd>
                </div>
              </dl>
            </section>

            <section>
              <h4>Failure Details</h4>
              <dl className="recovery-meta">
                <div>
                  <dt>Category</dt>
                  <dd>{item.failure_category.replaceAll("_", " ")}</dd>
                </div>
                <div>
                  <dt>Reason</dt>
                  <dd>{item.normalized_reason || "—"}</dd>
                </div>
                {item.failure_message && (
                  <div>
                    <dt>Gateway message</dt>
                    <dd>{item.failure_message}</dd>
                  </div>
                )}
              </dl>
            </section>

            <section>
              <h4>Recovery Recommendation</h4>
              <dl className="recovery-meta">
                <div>
                  <dt>Recommended action</dt>
                  <dd>{ACTION_LABELS[item.recommended_action] || item.recommended_action}</dd>
                </div>
                {item.alternative_payment_method && (
                  <div>
                    <dt>Alternative method</dt>
                    <dd>{item.alternative_payment_method}</dd>
                  </div>
                )}
                {item.retry_after && (
                  <div>
                    <dt>Suggested retry</dt>
                    <dd>{fmtDate(item.retry_after)}</dd>
                  </div>
                )}
                <div>
                  <dt>Severity</dt>
                  <dd>{item.severity}</dd>
                </div>
              </dl>
              {item.reasoning && <p className="recovery-explanation">{item.reasoning}</p>}
            </section>
          </div>

          <div className="recovery-actions">
            {actionable ? (
              <>
                <button className="btn btn-primary" onClick={handleRetry} disabled={busy}>
                  {busy ? "Working…" : "Accept & Restart Payment"}
                </button>
                <button className="btn btn-ghost" onClick={handleDismiss} disabled={busy}>
                  Dismiss
                </button>
              </>
            ) : (
              <p className="recovery-status-note">
                This recommendation has been {item.status.toLowerCase()} — no further actions are
                available.
              </p>
            )}
          </div>
          <p className="recovery-disclaimer">
            Accepting a recommendation restarts the normal checkout flow. The payment only
            completes after successful Razorpay verification — nothing is charged from this page.
          </p>
        </div>
      ) : (
        !error && (
          <div className="card recovery-empty">
            <h3>Recovery case not found.</h3>
            <Link to="/recovery" className="btn btn-primary">
              Back to Revenue Recovery
            </Link>
          </div>
        )
      )}

      {item && (
        <button className="btn btn-ghost btn-sm" onClick={() => load()} disabled={loading || busy}>
          <RefreshCcw size={14} /> Refresh case
        </button>
      )}
    </DashboardShell>
  );
}