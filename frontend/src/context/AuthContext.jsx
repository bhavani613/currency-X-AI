// ============================================================
// CurrencyX AI — Auth Context
// ------------------------------------------------------------
// Mock authentication using localStorage only. Designed so it
// can be swapped for the FastAPI backend (see services/api.js)
// without touching the consuming components.
//
// localStorage keys:
//   currencyx_user  — serialized user profile (kept after logout)
//   currencyx_auth  — "1" flag marking the user as authenticated
// ============================================================

import { createContext, useContext, useState, useEffect } from "react";

const AuthContext = createContext(null);
const USER_KEY = "currencyx_user";
const AUTH_KEY = "currencyx_auth";

function readJSON(key) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Restore session on refresh using the persisted auth flag.
  useEffect(() => {
    const authFlag = localStorage.getItem(AUTH_KEY);
    if (authFlag === "1") {
      const stored = readJSON(USER_KEY);
      setUser(stored);
    }
    setLoading(false);
  }, []);

  const commit = (data) => {
    localStorage.setItem(USER_KEY, JSON.stringify(data));
    localStorage.setItem(AUTH_KEY, "1");
    setUser(data);
  };

  const login = (data, _remember) => {
    commit(data);
    return data;
  };

  const signup = (data) => {
    commit(data);
    return data;
  };

  const updateUser = (patch) => {
    setUser((prev) => {
      const next = { ...prev, ...patch };
      localStorage.setItem(USER_KEY, JSON.stringify(next));
      return next;
    });
  };

  const logout = () => {
    // Clear the auth flag so refresh keeps the user signed out.
    // The saved profile (currencyx_user) is intentionally kept so a
    // returning user can sign in again with their stored details.
    localStorage.removeItem(AUTH_KEY);
    setUser(null);
  };

  const getStoredUser = (email) => {
    const stored = readJSON(USER_KEY);
    if (
      stored &&
      typeof stored.email === "string" &&
      stored.email.toLowerCase() === String(email || "").toLowerCase()
    ) {
      return stored;
    }
    return null;
  };

  const isAuthenticated = !!user;

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        isAuthenticated,
        login,
        signup,
        updateUser,
        logout,
        getStoredUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}