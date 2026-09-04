import { useState, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Lock, ShieldCheck, ArrowLeft } from "lucide-react";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import PaymentMethodCard from "../components/PaymentMethodCard";
import PasswordConfirmModal from "../components/PasswordConfirmModal";
import { createPaymentOrder, verifyPayment, analyzeFailure, completeRecoveryCase } from "../services/api";
import { saveTransaction } from "../services/transactionService";
import { currencySymbol } from "../services/currencies";

/** Deterministic demo-failure scenarios (same scenario => same recovery analysis). */
const DEMO_FAILURE_SCENARIOS = [
  {
    key: "INSUFFICIENT_FUNDS",
    label: "Insufficient funds",
    code: "INSUFFICIENT_FUNDS",
    message: "Insufficient balance in your account.",
  },
  {
    key: "BANK_TIMEOUT",
    label: "Bank / network failure",
    code: "BANK_TIMEOUT",
    message: "Your bank did not respond in time.",
  },
  {
    key: "AUTHENTICATION_FAILED",
    label: "Authentication failure",
    code: "AUTHENTICATION_FAILED",
    message: "Payment authentication failed or was cancelled.",
  },
  {
    key: "PAYMENT_TIMEOUT",
    label: "Payment timeout",
    code: "PAYMENT_TIMEOUT",
    message: "The payment request timed out before completing.",
  },
  {
    key: "GATEWAY_FAILURE",
    label: "Temporary gateway failure",
    code: "GATEWAY_TIMEOUT",
    message: "The payment gateway is temporarily unavailable.",
  },
];

const demoId = (prefix) =>
  `${prefix}_${Date.now().toString(36)}${Math.random().toString(36).slice(2, 10)}`;

/** Load Razorpay Checkout.js once; resolves with window.Razorpay. */
function loadRazorpayScript() {
  if (window.Razorpay) return Promise.resolve(window.Razorpay);
  return new Promise((resolve, reject) => {
    const existing = document.querySelector('script[src="https://checkout.razorpay.com/v1/checkout.js"]');
    if (existing) {
      existing.addEventListener("load", () => resolve(window.Razorpay));
      existing.addEventListener("error", reject);
      return;
    }
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.onload = () => resolve(window.Razorpay);
    script.onerror = () => reject(new Error("Failed to load the Razorpay checkout script. Check your internet connection."));
    document.body.appendChild(script);
  });
}

