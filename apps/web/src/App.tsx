import { useState, useEffect } from "react";
import {
  LayoutDashboard,
  FileText,
  Receipt,
  ShieldAlert,
  Shield,
  LogOut,
  Building2,
  Bell,
  Settings,
  BarChart3,
  ChevronRight,
} from "lucide-react";
import "./App.css";

// Page Imports
import { Login } from "./pages/Login";
import { Dashboard } from "./pages/Dashboard";
import { Contracts } from "./pages/Contracts";
import { Invoices } from "./pages/Invoices";
import { Compliance } from "./pages/Compliance";
import { Violations } from "./pages/Violations";
import { Reports } from "./pages/Reports";
import { Settings as SettingsPage } from "./pages/Settings";

type ActiveTab =
  | "dashboard"
  | "contracts"
  | "invoices"
  | "compliance"
  | "violations"
  | "reports"
  | "settings";

const NAV_ITEMS: {
  id: ActiveTab;
  label: string;
  icon: React.ReactNode;
  section: "procurement" | "compliance" | "system";
}[] = [
  { id: "dashboard",   label: "Dashboard",         icon: <LayoutDashboard size={16} />, section: "procurement" },
  { id: "contracts",   label: "Contracts",          icon: <FileText size={16} />,        section: "procurement" },
  { id: "invoices",    label: "Invoices",            icon: <Receipt size={16} />,         section: "procurement" },
  { id: "compliance",  label: "Compliance Checks",  icon: <Shield size={16} />,          section: "compliance"  },
  { id: "violations",  label: "Violations",          icon: <ShieldAlert size={16} />,     section: "compliance"  },
  { id: "reports",     label: "Reports",             icon: <BarChart3 size={16} />,       section: "system"      },
  { id: "settings",    label: "Settings",            icon: <Settings size={16} />,        section: "system"      },
];

const PAGE_META: Record<ActiveTab, { title: string; crumb: string }> = {
  dashboard:   { title: "Executive Dashboard",       crumb: "Overview" },
  contracts:   { title: "Contracts",                 crumb: "Procurement · Contracts" },
  invoices:    { title: "Invoices",                  crumb: "Procurement · Invoices" },
  compliance:  { title: "Compliance Checks",         crumb: "Compliance · Verification" },
  violations:  { title: "Violations",                crumb: "Compliance · Violations" },
  reports:     { title: "Reports & Analytics",       crumb: "System · Reports" },
  settings:    { title: "Settings",                  crumb: "System · Settings" },
};

function getInitials(name: string) {
  return name
    .split(" ")
    .map((p) => p[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem("c2p_token"));
  const [user, setUser] = useState<any | null>(null);
  const [activeTab, setActiveTab] = useState<ActiveTab>("dashboard");

  useEffect(() => {
    const storedUser = localStorage.getItem("c2p_user");
    if (storedUser) {
      try { setUser(JSON.parse(storedUser)); } catch { localStorage.removeItem("c2p_user"); }
    }
  }, [token]);

  const handleLoginSuccess = (newToken: string, loggedInUser: any) => {
    localStorage.setItem("c2p_token", newToken);
    localStorage.setItem("c2p_user", JSON.stringify(loggedInUser));
    setToken(newToken);
    setUser(loggedInUser);
    setActiveTab("dashboard");
  };

  const handleLogout = () => {
    localStorage.removeItem("c2p_token");
    localStorage.removeItem("c2p_user");
    setToken(null);
    setUser(null);
  };

  if (!token) {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }

  const renderContent = () => {
    switch (activeTab) {
      case "dashboard":  return <Dashboard />;
      case "contracts":  return <Contracts />;
      case "invoices":   return <Invoices />;
      case "compliance": return <Compliance />;
      case "violations": return <Violations />;
      case "reports":    return <Reports />;
      case "settings":   return <SettingsPage />;
      default:           return <Dashboard />;
    }
  };

  const meta = PAGE_META[activeTab];
  const sections: Array<"procurement" | "compliance" | "system"> = ["procurement", "compliance", "system"];
  const sectionLabels: Record<string, string> = {
    procurement: "Procurement",
    compliance:  "Compliance",
    system:      "System",
  };

  return (
    <div className="app-container">
      {/* ── SIDEBAR ── */}
      <aside className="sidebar">
        {/* Brand */}
        <div className="sidebar-brand">
          <div className="sidebar-brand-icon">
            <Building2 size={18} color="#fff" />
          </div>
          <div className="sidebar-brand-text">
            <span className="sidebar-brand-name">C2P Platform</span>
            <span className="sidebar-brand-sub">Contract to Payment</span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="sidebar-nav">
          {sections.map((section) => {
            const items = NAV_ITEMS.filter((n) => n.section === section);
            return (
              <div key={section} className="sidebar-section">
                <div className="sidebar-section-label">{sectionLabels[section]}</div>
                <ul className="sidebar-menu">
                  {items.map((item) => (
                    <li key={item.id}>
                      <button
                        onClick={() => setActiveTab(item.id)}
                        className={`sidebar-item ${activeTab === item.id ? "active" : ""}`}
                      >
                        <span className="sidebar-item-icon">{item.icon}</span>
                        <span>{item.label}</span>
                      </button>
                    </li>
                  ))}
                </ul>
                <div className="sidebar-divider" />
              </div>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="sidebar-footer">
          {user && (
            <div className="user-card">
              <div className="user-avatar">{getInitials(user.full_name || "U")}</div>
              <div className="user-info">
                <div className="user-name">{user.full_name}</div>
                <div className="user-role">{user.email}</div>
              </div>
            </div>
          )}
          <button onClick={handleLogout} className="btn-logout">
            <LogOut size={13} />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* ── MAIN CONTENT ── */}
      <main className="main-content">
        {/* Header */}
        <header className="header">
          <div className="header-left">
            <div className="page-breadcrumb">
              <span>C2P</span>
              <ChevronRight size={12} />
              {meta.crumb.split(" · ").map((part, i, arr) => (
                <span key={i} style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                  {part}
                  {i < arr.length - 1 && <ChevronRight size={12} />}
                </span>
              ))}
            </div>
            <h1 className="page-title">{meta.title}</h1>
          </div>

          <div className="header-right">
            <button className="header-icon-btn" title="Notifications">
              <Bell size={17} />
            </button>
            <button className="header-icon-btn" title="Settings" onClick={() => setActiveTab("settings")}>
              <Settings size={17} />
            </button>
            {user && (
              <div className="header-user-chip" onClick={() => setActiveTab("settings")} title="Account">
                <div className="header-avatar">{getInitials(user.full_name || "U")}</div>
                <span className="header-user-name">{user.full_name?.split(" ")[0]}</span>
              </div>
            )}
          </div>
        </header>

        {/* Page Content */}
        <div className="content-body">{renderContent()}</div>
      </main>
    </div>
  );
}

export default App;
