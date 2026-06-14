import React, { useState } from "react";
import { Shield, Eye, EyeOff } from "lucide-react";
import api from "../services/api";
import { useToast } from "../components/Toast";

interface LoginProps {
  onLoginSuccess: (token: string, user: any) => void;
}

export const Login: React.FC<LoginProps> = ({ onLoginSuccess }) => {
  const { showToast } = useToast();
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPass, setShowPass] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      if (isRegister) {
        await api.post("/auth/register", { email, full_name: fullName, password });
        showToast("Account created! Signing you in…", "success");
      }
      const resp = await api.post("/auth/login", { email, password });
      const token = resp.data.access_token;
      const userProfile = await api.get("/users/me", { headers: { Authorization: `Bearer ${token}` } });
      onLoginSuccess(token, userProfile.data);
    } catch (err: any) {
      let msg = "Authentication failed. Please check your credentials.";
      const detail = err.response?.data?.detail;
      if (typeof detail === "string") msg = detail;
      else if (Array.isArray(detail)) msg = detail.map((e: any) => e.msg).join(", ");
      setError(msg);
      showToast(msg, "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div style={{ width: "420px" }}>
        {/* Header */}
        <div style={{ textAlign: "center", marginBottom: "28px" }}>
          <div style={{ width: "52px", height: "52px", borderRadius: "14px", background: "var(--primary)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 16px" }}>
            <Shield size={26} color="#fff" />
          </div>
          <div style={{ fontSize: "24px", fontWeight: 800, color: "var(--text-primary)", letterSpacing: "-0.5px", marginBottom: "6px" }}>
            C2P Compliance Platform
          </div>
          <div style={{ fontSize: "13.5px", color: "var(--text-secondary)" }}>
            {isRegister ? "Create your enterprise account" : "Sign in to your workspace"}
          </div>
        </div>

        <div className="login-card">
          {error && (
            <div style={{ padding: "10px 14px", background: "var(--error-bg)", color: "var(--error-text)", borderRadius: "6px", fontSize: "12.5px", marginBottom: "16px", border: "1px solid rgba(217,45,32,0.2)", display: "flex", alignItems: "flex-start", gap: "8px" }}>
              <span style={{ marginTop: "1px" }}>⚠</span>
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
            {isRegister && (
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Full Name</label>
                <input
                  type="text" required className="form-input"
                  value={fullName} onChange={e => setFullName(e.target.value)}
                  placeholder="Jane Doe" autoComplete="name"
                />
              </div>
            )}

            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">Work Email</label>
              <input
                type="email" required className="form-input"
                value={email} onChange={e => setEmail(e.target.value)}
                placeholder="jane.doe@company.com" autoComplete="email"
              />
            </div>

            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">Password</label>
              <div style={{ position: "relative" }}>
                <input
                  type={showPass ? "text" : "password"} required className="form-input"
                  value={password} onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••" autoComplete={isRegister ? "new-password" : "current-password"}
                  style={{ paddingRight: "38px" }}
                />
                <button
                  type="button" onClick={() => setShowPass(p => !p)}
                  style={{ position: "absolute", right: "10px", top: "50%", transform: "translateY(-50%)", color: "var(--text-secondary)" }}
                >
                  {showPass ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            <button
              type="submit" className="btn-primary"
              style={{ justifyContent: "center", padding: "10px 16px", marginTop: "4px" }}
              disabled={loading}
            >
              {loading ? "Authenticating…" : isRegister ? "Create Account" : "Sign In"}
            </button>
          </form>

          <div style={{ marginTop: "16px", textAlign: "center", fontSize: "13px", color: "var(--text-secondary)" }}>
            {isRegister ? "Already have an account? " : "New to the platform? "}
            <button
              type="button"
              style={{ color: "var(--primary)", fontWeight: 600 }}
              onClick={() => { setIsRegister(r => !r); setError(null); }}
            >
              {isRegister ? "Sign in" : "Create account"}
            </button>
          </div>
        </div>

        <div style={{ marginTop: "20px", textAlign: "center", fontSize: "11.5px", color: "var(--text-tertiary)" }}>
          Enterprise Procurement · Finance · Compliance Automation
        </div>
      </div>
    </div>
  );
};
