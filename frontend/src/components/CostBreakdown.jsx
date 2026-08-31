import { Info } from "lucide-react";

function Row({ label, value, strong = false, highlight = false }) {
  return (
    <div className={`break-row ${strong ? "strong" : ""} ${highlight ? "highlight" : ""}`}>
      <span>{label}</span>
      <span>{value}</span>
    </div>
  );
}

export default function CostBreakdown({ data, currency = "₹" }) {
  const { requested, fees, recipientAmount } = data;

  return (
    <div className="cost-breakdown">
      <div className="cost-head">
        <h3>Cost Breakdown</h3>
        <Info size={16} />
      </div>

      <Row label="Amount to send" value={`${currency}${requested.amount.toLocaleString("en-IN")}`} />
      <Row
        label={`Exchange rate (${requested.sourceCurrency} → ${requested.destinationCurrency})`}
        value={`${currency}1 = ${requested.rate}`}
      />
      <Row label="FX markup" value={`${currency}${fees.fxMarkup.toLocaleString("en-IN")}`} />
      <Row label="Processing fee" value={`${currency}${fees.processingFee.toLocaleString("en-IN")}`} />
      <Row label="Other charges" value={`${currency}${fees.otherCharges.toLocaleString("en-IN")}`} />

      <div className="break-divider" />

      <Row label="Total fees" value={`${currency}${fees.totalFees.toLocaleString("en-IN")}`} strong />
      <Row label="Total cost" value={`${currency}${fees.totalCost.toLocaleString("en-IN")}`} strong />
      <Row
        label="Recipient receives"
        value={`${requested.destinationCurrency === "GBP" ? "£" : requested.destinationCurrency === "USD" ? "$" : ""}${recipientAmount}`}
        highlight
      />
    </div>
  );
}