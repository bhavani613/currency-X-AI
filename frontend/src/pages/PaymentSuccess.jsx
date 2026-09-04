import { useLocation, useNavigate } from "react-router-dom";
import { Check, Copy, ArrowLeft, Receipt } from "lucide-react";
import { useState } from "react";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import { getStoredTransactions } from "../services/transactionService";

export default function PaymentSuccess() {
  const navigate = useNavigate();
  const location = useLocation();
  const state = location.state || {};
  const result = state.result;

  // Prefer the transaction saved in localStorage by Checkout.jsx after
  // successful verification, so this page always matches the stored record.
  // sessionStorage is the fallback for a same-session refresh.
  const payment = (() => {
    try {
      const last = JSON.parse(sessionStorage.getItem("currencyx_last_payment") || "null");
      const orderId = last?.orderId;
      const stored = getStoredTransactions();
      const saved = orderId && stored.find((t) => t.razorpay_order_id === orderId);
      if (saved) {
        return {
          paymentId: saved.razorpay_payment_id,
          orderId: saved.razorpay_order_id,
          amount: saved.total_cost || saved.amount,
          currency: saved.currency,
          method: saved.payment_method,
          timestamp: saved.created_at,
          demo: Boolean(last?.demo),
        };
      }
      return last || null;
    } catch {
      return null;
    }
  })();

  const isDemo = Boolean(state.demo || payment?.demo);
  const isRecoveryRetry = Boolean(state.isRecoveryRetry);

  const txnId = payment?.paymentId || "—";
  const orderId = payment?.orderId || "—";
  const [copied, setCopied] = useState(false);

  const copy = () => {
    navigator.clipboard?.writeText(txnId);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  if (!result || !payment) {
    return (
      <div className="app-page">
        <Navbar />
        <div className="container page-wrap">
          <div className="card empty">
            <p>No transaction was completed. Start a new analysis to pay.</p>
            <button className="btn btn-ghost" onClick={() => navigate("/analyze")}>
              <ArrowLeft size={16} /> Go to Analyze
            </button>
          </div>
        </div>
        <Footer />
      </div>
    );
  }

  const requested = result.requested;
  const total = Number(result.fees?.totalCost || requested.amount);

  return (
    <div className="app-page">
      <Navbar />
      <div className="container page-wrap center-page">
        <div className="success-card card">
          <div className="success-check">
            <Check size={40} strokeWidth={3} />
          </div>
          {isDemo && <span className="demo-badge">DEMO MODE</span>}
          <h1 className="success-title">
            {isRecoveryRetry
              ? isDemo
                ? "✓ Demo Recovery Successful"
                : "✓ Payment Successful — Revenue Recovered"
              : isDemo
                ? "✓ Demo Payment Successful"
                : "✓ Payment Verified Successfully"}
          </h1>
          <p className="success-sub">
            {isRecoveryRetry
              ? isDemo
                ? "This was a simulated recovery payment — no real money was charged. The recovery case has been marked as recovered."
                : "Your retry payment was successful and the recovery case has been marked as recovered."
              : isDemo
                ? "This was a simulated payment — no real money was charged."
                : "Your international transfer is being processed."}
          </p>

          <div className="txn-row">
            <span className="txn-label">{isDemo ? "Demo Payment ID" : "Razorpay Payment ID"}</span>
            <span className="txn-value">
              {txnId}
              <button className="icon-btn" onClick={copy} aria-label="Copy payment id">
                {copied ? <Check size={15} /> : <Copy size={15} />}
              </button>
            </span>
          </div>
          <div className="txn-row">
            <span className="txn-label">{isDemo ? "Demo Order ID" : "Razorpay Order ID"}</span>
            <span className="txn-value">{orderId}</span>
          </div>

          <div className="success-summary">
            <div><span>Amount</span><strong>₹{payment.amount?.toLocaleString("en-IN")}</strong></div>
            <div><span>Currency</span><strong>{payment.currency}</strong></div>
            <div><span>Payment Method</span><strong>{payment.method || state.methodLabel || result.recommendation}</strong></div>
            <div><span>Timestamp</span><strong>{new Date(payment.timestamp).toLocaleString()}</strong></div>
          </div>

          <div className="success-actions">
            <button className="btn btn-primary" onClick={() => navigate("/transactions")}>
              <Receipt size={16} /> View Transaction History
            </button>
            <button className="btn btn-ghost" onClick={() => navigate("/dashboard")}>
              Back to Dashboard
            </button>
          </div>

          <div className="success-note">
            {isDemo
              ? "Demo payment simulated by CurrencyX AI. No real money moved and no Razorpay transaction was created."
              : "Payment verified via Razorpay TEST MODE signature verification. No real money moves."}
          </div>
        </div>
      </div>
      <Footer />
    </div>
  );
}