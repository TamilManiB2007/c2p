import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { User, Server, Info, Shield, Mail, Clock } from "lucide-react";
import api from "../services/api";

type SettingsTab = "profile" | "platform" | "about";

export const Settings: React.FC = () => {
  const [activeTab, setActiveTab] = useState<SettingsTab>("profile");

  const { data: profile, isLoading } = useQuery({
    queryKey: ["userProfile"],
    queryFn: async () => (await api.get("/users/me")).data,
  });

  const NAV = [
    { id: "profile" as SettingsTab, label: "My Profile", icon: <User size={14} /> },
    { id: "platform" as SettingsTab, label: "Platform Config", icon: <Server size={14} /> },
    { id: "about" as SettingsTab, label: "About C2P", icon: <Info size={14} /> },
  ];

  return (
    <div className="settings-layout">
      {/* Nav */}
      <div className="settings-nav">
        {NAV.map(n => (
          <button
            key={n.id}
            className={`settings-nav-item ${activeTab === n.id ? "active" : ""}`}
            onClick={() => setActiveTab(n.id)}
          >
            {n.icon}
            {n.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="settings-content">
        {/* Profile Tab */}
        {activeTab === "profile" && (
          <>
            <div className="settings-section">
              <div className="settings-section-title">Account Profile</div>
              <div className="settings-section-desc">Your identity and access information on the C2P platform.</div>

              {isLoading ? (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                  {[1,2,3,4].map(i => (
                    <div key={i} style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                      <div className="skeleton" style={{ width: "70px", height: "10px" }} />
                      <div className="skeleton" style={{ width: "100%", height: "36px", borderRadius: "6px" }} />
                    </div>
                  ))}
                </div>
              ) : (
                <div className="settings-field-grid">
                  <div className="form-group">
                    <label className="form-label">Full Name</label>
                    <input className="form-input" value={profile?.full_name || ""} readOnly style={{ backgroundColor: "var(--bg-app)", cursor: "default" }} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Email Address</label>
                    <div style={{ position: "relative" }}>
                      <input className="form-input" value={profile?.email || ""} readOnly style={{ backgroundColor: "var(--bg-app)", cursor: "default", paddingLeft: "32px" }} />
                      <Mail size={13} style={{ position: "absolute", left: "10px", top: "50%", transform: "translateY(-50%)", color: "var(--text-secondary)" }} />
                    </div>
                  </div>
                  <div className="form-group">
                    <label className="form-label">User ID</label>
                    <input className="form-input font-mono" value={`#${profile?.id || "—"}`} readOnly style={{ backgroundColor: "var(--bg-app)", cursor: "default" }} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Role</label>
                    <input className="form-input" value={profile?.role || "Compliance Officer"} readOnly style={{ backgroundColor: "var(--bg-app)", cursor: "default" }} />
                  </div>
                </div>
              )}
            </div>
            <div className="settings-section">
              <div className="settings-section-title">Security</div>
              <div className="settings-section-desc">Authentication is managed by the C2P API server using JWT tokens.</div>
              <div style={{ padding: "12px 16px", background: "var(--info-bg)", border: "1px solid rgba(47,107,255,0.2)", borderRadius: "6px", fontSize: "13px", color: "var(--info-text)", display: "flex", alignItems: "center", gap: "8px" }}>
                <Shield size={14} />
                Session is secured with a signed Bearer token. Tokens expire automatically after the configured TTL.
              </div>
            </div>
          </>
        )}

        {/* Platform Config Tab */}
        {activeTab === "platform" && (
          <div className="settings-section">
            <div className="settings-section-title">Platform Configuration</div>
            <div className="settings-section-desc">Runtime API and connection settings (read-only).</div>

            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {[
                { label: "API Base URL",        value: (import.meta as any).env?.VITE_API_URL || "http://127.0.0.1:8000", icon: <Server size={13} /> },
                { label: "API Version",          value: "v1", icon: <Info size={13} /> },
                { label: "Auth Strategy",        value: "JWT Bearer Token", icon: <Shield size={13} /> },
                { label: "Token Storage",        value: "localStorage (c2p_token)", icon: <Server size={13} /> },
                { label: "Request Timeout",      value: "30 seconds", icon: <Clock size={13} /> },
                { label: "Query Retry Policy",   value: "No retry on error", icon: <Info size={13} /> },
              ].map(item => (
                <div key={item.label} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 14px", background: "var(--bg-app)", borderRadius: "6px", border: "1px solid var(--border)" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", color: "var(--text-secondary)", fontWeight: 500 }}>
                    {item.icon} {item.label}
                  </div>
                  <span className="font-mono" style={{ fontSize: "12.5px", color: "var(--text-primary)", fontWeight: 600 }}>{item.value}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* About Tab */}
        {activeTab === "about" && (
          <div className="settings-section">
            <div style={{ display: "flex", alignItems: "flex-start", gap: "20px", marginBottom: "24px" }}>
              <div style={{ width: "56px", height: "56px", borderRadius: "12px", background: "var(--primary)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                <Shield size={28} color="#fff" />
              </div>
              <div>
                <div style={{ fontSize: "20px", fontWeight: 700, color: "var(--text-primary)", letterSpacing: "-0.3px" }}>C2P Compliance Platform</div>
                <div style={{ fontSize: "13px", color: "var(--text-secondary)", marginTop: "4px" }}>Contract-to-Payment Compliance Automation</div>
              </div>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {[
                { k: "Version",       v: "1.0.0" },
                { k: "Frontend",      v: "React 19 + TypeScript + Vite" },
                { k: "API Framework", v: "FastAPI (Python)" },
                { k: "Database",      v: "PostgreSQL + SQLAlchemy" },
                { k: "Auth",          v: "JWT Bearer (OAuth2PasswordBearer)" },
                { k: "UI Library",    v: "Lucide React + Recharts" },
                { k: "Query Layer",   v: "TanStack Query v5" },
              ].map(({ k, v }) => (
                <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "9px 14px", background: "var(--bg-app)", borderRadius: "6px", border: "1px solid var(--border)", fontSize: "13px" }}>
                  <span style={{ color: "var(--text-secondary)", fontWeight: 500 }}>{k}</span>
                  <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>{v}</span>
                </div>
              ))}
            </div>

            <div style={{ marginTop: "20px", padding: "14px", background: "var(--success-bg)", borderRadius: "6px", border: "1px solid rgba(18,183,106,0.2)", fontSize: "13px", color: "var(--success-text)" }}>
              🛡️ Designed for enterprise procurement and finance compliance workflows.
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
