import React, { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle, Eye, ShieldAlert, CheckCircle2, XCircle, X,
} from "lucide-react";
import api from "../services/api";
import { TableSkeleton } from "../components/Skeletons";

type Severity = "high" | "medium" | "low";

function getSeverity(det: any): Severity {
  let count = 0;
  if (det?.vendor_mismatch?.status === "failed")  count++;
  if (det?.contract_expired?.status === "failed") count++;
  if (det?.amount_exceeded?.status === "failed")  count++;
  if (count >= 3) return "high";
  if (count === 2) return "medium";
  return "low";
}

function getFailedRules(det: any): string[] {
  const r: string[] = [];
  if (det?.vendor_mismatch?.status === "failed")  r.push("Vendor Mismatch");
  if (det?.contract_expired?.status === "failed") r.push("Contract Expired");
  if (det?.amount_exceeded?.status === "failed")  r.push("Budget Exceeded");
  return r;
}

function formatDateTime(dt: string) {
  try { return new Date(dt).toLocaleString([], { month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit" }); }
  catch { return dt; }
}

export const Violations: React.FC = () => {
  const [detailOpen, setDetailOpen] = useState(false);
  const [selectedCheck, setSelectedCheck] = useState<any | null>(null);

  // Filter state
  const [vendorFilter, setVendorFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [severityFilter, setSeverityFilter] = useState("");

  const { data: violationsList, isLoading, isError } = useQuery({
    queryKey: ["violationsList"],
    queryFn: async () => (await api.get("/compliance/violations")).data,
  });

  // Derived vendor list for dropdown
  const vendorOptions = useMemo(() => {
    if (!violationsList) return [];
    const names = new Set<string>();
    violationsList.forEach((v: any) => {
      // We don't have vendor name directly; use contract_id as proxy label
      names.add(`Contract #${v.contract_id}`);
    });
    return Array.from(names);
  }, [violationsList]);

  // Apply filters
  const filtered = useMemo(() => {
    if (!violationsList) return [];
    return violationsList.filter((v: any) => {
      const det = v.details || {};
      const severity = getSeverity(det);
      const rules = getFailedRules(det);

      if (vendorFilter && !`Contract #${v.contract_id}`.includes(vendorFilter)) return false;
      if (typeFilter && !rules.some(r => r.toLowerCase().includes(typeFilter.toLowerCase()))) return false;
      if (severityFilter && severity !== severityFilter) return false;
      return true;
    });
  }, [violationsList, vendorFilter, typeFilter, severityFilter]);

  const hasFilters = vendorFilter || typeFilter || severityFilter;

  return (
    <div>
      <div className="table-section">
        {/* Toolbar */}
        <div className="table-toolbar">
          <div style={{ display: "flex", alignItems: "center", gap: "8px", flex: 1, flexWrap: "wrap" }}>
            <span className="table-title" style={{ color: "var(--error)" }}>
              <AlertTriangle size={15} />
              Violations Registry
            </span>
            {violationsList && (
              <span className="badge error" style={{ fontSize: "11px" }}>
                {filtered.length} violation{filtered.length !== 1 ? "s" : ""}
              </span>
            )}
          </div>
          <div className="violations-filters">
            <select
              className="filter-select"
              value={vendorFilter}
              onChange={e => setVendorFilter(e.target.value)}
            >
              <option value="">All Contracts</option>
              {vendorOptions.map(v => <option key={v} value={v.split("#")[1]}>{v}</option>)}
            </select>
            <select
              className="filter-select"
              value={typeFilter}
              onChange={e => setTypeFilter(e.target.value)}
            >
              <option value="">All Types</option>
              <option value="Vendor Mismatch">Vendor Mismatch</option>
              <option value="Contract Expired">Contract Expired</option>
              <option value="Budget Exceeded">Budget Exceeded</option>
            </select>
            <select
              className="filter-select"
              value={severityFilter}
              onChange={e => setSeverityFilter(e.target.value)}
            >
              <option value="">All Severities</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
            {hasFilters && (
              <button className="btn-ghost" style={{ fontSize: "12px" }} onClick={() => { setVendorFilter(""); setTypeFilter(""); setSeverityFilter(""); }}>
                <X size={12} /> Clear
              </button>
            )}
          </div>
        </div>

        {/* Table */}
        {isLoading ? (
          <TableSkeleton rows={5} cols={6} />
        ) : isError ? (
          <div className="error-state" style={{ margin: "24px" }}>
            <span>Failed to retrieve violation reports.</span>
          </div>
        ) : filtered.length === 0 ? (
          <div className="empty-state">
            {!violationsList?.length ? (
              <>
                <ShieldAlert size={36} style={{ color: "var(--success)" }} className="empty-state-icon" />
                <div className="empty-state-title" style={{ color: "var(--success-text)" }}>No violations found</div>
                <div className="empty-state-text">All compliance checks have passed successfully.</div>
              </>
            ) : (
              <>
                <ShieldAlert size={36} className="empty-state-icon" />
                <div className="empty-state-title">No matches</div>
                <div className="empty-state-text">Try clearing your filters to see all violations.</div>
              </>
            )}
          </div>
        ) : (
          <div className="enterprise-table-container">
            <table className="enterprise-table">
              <thead>
                <tr>
                  <th>Vendor / Contract</th>
                  <th>Invoice</th>
                  <th>Violations</th>
                  <th>Severity</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((check: any) => {
                  const det = check.details || {};
                  const severity = getSeverity(det);
                  const rules = getFailedRules(det);
                  return (
                    <tr key={check.id} onClick={() => { setSelectedCheck(check); setDetailOpen(true); }}>
                      <td>
                        <div style={{ fontWeight: 600 }}>Contract #{check.contract_id}</div>
                        <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>Audit #{check.id}</div>
                      </td>
                      <td>Invoice #{check.invoice_id}</td>
                      <td>
                        <div style={{ display: "flex", gap: "5px", flexWrap: "wrap" }}>
                          {rules.map((rule, i) => (
                            <span key={i} className="badge error" style={{ fontSize: "10.5px" }}>{rule}</span>
                          ))}
                        </div>
                      </td>
                      <td>
                        <span className={`badge severity-${severity}`}>
                          {severity.charAt(0).toUpperCase() + severity.slice(1)}
                        </span>
                      </td>
                      <td style={{ fontSize: "12px", color: "var(--text-secondary)" }}>{formatDateTime(check.created_at)}</td>
                      <td onClick={e => e.stopPropagation()}>
                        <button className="action-btn view" title="Inspect Failure" onClick={() => { setSelectedCheck(check); setDetailOpen(true); }}>
                          <Eye size={14} />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── DETAIL MODAL ── */}
      {detailOpen && selectedCheck && (
        <div className="modal-overlay">
          <div className="modal-card" style={{ width: "520px" }}>
            <div className="modal-header" style={{ borderBottomColor: "rgba(217,45,32,0.2)" }}>
              <span className="modal-title" style={{ color: "var(--error)" }}>
                <ShieldAlert size={16} />
                Violation Details — Audit #{selectedCheck.id}
              </span>
              <button className="modal-close" onClick={() => setDetailOpen(false)}><X size={15} /></button>
            </div>
            <div className="modal-body">
              {/* Summary row */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "12px", paddingBottom: "14px", borderBottom: "1px solid var(--border)" }}>
                <div>
                  <div style={{ fontSize: "11px", color: "var(--text-secondary)", fontWeight: 600, marginBottom: "3px" }}>CONTRACT</div>
                  <div style={{ fontSize: "13px", fontWeight: 700 }}>#{selectedCheck.contract_id}</div>
                </div>
                <div>
                  <div style={{ fontSize: "11px", color: "var(--text-secondary)", fontWeight: 600, marginBottom: "3px" }}>INVOICE</div>
                  <div style={{ fontSize: "13px", fontWeight: 700 }}>#{selectedCheck.invoice_id}</div>
                </div>
                <div>
                  <div style={{ fontSize: "11px", color: "var(--text-secondary)", fontWeight: 600, marginBottom: "3px" }}>SEVERITY</div>
                  <span className={`badge severity-${getSeverity(selectedCheck.details)}`} style={{ fontSize: "12px" }}>
                    {getSeverity(selectedCheck.details).charAt(0).toUpperCase() + getSeverity(selectedCheck.details).slice(1)}
                  </span>
                </div>
              </div>

              <div>
                <div style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.6px", color: "var(--text-secondary)", marginBottom: "10px" }}>
                  Rule Evaluation
                </div>
                <div className="rule-list">
                  {/* Rule 1 */}
                  <div className={`rule-item ${selectedCheck.details?.vendor_mismatch?.status === "passed" ? "passed" : "failed"}`}>
                    <div className="rule-header">
                      <span className="rule-name">Vendor Verification</span>
                      {selectedCheck.details?.vendor_mismatch?.status === "passed"
                        ? <CheckCircle2 size={15} style={{ color: "var(--success)" }} />
                        : <XCircle size={15} style={{ color: "var(--error)" }} />}
                    </div>
                    <span className="rule-detail">{selectedCheck.details?.vendor_mismatch?.detail}</span>
                  </div>
                  {/* Rule 2 */}
                  <div className={`rule-item ${selectedCheck.details?.contract_expired?.status === "passed" ? "passed" : "failed"}`}>
                    <div className="rule-header">
                      <span className="rule-name">Lifespan / Expiry Check</span>
                      {selectedCheck.details?.contract_expired?.status === "passed"
                        ? <CheckCircle2 size={15} style={{ color: "var(--success)" }} />
                        : <XCircle size={15} style={{ color: "var(--error)" }} />}
                    </div>
                    <span className="rule-detail">{selectedCheck.details?.contract_expired?.detail}</span>
                  </div>
                  {/* Rule 3 */}
                  <div className={`rule-item ${selectedCheck.details?.amount_exceeded?.status === "passed" ? "passed" : "failed"}`}>
                    <div className="rule-header">
                      <span className="rule-name">Budget / Limit Check</span>
                      {selectedCheck.details?.amount_exceeded?.status === "passed"
                        ? <CheckCircle2 size={15} style={{ color: "var(--success)" }} />
                        : <XCircle size={15} style={{ color: "var(--error)" }} />}
                    </div>
                    <span className="rule-detail">{selectedCheck.details?.amount_exceeded?.detail}</span>
                  </div>
                </div>
              </div>

              <div style={{ fontSize: "11.5px", color: "var(--text-secondary)" }}>
                Detected: {formatDateTime(selectedCheck.created_at)}
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn-primary" onClick={() => setDetailOpen(false)}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
