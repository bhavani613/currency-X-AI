import { useState, useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import { Search, X, Filter, ArrowUpDown } from "lucide-react";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import Loading from "../components/Loading";
import {
  getStoredTransactions,
} from "../services/transactionService";

const statusClass = (s) =>
  s === "completed" ? "success" : s === "pending" ? "pending" : "failed";

const SORTS = ["Newest first", "Oldest first", "Highest amount", "Lowest amount"];

function TransactionModal({ txn, onClose }) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3>Transaction Detail</h3>
          <button className="icon-btn" onClick={onClose} aria-label="Close"><X size={18} /></button>
        </div>
        <div className="modal-body">
          <h4 className="detail-section-title">Payment Information</h4>
          <div className="detail-grid">
            <div><span>Razorpay Payment ID</span><strong className="mono">{txn.razorpay_payment_id}</strong></div>
            <div><span>Razorpay Order ID</span><strong className="mono">{txn.razorpay_order_id}</strong></div>
            <div><span>Date and Time</span><strong>{new Date(txn.created_at).toLocaleString()}</strong></div>
            <div>
              <span>Status</span>
              <span className={`pill ${statusClass(txn.status)}`}>{txn.status}</span>
            </div>
          </div>

          <h4 className="detail-section-title">Transfer Details</h4>
          <div className="detail-grid">
            <div><span>Amount</span><strong>₹{txn.amount.toLocaleString("en-IN")} {txn.currency}</strong></div>
            <div><span>Source Currency</span><strong>{txn.currency}</strong></div>
            <div><span>Destination Country</span><strong>{txn.destination_country}</strong></div>
            <div><span>Destination Currency</span><strong>{txn.destination_currency}</strong></div>
            <div><span>Recipient Amount</span><strong>{txn.recipient_amount.toLocaleString()} {txn.destination_currency}</strong></div>
            <div><span>Payment Method</span><strong>{txn.payment_method}</strong></div>
          </div>

          <h4 className="detail-section-title">Cost Breakdown</h4>
          <div className="detail-grid">
            <div><span>Exchange Rate</span><strong>{txn.exchange_rate}</strong></div>
            <div><span>Total Fees</span><strong>₹{txn.total_fees.toLocaleString("en-IN")}</strong></div>
            <div><span>Total Cost</span><strong>₹{txn.total_cost.toLocaleString("en-IN")}</strong></div>
          </div>

          <button className="btn btn-ghost" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}

export default function Transactions() {
  const [all, setAll] = useState([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("All");
  const [sort, setSort] = useState(SORTS[0]);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    // Read real verified transactions from localStorage.
    setAll(getStoredTransactions());
    setLoading(false);
  }, []);

  const destinations = useMemo(
    () => [...new Set(all.map((t) => t.destination_country))],
    [all]
  );

  const filtered = useMemo(() => {
    const q = query.toLowerCase().trim();
    const list = all.filter(
      (t) =>
        (!q ||
          t.razorpay_payment_id?.toLowerCase().includes(q) ||
          t.razorpay_order_id?.toLowerCase().includes(q) ||
          t.destination_country?.toLowerCase().includes(q) ||
          t.payment_method?.toLowerCase().includes(q)) &&
        (status === "All" || t.status === status.toLowerCase())
    );
    const byDate = (a, b) => new Date(a.created_at) - new Date(b.created_at);
    switch (sort) {
      case "Oldest first": return [...list].sort(byDate);
      case "Highest amount": return [...list].sort((a, b) => b.amount - a.amount);
      case "Lowest amount": return [...list].sort((a, b) => a.amount - b.amount);
      default: return [...list].sort((a, b) => byDate(b, a));
    }
  }, [all, query, status, sort]);

  const hasFilters = query || status !== "All" || sort !== SORTS[0];

  return (
    <div className="app-page">
      <Navbar />
      <div className="container page-wrap">
        <div className="page-head">
          <div>
            <h1 className="page-title">Transactions</h1>
            <p className="page-sub">Browse your international payment history.</p>
          </div>
          <Link to="/analyze" className="btn btn-primary">New Payment</Link>
        </div>

        <div className="filters">
          <div className="search-box">
            <Search size={17} />
            <input placeholder="Search by payment ID, order ID, country or method…" value={query}
              onChange={(e) => setQuery(e.target.value)} aria-label="Search transactions" />
            {query && (
              <button className="icon-btn" onClick={() => setQuery("")} aria-label="Clear search"><X size={15} /></button>
            )}
          </div>
          <div className="filter-select">
            <Filter size={15} />
            <select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Filter by status">
              <option value="All">All</option>
              <option value="completed">Completed</option>
            </select>
          </div>
          <div className="filter-select">
            <ArrowUpDown size={15} />
            <select value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Sort transactions">
              {SORTS.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
        </div>

        <section className="card">
          {loading ? (
            <Loading label="Loading transactions…" />
          ) : filtered.length === 0 ? (
            all.length === 0 ? (
              <div className="empty">
                <p>No completed transactions yet</p>
                <Link to="/analyze" className="btn btn-primary">Analyze a Payment</Link>
              </div>
            ) : (
              <div className="empty">
                <p>No transactions match your filters.</p>
                {hasFilters && (
                  <button className="btn btn-ghost"
                    onClick={() => { setQuery(""); setStatus("All"); setSort(SORTS[0]); }}>
                    Clear filters
                  </button>
                )}
              </div>
            )
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Date</th><th>Payment ID</th><th>Destination</th><th>Amount</th>
                    <th>Payment Method</th><th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((t) => (
                    <tr key={t.id} className="clickable-row" onClick={() => setSelected(t)}>
                      <td>{new Date(t.created_at).toLocaleDateString()}</td>
                      <td className="mono">{t.razorpay_payment_id}</td>
                      <td>{t.destination_country}</td>
                      <td>₹{t.amount.toLocaleString("en-IN")}</td>
                      <td>{t.payment_method}</td>
                      <td><span className={`pill ${statusClass(t.status)}`}>{t.status}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>

      {selected && <TransactionModal txn={selected} onClose={() => setSelected(null)} />}

      <Footer />
    </div>
  );
}