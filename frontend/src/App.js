import React, { useState, useEffect, createContext, useContext, Component } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import axios from "axios";
import "./index.css";

import AuthPage from "./AuthPage";
import Dashboard from "./Dashboard";

// ── Error Boundary ───────────────────────────────────────────────
class ErrorBoundary extends Component {
  state = { hasError: false, error: null };
  static getDerivedStateFromError(error) { return { hasError: true, error }; }
  componentDidCatch(error, info) { console.error("App crash:", error, info); }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ minHeight:"100vh", background:"#0a0a14", display:"flex", alignItems:"center", justifyContent:"center", flexDirection:"column", gap:"16px", color:"#e2e8f0", fontFamily:"Inter,sans-serif" }}>
          <div style={{ fontSize:"48px" }}>⚠️</div>
          <h2 style={{ fontSize:"20px", fontWeight:"700" }}>Something went wrong</h2>
          <p style={{ color:"#64748b", fontSize:"13px", maxWidth:"400px", textAlign:"center" }}>{this.state.error?.message}</p>
          <button onClick={()=>{ localStorage.clear(); window.location.reload(); }} style={{ padding:"10px 24px", background:"#6366f1", color:"#fff", border:"none", borderRadius:"10px", cursor:"pointer", fontWeight:"700" }}>
            Clear & Reload
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

// ── Theme Context ────────────────────────────────────────────────
export const ThemeContext = createContext({ theme: "dark", toggleTheme: () => {} });
export const useTheme = () => useContext(ThemeContext);

// ── Global axios interceptor ─────────────────────────────────────
axios.interceptors.response.use(
  (res) => res,
  (err) => {
    const detail = err.response?.data?.detail || "";
    const is401  = err.response?.status === 401;
    const isAuthError = is401 && (
      detail.includes("validate credentials") ||
      detail.includes("not authenticated") ||
      detail.includes("token") ||
      detail.includes("expired")
    );
    if (isAuthError) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      window.dispatchEvent(new Event("auth-change"));
    }
    return Promise.reject(err);
  }
);

export default function App() {
  // ── Auth state ─────────────────────────────────────────────────
  const [token, setToken] = useState(() => {
    const t = localStorage.getItem("access_token");
    if (!t || t === "undefined" || t === "null") {
      localStorage.removeItem("access_token");
      return null;
    }
    return t;
  });

  // ── Theme state ────────────────────────────────────────────────
  const [theme, setTheme] = useState(() => localStorage.getItem("theme") || "dark");

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }, [theme]);

  const toggleTheme = () => setTheme((t) => (t === "dark" ? "light" : "dark"));

  // ── Auth listener ──────────────────────────────────────────────
  useEffect(() => {
    const handleStorage = () => setToken(localStorage.getItem("access_token"));
    window.addEventListener("storage", handleStorage);
    window.addEventListener("auth-change", handleStorage);
    return () => {
      window.removeEventListener("storage", handleStorage);
      window.removeEventListener("auth-change", handleStorage);
    };
  }, []);

  const handleLogout = () => {
    localStorage.clear();
    setToken(null);
    window.dispatchEvent(new Event("auth-change"));
  };

  return (
    <ErrorBoundary>
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      <BrowserRouter>
        <ToastContainer
          position="top-right" autoClose={3500} hideProgressBar={false}
          theme={theme}
          toastStyle={{
            background: theme === "dark" ? "#1a1a2e" : "#ffffff",
            border: "1px solid rgba(99,102,241,0.25)",
            color: theme === "dark" ? "#e2e8f0" : "#1e1e3a",
          }}
        />
        <Routes>
          <Route path="/login"     element={!token ? <AuthPage onAuth={setToken} /> : <Navigate to="/dashboard" />} />
          <Route path="/dashboard" element={token   ? <Dashboard onLogout={handleLogout} /> : <Navigate to="/login" />} />
          <Route path="*"          element={<Navigate to={token ? "/dashboard" : "/login"} />} />
        </Routes>
      </BrowserRouter>
    </ThemeContext.Provider>
    </ErrorBoundary>
  );
}
