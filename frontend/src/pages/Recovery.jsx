import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  RefreshCcw,
  ShieldAlert,
  IndianRupee,
  TrendingUp,
  AlertTriangle,
  XCircle,
  ArrowRight,
} from "lucide-react";
import {
  getRecoverySummary,
  getRecoveryCases,
  retryRecoveryCase,
  completeRecoveryCase,
  dismissRecoveryCase,
  seedDemoRecoveryCases,
} from "../services/api";
import { buildRetryPrefill } from "../services/retryPrefill";
import { DashboardShell } from "./Dashboard";

/** Attempt statuses the backend /cases filter actually supports. */
const STATUS_FILTERS = [
  { value: "", label: "All" },
  { value: "FAILED", label: "Failed" },
  { value: "ABANDONED", label: "Abandoned" },
  { value: "PENDING", label: "Pending" },
  { value: "RECOVERY_RECOMMENDED", label: "Recovery Recommended" },
];

/** Recommendation statuses shown as badges (backend values only). */
const REC_STATUS_CLASS = {
  PENDING: "pending",
  ACCEPTED: "success",
  DISMISSED: "failed",
  EXECUTED: "success",
};

/** Risk level badge class — backend returns LOW / MEDIUM / HIGH. */
const riskClass = (level) =>
  ({ LOW: "low", MEDIUM: "medium", HIGH: "high", CRITICAL: "critical" }[level] || "low");

const fmtMoney = (n) =>
  typeof n === "number" ? n.toLocaleString("en-IN", { maximumFractionDigits: 2 }) : "—";

const fmtDate = (iso) => {
  try {
    return new Date(iso).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
  } catch {
    return "—";
  }
};

const ACTION_LABELS = {
  RETRY_LATER: "Retry later",
  RETRY_SOON: "Retry soon",
  RETRY_IMMEDIATELY: "Retry immediately",
  REQUEST_ALTERNATIVE_PAYMENT_METHOD: "Use alternative method",
  SEND_RECOVERY_REMINDER: "Send recovery reminder",
};

function actionLabel(action) {
  return ACTION_LABELS[action] || action.replaceAll("_", " ").toLowerCase();
}

