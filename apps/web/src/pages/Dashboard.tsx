import React from "react";
import { useQuery } from "@tanstack/react-query";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend, LineChart, Line, CartesianGrid,
} from "recharts";
import { FileText, Receipt, CheckCircle, AlertTriangle, TrendingUp, TrendingDown } from "lucide-react";
import api from "../services/api";
import { MetricSkeleton, ChartSkeleton, ActivitySkeleton } from "../components/Skeletons";

// ── Recharts custom tooltip ──────────────────────────────────────────────────
const EnterpriseTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div style={{
        background: "#fff",
        border: "1px solid #E5E7EB",
        borderRadius: "6px",
        padding: "8px 12px",
        fontSize: "12.5px",
        color: "#111827",
        boxShadow: "0 4px 6px rgba(0,0,0,0.06)",
      }}>
        {label && <div style={{ fontWeight: 600, marginBottom: "4px" }}>{label}</div>}
        {payload.map((p: any, i: number) => (
          <div key={i} style={{ color: p.color }}>{p.name}: <strong>{p.value}</strong></div>
        ))}
      </div>
    );
  }
  return null;
};

function formatTime(dateStr: string) {
  try {
    const d = new Date(dateStr);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) + " · " +
      d.toLocaleDateString([], { month: "short", day: "numeric" });
  } catch { return dateStr; }
}

function formatDate(dateStr: string) {
  try {
    return new Date(dateStr).toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" });
  } catch { return dateStr; }
}

