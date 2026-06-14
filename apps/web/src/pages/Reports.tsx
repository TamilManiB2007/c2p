import React from "react";
import { useQuery } from "@tanstack/react-query";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from "recharts";
import { FileText, Receipt, Shield, ShieldAlert, Download, BarChart3 } from "lucide-react";
import api from "../services/api";
import { ChartSkeleton, MetricSkeleton } from "../components/Skeletons";

const EnterpriseTooltip = ({ active, payload, label }: any) => {
  if (active && payload?.length) {
    return (
      <div style={{ background: "#fff", border: "1px solid #E5E7EB", borderRadius: "6px", padding: "8px 12px", fontSize: "12px", boxShadow: "0 4px 6px rgba(0,0,0,0.06)" }}>
        {label && <div style={{ fontWeight: 600, marginBottom: "4px" }}>{label}</div>}
        {payload.map((p: any, i: number) => (
          <div key={i} style={{ color: p.color }}>{p.name}: <strong>{p.value}</strong></div>
        ))}
      </div>
    );
  }
  return null;
};

function exportAllCSV(label: string, headers: string[], rows: any[][]) {
  const csv = "data:text/csv;charset=utf-8," + [headers, ...rows].map(r => r.join(",")).join("\n");
  const a = document.createElement("a");
  a.setAttribute("href", encodeURI(csv));
  a.setAttribute("download", `${label}_report.csv`);
  document.body.appendChild(a); a.click(); a.remove();
}

