import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { UserCircle, LogOut, Save, Bell, Globe2 } from "lucide-react";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import { useAuth } from "../context/AuthContext";
import { COUNTRIES } from "../services/mockData";

export default function Profile() {
  const { user, logout, updateUser } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({
    name: user?.name || "",
    email: user?.email || "",
    defaultCurrency: "INR",
    defaultCountry: "India",
    notifications: true,
  });
  const [saved, setSaved] = useState(false);

  const handleSave = (e) => {
    e.preventDefault();
    updateUser({ ...form });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="app-page">
      <Navbar />
      <div className="container page-wrap profile-layout">
        <div className="page-head">
          <div>
            <h1 className="page-title">Profile</h1>
            <p className="page-sub">Manage your account and transfer preferences.</p>
          </div>
        </div>

        <form className="card profile-card" onSubmit={handleSave}>
          <div className="profile-identity">
            <span className="profile-avatar"><UserCircle size={34} /></span>
            <div>
              <strong>{form.name || "Your name"}</strong>
              <span>{form.email}</span>
            </div>
          </div>

          <div className="form-grid">
            <div className="field">
              <label htmlFor="pf-name">Name</label>
              <input id="pf-name" value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </div>
            <div className="field">
              <label htmlFor="pf-email">Email</label>
              <input id="pf-email" type="email" value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })} />
            </div>
          </div>

          <div className="field-group">
            <h3 className="field-group-title"><Globe2 size={16} /> Preferences</h3>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="pf-ccy">Default source currency</label>
                <select id="pf-ccy" value={form.defaultCurrency}
                  onChange={(e) => setForm({ ...form, defaultCurrency: e.target.value })}>
                  <option value="INR">INR — Indian Rupee</option>
                  <option value="USD">USD — US Dollar</option>
                  <option value="EUR">EUR — Euro</option>
                </select>
              </div>
              <div className="field">
                <label htmlFor="pf-country">Default country</label>
                <select id="pf-country" value={form.defaultCountry}
                  onChange={(e) => setForm({ ...form, defaultCountry: e.target.value })}>
                  <option>India</option>
                  {COUNTRIES.map((c) => <option key={c.country} value={c.country}>{c.country}</option>)}
                </select>
              </div>
            </div>
          </div>

          <div className="field-group">
            <h3 className="field-group-title"><Bell size={16} /> Notifications</h3>
            <label className="checkbox">
              <input type="checkbox" checked={form.notifications}
                onChange={(e) => setForm({ ...form, notifications: e.target.checked })} />
              <span>Email me alerts about fees changes and savings opportunities</span>
            </label>
          </div>

          <div className="profile-actions">
            <button className="btn btn-primary" type="submit"><Save size={16} /> Save Changes</button>
            <button className="btn btn-ghost" type="button" onClick={handleLogout}>
              <LogOut size={16} /> Logout
            </button>
            {saved && <span className="save-ok">✓ Saved</span>}
          </div>
        </form>
      </div>
      <Footer />
    </div>
  );
}