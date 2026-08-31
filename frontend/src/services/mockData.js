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
];

export const PURPOSES = [
  "Education",
  "Business",
  "Travel",
  "Family",
  "Shopping",
  "Other",
];

export const STATUSES = ["Success", "Pending", "Failed"];

// Payment methods used by the analysis engine.
export const PAYMENT_METHODS = [
  {
    id: "SMART",
    label: "Smart Payment",
    tagline: "AI-selected lowest cost",
    fxMarkupPct: 0.35,
    processingFeePct: 0.15,
    fixedFee: 99,
    speed: "1–2 days",
    recommended: true,
  },
  {
    id: "BANK_TRANSFER",
    label: "Bank Transfer",
    tagline: "Traditional wire transfer",
    fxMarkupPct: 1.8,
    processingFeePct: 0.9,
    fixedFee: 450,
    speed: "2–5 days",
  },
  {
    id: "DEBIT_CARD",
    label: "Debit Card",
    tagline: "Pay directly with your card",
    fxMarkupPct: 2.4,
    processingFeePct: 1.1,
    fixedFee: 200,
    speed: "Instant",
  },
  {
    id: "CREDIT_CARD",
    label: "Credit Card",
    tagline: "Earn points but pay more",
    fxMarkupPct: 3.2,
    processingFeePct: 1.5,
    fixedFee: 250,
    speed: "Instant",
  },
];

export const MOCK_DASHBOARD_STATS = [
  { id: "totalPayments", label: "Total Payments", value: 24, suffix: "" },
  { id: "totalVolume", label: "Total Volume", value: 18.4, prefix: "₹", suffix: "L" },
  { id: "potentialSavings", label: "Potential Savings", value: 4248, prefix: "₹", suffix: "" },
  { id: "intlPayments", label: "International Payments", value: 16, suffix: "" },
];

export const MOCK_AI_INSIGHT =
  "You could potentially save ₹4,250 on your recent international payments by choosing lower-cost payment methods.";

export const MOCK_TRANSACTIONS = [
  {
    id: "CX-2024-00912",
    date: "2024-06-18",
    destination: "United Kingdom",
    currency: "GBP",
    amount: 100000,
    recipientAmount: 875.6,
    method: "Smart Payment",
    status: "Success",
    savings: 3000,
  },
  {
    id: "CX-2024-00887",
    date: "2024-06-11",
    destination: "United States",
    currency: "USD",
    amount: 150000,
    recipientAmount: 1560.4,
    method: "Bank Transfer",
    status: "Pending",
    savings: 1280,
  },
  {
    id: "CX-2024-00851",
    date: "2024-05-29",
    destination: "Australia",
    currency: "AUD",
    amount: 60000,
    recipientAmount: 1048.2,
    method: "Debit Card",
    status: "Success",
    savings: 720,
  },
  {
    id: "CX-2024-00820",
    date: "2024-05-22",
    destination: "United Arab Emirates",
    currency: "AED",
    amount: 80000,
    recipientAmount: 3524.3,
    method: "Credit Card",
    status: "Failed",
    savings: 0,
  },
  {
    id: "CX-2024-00794",
    date: "2024-05-14",
    destination: "Canada",
    currency: "CAD",
    amount: 120000,
    recipientAmount: 1956.8,
    method: "Smart Payment",
    status: "Success",
    savings: 2140,
  },
  {
    id: "CX-2024-00760",
    date: "2024-05-03",
    destination: "Singapore",
    currency: "SGD",
    amount: 45000,
    recipientAmount: 733.9,
    method: "Bank Transfer",
    status: "Success",
    savings: 610,
  },
];

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

// Live exchange rates used for the mock analysis engine.
export const FX_RATES = {
  GBP: 0.008756,
  USD: 0.01197,
  AED: 0.04396,
  AUD: 0.0180,
  CAD: 0.0163,
  SGD: 0.01597,
  EUR: 0.01102,
  JPY: 1.799,
};

// Default profile stored on signup.
export const DEFAULT_PROFILE = {
  name: "",
  email: "",
  defaultCurrency: "INR",
  defaultCountry: "India",
  notifications: true,
};