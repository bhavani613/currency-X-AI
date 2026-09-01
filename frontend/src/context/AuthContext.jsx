// ============================================================
// CurrencyX AI — Auth Context
// ------------------------------------------------------------
// Real authentication backed by the FastAPI + PostgreSQL backend
// (POST /auth/signup, POST /auth/login). localStorage is used ONLY
// to persist the frontend session state (user profile + JWT) —
// the actual accounts live in PostgreSQL with bcrypt password
// hashes. Passwords are never stored client-side.
//
// localStorage keys:
//   currencyx_user   — serialized user profile (session state)
//   currencyx_auth   — "1" flag marking the user as authenticated
//   currencyx_token  — JWT access token from the backend
// ============================================================

import { createContext, useContext, useState, useEffect } from "react";
import { loginUser, signupUser } from "../services/api";

const AuthContext = createContext(null);
const USER_KEY = "currencyx_user";
const AUTH_KEY = "currencyx_auth";
const TOKEN_KEY = "currencyx_token";

function readJSON(key) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

/** Normalize the backend user payload for the UI. */
function toProfile(apiUser) {
  return {
    id: apiUser.id,
    name: apiUser.full_name,
    email: apiUser.email,
  };
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Restore session on refresh using the persisted auth state.
  // NOTE: this restores the *session*, not the account — accounts
  // persist in PostgreSQL and are re-verified on every login.
  useEffect(() => {
    const authFlag = localStorage.getItem(AUTH_KEY);
    if (authFlag === "1") {
      setUser(readJSON(USER_KEY));
    }
    setLoading(false);
  }, []);

  const commit = (profile, token) => {
    localStorage.setItem(USER_KEY, JSON.stringify(profile));
    localStorage.setItem(AUTH_KEY, "1");
    if (token) localStorage.setItem(TOKEN_KEY, token);
    setUser(profile);
  };

  /**
   * login — verifies credentials against PostgreSQL via the backend.
   * Throws the backend's error message (e.g. "Invalid email or password.")
   * so pages can display it directly.
   */
  const login = async ({ email, password }) => {
    const data = await loginUser({ email, password });
    const profile = toProfile(data.user);
    commit(profile, data.access_token);
    return profile;
  };

  /**
   * signup — creates the account in PostgreSQL via the backend.
   * Throws with the backend message on duplicate email/validation errors.
   */
  const signup = async ({ fullName, email, password }) => {
    const data = await signupUser({ fullName, email, password });
    const profile = toProfile(data.user);
    commit(profile, data.access_token);
    return profile;
  };

  const updateUser = (patch) => {
    setUser((prev) => {
      const next = { ...prev, ...patch };
      localStorage.setItem(USER_KEY, JSON.stringify(next));
      return next;
    });
  };

  const logout = () => {
    localStorage.removeItem(AUTH_KEY);
    localStorage.removeItem(TOKEN_KEY);
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