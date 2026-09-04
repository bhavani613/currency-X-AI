import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  BarChart3,
  ShieldCheck,
  ArrowUpRight,
  Zap,
  Landmark,
  CreditCard,
  Smartphone,
  Globe,
  Wallet,
  Bot,
  Lock,
  Sparkles,
  Check,
} from "lucide-react";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import PaymentForm from "../components/PaymentForm";
import { analyzePayment } from "../services/api";
import { useAuth } from "../context/AuthContext";

const INTRO_FORM = {
  amount: "100000",
  destinationCountry: "United Kingdom",
  destinationCurrency: "GBP",
  purpose: "Education",
};

function HeroPreviewCard() {
  const [form, setForm] = useState(INTRO_FORM);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setResult(null);
    const parsedAmount = Number(form.amount);
    try {
      const res = await analyzePayment({ ...form, amount: parsedAmount });
      setResult(res);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="hero-card">
      <div className="hero-card-head">
        <span className="mini-badge">PAYMENT ESTIMATE</span>
        <span className="card-ai-badge">
          <Bot size={14} /> AI
        </span>
      </div>
{loading ? (
        <div className="hero-card-loading">
          <div className="pulse-bar" />
          <div className="pulse-bar short" />
          <p>Calculating real cost…</p>
        </div>
      ) : result ? (
        <div className="preview-result">
          <div className="preview-row">
            <span className="preview-label">You Send</span>
            <span className="preview-large">
              ₹{result.requested.amount.toLocaleString("en-IN")}{" "}
              <small>{result.requested.sourceCurrency}</small>
            </span>
          </div>
          <div className="preview-row">
            <span className="preview-label">Recipient</span>
            <span className="preview-value">
              {result.requested.destinationCountry}
            </span>
          </div>
          <div className="preview-row">
            <span className="preview-label">Estimated recipient</span>
            <span className="preview-accent">
              £{result.recipientAmount}{" "}
              <small>{result.requested.destinationCurrency}</small>
            </span>
          </div>
          <div className="preview-divider" />
          <div className="preview-row">
            <span className="preview-label">Estimated fees</span>
            <span className="preview-value">
              ₹{result.fees.totalFees.toLocaleString("en-IN")}
            </span>
          </div>
          <div className="preview-row savings">
            <span className="preview-label">Potential savings</span>
            <span className="preview-saving">
              ₹{result.savings.toLocaleString("en-IN")}
            </span>
          </div>

          <div className="preview-actions">
            <button
              className="btn btn-primary btn-block"
              onClick={() =>
                navigate("/analyze", {
                  state: { ...form, amount: result.requested.amount },
                })
              }
            >
              Full analysis <ArrowUpRight size={16} />
            </button>
            <button
              className="btn btn-ghost btn-block"
              onClick={() => {
                setResult(null);
                setForm(INTRO_FORM);
              }}
            >
              New calculation
            </button>
          </div>
        </div>
      ) : (
        <PaymentForm
          form={form}
          onChange={setForm}
          onSubmit={handleSubmit}
          submitting={loading}
        />
      )}
    </div>
  );
}