function SummaryCards({ summary }) {
  if (!summary) return null;
  const cards = [
    {
      label: "Revenue At Risk",
      value: `₹${fmtMoney(summary.potential_recoverable_revenue)}`,
      icon: IndianRupee,
    },
    {
      label: "Recovered Revenue",
      value: `₹${fmtMoney(summary.recovered_revenue || 0)}`,
      icon: TrendingUp,
    },
    { label: "Recoverable Cases", value: String(summary.failed_payments), icon: RefreshCcw },
    { label: "Recovered Cases", value: String(summary.recovered_cases || 0), icon: RefreshCcw },
    { label: "High Priority", value: String(summary.high_priority_recoveries), icon: AlertTriangle },
    {
      label: "Avg Recovery Probability",
      value: `${summary.average_recovery_probability}%`,
      icon: TrendingUp,
    },
  ];
  return (
    <div className="stats-grid">
      {cards.map(({ label, value, icon: Icon }) => (
        <div className="stat-card" key={label}>
          <div className="stat-icon">
            <Icon size={20} />
          </div>
          <div className="stat-body">
            <p className="stat-label">{label}</p>
            <p className="stat-value">{value}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

function CaseCard({ item, busyId, onRetry, onDismiss }) {
  const busy = busyId === item.id;
  const actionable = item.status === "PENDING";
  return (
    <article className="card recovery-case">
      <div className="recovery-case-head">
        <div>
          <span className={`badge risk-${riskClass(item.risk_level)}`}>{item.risk_level} RISK</span>{" "}
          <span className={`badge ${REC_STATUS_CLASS[item.status] || "pending"}`}>{item.status}</span>
        </div>
        <span className="recovery-probability">{item.recovery_probability}% recoverable</span>
      </div>

      <h3 className="recovery-case-title">
        ₹{fmtMoney(item.amount)} {item.currency} · {item.payment_method}
      </h3>
      <p className="recovery-reason">{item.normalized_reason || item.failure_message}</p>

      <dl className="recovery-meta">
        <div>
          <dt>Failure</dt>
          <dd>{item.failure_category.replaceAll("_", " ")}</dd>
        </div>
        <div>
          <dt>Recommended action</dt>
          <dd>{actionLabel(item.recommended_action)}</dd>
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
          <dt>Detected</dt>
          <dd>{fmtDate(item.created_at)}</dd>
        </div>
      </dl>

      {item.reasoning && <p className="recovery-explanation">AI insight: {item.reasoning}</p>}

      <div className="recovery-actions">
        <Link to={`/recovery/${item.id}`} className="btn btn-ghost btn-sm">
          View Details
        </Link>
        {actionable && (
          <>
            <button className="btn btn-primary btn-sm" disabled={busy} onClick={() => onRetry(item)}>
              {busy ? "Working…" : "Retry Payment"}
            </button>
            <button className="btn btn-ghost btn-sm" disabled={busy} onClick={() => onDismiss(item)}>
              Dismiss
            </button>
          </>
        )}
      </div>
    </article>
  );
}

export default function Recovery() {
  const navigate = useNavigate();
  const location = useLocation();
  // One-time banners after a failed payment:
  //  * demoFailure — a simulated (DEMO MODE) failed payment
  //  * realFailure — a real Razorpay checkout failure ingested into recovery
  const demoFailure = location.state?.demoFailure || null;
  const realFailure = location.state?.realFailure || null;
  const [summary, setSummary] = useState(null);
  const [cases, setCases] = useState([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);
  const [notice, setNotice] = useState(() => {
    if (realFailure) {
      return (
        `Razorpay Payment Failure (${realFailure.failureCode || "unknown"}): ` +
        `${realFailure.failureMessage || "The payment could not be completed."} ` +
        "A recovery recommendation has been created below."
      );
    }
    if (demoFailure) {
      return (
        `Demo payment failed (${demoFailure.scenarioLabel}): ${demoFailure.failureMessage} ` +
        "A recovery recommendation has been created below."
      );
    }
    return "";
  });

  const load = useCallback(
    async (filter = statusFilter) => {
      setLoading(true);
      setError("");
      try {
        const [sum, caseList] = await Promise.all([
          getRecoverySummary(),
          getRecoveryCases({ status: filter || undefined, limit: 50 }),
        ]);
        setSummary(sum);
        setCases(caseList);
      } catch (err) {
        setError(err.message || "Failed to load recovery data.");
      } finally {
        setLoading(false);
      }
    },
    [statusFilter]
  );

  useEffect(() => {
    load(statusFilter);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  const handleRetry = async (item) => {
    if (busyId) return; // prevent duplicate requests
    setBusyId(item.id);
    setError("");
    setNotice("");
    try {
      const res = await retryRecoveryCase(item.id);
      setNotice(res.message || "Recommendation accepted.");
      // Store recovery case ID so Checkout can mark it recovered after verified payment
      sessionStorage.setItem("currencyx_recovery_case_id", res.case_id || item.id);
      sessionStorage.setItem("currencyx_recovery_amount", String(item.amount || 0));
      navigate("/analyze", { state: buildRetryPrefill(res.retry_payment || {}) });
    } catch (err) {
      setError(err.message || "Failed to accept the recommendation.");
      await load(); // state may have changed server-side — refresh
    } finally {
      setBusyId(null);
    }
  };

  const handleDismiss = async (item) => {
    if (busyId) return;
    setBusyId(item.id);
    setError("");
    setNotice("");
    try {
      const res = await dismissRecoveryCase(item.id);
      setNotice(res.message || "Recommendation dismissed.");
    } catch (err) {
      setError(err.message || "Failed to dismiss the recommendation.");
    } finally {
      setBusyId(null);
      await load(); // always refresh after an action attempt
    }
  };

  const handleSeed = async () => {
    if (seeding) return;
    setSeeding(true);
    setError("");
    setNotice("");
    try {
      const res = await seedDemoRecoveryCases();
      setNotice(`Created ${res.created} demo recovery cases.`);
      await load();
    } catch (err) {
      setError(err.message || "Demo seeding is unavailable.");
    } finally {
      setSeeding(false);
    }
  };

  return (
    <DashboardShell active="/recovery">
      <div className="page-head">
        <div>
          <h1 className="page-title">Revenue Recovery</h1>
          <p className="page-sub">Track failed, abandoned, and recoverable payments.</p>
        </div>
        <button
          className="btn btn-ghost"
          onClick={handleSeed}
          disabled={seeding}
          title="Development-only: seed five sample failed payments"
        >
          <ShieldAlert size={16} /> {seeding ? "Creating…" : "Create Demo Failures (Dev)"}
        </button>
      </div>

      {error && (
        <div className="alert error" role="alert">
          <XCircle size={16} /> {error}{" "}
          <button className="alert-retry" onClick={() => load()}>
            Retry
          </button>
        </div>
      )}
      {notice && (
        <div className="alert success" role="status">
          {notice}
        </div>
      )}

      <SummaryCards summary={summary} />

      <div className="recovery-toolbar">
        <label className="field-inline">
          <span>Status</span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            disabled={loading}
          >
            {STATUS_FILTERS.map((f) => (
              <option key={f.value} value={f.value}>
                {f.label}
              </option>
            ))}
          </select>
        </label>
        <button className="btn btn-ghost btn-sm" onClick={() => load()} disabled={loading}>
          <RefreshCcw size={14} className={loading ? "spin" : ""} /> Refresh
        </button>
      </div>

      {loading ? (
        <div className="card results-loading">
          <div className="spinner" /> <p>Loading recovery cases…</p>
        </div>
      ) : cases.length === 0 && !error ? (
        <div className="card recovery-empty">
          <h3>No recovery opportunities found.</h3>
          <p>Your recent payment activity does not currently require recovery action.</p>
          <Link to="/analyze" className="btn btn-primary">
            Analyze a Payment <ArrowRight size={16} />
          </Link>
        </div>
      ) : (
        <div className="recovery-list">
          {cases.map((item) => (
            <CaseCard
              key={item.id}
              item={item}
              busyId={busyId}
              onRetry={handleRetry}
              onDismiss={handleDismiss}
            />
          ))}
        </div>
      )}
    </DashboardShell>
  );
}