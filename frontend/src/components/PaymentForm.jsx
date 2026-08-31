import { ArrowDown, Zap } from "lucide-react";
import { COUNTRIES, PURPOSES } from "../services/mockData";

export default function PaymentForm({ form, onChange, onSubmit, submitting }) {
  return (
    <form className="payment-form" onSubmit={onSubmit}>
      <div className="field">
        <label htmlFor="pf-amount">Amount you send</label>
        <div className="input-wrap">
          <span className="input-prefix">₹</span>
          <input
            id="pf-amount"
            type="number"
            min="1"
            value={form.amount}
            onChange={(e) => onChange({ ...form, amount: e.target.value })}
            placeholder="100000"
            aria-label="Amount"
          />
          <span className="input-suffix">INR</span>
        </div>
      </div>

      <div className="swap-arrow">
        <ArrowDown size={16} />
      </div>

      <div className="field two-col">
        <div>
          <label htmlFor="pf-country">Destination country</label>
          <select
            id="pf-country"
            value={form.destinationCountry}
            onChange={(e) => {
              const c = COUNTRIES.find((c) => c.country === e.target.value);
              onChange({
                ...form,
                destinationCountry: e.target.value,
                destinationCurrency: c ? c.currency : "",
              });
            }}
          >
            {COUNTRIES.map((c) => (
              <option key={c.country} value={c.country}>
                {c.country}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="pf-currency">Destination currency</label>
          <select
            id="pf-currency"
            value={form.destinationCurrency}
            onChange={(e) => onChange({ ...form, destinationCurrency: e.target.value })}
          >
            <option value="">Auto</option>
            {COUNTRIES.map((c) => (
              <option key={c.currency} value={c.currency}>
                {c.currency}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="field">
        <label htmlFor="pf-purpose">Purpose</label>
        <select
          id="pf-purpose"
          value={form.purpose}
          onChange={(e) => onChange({ ...form, purpose: e.target.value })}
        >
          {PURPOSES.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
      </div>

      <button className="btn btn-primary btn-block" disabled={submitting}>
        <Zap size={17} /> {submitting ? "Analyzing…" : "Analyze Payment"}
      </button>
    </form>
  );
}