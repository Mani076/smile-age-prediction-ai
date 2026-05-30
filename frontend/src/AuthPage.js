import React, { useState } from "react";
import { toast } from "react-toastify";
import axios from "axios";
import { useTheme } from "./App";

const API = "http://localhost:8000";

function passwordStrength(pw) {
  let s = 0;
  if (pw.length >= 8) s++;
  if (/[A-Z]/.test(pw)) s++;
  if (/[0-9]/.test(pw)) s++;
  if (/[^A-Za-z0-9]/.test(pw)) s++;
  return s;
}
const SL = ["", "Weak", "Fair", "Good", "Strong"];
const SC = ["", "#ef4444", "#f59e0b", "#06b6d4", "#10b981"];

function Field({ label, children }) {
  return (
    <div style={{ marginBottom: "14px" }}>
      <label style={{ display: "block", fontSize: "12px", fontWeight: "700", color: "var(--text3)", marginBottom: "6px", letterSpacing: "0.05em" }}>
        {label}
      </label>
      {children}
    </div>
  );
}

export default function AuthPage({ onAuth }) {
  const { theme, toggleTheme } = useTheme();
  const [mode, setMode]       = useState("login");
  const [loading, setLoading] = useState(false);
  const [loginForm, setLoginForm] = useState({ email: "", password: "" });
  const [regForm, setRegForm] = useState({
    first_name: "", last_name: "", email: "",
    phone: "", password: "", confirm_password: "",
  });

  const pwStrength = passwordStrength(regForm.password);

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!loginForm.email || !loginForm.password) { toast.warning("Fill in all fields"); return; }
    setLoading(true);
    try {
      const res = await axios.post(`${API}/api/auth/login`, loginForm);
      localStorage.setItem("access_token", res.data.access_token);
      if (res.data.refresh_token) localStorage.setItem("refresh_token", res.data.refresh_token);
      toast.success("Welcome back!");
      onAuth(res.data.access_token);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Login failed");
    }
    setLoading(false);
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    if (!regForm.first_name || !regForm.last_name || !regForm.email || !regForm.password) {
      toast.warning("Fill in all required fields"); return;
    }
    if (regForm.password !== regForm.confirm_password) { toast.error("Passwords do not match"); return; }
    if (pwStrength < 2) { toast.warning("Password is too weak"); return; }
    setLoading(true);
    try {
      await axios.post(`${API}/api/auth/register`, {
        first_name: regForm.first_name,
        last_name:  regForm.last_name,
        email:      regForm.email,
        phone_number: regForm.phone || undefined,
        password:   regForm.password,
        confirm_password: regForm.confirm_password,
      });
      toast.success("Account created! Please log in.");
      setMode("login");
      setLoginForm({ email: regForm.email, password: "" });
    } catch (err) {
      toast.error(err.response?.data?.detail || "Registration failed");
    }
    setLoading(false);
  };

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)", display: "flex", alignItems: "center", justifyContent: "center", padding: "20px" }}>
      <button onClick={toggleTheme} style={{ position: "fixed", top: "16px", right: "16px", background: "var(--card)", border: "1px solid var(--border)", borderRadius: "10px", padding: "8px 12px", cursor: "pointer", color: "var(--text2)", fontSize: "18px" }}>
        {theme === "dark" ? "☀️" : "🌙"}
      </button>
      <div className="card fade-in" style={{ width: "100%", maxWidth: "420px", padding: "36px" }}>
        <div style={{ textAlign: "center", marginBottom: "28px" }}>
          <div style={{ width: "60px", height: "60px", background: "linear-gradient(135deg,#6366f1,#06b6d4)", borderRadius: "18px", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "28px", margin: "0 auto 14px", boxShadow: "0 0 24px rgba(99,102,241,0.4)" }}>🤖</div>
          <h1 style={{ fontSize: "22px", fontWeight: "900" }} className="gradient-text">AI Face Analysis</h1>
          <p style={{ color: "var(--text3)", fontSize: "13px", marginTop: "4px" }}>Smile · Age · Emotion Detection</p>
        </div>
        <div style={{ display: "flex", background: "var(--bg2)", borderRadius: "10px", padding: "4px", marginBottom: "24px" }}>
          {["login", "register"].map(m => (
            <button key={m} onClick={() => setMode(m)} style={{ flex: 1, padding: "8px", borderRadius: "8px", border: "none", cursor: "pointer", fontWeight: "700", fontSize: "13px", fontFamily: "Inter,sans-serif", background: mode === m ? "var(--card)" : "transparent", color: mode === m ? "var(--primary-light)" : "var(--text3)", transition: "all 0.2s" }}>
              {m === "login" ? "Sign In" : "Sign Up"}
            </button>
          ))}
        </div>
        {mode === "login" && (
          <form onSubmit={handleLogin} className="fade-in">
            <Field label="EMAIL">
              <input type="email" placeholder="you@example.com" value={loginForm.email} onChange={e => setLoginForm(f => ({ ...f, email: e.target.value }))} />
            </Field>
            <Field label="PASSWORD">
              <input type="password" placeholder="••••••••" value={loginForm.password} onChange={e => setLoginForm(f => ({ ...f, password: e.target.value }))} />
            </Field>
            <button type="submit" className="btn btn-primary" disabled={loading} style={{ width: "100%", justifyContent: "center", marginTop: "8px", padding: "13px" }}>
              {loading ? "Signing in..." : "Sign In →"}
            </button>
          </form>
        )}
        {mode === "register" && (
          <form onSubmit={handleRegister} className="fade-in">
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              <Field label="FIRST NAME"><input placeholder="John" value={regForm.first_name} onChange={e => setRegForm(f => ({ ...f, first_name: e.target.value }))} /></Field>
              <Field label="LAST NAME"><input placeholder="Doe" value={regForm.last_name} onChange={e => setRegForm(f => ({ ...f, last_name: e.target.value }))} /></Field>
            </div>
            <Field label="EMAIL"><input type="email" placeholder="you@example.com" value={regForm.email} onChange={e => setRegForm(f => ({ ...f, email: e.target.value }))} /></Field>
            <Field label="PHONE (optional)"><input placeholder="+1234567890" value={regForm.phone} onChange={e => setRegForm(f => ({ ...f, phone: e.target.value }))} /></Field>
            <Field label="PASSWORD">
              <input type="password" placeholder="Min 8 chars" value={regForm.password} onChange={e => setRegForm(f => ({ ...f, password: e.target.value }))} />
              {regForm.password && (
                <div style={{ marginTop: "6px" }}>
                  <div style={{ height: "4px", borderRadius: "99px", background: "var(--bg3)", overflow: "hidden" }}>
                    <div style={{ height: "100%", width: `${pwStrength * 25}%`, background: SC[pwStrength], borderRadius: "99px", transition: "all 0.3s" }} />
                  </div>
                  <p style={{ fontSize: "11px", color: SC[pwStrength], marginTop: "3px", fontWeight: "600" }}>{SL[pwStrength]}</p>
                </div>
              )}
            </Field>
            <Field label="CONFIRM PASSWORD">
              <input type="password" placeholder="Repeat password" value={regForm.confirm_password} onChange={e => setRegForm(f => ({ ...f, confirm_password: e.target.value }))} />
              {regForm.confirm_password && regForm.password !== regForm.confirm_password && (
                <p style={{ fontSize: "11px", color: "var(--danger)", marginTop: "3px" }}>Passwords do not match</p>
              )}
            </Field>
            <button type="submit" className="btn btn-primary" disabled={loading} style={{ width: "100%", justifyContent: "center", marginTop: "8px", padding: "13px" }}>
              {loading ? "Creating account..." : "Create Account →"}
            </button>
          </form>
        )}
        <p style={{ textAlign: "center", color: "var(--text3)", fontSize: "12px", marginTop: "20px" }}>
          {mode === "login" ? "Don't have an account? " : "Already have an account? "}
          <button onClick={() => setMode(mode === "login" ? "register" : "login")} style={{ background: "none", border: "none", color: "var(--primary-light)", cursor: "pointer", fontWeight: "700", fontSize: "12px" }}>
            {mode === "login" ? "Sign up" : "Sign in"}
          </button>
        </p>
      </div>
    </div>
  );
}