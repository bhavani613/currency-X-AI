import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Bot,
  Send,
  User,
  Sparkles,
  Lightbulb,
  ShieldCheck,
  TrendingUp,
  AlertTriangle,
  ArrowRight,
} from "lucide-react";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import Loading from "../components/Loading";
import { askAdvisor, getAdvisorInsights, analyzePayment } from "../services/api";
import { COUNTRIES, PURPOSES } from "../services/mockData";

const SUGGESTED = [
  "What's the cheapest way to send ₹1 lakh to the UK?",
  "How much will my recipient receive?",
  "Which payment method should I choose?",
  "How can I reduce FX costs?",
];

const INTRO = [
  {
    role: "ai",
    text: "Hi, I'm the CurrencyX AI Advisor 👋 Ask me anything about your international payments — costs, fees, rates or the best way to send money abroad.",
  },
];

const ADVISOR_STORE_KEY = "currencyx_last_advisor";

const DEFAULT_ADVISOR_FORM = {
  amount: "100000",
  sourceCurrency: "INR",
  destinationCountry: "United Kingdom",
  destinationCurrency: "GBP",
  purpose: "Education",
};

const RISK_META = {
  low: { label: "Low Risk", cls: "badge soft", icon: ShieldCheck },
  medium: { label: "Medium Risk", cls: "badge warn", icon: AlertTriangle },
  high: { label: "High Risk", cls: "badge danger", icon: AlertTriangle },
};

// Lightweight rendering: convert **bold** markers into <strong>.
function renderText(text) {
  const parts = text.split(/\*\*(.+?)\*\*/g);
  return parts.map((p, i) =>
    i % 2 === 1 ? <strong key={i}>{p}</strong> : <span key={i}>{p}</span>
  );
}