export default function Home() {
  const { isAuthenticated } = useAuth();
  return (
    <div className="site">
      <Navbar />

      {/* HERO */}
      <section className="hero">
        <div className="container hero-grid">
          <div className="hero-content">
            <span className="badge">
              <Sparkles size={13} /> AI-Powered Cross-Border Payments
            </span>
            <h1>
              Know the <span className="text-accent">real cost</span>
              <br />
              before you pay internationally.
            </h1>
            <p>
              CurrencyX AI analyses exchange rates, hidden FX markups, fees and
              payment methods — so you always know exactly what it really costs
              to send money abroad, and how much you can save.
            </p>
            <div className="hero-buttons">
              <Link
                to={isAuthenticated ? "/analyze" : "/signup"}
                className="btn btn-primary"
              >
                Calculate Payment <ArrowUpRight size={17} />
              </Link>
            </div>
            <div className="stats">
              <div>
                <h3>100%</h3>
                <p>Cost Transparency</p>
              </div>
              <div>
                <h3>AI</h3>
                <p>Smart Recommendations</p>
              </div>
              <div>
                <h3>Global</h3>
                <p>Cross-Border Ready</p>
              </div>
            </div>
          </div>

          <HeroPreviewCard />
        </div>
      </section>

      {/* WHY */}
      <section className="section alt" id="features">
        <div className="container">
          <div className="section-heading center">
            <span className="kicker">WHY CURRENCYX AI?</span>
            <h2>More than a currency converter</h2>
            <p className="sub">
              Banks hide their real costs in the exchange rate. We surface every
              rupee so you pay less, every time.
            </p>
          </div>
          <div className="cards-grid three">
            <div className="card feature-card">
              <div className="feature-icon"><BarChart3 size={22} /></div>
              <h3>True Cost Analysis</h3>
              <p>
                Break down FX markups, processing fees and other charges before
                you commit — no black boxes, no surprises.
              </p>
            </div>
            <div className="card feature-card">
              <div className="feature-icon"><Bot size={22} /></div>
              <h3>AI Payment Advisor</h3>
              <p>
                Ask plain-language questions and get clear, cost-focused answers
                and recommendations for cross-border payments.
              </p>
            </div>
            <div className="card feature-card">
              <div className="feature-icon"><Globe size={22} /></div>
              <h3>Smart Comparison</h3>
              <p>
                Compare bank transfer, cards and smart routing side-by-side to
                find the cheapest option instantly.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section className="section" id="how-it-works">
        <div className="container">
          <div className="section-heading center">
            <span className="kicker">HOW IT WORKS</span>
            <h2>Three steps to lower-cost transfers</h2>
          </div>
          <div className="cards-grid three steps">
            <div className="step-card card">
              <span className="step-num">01</span>
              <h3>Enter your payment</h3>
              <p>
                Tell us the amount, destination and purpose of your transfer.
              </p>
            </div>
            <div className="step-card card">
              <span className="step-num">02</span>
              <h3>AI analyses the cost</h3>
              <p>
                We compute the true cost across rates, fees and hidden markups.
              </p>
            </div>
            <div className="step-card card">
              <span className="step-num">03</span>
              <h3>Pay the smart way</h3>
              <p>Choose the recommended route and keep more of your money.</p>
            </div>
          </div>
        </div>
      </section>

      {/* COMPARISON */}
      <section className="section alt">
        <div className="container compare-wrap">
          <div className="section-heading">
            <span className="kicker">SMART PAYMENT COMPARISON</span>
            <h2>The same transfer, radically different costs</h2>
            <p className="sub">
              Sending ₹1,00,000 to the UK? Here's what hidden fees do to what
              your recipient actually gets.
            </p>
          </div>
<div className="compare-grid">
            {[
              { icon: Zap, name: "Smart Payment", fee: "₹1,033", note: "Best total cost", best: true },
              { icon: Landmark, name: "Bank Transfer", fee: "₹3,150", note: "High markup" },
              { icon: CreditCard, name: "Debit Card", fee: "₹3,650", note: "Convenient" },
              { icon: Smartphone, name: "Credit Card", fee: "₹4,077", note: "Highest cost" },
            ].map((m) => {
              const Icon = m.icon;
              return (
                <div className={`compare-card card ${m.best ? "best" : ""}`} key={m.name}>
                  {m.best && <span className="rec-badge">RECOMMENDED</span>}
                  <span className="compare-icon"><Icon size={20} /></span>
                  <h4>{m.name}</h4>
                  <p>{m.note}</p>
                  <strong className="compare-fee">{m.fee}</strong>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* AI ADVISOR */}
      <section className="section">
        <div className="container advisor-band">
          <div className="advisor-text">
            <span className="kicker"><Bot size={14} /> AI ADVISOR</span>
            <h2>Ask before you send</h2>
            <p>
              "What's the cheapest way to send ₹1 lakh to the UK?" Get clear,
              cost-focused guidance in seconds — like a personal FX advisor.
            </p>
            <Link
              to={isAuthenticated ? "/advisor" : "/signup"}
              className="btn btn-primary"
            >
              Open AI Advisor
            </Link>
          </div>
          <div className="advisor-demo card">
            <div className="chat-bubble user">
              What's the cheapest way to send ₹1 lakh to the UK?
            </div>
            <div className="chat-bubble ai">
              Smart Payment currently has the lowest total cost — roughly ₹2,000
              cheaper than a typical credit card for this amount.
            </div>
          </div>
        </div>
      </section>

      {/* SECURITY / TRUST */}
      <section className="section alt">
        <div className="container trust-row">
          <div className="trust-item card">
            <span className="feature-icon"><Lock size={20} /></span>
            <h3>Bank-grade security</h3>
            <p>Your money and data are protected with industry-standard encryption.</p>
          </div>
          <div className="trust-item card">
            <span className="feature-icon"><ShieldCheck size={20} /></span>
            <h3>Transparent by design</h3>
            <p>Every fee and markup shown up front. No hidden spreads. Ever.</p>
          </div>
          <div className="trust-item card">
            <span className="feature-icon"><Wallet size={20} /></span>
            <h3>You stay in control</h3>
            <p>Compare, choose and send the way you want — without being locked in.</p>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="cta">
        <div className="container cta-inner">
          <h2>Never overpay for an international transfer.</h2>
          <p>See the real cost of your next payment in seconds.</p>
          <div className="cta-buttons">
            <Link
              to={isAuthenticated ? "/dashboard" : "/signup"}
              className="btn btn-primary"
            >
              Get Started <ArrowUpRight size={17} />
            </Link>
            <Link
              to={isAuthenticated ? "/analyze" : "/signup"}
              className="btn btn-secondary"
            >
              Calculate a Payment
            </Link>
          </div>
          <div className="cta-check">
            <span><Check size={14} /> Free to try</span>
            <span><Check size={14} /> No card required</span>
            <span><Check size={14} /> Live cost analysis</span>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}