export const Reports: React.FC = () => {
  const { data: contractsData, isLoading: l1 } = useQuery({
    queryKey: ["contractsFull"],
    queryFn: async () => (await api.get("/contracts/", { params: { page: 1, page_size: 100 } })).data,
  });

  const { data: invoicesData, isLoading: l2 } = useQuery({
    queryKey: ["invoicesFull"],
    queryFn: async () => (await api.get("/invoices/", { params: { page: 1, page_size: 100 } })).data,
  });

  const { data: checksData, isLoading: l3 } = useQuery({
    queryKey: ["checksFull"],
    queryFn: async () => (await api.get("/compliance/checks", { params: { page: 1, page_size: 100 } })).data,
  });

  const { data: violationsData, isLoading: l4 } = useQuery({
    queryKey: ["violationsList"],
    queryFn: async () => (await api.get("/compliance/violations")).data,
  });

  const isLoading = l1 || l2 || l3 || l4;

  const contracts  = contractsData?.contracts ?? [];
  const invoices   = invoicesData?.invoices   ?? [];
  const checks     = checksData?.checks       ?? [];
  const violations = violationsData           ?? [];

  const totalContractValue = contracts.reduce((sum: number, c: any) => sum + Number(c.contract_amount || 0), 0);
  const totalInvoiceValue  = invoices.reduce((sum: number, i: any) => sum + Number(i.total_amount || 0), 0);
  const passedChecks = checks.filter((c: any) => c.status === "passed").length;
  const complianceRate = checks.length ? Math.round((passedChecks / checks.length) * 100) : 0;

  // Vendor contracts chart
  const vendorData = React.useMemo(() => {
    const counts: Record<string, number> = {};
    contracts.forEach((c: any) => { const v = c.vendor_name || "Unknown"; counts[v] = (counts[v] || 0) + 1; });
    return Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 10).map(([name, value]) => ({ name: name.length > 14 ? name.slice(0, 14) + "…" : name, Contracts: value }));
  }, [contracts]);

  // Compliance rate pie
  const compliancePie = React.useMemo(() => {
    const p = checks.filter((c: any) => c.status === "passed").length;
    const f = checks.filter((c: any) => c.status !== "passed").length;
    return [{ name: "Passed", value: p }, { name: "Failed", value: f }].filter(d => d.value > 0);
  }, [checks]);

  // Violation breakdown
  const violationBreakdown = React.useMemo(() => {
    let vm = 0, ce = 0, ae = 0;
    violations.forEach((v: any) => {
      if (v.details?.vendor_mismatch?.status === "failed")  vm++;
      if (v.details?.contract_expired?.status === "failed") ce++;
      if (v.details?.amount_exceeded?.status === "failed")  ae++;
    });
    return [
      { name: "Vendor Mismatch", value: vm },
      { name: "Expired Contract", value: ce },
      { name: "Budget Exceeded", value: ae },
    ].filter(d => d.value > 0);
  }, [violations]);

  return (
    <div>
      {/* KPIs */}
      <div className="reports-grid">
        {isLoading ? <><MetricSkeleton /><MetricSkeleton /><MetricSkeleton /></> : (
          <>
            <div className="report-stat-card">
              <div className="report-stat-label"><FileText size={13} /> Total Contract Value</div>
              <div className="report-stat-value">${totalContractValue.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</div>
              <div className="report-stat-sub">{contracts.length} contracts on record</div>
            </div>
            <div className="report-stat-card">
              <div className="report-stat-label"><Receipt size={13} /> Total Invoice Value</div>
              <div className="report-stat-value">${totalInvoiceValue.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</div>
              <div className="report-stat-sub">{invoices.length} invoices submitted</div>
            </div>
            <div className="report-stat-card">
              <div className="report-stat-label"><Shield size={13} /> Compliance Rate</div>
              <div className="report-stat-value" style={{ color: complianceRate >= 80 ? "var(--success-text)" : complianceRate >= 50 ? "var(--warning-text)" : "var(--error-text)" }}>
                {complianceRate}%
              </div>
              <div className="report-stat-sub">{passedChecks} of {checks.length} checks passed · {violations.length} violations</div>
            </div>
          </>
        )}
      </div>

      {/* Charts row */}
      <div className="charts-grid" style={{ marginBottom: "20px" }}>
        {isLoading ? <ChartSkeleton /> : (
          <div className="chart-card">
            <div className="chart-header">
              <div>
                <div className="chart-title">Contracts by Vendor</div>
                <div className="chart-subtitle">Top 10 vendors by contract count</div>
              </div>
              <button className="btn-secondary" style={{ fontSize: "12px", padding: "5px 10px" }}
                onClick={() => exportAllCSV("contracts", ["ID", "Number", "Vendor", "Amount", "Status", "End Date"], contracts.map((c: any) => [c.id, c.contract_number, c.vendor_name, c.contract_amount || "N/A", c.status, c.end_date || "N/A"]))}>
                <Download size={12} /> Export
              </button>
            </div>
            {vendorData.length === 0 ? (
              <div className="empty-state" style={{ padding: "32px" }}><div className="empty-state-text">No contract data yet</div></div>
            ) : (
              <div className="chart-container">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={vendorData} margin={{ left: -10, right: 10 }}>
                    <XAxis dataKey="name" fontSize={11} tick={{ fill: "#6B7280" }} />
                    <YAxis allowDecimals={false} fontSize={11} tick={{ fill: "#6B7280" }} />
                    <Tooltip content={<EnterpriseTooltip />} />
                    <Bar dataKey="Contracts" fill="#2F6BFF" radius={[3, 3, 0, 0]} maxBarSize={40} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        )}

        {isLoading ? <ChartSkeleton /> : (
          <div className="chart-card">
            <div className="chart-header">
              <div>
                <div className="chart-title">Compliance Distribution</div>
                <div className="chart-subtitle">Pass vs fail across all checks</div>
              </div>
            </div>
            {compliancePie.length === 0 ? (
              <div className="empty-state" style={{ padding: "32px" }}><div className="empty-state-text">No check data yet</div></div>
            ) : (
              <div className="chart-container">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={compliancePie} cx="50%" cy="45%" innerRadius={55} outerRadius={80} paddingAngle={4} dataKey="value">
                      {compliancePie.map((_, i) => <Cell key={i} fill={i === 0 ? "#12B76A" : "#D92D20"} />)}
                    </Pie>
                    <Tooltip content={<EnterpriseTooltip />} />
                    <Legend iconSize={9} iconType="circle" wrapperStyle={{ fontSize: "11px" }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Violation breakdown */}
      {!isLoading && violationBreakdown.length > 0 && (
        <div className="chart-card" style={{ marginBottom: "20px" }}>
          <div className="chart-header">
            <div>
              <div className="chart-title">Violation Breakdown by Rule</div>
              <div className="chart-subtitle">Which rules are triggered most frequently</div>
            </div>
            <button className="btn-secondary" style={{ fontSize: "12px", padding: "5px 10px" }}
              onClick={() => exportAllCSV("violations", ["Audit ID", "Contract ID", "Invoice ID", "Status", "Date"], violations.map((v: any) => [v.id, v.contract_id, v.invoice_id, v.status, v.created_at]))}>
              <Download size={12} /> Export
            </button>
          </div>
          <div className="chart-container" style={{ height: "200px" }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={violationBreakdown} layout="vertical" margin={{ left: 0, right: 20 }}>
                <XAxis type="number" allowDecimals={false} fontSize={11} tick={{ fill: "#6B7280" }} />
                <YAxis type="category" dataKey="name" fontSize={11} tick={{ fill: "#6B7280" }} width={120} />
                <Tooltip content={<EnterpriseTooltip />} />
                <Bar dataKey="value" name="Violations" fill="#D92D20" radius={[0, 3, 3, 0]} maxBarSize={22} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Quick export row */}
      <div className="chart-card">
        <div className="chart-header" style={{ marginBottom: 0 }}>
          <div className="chart-title" style={{ display: "flex", alignItems: "center", gap: "7px" }}>
            <BarChart3 size={15} style={{ color: "var(--primary)" }} /> Quick Export
          </div>
        </div>
        <div style={{ padding: "16px 20px", display: "flex", gap: "10px", flexWrap: "wrap" }}>
          <button className="btn-secondary" onClick={() => exportAllCSV("contracts", ["ID", "Number", "Vendor", "Amount", "Status", "End Date"], contracts.map((c: any) => [c.id, c.contract_number, c.vendor_name, c.contract_amount || "", c.status, c.end_date || ""]))}>
            <Download size={13} /> Contracts CSV
          </button>
          <button className="btn-secondary" onClick={() => exportAllCSV("invoices", ["ID", "Invoice Number", "Vendor", "Amount", "Date", "Status"], invoices.map((i: any) => [i.id, i.invoice_number, i.vendor_name, i.total_amount, i.invoice_date, i.status]))}>
            <Download size={13} /> Invoices CSV
          </button>
          <button className="btn-secondary" onClick={() => exportAllCSV("violations", ["Audit ID", "Contract ID", "Invoice ID", "Status", "Date"], violations.map((v: any) => [v.id, v.contract_id, v.invoice_id, v.status, v.created_at]))}>
            <ShieldAlert size={13} style={{ color: "var(--error)" }} /> Violations CSV
          </button>
        </div>
      </div>
    </div>
  );
};