export default function AIAdvisor() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState(INTRO);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef(null);

  // --- Advisor insights state -------------------------------------------
  const [aform, setAform] = useState(() => {
    try {
      const saved = JSON.parse(sessionStorage.getItem(ADVISOR_STORE_KEY));
      if (saved?.input) return { ...DEFAULT_ADVISOR_FORM, ...saved.input };
      const last = JSON.parse(sessionStorage.getItem("currencyx_last_analysis"));
      if (last) {
        return {
          ...DEFAULT_ADVISOR_FORM,
          amount: String(last.amount ?? DEFAULT_ADVISOR_FORM.amount),
          sourceCurrency: last.sourceCurrency || "INR",
          destinationCountry: last.destinationCountry || DEFAULT_ADVISOR_FORM.destinationCountry,
          destinationCurrency: last.destinationCurrency || "GBP",
          purpose: last.purpose || DEFAULT_ADVISOR_FORM.purpose,
        };
      }
    } catch {
      /* ignore corrupt storage */
    }
    return DEFAULT_ADVISOR_FORM;
  });
  const [advice, setAdvice] = useState(() => {
    try {
      const saved = JSON.parse(sessionStorage.getItem(ADVISOR_STORE_KEY));
      return saved?.result || null;
    } catch {
      return null;
    }
  });
  const [aLoading, setALoading] = useState(false);
  const [aError, setAError] = useState("");

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  const send = async (text) => {
    const safe = text.trim();
    if (!safe || loading) return;
    setMessages((m) => [...m, { role: "user", text: safe }]);
    setInput("");
    setLoading(true);
    const reply = await askAdvisor(safe);
    setMessages((m) => [...m, { role: "ai", text: reply }]);
    setLoading(false);
  };

  // --- Advisor form handlers ---------------------------------------------
  const getInsights = async (e) => {
    e?.preventDefault?.();
    if (aLoading) return; // prevent duplicate requests
    const amount = Number(aform.amount);
    if (!amount || amount <= 0) {
      setAError("Please enter a valid amount greater than 0.");
      return;
    }
    if (!aform.destinationCurrency) {
      setAError("Please select a destination currency.");
      return;
    }
    setALoading(true);
    setAError("");
    try {
      const result = await getAdvisorInsights({ ...aform, amount });
      setAdvice(result);
      sessionStorage.setItem(
        ADVISOR_STORE_KEY,
        JSON.stringify({ input: { ...aform, amount: String(amount) }, result })
      );
    } catch (err) {
      setAError(err.message || "Something went wrong. Please try again.");
    } finally {
      setALoading(false);
    }
  };

  const proceedToPayment = async () => {
    if (aLoading) return;
    setALoading(true);
    setAError("");
    try {
      // Reuse the existing payment analysis + checkout contract.
      const result = await analyzePayment({
        amount: Number(aform.amount),
        sourceCurrency: aform.sourceCurrency,
        destinationCountry: aform.destinationCountry,
        destinationCurrency: aform.destinationCurrency,
        purpose: aform.purpose,
      });
      navigate("/checkout", { state: { result } });
    } catch (err) {
      setAError(err.message || "Could not start the payment. Please try again.");
    } finally {
      setALoading(false);
    }
  };

  const analyzeAnother = () => {
    setAdvice(null);
    setAform(DEFAULT_ADVISOR_FORM);
    sessionStorage.removeItem(ADVISOR_STORE_KEY);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="app-page">
      <Navbar />
      <div className="container page-wrap advisor-page">
        <div className="advisor-header">
          <div>
            <h1 className="page-title">CurrencyX AI Advisor</h1>
            <p className="page-sub">Ask me about your international payment.</p>
          </div>
          <span className="badge soft"><Sparkles size={13} /> AI Assistant</span>
        </div>

        {aError && <div className="alert error">{aError}</div>}

        <form className="card payment-form advisor-form" onSubmit={getInsights}>
          <div className="field">
            <label htmlFor="adv-amount">Amount you send</label>
            <div className="input-wrap">
              <span className="input-prefix">₹</span>
              <input
                id="adv-amount"
                type="number"
                min="1"
                value={aform.amount}
                onChange={(e) => setAform({ ...aform, amount: e.target.value })}
                placeholder="100000"
                aria-label="Amount"
              />
              <span className="input-suffix">{aform.sourceCurrency}</span>
            </div>
          </div>

          <div className="field two-col">
            <div>
              <label htmlFor="adv-country">Destination country</label>
              <select
                id="adv-country"
                value={aform.destinationCountry}
                onChange={(e) => {
                  const c = COUNTRIES.find((c) => c.country === e.target.value);
                  setAform({
                    ...aform,
                    destinationCountry: e.target.value,
                    destinationCurrency: c ? c.currency : "",
                  });
                }}
              >
                {COUNTRIES.map((c) => (
                  <option key={c.country} value={c.country}>{c.country}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="adv-currency">Destination currency</label>
              <select
                id="adv-currency"
                value={aform.destinationCurrency}
                onChange={(e) => setAform({ ...aform, destinationCurrency: e.target.value })}
              >
                <option value="">Auto</option>
                {COUNTRIES.map((c) => (
                  <option key={c.currency} value={c.currency}>{c.currency}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="field two-col">
            <div>
              <label htmlFor="adv-purpose">Payment purpose</label>
              <select
                id="adv-purpose"
                value={aform.purpose}
                onChange={(e) => setAform({ ...aform, purpose: e.target.value })}
              >
                {PURPOSES.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="adv-source">Source currency</label>
              <select
                id="adv-source"
                value={aform.sourceCurrency}
                onChange={(e) => setAform({ ...aform, sourceCurrency: e.target.value })}
              >
                <option value="INR">INR</option>
              </select>
            </div>
          </div>

          <button className="btn btn-primary btn-lg" type="submit" disabled={aLoading}>
            <Sparkles size={16} /> {aLoading ? "Analyzing your payment..." : "Get AI Insights"}
          </button>
        </form>

        {aLoading && !advice && (
          <div className="card empty">
            <Loading label="Analyzing your payment..." spinner />
          </div>
        )}

        {advice && (
          <div className="advisor-results">
            <section className="card advisor-summary">
              <div className="card-head">
                <h3><Lightbulb size={16} /> AI Summary</h3>
                {(() => {
                  const meta = RISK_META[advice.risk_level] || RISK_META.low;
                  const Icon = meta.icon;
                  return (
                    <span className={meta.cls}><Icon size={13} /> {meta.label}</span>
                  );
                })()}
              </div>
              <p className="advisor-summary-text">{advice.summary}</p>
              <div className="summary-rows">
                <div>
                  <span>Recommended method</span>
                  <strong>{advice.recommended_method}</strong>
                </div>
                <div>
                  <span>Potential savings</span>
                  <strong>₹{advice.potential_savings?.toLocaleString("en-IN")}</strong>
                </div>
                <div>
                  <span>Risk level</span>
                  <strong className="text-capitalize">{advice.risk_level}</strong>
                </div>
              </div>
            </section>

            <section className="card">
              <div className="card-head"><h3><TrendingUp size={16} /> Key Insights</h3></div>
              <div className="insight-list">
                {advice.insights.map((ins, i) => (
                  <div className="insight-item" key={i}>
                    <span className="insight-dot" />
                    <div>
                      <strong>{ins.title}</strong>
                      <p>{ins.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <section className="card">
              <div className="card-head"><h3><Lightbulb size={16} /> Smart Tips</h3></div>
              <ul className="tips-list">
                {advice.tips.map((tip, i) => (
                  <li key={i}>{tip}</li>
                ))}
              </ul>
              <p className="chat-note">{advice.disclaimer}</p>
            </section>

            <div className="checkout-actions">
              <button
                className="btn btn-primary btn-lg"
                onClick={proceedToPayment}
                disabled={aLoading}
              >
                Proceed to Payment <ArrowRight size={16} />
              </button>
              <button className="btn btn-ghost" onClick={analyzeAnother} disabled={aLoading}>
                Analyze Another Payment
              </button>
            </div>
          </div>
        )}

        <div className="chat-shell">
          <div className="chat-window" ref={scrollRef}>
            {messages.map((m, i) => (
              <div key={i} className={`msg ${m.role}`}>
                <span className="msg-avatar">
                  {m.role === "ai" ? <Bot size={16} /> : <User size={16} />}
                </span>
                <div className="msg-bubble">
                  {renderText(m.text)}
                </div>
              </div>
            ))}
            {loading && (
              <div className="msg ai">
                <span className="msg-avatar"><Bot size={16} /></span>
                <div className="msg-bubble typing">
                  <Loading label="Thinking…" spinner />
                </div>
              </div>
            )}
          </div>

          {messages.length <= 1 && (
            <div className="suggestions">
              <p className="suggest-title">Try asking</p>
              {SUGGESTED.map((s) => (
                <button key={s} className="suggestion-chip" onClick={() => send(s)}>
                  {s}
                </button>
              ))}
            </div>
          )}

          <form
            className="chat-input"
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about fees, rates or the cheapest way to send money…"
              aria-label="Message"
            />
            <button className="btn btn-primary" type="submit" disabled={loading || !input.trim()}>
              <Send size={17} />
            </button>
          </form>
          <p className="chat-note">AI Advisor reflects demo estimates and may be inaccurate.</p>
        </div>
      </div>
      <Footer />
    </div>
  );
}