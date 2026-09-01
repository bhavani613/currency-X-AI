// ============================================================
// CurrencyX AI — Currency configuration (single source of truth)
// ------------------------------------------------------------
// Reusable list of supported source currencies. The backend
// supports the same codes (see app/services/payment_analyzer.py).
// ============================================================

export const CURRENCIES = [
  { code: "INR", name: "Indian Rupee", symbol: "₹" },
  { code: "USD", name: "US Dollar", symbol: "$" },
  { code: "EUR", name: "Euro", symbol: "€" },
  { code: "GBP", name: "British Pound", symbol: "£" },
  { code: "CAD", name: "Canadian Dollar", symbol: "C$" },
  { code: "AUD", name: "Australian Dollar", symbol: "A$" },
  { code: "SGD", name: "Singapore Dollar", symbol: "S$" },
  { code: "AED", name: "UAE Dirham", symbol: "د.إ" },
  { code: "JPY", name: "Japanese Yen", symbol: "¥" },
  { code: "CHF", name: "Swiss Franc", symbol: "Fr" },
  { code: "NZD", name: "New Zealand Dollar", symbol: "NZ$" },
];

export const DEFAULT_SOURCE_CURRENCY = "INR";

/** Symbol lookup by currency code (falls back to the code itself). */
export function currencySymbol(code) {
  return CURRENCIES.find((c) => c.code === code)?.symbol || code || "";
}