export const Dashboard: React.FC = () => {
  // ── Metric totals ──────────────────────────────────────────────────────────
  const { data: contractsData, isLoading: l1, error: e1 } = useQuery({
    queryKey: ["contracts", 1, 1],
    queryFn: async () => (await api.get("/contracts/", { params: { page: 1, page_size: 1 } })).data,
  });

  const { data: invoicesData, isLoading: l2, error: e2 } = useQuery({
    queryKey: ["invoices", 1, 1],
    queryFn: async () => (await api.get("/invoices/", { params: { page: 1, page_size: 1 } })).data,
  });

  const { data: checksData, isLoading: l3, error: e3 } = useQuery({
    queryKey: ["complianceChecks", 1, 1],
    queryFn: async () => (await api.get("/compliance/checks", { params: { page: 1, page_size: 1 } })).data,
  });

  const { data: violationsData, isLoading: l4, error: e4 } = useQuery({
    queryKey: ["violationsList"],
    queryFn: async () => (await api.get("/compliance/violations")).data,
  });

  // ── Full data for charts ───────────────────────────────────────────────────
  const { data: fullContracts } = useQuery({
    queryKey: ["contractsFull"],
    queryFn: async () => (await api.get("/contracts/", { params: { page: 1, page_size: 100 } })).data.contracts,
  });

  const { data: fullInvoices } = useQuery({
    queryKey: ["invoicesFull"],
    queryFn: async () => (await api.get("/invoices/", { params: { page: 1, page_size: 100 } })).data.invoices,
  });

  const { data: fullChecks } = useQuery({
    queryKey: ["checksFull"],
    queryFn: async () => (await api.get("/compliance/checks", { params: { page: 1, page_size: 100 } })).data.checks,
  });

  const isMetricsLoading = l1 || l2 || l3 || l4;
  const hasError = e1 || e2 || e3 || e4;

  if (hasError) {
    return (
      <div className="error-state" style={{ marginTop: "40px" }}>
        <AlertTriangle size={32} />
        <div>
          <div style={{ fontWeight: 700, marginBottom: "6px" }}>Cannot reach compliance server</div>
          <div style={{ fontSize: "13px" }}>Verify the API server is running on port 8000.</div>
        </div>
      </div>
    );
  }

  const totalContracts = contractsData?.total ?? 0;
  const totalInvoices  = invoicesData?.total  ?? 0;
  const totalChecks    = checksData?.total    ?? 0;
  const totalViolations = violationsData?.length ?? 0;

  // ── Chart Data ─────────────────────────────────────────────────────────────

  // Vendor breakdown bar chart
  const vendorChartData = React.useMemo(() => {
    if (!fullContracts?.length) return [];
    const counts: Record<string, number> = {};
    fullContracts.forEach((c: any) => {
      const v = c.vendor_name || "Unknown";
      counts[v] = (counts[v] || 0) + 1;
    });
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 8)
      .map(([name, value]) => ({ name: name.length > 14 ? name.slice(0, 14) + "…" : name, value }));
  }, [fullContracts]);

  // Compliance status pie
  const statusChartData = React.useMemo(() => {
    if (!fullChecks?.length) return [];
    let passed = 0, failed = 0;
    fullChecks.forEach((c: any) => {
      if (c.status === "passed") passed++;
      else failed++;
    });
    return [
      { name: "Passed", value: passed },
      { name: "Failed", value: failed },
    ].filter((d) => d.value > 0);
  }, [fullChecks]);

  // Compliance trend line (checks per day)
  const trendData = React.useMemo(() => {
    if (!fullChecks?.length) return [];
    const byDay: Record<string, { passed: number; failed: number }> = {};
    fullChecks.forEach((c: any) => {
      const day = c.created_at?.slice(0, 10) ?? "unknown";
      if (!byDay[day]) byDay[day] = { passed: 0, failed: 0 };
      if (c.status === "passed") byDay[day].passed++;
      else byDay[day].failed++;
    });
    return Object.entries(byDay)
      .sort((a, b) => a[0].localeCompare(b[0]))
      .slice(-14)
      .map(([date, v]) => ({
        date: new Date(date).toLocaleDateString([], { month: "short", day: "numeric" }),
        Passed: v.passed,
        Failed: v.failed,
      }));
  }, [fullChecks]);

  // Recent activity items (last 5 checks)
  const recentChecks = React.useMemo(() =>
    (fullChecks ?? []).slice(0, 5), [fullChecks]);

  // Latest uploads (last 5 contracts + 5 invoices merged, sorted by date)
  const recentUploads = React.useMemo(() => {
    const contracts = (fullContracts ?? []).map((c: any) => ({
      type: "contract",
      label: `Contract ${c.contract_number}`,
      sub: c.vendor_name,
      date: c.created_at,
    }));
    const invoices = (fullInvoices ?? []).map((i: any) => ({
      type: "invoice",
      label: `Invoice ${i.invoice_number}`,
      sub: i.vendor_name,
      date: i.created_at,
    }));
    return [...contracts, ...invoices]
      .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
      .slice(0, 5);
  }, [fullContracts, fullInvoices]);

  // Recent violations
  const recentViolations = React.useMemo(() =>
    (violationsData ?? []).slice(0, 5), [violationsData]);

  const PIE_COLORS = ["#12B76A", "#D92D20"];

  return (
    <div>
      {/* ── Row 1: KPI Cards ── */}
      <div className="metrics-grid">
        {isMetricsLoading ? (
          <><MetricSkeleton /><MetricSkeleton /><MetricSkeleton /><MetricSkeleton /></>
        ) : (
          <>
            <div className="metric-card contracts">
              <div className="metric-icon-wrapper">
                <FileText size={18} />
              </div>
              <div className="metric-info">
                <span className="metric-label">Total Contracts</span>
                <span className="metric-value">{totalContracts.toLocaleString()}</span>
                <span className="metric-trend up"><TrendingUp size={11} /> Active this period</span>
              </div>
            </div>

            <div className="metric-card invoices">
              <div className="metric-icon-wrapper">
                <Receipt size={18} />
              </div>
              <div className="metric-info">
                <span className="metric-label">Total Invoices</span>
                <span className="metric-value">{totalInvoices.toLocaleString()}</span>
                <span className="metric-trend up"><TrendingUp size={11} /> Submitted</span>
              </div>
            </div>

            <div className="metric-card compliance">
              <div className="metric-icon-wrapper">
                <CheckCircle size={18} />
              </div>
              <div className="metric-info">
                <span className="metric-label">Compliance Checks</span>
                <span className="metric-value">{totalChecks.toLocaleString()}</span>
                <span className="metric-trend up"><TrendingUp size={11} /> Audit runs</span>
              </div>
            </div>

            <div className="metric-card violations">
              <div className="metric-icon-wrapper">
                <AlertTriangle size={18} />
              </div>
              <div className="metric-info">
                <span className="metric-label">Violations</span>
                <span className="metric-value">{totalViolations.toLocaleString()}</span>
                {totalViolations > 0
                  ? <span className="metric-trend down"><TrendingDown size={11} /> Requires attention</span>
                  : <span className="metric-trend up"><TrendingUp size={11} /> All clear</span>
                }
              </div>
            </div>
          </>
        )}
      </div>

      {/* ── Row 2: Charts ── */}
      <div className="charts-grid-3">
        {/* Compliance trend line */}
        {isMetricsLoading ? <ChartSkeleton /> : (
          <div className="chart-card" style={{ gridColumn: "span 1" }}>
            <div className="chart-header">
              <div>
                <div className="chart-title">Compliance Trend</div>
                <div className="chart-subtitle">Passed vs Failed checks by day</div>
              </div>
            </div>
            {trendData.length === 0 ? (
              <div className="empty-state" style={{ padding: "32px" }}>
                <div className="empty-state-text">Run compliance checks to see trend data</div>
              </div>
            ) : (
              <div className="chart-container">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trendData} margin={{ left: -10, right: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
                    <XAxis dataKey="date" fontSize={11} tick={{ fill: "#6B7280" }} />
                    <YAxis allowDecimals={false} fontSize={11} tick={{ fill: "#6B7280" }} />
                    <Tooltip content={<EnterpriseTooltip />} />
                    <Legend iconSize={10} iconType="circle" wrapperStyle={{ fontSize: "11px" }} />
                    <Line type="monotone" dataKey="Passed" stroke="#12B76A" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="Failed" stroke="#D92D20" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        )}

        {/* Violation distribution pie */}
        {isMetricsLoading ? <ChartSkeleton /> : (
          <div className="chart-card">
            <div className="chart-header">
              <div>
                <div className="chart-title">Check Results</div>
                <div className="chart-subtitle">Pass/fail ratio</div>
              </div>
            </div>
            {statusChartData.length === 0 ? (
              <div className="empty-state" style={{ padding: "32px" }}>
                <div className="empty-state-text">No check results yet</div>
              </div>
            ) : (
              <div className="chart-container">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={statusChartData}
                      cx="50%" cy="45%"
                      innerRadius={55} outerRadius={80}
                      paddingAngle={4} dataKey="value"
                    >
                      {statusChartData.map((_, i) => (
                        <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip content={<EnterpriseTooltip />} />
                    <Legend iconSize={9} iconType="circle" wrapperStyle={{ fontSize: "11px" }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        )}

        {/* Vendor breakdown bar */}
        {isMetricsLoading ? <ChartSkeleton /> : (
          <div className="chart-card">
            <div className="chart-header">
              <div>
                <div className="chart-title">Vendor Breakdown</div>
                <div className="chart-subtitle">Contracts by vendor</div>
              </div>
            </div>
            {vendorChartData.length === 0 ? (
              <div className="empty-state" style={{ padding: "32px" }}>
                <div className="empty-state-text">No vendor data</div>
              </div>
            ) : (
              <div className="chart-container">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={vendorChartData} layout="vertical" margin={{ left: 0, right: 10 }}>
                    <XAxis type="number" allowDecimals={false} fontSize={11} tick={{ fill: "#6B7280" }} />
                    <YAxis type="category" dataKey="name" fontSize={10} tick={{ fill: "#6B7280" }} width={80} />
                    <Tooltip content={<EnterpriseTooltip />} />
                    <Bar dataKey="value" name="Contracts" fill="#2F6BFF" radius={[0, 3, 3, 0]} maxBarSize={18} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Row 3: Activity Feeds ── */}
      <div className="activity-grid">
        {/* Recent Activity */}
        {isMetricsLoading ? <ActivitySkeleton /> : (
          <div className="activity-card">
            <div className="activity-header">
              <div className="activity-title">
                <CheckCircle size={14} style={{ color: "var(--success)" }} />
                Recent Activity
              </div>
              <span className="activity-count">{recentChecks.length}</span>
            </div>
            <div className="activity-list">
              {recentChecks.length === 0 ? (
                <div className="activity-empty">No recent checks</div>
              ) : recentChecks.map((c: any) => (
                <div key={c.id} className="activity-item">
                  <div className={`activity-dot ${c.status === "passed" ? "success" : "error"}`} />
                  <div className="activity-content">
                    <div className="activity-text">
                      Check #{c.id} — Contract #{c.contract_id} / Invoice #{c.invoice_id}
                    </div>
                    <div className="activity-meta">
                      {c.status === "passed" ? "✓ Passed" : "✗ Failed"} · {formatTime(c.created_at)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Latest Uploads */}
        {isMetricsLoading ? <ActivitySkeleton /> : (
          <div className="activity-card">
            <div className="activity-header">
              <div className="activity-title">
                <FileText size={14} style={{ color: "var(--primary)" }} />
                Latest Uploads
              </div>
              <span className="activity-count">{recentUploads.length}</span>
            </div>
            <div className="activity-list">
              {recentUploads.length === 0 ? (
                <div className="activity-empty">No documents uploaded yet</div>
              ) : recentUploads.map((u, i) => (
                <div key={i} className="activity-item">
                  <div className={`activity-dot ${u.type === "contract" ? "info" : "warning"}`} />
                  <div className="activity-content">
                    <div className="activity-text">{u.label}</div>
                    <div className="activity-meta">
                      {u.sub} · {formatDate(u.date)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recent Violations */}
        {isMetricsLoading ? <ActivitySkeleton /> : (
          <div className="activity-card">
            <div className="activity-header">
              <div className="activity-title">
                <AlertTriangle size={14} style={{ color: "var(--error)" }} />
                Recent Violations
              </div>
              <span className="activity-count" style={{ background: recentViolations.length > 0 ? "var(--error-bg)" : undefined, color: recentViolations.length > 0 ? "var(--error-text)" : undefined }}>
                {recentViolations.length}
              </span>
            </div>
            <div className="activity-list">
              {recentViolations.length === 0 ? (
                <div className="activity-empty" style={{ color: "var(--success-text)" }}>
                  🎉 No violations — all checks passed!
                </div>
              ) : recentViolations.map((v: any) => {
                const det = v.details || {};
                const rules: string[] = [];
                if (det.vendor_mismatch?.status === "failed") rules.push("Vendor Mismatch");
                if (det.contract_expired?.status === "failed") rules.push("Expired");
                if (det.amount_exceeded?.status === "failed") rules.push("Budget Exceeded");
                return (
                  <div key={v.id} className="activity-item">
                    <div className="activity-dot error" />
                    <div className="activity-content">
                      <div className="activity-text">
                        Contract #{v.contract_id} · Invoice #{v.invoice_id}
                      </div>
                      <div className="activity-meta">
                        {rules.join(" · ")} · {formatTime(v.created_at)}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
