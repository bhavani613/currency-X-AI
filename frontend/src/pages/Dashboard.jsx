import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  ArrowLeftRight,
  Bot,
  ListOrdered,
  UserCircle,
  LogOut,
  Search,
  Sparkles,
  ArrowUpRight,
} from "lucide-react";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import StatCard from "../components/StatCard";
import Loading from "../components/Loading";
import { useAuth } from "../context/AuthContext";
import { getStoredTransactions } from "../services/transactionService";
import { MOCK_AI_INSIGHT } from "../services/mockData";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/analyze", label: "Analyze Payment", icon: ArrowLeftRight },
  { to: "/advisor", label: "AI Advisor", icon: Bot },
  { to: "/transactions", label: "Transactions", icon: ListOrdered },
  { to: "/profile", label: "Profile", icon: UserCircle },
];

const statusClass = (s) => {
  switch (s) {
    case "Success": return "success";
    case "Pending": return "pending";
    default: return "failed";
  }
};

const fmt = (n) => n.toLocaleString("en-IN");

function DashboardShell({ active, children }) {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const firstName = "there";

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="app-page">
      <Navbar />
      <div className="dashboard-layout container">
        <aside className="sidebar">
          <nav className="side-nav">
            {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
              <Link
                key={to}
                to={to}
                end={end}
                className={({ isActive }) => `side-link ${isActive ? "active" : ""}`}
              >
                <Icon size={18} /> {label}
              </Link>
            ))}
          </nav>
          <button className="side-logout" onClick={handleLogout}>
            <LogOut size={18} /> Logout
          </button>
        </aside>

        <main className="dashboard-main">{children}</main>
      </div>
      <Footer />
    </div>
  );
}

export default function Dashboard() {
  const { user } = useAuth();
  const firstName = user?.name?.split(" ")[0] || "there";
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Real verified transactions from localStorage.
    setTransactions(getStoredTransactions());
    setLoading(false);
  }, []);

  const recent = transactions.slice(0, 5);

  // Real statistics computed from verified transactions in localStorage.
  const totalSent = transactions.reduce((sum, t) => sum + (Number(t.amount) || 0), 0);
  const totalFees = transactions.reduce((sum, t) => sum + (Number(t.total_fees) || 0), 0);
  const stats = [
    { id: "totalPayments", label: "Total Transactions", value: transactions.length, suffix: "" },
    { id: "totalVolume", label: "Total Amount Sent", value: totalSent, prefix: "₹", suffix: "" },
    { id: "potentialSavings", label: "Total Fees Paid", value: totalFees, prefix: "₹", suffix: "" },
    {
      id: "intlPayments",
      label: "Latest Transaction",
      value: transactions[0]
        ? `₹${fmt(transactions[0].amount)} → ${transactions[0].destination_country || "—"}`
        : "—",
    },
  ];

  return (
    <DashboardShell active="/dashboard">
      <div className="page-head">
        <div>
          <h1 className="page-title">
            {greeting}, {firstName}
          </h1>
          <p className="page-sub">Here's your cross-border payments overview.</p>
        </div>
        <Link to="/analyze" className="btn btn-primary">
          Analyze a Payment <ArrowUpRight size={16} />
        </Link>
      </div>

      <div className="stats-grid">
        {stats.map((s) => (
          <StatCard key={s.id} {...s} />
        ))}
      </div>

      <div className="dash-grid">
        <section className="card dash-table-card">
          <div className="card-head">
            <h3>Recent Transactions</h3>
            <Link to="/transactions" className="text-link">
              View all
            </Link>
          </div>

          {loading ? (
            <Loading label="Loading transactions…" />
          ) : recent.length === 0 ? (
            <div className="empty">
              <p>No transactions yet.</p>
            </div>
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Destination</th>
                    <th>Amount</th>
                    <th>Currency</th>
                    <th>Status</th>
                    <th>Savings</th>
                  </tr>
                </thead>
                <tbody>
                  {recent.map((t) => (
                    <tr key={t.id}>
                      <td>{new Date(t.created_at).toLocaleDateString()}</td>
                      <td>{t.destination_country}</td>
                      <td>₹{fmt(t.amount)}</td>
                      <td>{t.destination_currency}</td>
                      <td><span className={`pill ${statusClass(t.status)}`}>{t.status}</span></td>
                      <td className={t.total_fees ? "cell-save" : ""}>
                        {t.total_fees ? `₹${fmt(t.total_fees)}` : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="card ai-insight">
          <div className="ai-insight-head">
            <span className="feature-icon"><Sparkles size={20} /></span>
            <h3>AI Insight</h3>
          </div>
          <p>{MOCK_AI_INSIGHT}</p>
          <Link to="/advisor" className="btn btn-ghost btn-sm">
            Ask AI Advisor
          </Link>
        </section>
      </div>
    </DashboardShell>
  );
}