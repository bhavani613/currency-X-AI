// ============================================================
// CurrencyX AI — API Service Layer
// ------------------------------------------------------------
// Central configuration for the future FastAPI backend.
//
//  Real API calls will be connected here. Until then these
//  functions return mock data / promises so the frontend can be
//  developed and demoed independently.
// ============================================================

import { AI_REPLIES } from "./mockData";

export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1"
).replace(/\/+$/, "");

/** Backend origin (scheme + host + port) for health/readiness probes. */
export const API_ORIGIN = (() => {
  try {
    return new URL(API_BASE_URL).origin;
  } catch {
    return "http://127.0.0.1:8000";
  }
})();

// ------------------------------------------------------------------
// Error handling
// ------------------------------------------------------------------

/** User-facing message for network-level failures (backend down / CORS). */
function networkErrorMessage(backendReachable = false) {
  if (typeof navigator !== "undefined" && navigator.onLine === false) {
    return "You appear to be offline. Please check your internet connection and try again.";
  }
  // fetch() cannot distinguish "connection refused" from a CORS block — both
  // surface as a TypeError. When a /health probe proves the backend is up, the
  // failure is almost certainly a browser-side block (CORS / origin), so guide
  // the user there instead of telling them the backend is down.
  if (backendReachable) {
    return (
      "The CurrencyX AI backend is reachable, but the browser could not complete " +
      "this request. This usually means the request was blocked (CORS) — check " +
      "that the backend CORS_ORIGINS setting includes your frontend origin " +
      "(for example http://localhost:5173) and try again."
    );
  }
  return (
    "Cannot connect to the CurrencyX AI backend. Please make sure the backend " +
    "is running on port 8000. If it is running, the request may have been " +
    "blocked by the browser (CORS) — check the backend CORS_ORIGINS setting " +
    "and the frontend origin."
  );
}

/**
 * Extract the backend's safe error detail from a FastAPI response.
 * FastAPI returns `{ detail: "..." }` or `{ detail: [{ msg, loc, ... }] }`.
 * Returns "" when the body has no usable message.
 */
async function extractDetail(res) {
  try {
    const body = await res.json();
    const detail = body?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      return detail.map((d) => `${(d.loc || []).join(".")}: ${d.msg}`).join("; ");
    }
    if (detail) return String(detail);
  } catch {
    /* response had no JSON body — fall through */
  }
  return "";
}

/**
 * Convert a non-2xx response into a clean, user-friendly Error.
 * Useful backend messages are preserved for 4xx client errors; 5xx
 * responses are never surfaced verbatim (they may contain internals).
 */
async function responseToError(res) {
  const detail = await extractDetail(res);
  if (res.status === 401) {
    return new Error(detail || "Your session has expired. Please log in again.");
  }
  if (res.status === 403) {
    return new Error(detail || "You do not have permission to perform this action.");
  }
  if (res.status === 404) {
    return new Error(detail || "Requested resource was not found.");
  }
  if (res.status === 409) {
    return new Error(detail || "This conflicts with an existing record.");
  }
  if (res.status === 429) {
    return new Error("Too many requests. Please try again shortly.");
  }
  if (res.status >= 500) {
    return new Error(
      detail
        ? `CurrencyX AI backend encountered an error: ${detail}`
        : "CurrencyX AI backend encountered an internal error. Please try again."
    );
  }
  return new Error(detail || `Request failed with status ${res.status}.`);
}

/** Shared request helper — all API calls go through this so connection,
 * CORS, and HTTP error handling stay consistent across the app.
 * Pass `auth: true` to attach the stored JWT bearer token.
 */
const AUTH_TOKEN_KEY = "currencyx_token";

