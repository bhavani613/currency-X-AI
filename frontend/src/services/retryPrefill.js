// ============================================================
// CurrencyX AI — Recovery retry prefill helper
// ------------------------------------------------------------
// Builds the Analyze-page form state for a recovery retry. The
// recovery case stores the amount/source currency; the remaining
// analysis context (destination, purpose) is merged from the
// stored last-analysis inputs when available so the Analyze page
// opens fully prefilled instead of losing the destination.
// ============================================================

const LAST_ANALYSIS_KEY = "currencyx_last_analysis";

export function buildRetryPrefill(retryPayment = {}) {
  const prefill = {
    amount: retryPayment.amount != null ? String(retryPayment.amount) : "",
    sourceCurrency: retryPayment.currency || "INR",
    destinationCountry: "",
    destinationCurrency: "",
    purpose: "Other",
  };

  try {
    const stored = JSON.parse(sessionStorage.getItem(LAST_ANALYSIS_KEY) || "null");
    if (stored && typeof stored === "object") {
      prefill.sourceCurrency = prefill.sourceCurrency || stored.sourceCurrency || "INR";
      prefill.destinationCountry = prefill.destinationCountry || stored.destinationCountry || "";
      prefill.destinationCurrency = prefill.destinationCurrency || stored.destinationCurrency || "";
      prefill.purpose = stored.purpose || prefill.purpose;
      // Amount: prefer the case's stored amount (authoritative for the retry),
      // fall back to the last analysis amount when the case has none.
      if (!prefill.amount && stored.amount) prefill.amount = String(stored.amount);
    }
  } catch {
    /* corrupted storage — keep the case-provided values only */
  }

  return prefill;
}