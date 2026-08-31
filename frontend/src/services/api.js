// ============================================================
// CurrencyX AI — API Service Layer
// ------------------------------------------------------------
// Central configuration for the future FastAPI backend.
//
//  Real API calls will be connected here. Until then these
//  functions return mock data / promises so the frontend can be
//  developed and demoed independently.
// ============================================================

import {
  MOCK_TRANSACTIONS,
  AI_REPLIES,
} from "./mockData";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1";

/** Error thrown when the backend cannot be reached at all. */
const CONNECTION_ERROR =
  "Unable to connect to the CurrencyX AI analysis service. Please make sure the backend is running.";

/**
 * Extract a human-readable message from a FastAPI error response.
 * FastAPI returns `{ detail: "..." }` or `{ detail: [{ msg, loc, ... }] }`.
 */
async function extractBackendError(res) {
  let message = `Request failed with status ${res.status}.`;
  try {
    const body = await res.json();
    const detail = body?.detail;
    if (typeof detail === "string") {
      message = detail;
    } else if (Array.isArray(detail) && detail.length > 0) {
      message = detail
        .map((d) => `${(d.loc || []).join(".")}: ${d.msg}`)
        .join("; ");
    } else if (detail) {
      message = String(detail);
    }
  } catch {
    /* response had no JSON body — keep the default message */
  }
  return new Error(message);
}

/**
 * analyzePayment — calls the FastAPI backend
 * POST ${API_BASE_URL}/payments/analyze and normalizes the snake_case
 * response into the shape the existing UI components expect
 * ({ requested, fees, recipientAmount, methods, savings,
 *    recommendation, explanation, disclaimer }).
 */
