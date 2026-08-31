// ============================================================
// CurrencyX AI — Transaction storage service (localStorage)
// ------------------------------------------------------------
// Prototype-only persistence for verified payments.
//
// Storage rules:
//   * A transaction is saved ONLY after the backend signature
//     verification succeeds (Checkout.jsx calls saveTransaction).
//   * Duplicates are detected by razorpay_payment_id /
//     razorpay_order_id so refreshing never double-inserts.
//   * Only non-sensitive metadata is stored — never card numbers,
//     CVV, bank details, passwords or any secret keys.
// ============================================================

const STORAGE_KEY = "currencyx_transactions";

/** Read all stored transactions (newest first). */
export function getStoredTransactions() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const list = raw ? JSON.parse(raw) : [];
    return Array.isArray(list) ? list : [];
  } catch {
    // Corrupt storage — reset rather than crash.
    localStorage.removeItem(STORAGE_KEY);
    return [];
  }
}

/**
 * Save a verified transaction. Returns the stored list.
 * No-ops (and returns the existing list) when a transaction with the
 * same Razorpay payment ID or order ID already exists.
 */
export function saveTransaction(txn) {
  const list = getStoredTransactions();
  const duplicate = list.some(
    (t) =>
      (txn.razorpay_payment_id && t.razorpay_payment_id === txn.razorpay_payment_id) ||
      (txn.razorpay_order_id && t.razorpay_order_id === txn.razorpay_order_id)
  );
  if (duplicate) return list;

  const record = {
    id: txn.id || `CX-${Date.now()}-${Math.random().toString(36).slice(2, 8).toUpperCase()}`,
    razorpay_payment_id: txn.razorpay_payment_id,
    razorpay_order_id: txn.razorpay_order_id,
    amount: Number(txn.amount) || 0,
    currency: txn.currency || "INR",
    destination_country: txn.destination_country || "",
    destination_currency: txn.destination_currency || "",
    recipient_amount: Number(txn.recipient_amount) || 0,
    payment_method: txn.payment_method || "",
    exchange_rate: Number(txn.exchange_rate) || 0,
    total_fees: Number(txn.total_fees) || 0,
    total_cost: Number(txn.total_cost) || 0,
    // "completed" is only ever set here — i.e. after successful
    // backend verification. Failed/unverified payments never reach this.
    status: txn.status || "completed",
    created_at: txn.created_at || new Date().toISOString(),
  };

  const next = [record, ...list];
  localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  return next;
}

/** Check whether a payment has already been recorded. */
export function hasTransaction(razorpayPaymentIdOrOrderId) {
  const key = String(razorpayPaymentIdOrOrderId || "");
  if (!key) return false;
  return getStoredTransactions().some(
    (t) => t.razorpay_payment_id === key || t.razorpay_order_id === key
  );
}