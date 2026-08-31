import { Link } from "react-router-dom";
import { Compass, Home } from "lucide-react";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";

export default function NotFound() {
  return (
    <div className="app-page">
      <Navbar />
      <div className="container page-wrap center-page">
        <div className="notfound">
          <span className="feature-icon"><Compass size={26} /></span>
          <h1 className="page-title">404</h1>
          <p className="page-sub">The page you're looking for doesn't exist.</p>
          <div className="notfound-actions">
            <Link to="/" className="btn btn-primary"><Home size={16} /> Back to Home</Link>
            <Link to="/analyze" className="btn btn-ghost">Calculate a Payment</Link>
          </div>
        </div>
      </div>
      <Footer />
    </div>
  );
}