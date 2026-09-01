import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Lock, ShieldCheck, ArrowLeft } from "lucide-react";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import PaymentMethodCard from "../components/PaymentMethodCard";
import { createPaymentOrder, verifyPayment } from "../services/api";
import { saveTransaction } from "../services/transactionService";
import { currencySymbol } from "../services/currencies";

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

  const proceed = async () => {
    if (!result) {
      navigate("/analyze");
      return;
    }
    if (paying) return; // prevent duplicate payment attempts
    setPaying(true);
    setError("");

    try {
      // 1. Create the Razorpay order on the backend (TEST MODE)
      const order = await createPaymentOrder({
        amount: payInr, // always INR payable amount
        currency: "INR",
        receipt: `currencyx-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      });

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
            saveTransaction({
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_order_id: response.razorpay_order_id,
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
                paymentId: response.razorpay_payment_id,
                orderId: response.razorpay_order_id,
                amount: payInr,
                currency: "INR",
                method: activeMethod?.label || result.recommendation,
                timestamp: new Date().toISOString(),
              })
            );
            navigate("/payment-success", {
              state: { result, methodId: activeMethod?.id, methodLabel: activeMethod?.label },
            });
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
              <button className="btn btn-primary btn-lg" onClick={proceed} disabled={paying}>
                <Lock size={16} /> {paying ? "Processing Payment…" : "Proceed to Secure Payment"}
              </button>
              <p className="checkout-note">
                Payments are processed securely by Razorpay in TEST MODE. No real money moves.
              </p>
            </div>
          </div>
        )}
      </div>
      <Footer />
    </div>
  );
}