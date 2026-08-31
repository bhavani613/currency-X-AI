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

const DEFAULT_FORM = {
  amount: "100000",
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
                    <h3>Payment method comparison</h3>
                    <span className="caption">Lowest cost highlighted</span>
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
                        showSelect={false}
                      />
                    ))}
                  </div>
                  <div className="ai-explanation">
                    <Sparkles size={16} />
                    <p>{result.explanation}</p>
                  </div>
                  {result.disclaimer && (
                    <p className="caption" style={{ padding: "0 1.25rem 1.25rem" }}>
                      {result.disclaimer}
                    </p>
                  )}
                </section>

                <div className="analyze-actions">
                  <button
                    className="btn btn-primary"
                    onClick={() => navigate("/checkout", { state: { form, result } })}
                  >
                    Proceed to Checkout <ArrowUpRight size={16} />
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