export default function Checkout() {
  const navigate = useNavigate();
  const location = useLocation();
  const state = location.state || {};

  const result = state.result;
  const requested = result?.requested || {};
  const summary = result?.fees || {};

  const [chosen, setChosen] = useState(
    state.selectedPaymentMethod?.id || state.methodId || result?.recommendation || ""
  );
  const [paying, setPaying] = useState(false);
  const [error, setError] = useState("");
  // DEMO MODE state — a demo_order_* was created; no Razorpay checkout opens.
  const [demoOrder, setDemoOrder] = useState(null);
  const [demoScenario, setDemoScenario] = useState(DEMO_FAILURE_SCENARIOS[0].key);
  // Password confirmation modal
  const [passwordModalOpen, setPasswordModalOpen] = useState(false);
  const [pendingPaymentAction, setPendingPaymentAction] = useState(null);

  const activeMethod =
    result?.methods?.find((m) => m.id === chosen) || result?.methods?.[0];

  const total = Number(summary.totalCost || requested.amount);
  const srcCurrency = requested.sourceCurrency || "INR";
  const isSourceInr = srcCurrency === "INR";
  // Razorpay checkout settles in INR only. For non-INR analyses we use the
  // backend's explicit INR equivalent of the total cost — never silently
  // treating a foreign-currency amount as INR.
  const payInr = Number(result?.totalCostInInr ?? total);
  const srcSymbol = currencySymbol(srcCurrency);

  // Clear recovery context when Checkout unmounts without completed payment.
  // This prevents a stale recovery case ID from being used by a future normal payment.
  useEffect(() => {
    return () => {
      // Only clear if payment was not completed (completeVerifiedPayment clears it itself)
      if (sessionStorage.getItem("currencyx_recovery_case_id")) {
        // Check if we're navigating to payment-success (payment completed)
        // If not, clear the recovery context
        const lastPayment = sessionStorage.getItem("currencyx_last_payment");
        if (!lastPayment) {
          sessionStorage.removeItem("currencyx_recovery_case_id");
          sessionStorage.removeItem("currencyx_recovery_amount");
        }
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /** Shared post-verification success path (real + demo success land here). */
  const completeVerifiedPayment = (paymentId, orderId) => {
    saveTransaction({
      razorpay_payment_id: paymentId,
      razorpay_order_id: orderId,
      amount: total,
      currency: srcCurrency,
      destination_country: requested.destinationCountry,
      destination_currency: requested.destinationCurrency,
      recipient_amount: result.recipientAmount,
      payment_method: activeMethod?.label || result.recommendation,
      exchange_rate: requested.rate,
      total_fees: summary.totalFees,
      total_cost: summary.totalCost,
      status: "completed",
    });
    sessionStorage.setItem(
      "currencyx_last_payment",
      JSON.stringify({
        paymentId,
        orderId,
        amount: payInr,
        currency: "INR",
        method: activeMethod?.label || result.recommendation,
        timestamp: new Date().toISOString(),
        demo: Boolean(demoOrder),
      })
    );

    // Check if this payment originated from a recovery retry
    const recoveryCaseId = sessionStorage.getItem("currencyx_recovery_case_id");
    const recoveryAmount = sessionStorage.getItem("currencyx_recovery_amount");
    const isRecoveryRetry = Boolean(recoveryCaseId);

    // Clear recovery context from sessionStorage
    sessionStorage.removeItem("currencyx_recovery_case_id");
    sessionStorage.removeItem("currencyx_recovery_amount");

    // If this was a recovery retry, mark the recovery case as recovered
    // Fire-and-forget: do not block the user navigation on this
    if (isRecoveryRetry) {
      const recoveredAmount = recoveryAmount ? parseFloat(recoveryAmount) : undefined;
      completeRecoveryCase(recoveryCaseId, recoveredAmount).catch(() => {
        // Non-critical: recovery tracking failure should not block the user
      });
    }

    setPaying(false);
    navigate("/payment-success", {
      state: {
        result,
        methodId: activeMethod?.id,
        methodLabel: activeMethod?.label,
        demo: Boolean(demoOrder),
        isRecoveryRetry,
        recoveryCaseId,
      },
    });
  };

  const proceed = async () => {
    if (!result) {
      navigate("/analyze");
      return;
    }
    if (paying) return; // prevent duplicate payment attempts
    setPaying(true);
    setError("");
    setDemoOrder(null);

    try {
      // 1. Create the payment order on the backend (TEST MODE or DEMO MODE)
      const order = await createPaymentOrder({
        amount: payInr, // always INR payable amount
        currency: "INR",
        receipt: `currencyx-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      });

      // DEMO MODE — show the simulation panel instead of opening Razorpay.
      if (order.demo) {
        setDemoOrder(order);
        setPaying(false);
        return;
      }

      // 2. Load Razorpay Checkout.js (dynamically, only when needed)
      const Razorpay = await loadRazorpayScript();

      // 3. Open Razorpay Checkout
      const rzp = new Razorpay({
        key: order.key_id,
        amount: order.amount,
        currency: order.currency,
        name: "CurrencyX AI",
        description: `Transfer to ${requested.destinationCountry || "international recipient"}`,
        order_id: order.order_id,
        prefill: { name: "CurrencyX AI Customer" },
        theme: { color: "#4be3b9" },
        modal: {
          ondismiss: () => {
            setPaying(false);
            setError("Payment was cancelled before completion. No money has been charged.");
          },
        },
        handler: async (response) => {
          // 4. Verify the payment signature on the backend. Only a
          // successful verification lets us navigate to the success page.
          try {
            await verifyPayment({
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_order_id: response.razorpay_order_id,
              razorpay_signature: response.razorpay_signature,
            });
            // Verification succeeded — record the transaction
            // (saveTransaction skips duplicates on refresh/retry).
            completeVerifiedPayment(response.razorpay_payment_id, response.razorpay_order_id);
          } catch (err) {
            setPaying(false);
            setError(err.message || "Payment verification failed. Please contact support before retrying.");
          }
        },
      });

      rzp.on("payment.failed", () => {
        setPaying(false);
        setError("The payment failed at Razorpay. Please try a different payment method.");
      });

      rzp.open();
    } catch (err) {
      setPaying(false);
      setError(err.message || "Could not start the payment. Please try again.");
    }
  };

  /** Simulate a SUCCESSFUL demo payment (demo ids verified by the backend). */
  const handleDemoSuccess = async () => {
    if (paying || !demoOrder) return;
    setPaying(true);
    setError("");
    try {
      const paymentId = demoId("demo_payment");
      await verifyPayment({
        razorpay_payment_id: paymentId,
        razorpay_order_id: demoOrder.order_id,
        razorpay_signature: `demo_signature_${Date.now().toString(36)}`,
      });
      completeVerifiedPayment(paymentId, demoOrder.order_id);
    } catch (err) {
      setPaying(false);
      setError(err.message || "Demo payment could not be completed. Please try again.");
    }
  };

  /** Simulate a FAILED demo payment → persists attempt + recovery recommendation. */
  const handleDemoFailure = async () => {
    if (paying || !demoOrder) return;
    const scenario =
      DEMO_FAILURE_SCENARIOS.find((s) => s.key === demoScenario) || DEMO_FAILURE_SCENARIOS[0];
    setPaying(true);
    setError("");
    try {
      const paymentId = demoId("demo_payment");
      const res = await analyzeFailure({
        amount: total,
        currency: srcCurrency,
        payment_method: activeMethod?.label || result.recommendation,
        failure_code: scenario.code,
        failure_message: scenario.message,
        gateway_payment_id: paymentId,
        gateway_order_id: demoOrder.order_id,
      });
      setPaying(false);
      navigate("/recovery", {
        state: {
          demoFailure: {
            scenarioLabel: scenario.label,
            failureMessage: scenario.message,
            paymentAttemptId: res.payment_attempt_id,
            analysis: res.analysis,
          },
        },
      });
    } catch (err) {
      setPaying(false);
      setError(err.message || "Demo failure could not be recorded. Please try again.");
    }
  };

  /** Handle password confirmation — dispatch to the pending payment action. */
  const handlePasswordConfirmed = () => {
    const action = pendingPaymentAction;
    setPendingPaymentAction(null);
    setPasswordModalOpen(false);
    if (action === "normal") {
      proceed();
    } else if (action === "demo-success") {
      handleDemoSuccess();
    }
  };
  return (
    <div className="app-page">
      <Navbar />
      <div className="container page-wrap">
        <div className="page-head">
          <div>
            <h1 className="page-title">Checkout</h1>
            <p className="page-sub">Review your transfer and payment method.</p>
          </div>
          <span className="badge soft"><ShieldCheck size={13} /> Secure checkout</span>
        </div>

        {error && <div className="alert error">{error}</div>}

        {!result ? (
          <div className="card empty checkout-empty">
            <p>No analysis selected yet. Run an analysis first to continue to checkout.</p>
            <button className="btn btn-ghost" onClick={() => navigate("/analyze")}>
              <ArrowLeft size={16} /> Go to Analyze
            </button>
          </div>
        ) : (
          <div className="checkout-grid">
            <section className="card checkout-summary">
              <div className="card-head"><h3>Payment Summary</h3></div>
              <div className="summary-rows">
                <div><span>Amount</span><strong>₹{requested.amount?.toLocaleString("en-IN")} INR</strong></div>
                <div><span>Destination</span><strong>{requested.destinationCountry}</strong></div>
                <div><span>Recipient gets</span><strong>{result.recipientCurrency || requested.destinationCurrency} {result.recipientAmount?.toLocaleString?.() ?? result.recipientAmount}</strong></div>
                <div><span>Exchange rate</span><strong>{requested.rate} {requested.destinationCurrency} per {srcCurrency}</strong></div>
                <div><span>Total fees</span><strong>₹{summary.totalFees?.toLocaleString("en-IN")}</strong></div>
                {!isSourceInr && (
                  <div>
                    <span>Payable in INR (Razorpay)</span>
                    <strong>{"\u20B9"}{payInr.toLocaleString("en-IN")} INR</strong>
                  </div>
                )}
                {state.recipientUpiId && (
                  <div>
                    <span>Recipient UPI ID</span>
                    <strong>{state.recipientUpiId}</strong>
                  </div>
                )}
                {state.selectedPaymentMethod && (
                  <div>
                    <span>Payment method</span>
                    <strong>{state.selectedPaymentMethod.label}</strong>
                  </div>
                )}
              </div>
              <div className="summary-total">
                <span>Total</span>
                <strong>₹{total.toLocaleString("en-IN")} INR</strong>
              </div>
            </section>

            <section className="card">
              <div className="card-head">
                <h3>Selected Payment Method</h3>
              </div>
              <div className="methods-list">
                {result.methods.map((m) => (
                  <PaymentMethodCard
                    key={m.id}
                    method={{ ...m, symbol: "" }}
                    selected={chosen === m.id}
                    onSelect={setChosen}
                  />
                ))}
              </div>
            </section>

            <div className="checkout-actions">
              {demoOrder ? (
                <div className="demo-panel card">
                  <span className="demo-badge">DEMO MODE</span>
                  <p className="demo-order-id">
                    Demo order: <strong>{demoOrder.order_id}</strong>
                  </p>
                  <label className="demo-scenario">
                    <span>Simulated failure scenario</span>
                    <select
                      value={demoScenario}
                      onChange={(e) => setDemoScenario(e.target.value)}
                    >
                      {DEMO_FAILURE_SCENARIOS.map((s) => (
                        <option key={s.key} value={s.key}>
                          {s.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <div className="demo-buttons">
                    <button
                      className="btn btn-primary btn-lg"
                      onClick={() => {
                        setPendingPaymentAction("demo-success");
                        setPasswordModalOpen(true);
                      }}
                      disabled={paying}
                    >
                      <ShieldCheck size={16} /> Simulate Successful Payment
                    </button>
                    <button
                      className="btn btn-ghost btn-lg"
                      onClick={handleDemoFailure}
                      disabled={paying}
                    >
                      <ArrowLeft size={16} /> Simulate Failed Payment
                    </button>
                  </div>
                  <p className="demo-note">
                    DEMO MODE — simulated payments only. No real money is charged and no real
                    Razorpay Checkout opens.
                  </p>
                </div>
              ) : (
                <>
                  <button
                    className="btn btn-primary btn-lg"
                    onClick={() => {
                      setPendingPaymentAction("normal");
                      setPasswordModalOpen(true);
                    }}
                    disabled={paying}
                  >
                    <Lock size={16} /> {paying ? "Processing Payment…" : "Proceed to Secure Payment"}
                  </button>
                  <p className="checkout-note">
                    Payments are processed securely by Razorpay in TEST MODE. No real money moves.
                  </p>
                </>
              )}
            </div>
          </div>
        )}
      </div>
      <PasswordConfirmModal
        isOpen={passwordModalOpen}
        onClose={() => {
          setPasswordModalOpen(false);
          setPendingPaymentAction(null);
        }}
        onConfirmed={handlePasswordConfirmed}
        title="Confirm your password"
        subtitle="Enter your current account password to proceed with the payment."
      />
      <Footer />
    </div>
  );
}