export async function analyzePayment({
  amount = 100000,
  sourceCurrency = "INR",
  destinationCountry = "United Kingdom",
  destinationCurrency = "",
  purpose = "Other",
}) {
  let res;
  try {
    res = await fetch(`${API_BASE_URL}/payments/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        amount,
        source_currency: sourceCurrency,
        destination_country: destinationCountry,
        destination_currency: destinationCurrency,
        purpose,
      }),
    });
  } catch {
    // fetch only throws on network-level failures (backend down, CORS block)
    throw new Error(CONNECTION_ERROR);
  }

  if (!res.ok) {
    throw await extractBackendError(res);
  }

  const data = await res.json();
  return normalizeAnalysisResponse(data);
}

// ---------------------------------------------------------------------------
// Backend → frontend response normalization
// ---------------------------------------------------------------------------

/** Map backend method names to the ids used by PaymentMethodCard icons. */
const METHOD_IDS = {
  "Smart Payment": "SMART",
  "Bank Transfer": "BANK_TRANSFER",
  "Debit Card": "DEBIT_CARD",
  "Credit Card": "CREDIT_CARD",
};

const METHOD_TAGLINES = {
  SMART: "Best balance of cost & speed",
  BANK_TRANSFER: "Traditional & reliable",
  DEBIT_CARD: "Instant but costlier",
  CREDIT_CARD: "Pay now, settle later",
};

const METHOD_SPEEDS = {
  SMART: "1-2 business days",
  BANK_TRANSFER: "2-4 business days",
  DEBIT_CARD: "Within minutes",
  CREDIT_CARD: "Within minutes",
};

function normalizeAnalysisResponse(data) {
  const currencySymbols = {
    GBP: "£",
    USD: "$",
    AED: "AED ",
    AUD: "A$",
    CAD: "C$",
  };

  const payment = data.payment || {};
  const fees = data.cost_breakdown || {};
  const recipient = data.recipient || {};
  const rec = data.recommendation || {};

  const methods = (data.payment_methods || []).map((m) => {
    const id = METHOD_IDS[m.name] || m.name;
    const fee = Number(m.estimated_fee) || 0;
    const transferable = Math.max(0, amount - fee);
    return {
      id,
      label: m.name,
      tagline: METHOD_TAGLINES[id] || "Payment option",
      speed: METHOD_SPEEDS[id] || "1-4 business days",
      fxMarkupPct: amount > 0 ? +((fee / amount) * 100).toFixed(1) : 0,
      totalFees: +fee.toFixed(2),
      recipientAmount: +(
        transferable * (data.exchange_rate || 0)
      ).toFixed(2),
      symbol: currencySymbols[recipient.currency] || "",
      isCheapest: m.name === rec.method,
      recommended: m.name === rec.method,
    };
  });

  return {
    requested: {
      amount: payment.amount ?? amount,
      sourceCurrency: payment.source_currency ?? sourceCurrency,
      destinationCountry: payment.destination_country ?? destinationCountry,
      destinationCurrency: payment.destination_currency ?? destinationCurrency,
      purpose: payment.purpose ?? purpose,
      rate: data.exchange_rate,
    },
    fees: {
      fxMarkup: fees.fx_markup ?? 0,
      processingFee: fees.processing_fee ?? 0,
      otherCharges: fees.other_charges ?? 0,
      totalFees: fees.total_fees ?? 0,
      totalCost: fees.total_cost ?? 0,
    },
    recipientAmount: recipient.estimated_amount ?? 0,
    recipientCurrency: recipient.currency ?? "",
    methods,
    savings: rec.potential_savings ?? 0,
    recommendation: rec.method ?? "",
    explanation: rec.reason ?? "",
    disclaimer: data.disclaimer ?? "",
  };
}

const wait = (ms = 700) => new Promise((r) => setTimeout(r, ms));

/** getTransactions — returns transaction history. */
export async function getTransactions() {
  await wait();
  // Real API: GET ${API_BASE_URL}/transactions
  return [...MOCK_TRANSACTIONS];
}

/** getTransaction — returns a single transaction by id. */
export async function getTransaction(id) {
  await wait();
  return MOCK_TRANSACTIONS.find((t) => t.id === id) || null;
}

/** loginUser — placeholder for POST /auth/login */
export async function loginUser({ email, password }) {
  await wait();
  // Real API: POST ${API_BASE_URL}/auth/login
  return { ok: true, email };
}

/** signupUser — placeholder for POST /auth/signup */
export async function signupUser({ fullName, email, password }) {
  await wait();
  // Real API: POST ${API_BASE_URL}/auth/signup
  return { ok: true, fullName, email };
}

/** logoutUser — placeholder for POST /auth/logout (or client-side clear) */
export async function logoutUser() {
  await wait();
  // Real API: POST ${API_BASE_URL}/auth/logout
  return { ok: true };
}

/** askAdvisor — returns a mock AI reply based on keywords. */
export async function askAdvisor(question) {
  await wait(900);
  const q = question.toLowerCase();
  const match =
    AI_REPLIES.find((r) => r.keywords.some((k) => q.includes(k))) ||
    AI_REPLIES[4];
  return match.answer;
}

// ============================================================
// Razorpay payment flow (TEST MODE)
// ============================================================

const PAYMENT_CONNECTION_ERROR =
  "Unable to reach the CurrencyX AI payment service. Please make sure the backend is running.";

async function paymentRequest(path, body) {
  let res;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error(PAYMENT_CONNECTION_ERROR);
  }
  if (!res.ok) {
    throw await extractBackendError(res);
  }
  return res.json();
}

/**
 * getAdvisorInsights — POST /advisor/analyze
 * Rule-based AI advisor insights derived from the payment analysis engine.
 * Returns { success, summary, recommended_method, potential_savings,
 * insights: [{title, description}], risk_level, tips, disclaimer }.
 */
export async function getAdvisorInsights({
  amount,
  sourceCurrency,
  destinationCountry,
  destinationCurrency,
  purpose,
}) {
  let res;
  try {
    res = await fetch(`${API_BASE_URL}/advisor/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        amount,
        source_currency: sourceCurrency,
        destination_country: destinationCountry,
        destination_currency: destinationCurrency,
        purpose,
      }),
    });
  } catch {
    throw new Error(PAYMENT_CONNECTION_ERROR);
  }
  if (!res.ok) {
    throw await extractBackendError(res);
  }
  return res.json();
}

/**
 * createPaymentOrder — POST /payments/create-order
 * Returns { success, order_id, amount (paise), currency, key_id }.
 * The secret key never touches the frontend.
 */
export async function createPaymentOrder({ amount, currency = "INR", receipt }) {
  return paymentRequest("/payments/create-order", { amount, currency, receipt });
}

/**
 * verifyPayment — POST /payments/verify
 * Sends the Razorpay checkout response for server-side signature
 * verification. Returns { success, message } only when verification passes.
 */
export async function verifyPayment({ razorpay_payment_id, razorpay_order_id, razorpay_signature }) {
  return paymentRequest("/payments/verify", {
    razorpay_payment_id,
    razorpay_order_id,
    razorpay_signature,
  });
}