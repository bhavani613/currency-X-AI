import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Sparkles, ArrowUpRight } from "lucide-react";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import PaymentForm from "../components/PaymentForm";
import CostBreakdown from "../components/CostBreakdown";
import PaymentMethodCard from "../components/PaymentMethodCard";
import Loading from "../components/Loading";
import { analyzePayment } from "../services/api";
import { DEFAULT_SOURCE_CURRENCY } from "../services/currencies";

const DEFAULT_FORM = {
  amount: "100000",
  sourceCurrency: DEFAULT_SOURCE_CURRENCY,
  destinationCountry: "United Kingdom",
  destinationCurrency: "GBP",
  purpose: "Education",
};

export default function AnalyzePayment() {
  const location = useLocation();
  const navigate = useNavigate();

  const [form, setForm] = useState(location.state || DEFAULT_FORM);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selectedPaymentMethod, setSelectedPaymentMethod] = useState(null);
  const [recipientUpiId, setRecipientUpiId] = useState("");
  const [upiError, setUpiError] = useState("");
  const [bankDetails, setBankDetails] = useState({
    recipientName: "",
    accountNumber: "",
    ifscSwift: "",
    bankName: "",
  });

  const chosenMethod =
    result?.methods?.find((m) => m.id === selectedPaymentMethod) || null;

  const runAnalysis = async (formData = form) => {
    if (loading) return; // prevent duplicate requests
    setLoading(true);
    setError("");
    setResult(null);
    const amount = Number(formData.amount);
    if (!amount || amount <= 0) {
      setError("Please enter a valid amount greater than 0.");
      setLoading(false);
      return;
    }
    if (!formData.destinationCurrency) {
      setError("Please select a destination currency.");
      setLoading(false);
      return;
    }
    try {
      const res = await analyzePayment({ ...formData, amount });
      setResult(res);
      // Default selection: the backend's recommended method.
      setSelectedPaymentMethod(
        res.methods.find((m) => m.isCheapest || m.recommended)?.id ||
          res.methods[0]?.id ||
          null
      );
      setRecipientUpiId("");
      setUpiError("");
      setBankDetails({ recipientName: "", accountNumber: "", ifscSwift: "", bankName: "" });
      // Persist the (non-sensitive) analysis input so the AI Advisor page
      // can prefill and reuse it without a duplicate API call.
      sessionStorage.setItem(
        "currencyx_last_analysis",
        JSON.stringify({ ...formData, amount: String(amount) })
      );
    } catch (err) {
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const recommended = result?.methods?.find((m) => m.isCheapest || m.recommended);

  return (
    <div className="app-page">
      <Navbar />
      <div className="container page-wrap">
        <div className="page-head">
          <div>
            <h1 className="page-title">Analyze Payment</h1>
            <p className="page-sub">
              See the true cost of your international transfer before you pay.

          </p>
          </div>
        </div>

        {error && <div className="alert error">{error}</div>}

        <div className="analyze-layout">
          <section className="card form-card">
            <div className="card-head">
              <h3>Transfer details</h3>
            </div>
            <PaymentForm
              form={form}
              onChange={setForm}
              onSubmit={(e) => {
                e.preventDefault();
                runAnalysis();
              }}
              submitting={loading}
            />
          </section>

          <section className="results-col">
            {loading ? (
              <div className="card results-loading">
                <Loading label="Calculating real cost…" spinner />
              </div>
            ) : error ? (
              <div className="card empty">
                <p>{error}</p>
              </div>
            ) : result ? (
              <>
                <section className="card cost-card">
                  <div className="cost-card-head">
                    <h3>Analysis result</h3>
                    <span className="badge soft">via {result.recommendation}</span>
                  </div>
                  <CostBreakdown data={result} />
                  <div className="savings-banner">
                    <Sparkles size={18} />
                    <div>
                      <strong>Potential savings: ₹{result.savings.toLocaleString("en-IN")}</strong>
                      <p>by choosing {result.recommendation} over the priciest option.</p>
                    </div>
                  </div>
                </section>

                <section className="card">
                  <div className="card-head">
                    <h3>Payment Methods</h3>
                    <span className="caption">Select how you'd like to pay</span>
                  </div>
                  <div className="methods-list">
                    {result.methods.map((m) => (
                      <PaymentMethodCard
                        key={m.id}
                        method={{
                          ...m,
                          symbol: m.symbol || "",
                          isCheapest: !!(m.isCheapest || m.recommended),
                        }}
                        selected={selectedPaymentMethod === m.id}
                        onSelect={setSelectedPaymentMethod}
                      />
                    ))}
                  </div>

                  {chosenMethod?.id === "UPI" && (
                    <div className="method-details">
                      <h4>UPI Details</h4>
                      <div className="field">
                        <label htmlFor="upi-id">Recipient UPI ID</label>
                        <input
                          id="upi-id"
                          type="text"
                          placeholder="recipient@upi"
                          value={recipientUpiId}
                          onChange={(e) => {
                            setRecipientUpiId(e.target.value);
                            setUpiError("");
                          }}
                        />
                        {upiError && <p className="caption" style={{ color: "#ff8f8f" }}>{upiError}</p>}
                      </div>
                      <p className="caption">
                        The payment itself is completed securely through Razorpay checkout — entering
                        a UPI ID here only records the recipient's UPI address.
                      </p>
                    </div>
                  )}

                  {chosenMethod?.id === "BANK_TRANSFER" && (
                    <div className="method-details">
                      <h4>Bank Transfer Details</h4>
                      <div className="field two-col">
                        <div>
                          <label htmlFor="bt-name">Recipient name</label>
                          <input id="bt-name" type="text" value={bankDetails.recipientName}
                            onChange={(e) => setBankDetails({ ...bankDetails, recipientName: e.target.value })} />
                        </div>
                        <div>
                          <label htmlFor="bt-account">Bank account number</label>
                          <input id="bt-account" type="text" value={bankDetails.accountNumber}
                            onChange={(e) => setBankDetails({ ...bankDetails, accountNumber: e.target.value })} />
                        </div>
                      </div>
                      <div className="field two-col">
                        <div>
                          <label htmlFor="bt-ifsc">IFSC / SWIFT code</label>
                          <input id="bt-ifsc" type="text" value={bankDetails.ifscSwift}
                            onChange={(e) => setBankDetails({ ...bankDetails, ifscSwift: e.target.value })} />
                        </div>
                        <div>
                          <label htmlFor="bt-bank">Bank name</label>
                          <input id="bt-bank" type="text" value={bankDetails.bankName}
                            onChange={(e) => setBankDetails({ ...bankDetails, bankName: e.target.value })} />
                        </div>
                      </div>
                      <p className="caption">
                        These are recipient details for your records only. The actual payment is
                        completed securely through the Razorpay checkout — we never store bank
                        credentials.
                      </p>
                    </div>
                  )}

                  {(chosenMethod?.id === "DEBIT_CARD" || chosenMethod?.id === "CREDIT_CARD") && (
                    <div className="method-details">
                      <h4>{chosenMethod.label}</h4>
                      <p className="caption">
                        Your card details will be entered securely in Razorpay Checkout.
                      </p>
                    </div>
                  )}

                  {chosenMethod?.id === "SMART" && result.explanation && (
                    <div className="ai-explanation">
                      <Sparkles size={16} />
                      <p>{result.explanation}</p>
                    </div>
                  )}

                  {result.disclaimer && (
                    <p className="caption" style={{ padding: "0 1.25rem 1.25rem" }}>
                      {result.disclaimer}
                    </p>
                  )}
                </section>

                <div className="analyze-actions">
                  <button
                    className="btn btn-primary"
                    disabled={!selectedPaymentMethod}
                    onClick={() => {
                      if (chosenMethod?.id === "UPI") {
                        const upi = recipientUpiId.trim();
                        if (!upi) {
                          setUpiError("Recipient UPI ID is required.");
                          return;
                        }
                        if (!/^[\w.\-]{2,}@[a-zA-Z]{2,}$/.test(upi)) {
                          setUpiError("Enter a valid UPI ID in the format username@provider.");
                          return;
                        }
                      }
                      navigate("/checkout", {
                        state: {
                          form,
                          result,
                          selectedPaymentMethod: chosenMethod,
                          recipientUpiId:
                            chosenMethod?.id === "UPI" ? recipientUpiId.trim() : undefined,
                          bankDetails:
                            chosenMethod?.id === "BANK_TRANSFER"
                              ? {
                                  recipientName: bankDetails.recipientName.trim(),
                                  accountNumber: bankDetails.accountNumber.trim(),
                                  ifscSwift: bankDetails.ifscSwift.trim(),
                                  bankName: bankDetails.bankName.trim(),
                                }
                              : undefined,
                        },
                      });
                    }}
                  >
                    Proceed to Payment <ArrowUpRight size={16} />
                  </button>
                  <button
                    className="btn btn-ghost"
                    onClick={() => runAnalysis()}
                    disabled={loading}
                  >
                    Re-run analysis
                  </button>
                </div>
              </>
            ) : (
              <div className="card empty">
                <span className="feature-icon"><Sparkles size={20} /></span>
                <p>Fill in your transfer details and hit "Analyze Payment" to see the real cost breakdown and savings forecast.</p>
              </div>
            )}
          </section>
        </div>
      </div>
      <Footer />
    </div>
  );
}