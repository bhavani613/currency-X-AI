import { Link } from "react-router-dom";
import { BarChart3, ShieldCheck, Globe, Mail, Share2 } from "lucide-react";

export default function Footer() {
  return (
    <footer className="footer">
      <div className="container footer-grid">
        <div className="footer-brand">
          <div className="footer-logo">
            <BarChart3 size={20} />
            <span>
              Currency<span>X</span> AI
            </span>
          </div>
          <p>
            The real cost of international payments, made transparent. Analyse
            fees, rates and savings before you send money abroad.
          </p>
          <div className="footer-social">
            <a href="#twitter" aria-label="Twitter" onClick={(e) => e.preventDefault()}>
              <Share2 size={18} />
            </a>
            <a href="#github" aria-label="GitHub" onClick={(e) => e.preventDefault()}>
              <Globe size={18} />
            </a>
            <a href="#linkedin" aria-label="LinkedIn" onClick={(e) => e.preventDefault()}>
              <Mail size={18} />
            </a>
          </div>
        </div>

        <div className="footer-col">
          <h4>Product</h4>
          <Link to="/analyze">Analyze Payment</Link>
          <Link to="/advisor">AI Advisor</Link>
          <Link to="/transactions">Transactions</Link>
          <Link to="/dashboard">Dashboard</Link>
        </div>

        <div className="footer-col">
          <h4>Company</h4>
          <a href="#about" onClick={(e) => e.preventDefault()}>About</a>
          <a href="#careers" onClick={(e) => e.preventDefault()}>Careers</a>
          <a href="#blog" onClick={(e) => e.preventDefault()}>Blog</a>
          <a href="#contact" onClick={(e) => e.preventDefault()}>Contact</a>
        </div>

        <div className="footer-col">
          <h4>Legal</h4>
          <a href="#privacy" onClick={(e) => e.preventDefault()}>Privacy</a>
          <a href="#terms" onClick={(e) => e.preventDefault()}>Terms</a>
        </div>
      </div>

      <div className="footer-bottom container">
        <span>© {new Date().getFullYear()} CurrencyX AI. A buildathon prototype.</span>
        <span className="footer-trust">
          <ShieldCheck size={15} /> Bank-grade security
        </span>
      </div>
    </footer>
  );
}