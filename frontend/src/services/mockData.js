// ============================================================
// CurrencyX AI — Mock Data
// ------------------------------------------------------------
// Centralised mock data. Replace blend with real API responses
// (see ./api.js) once the FastAPI backend is connected.
// ============================================================

export const COUNTRIES = [
  { country: "United Kingdom", currency: "GBP", symbol: "£" },
  { country: "United States", currency: "USD", symbol: "$" },
  { country: "United Arab Emirates", currency: "AED", symbol: "د.إ" },
  { country: "Australia", currency: "AUD", symbol: "A$" },
  { country: "Canada", currency: "CAD", symbol: "C$" },
  { country: "Singapore", currency: "SGD", symbol: "S$" },
  { country: "Germany", currency: "EUR", symbol: "€" },
  { country: "France", currency: "EUR", symbol: "€" },
  { country: "Japan", currency: "JPY", symbol: "¥" },
  { country: "Switzerland", currency: "CHF", symbol: "Fr" },
  { country: "New Zealand", currency: "NZD", symbol: "NZ$" },
];

export const PURPOSES = [
  "Education",
  "Business",
  "Travel",
  "Family",
  "Shopping",
  "Other",
];

export const MOCK_AI_INSIGHT =
  "You could potentially save ₹4,250 on your recent international payments by choosing lower-cost payment methods.";

// Predefined replies for the AI Advisor chat.
export const AI_REPLIES = [
  {
    keywords: ["cheapest", "how to save", "reduce", "lowest cost", "save money"],
    answer:
      "Based on current rates, **Smart Payment** typically offers the lowest total cost. Compared to a credit card, you can save roughly 2–3% on FX markup alone. I'd recommend starting there for transfers above ₹50,000.",
  },
  {
    keywords: ["how much", "receive", "recipient", "get", "convert"],
    answer:
      "I can estimate the recipient amount. After exchange rate and fees, the exact figure depends on your method and amount. Use **Analyze Payment** and I'll break down the full cost before you lock anything in.",
  },
  {
    keywords: ["method", "choose", "which", "card", "bank"],
    answer:
      "For mid-to-large transfers, **Smart Payment** gives the best blend of low fees and speed. Cards are convenient but carry higher FX markups. If you only need near-instant settlement, a debit card is the middle ground.",
  },
  {
    keywords: ["fx", "markup", "exchange", "mid", "rate", "spread"],
    answer:
      "FX markup is the hidden spread banks add above the mid-market rate. It can be 2–4% of your amount. CurrencyX AI surfaces this cost so you can avoid overpaying — choosing a lower-markup method is the easiest win.",
  },
  {
    keywords: ["saving", "savings", "insight", "advice", "hello", "hi", "help"],
    answer:
      "Happy to help! Ask me about the cheapest way to send money abroad, what your recipient will receive, or how to reduce FX costs. I'll give you a clear, cost-focused recommendation.",
  },
];

