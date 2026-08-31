import { useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { Menu, X, BarChart3 } from "lucide-react";
import { useAuth } from "../context/AuthContext";

function BrandMark() {
  return (
    <Link to="/" className="brand">
      <span className="brand-mark">
        <BarChart3 size={20} />
      </span>
      <span className="brand-text">
        Currency<span>X</span> AI
      </span>
    </Link>
  );
}

export default function Navbar() {
  const [open, setOpen] = useState(false);
  const { isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const links = isAuthenticated
    ? [
        { to: "/dashboard", label: "Dashboard" },
        { to: "/analyze", label: "Analyze" },
        { to: "/advisor", label: "AI Advisor" },
        { to: "/transactions", label: "Transactions" },
      ]
    : [
        { to: "/#features", label: "Features" },
        { to: "/#how-it-works", label: "How it Works" },
        { to: "/advisor", label: "AI Advisor" },
      ];

  return (
    <header className="navbar">
      <div className="navbar-inner container">
        <BrandMark />

        <nav className={`nav-links ${open ? "open" : ""}`}>
          {links.map((l) => (
            <NavLink
              key={l.label}
              to={l.to}
              className={({ isActive }) => (isActive ? "active" : "")}
              onClick={() => setOpen(false)}
            >
              {l.label}
            </NavLink>
          ))}

          <div className="nav-auth">
            {isAuthenticated ? (
              <button className="btn btn-ghost btn-sm" onClick={handleLogout}>
                Logout
              </button>
            ) : (
              <>
                <Link to="/login" className="btn btn-ghost btn-sm">
                  Login
                </Link>
                <Link to="/signup" className="btn btn-primary btn-sm">
                  Get Started
                </Link>
              </>
            )}
          </div>
        </nav>

        <button
          className="nav-toggle"
          aria-label="Toggle menu"
          onClick={() => setOpen((v) => !v)}
        >
          {open ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>
    </header>
  );
}