async function request(path, { method = "GET", body, auth = false } = {}) {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth) {
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  let res;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    });
  } catch (err) {
    // fetch only throws on network-level failures (backend down, offline, CORS block).
    // Probe /health first so the error message never falsely claims the backend
    // is down when it is actually reachable.
    const reachable = await checkBackendHealth();
    if (import.meta.env.DEV) {
      console.warn(
        "[api] request failed:",
        path,
        err?.name,
        err?.message,
        "backend reachable:",
        reachable
      );
    }
    throw new Error(networkErrorMessage(reachable));
  }
  if (!res.ok) {
    throw await responseToError(res);
  }
  return res.json();
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
  const data = await request("/payments/analyze", {
    method: "POST",
    body: {
      amount,
      source_currency: sourceCurrency,
      destination_country: destinationCountry,
      destination_currency: destinationCurrency,
      purpose,
    },
  });
  return normalizeAnalysisResponse(data, {
    amount,
    sourceCurrency,
    destinationCountry,
    destinationCurrency,
    purpose,
  });
}

// ---------------------------------------------------------------------------
// Backend → frontend response normalization
// ---------------------------------------------------------------------------

/** Map backend method names to the ids used by PaymentMethodCard icons. */
const METHOD_IDS = {
  "Smart Payment": "SMART",
  "Bank Transfer": "BANK_TRANSFER",
  UPI: "UPI",
  "Debit Card": "DEBIT_CARD",
  "Credit Card": "CREDIT_CARD",
};

const METHOD_TAGLINES = {
  SMART: "Best balance of cost & speed",
  BANK_TRANSFER: "Traditional & reliable",
  UPI: "Fast & low-cost",
  DEBIT_CARD: "Instant but costlier",
  CREDIT_CARD: "Pay now, settle later",
};

const METHOD_SPEEDS = {
  SMART: "1-2 business days",
  BANK_TRANSFER: "2-4 business days",
  UPI: "Within minutes",
  DEBIT_CARD: "Within minutes",
  CREDIT_CARD: "Within minutes",
};

function normalizeAnalysisResponse(
  data,
  { amount, sourceCurrency, destinationCountry, destinationCurrency, purpose } = {}
) {
  const currencySymbols = {
    INR: "₹",
    GBP: "£",
    USD: "$",
    AED: "AED ",
    AUD: "A$",
    CAD: "C$",
    SGD: "S$",
    EUR: "€",
    JPY: "¥",
    CHF: "Fr",
    NZD: "NZ$",
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
      totalCost: +(amount + fee).toFixed(2),
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
    // INR equivalents used for the Razorpay checkout (INR-only) flow.
    amountInInr: data.amount_in_inr ?? null,
    totalCostInInr: data.total_cost_in_inr ?? null,
    methods,
    savings: rec.potential_savings ?? 0,
    recommendation: rec.method ?? "",
    explanation: rec.reason ?? "",
    disclaimer: data.disclaimer ?? "",
  };
}

const wait = (ms = 700) => new Promise((r) => setTimeout(r, ms));

/** Shared JSON POST helper with the standard error handling. */
function postJSON(path, body) {
  return request(path, { method: "POST", body });
}

/**
 * loginUser — POST /auth/login against the FastAPI + PostgreSQL backend.
 * Returns { success, user: { id, full_name, email }, access_token }.
 * Throws a clean Error with the backend message on invalid credentials.
 */
export function loginUser({ email, password }) {
  return postJSON("/auth/login", { email, password });
}

/**
 * signupUser — POST /auth/signup. The account is created in PostgreSQL
 * with a bcrypt password hash (never sent or stored in plaintext).
 * Throws with the backend message on duplicate email/validation errors.
 */
export function signupUser({ fullName, email, password }) {
  return postJSON("/auth/signup", { full_name: fullName, email, password });
}

/**
 * forgotPassword — POST /auth/forgot-password.
 * Always succeeds with a generic message so the response cannot be used
 * to discover whether an email is registered (no user enumeration).
 * Returns { success, message }.
 */
export function forgotPassword({ email }) {
  return postJSON("/auth/forgot-password", { email });
}

/**
 * resetPassword — POST /auth/reset-password.
 * Completes a password reset with the single-use token from the reset
 * link/email. Returns { success, message } or throws on invalid/expired
 * tokens or weak passwords.
 */
export function resetPassword({ token, password }) {
  return postJSON("/auth/reset-password", { token, password });
}

/**
 * verifyPassword — POST /auth/verify-password.
 * Requires an authenticated session (JWT). Verifies the user's current
 * password against the stored bcrypt hash before authorizing a sensitive
 * action such as executing a payment. Returns { success: true } or throws
 * a clean Error on mismatch / auth failure.
 * The password is sent once over HTTPS and is never stored client-side.
 */
