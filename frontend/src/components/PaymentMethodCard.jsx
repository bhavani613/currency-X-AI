import {
  Zap,
  Landmark,
  CreditCard,
  Smartphone,
  BadgeCheck,
  Check,
  Clock,
} from "lucide-react";

const ICONS = {
  SMART: Zap,
  BANK_TRANSFER: Landmark,
  DEBIT_CARD: CreditCard,
  CREDIT_CARD: Smartphone,
};

export default function PaymentMethodCard({ method, selected, onSelect, showSelect = true }) {
  const Icon = ICONS[method.id] || Zap;
  const isRecommended = method.recommended;
  const cheapest = method.isCheapest;

  return (
    <div
      className={`method-card ${selected ? "selected" : ""} ${
        showSelect ? "clickable" : ""
      } ${cheapest ? "cheapest" : ""}`}
      onClick={showSelect ? () => onSelect(method.id) : undefined}
    >
      <div className="method-top">
        <span className="method-icon">
          <Icon size={21} />
        </span>
        <div className="method-title">
          <h4>{method.label}</h4>
          <p>{method.tagline}</p>
        </div>
        {(cheapest || isRecommended) && (
          <span className="rec-badge">
            <BadgeCheck size={13} /> RECOMMENDED
          </span>
        )}
      </div>

      <div className="method-meta">
        <div>
          <span>Recipient gets</span>
          <strong>
            {method.recipientAmount !== undefined
              ? `${method.symbol || ""}${method.recipientAmount}`
              : "—"}
          </strong>
        </div>
        <div>
          <span>Total fees</span>
          <strong>₹{method.totalFees?.toLocaleString("en-IN") ?? "—"}</strong>
        </div>
        <div>
          <span>Markup</span>
          <strong>{method.fxMarkupPct}%</strong>
        </div>
        <div className="method-speed">
          <Clock size={13} /> {method.speed}
        </div>
      </div>

      {showSelect && selected && (
        <div className="method-selected-tag">
          <Check size={15} /> Selected
        </div>
      )}
    </div>
  );
}