export function verifyPassword(password) {
  return request("/auth/verify-password", { method: "POST", body: { password }, auth: true });
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

async function paymentRequest(path, body) {
  // Payment endpoints require authentication server-side — always send the JWT.
  return request(path, { method: "POST", body, auth: true });
}

/**
 * checkBackendHealth — GET /health (lightweight, unauthenticated).
 * Used by the navbar status indicator. Returns true when reachable.
 */
export async function checkBackendHealth() {
  try {
    const res = await fetch(`${API_ORIGIN}/health`, { method: "GET" });
    return res.ok;
  } catch {
    return false;
  }
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
  return request("/advisor/analyze", {
    method: "POST",
    body: {
      amount,
      source_currency: sourceCurrency,
      destination_country: destinationCountry,
      destination_currency: destinationCurrency,
      purpose,
    },
  });
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

// ============================================================
// Revenue Recovery Agent (JWT-protected endpoints)
// ============================================================

/** getRecoverySummary — GET /recovery/summary. Overview for the current user. */
export function getRecoverySummary() {
  return request("/recovery/summary", { auth: true });
}

/**
 * getRecoveryCases — GET /recovery/cases
 * Optional `status` filter (PENDING / FAILED / ABANDONED / RECOVERY_RECOMMENDED)
 * plus limit/offset pagination. Only sends parameters the backend supports.
 */
export function getRecoveryCases({ status, limit = 50, offset = 0 } = {}) {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  const qs = params.toString();
  return request(`/recovery/cases${qs ? `?${qs}` : ""}`, { auth: true });
}

/** getRecoveryCase — GET /recovery/cases/{id}. Single case detail. */
export function getRecoveryCase(id) {
  return request(`/recovery/cases/${encodeURIComponent(id)}`, { auth: true });
}

/** retryRecoveryCase — POST /recovery/cases/{id}/retry. Accepts the recommendation;
 * the actual payment still goes through the normal checkout/Razorpay flow.
 * Returns { success, case_id, payment_attempt_id, recommendation_id, retry_payment }. */
export function retryRecoveryCase(id) {
  return request(`/recovery/cases/${encodeURIComponent(id)}/retry`, { method: "POST", auth: true });
}

/** completeRecoveryCase — POST /recovery/cases/{id}/complete. Marks a recovery case
 * as successfully recovered after verified payment success. Idempotent: calling
 * multiple times does not double-count recovered revenue. */
export function completeRecoveryCase(id, recoveredAmount) {
  const body = recoveredAmount != null ? { recovered_amount: recoveredAmount } : {};
  return request(`/recovery/cases/${encodeURIComponent(id)}/complete`, { method: "POST", body, auth: true });
}

/** dismissRecoveryCase — POST /recovery/cases/{id}/dismiss. No payment side effects. */
export function dismissRecoveryCase(id) {
  return request(`/recovery/cases/${encodeURIComponent(id)}/dismiss`, { method: "POST", auth: true });
}

/** seedDemoRecoveryCases — POST /recovery/dev/demo-cases. DEV ONLY seed helper;
 * the backend rejects it when RECOVERY_DEMO_ENABLED=false. */
export function seedDemoRecoveryCases() {
  return request("/recovery/dev/demo-cases", { method: "POST", auth: true });
}

/**
 * createPaymentAttempt — POST /recovery/payment-attempts.
 * Records a payment attempt (created / pending / failed / abandoned) for the
 * authenticated user. Used by the demo failure flow before analysis.
 */
export function createPaymentAttempt(data) {
  return request("/recovery/payment-attempts", { method: "POST", body: data, auth: true });
}

/**
 * analyzeFailure — POST /recovery/analyze-failure.
 * Runs the deterministic Revenue Recovery engine on the failure, persists the
 * attempt + recommendation, and returns { success, payment_attempt_id,
 * recommendation_id, analysis }.
 */
export function analyzeFailure(data) {
  return request("/recovery/analyze-failure", { method: "POST", body: data, auth: true });
}