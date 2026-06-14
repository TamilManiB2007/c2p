import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Play, Eye, X, ShieldCheck, CheckCircle2, XCircle,
  AlertTriangle, Shield, Clock,
} from "lucide-react";
import api from "../services/api";
import { useToast } from "../components/Toast";
import { TableSkeleton } from "../components/Skeletons";

function formatDateTime(dt: string) {
  try { return new Date(dt).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }); }
  catch { return dt; }
}

const RuleRow: React.FC<{
  name: string;
  rule: { status?: string; detail?: string } | undefined;
}> = ({ name, rule }) => {
  const status = rule?.status;
  const isPassed = status === "passed";
  const isFailed = status === "failed";
  return (
    <div className={`rule-item ${isPassed ? "passed" : isFailed ? "failed" : ""}`}>
      <div className="rule-header">
        <span className="rule-name">{name}</span>
        {isPassed && <CheckCircle2 size={15} style={{ color: "var(--success)", flexShrink: 0 }} />}
        {isFailed && <XCircle size={15} style={{ color: "var(--error)", flexShrink: 0 }} />}
        {!status && <AlertTriangle size={15} style={{ color: "var(--warning)", flexShrink: 0 }} />}
      </div>
      <span className="rule-detail">{rule?.detail ?? "Not evaluated"}</span>
    </div>
  );
};

export const Compliance: React.FC = () => {
  const { showToast } = useToast();
  const queryClient = useQueryClient();

  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [runOpen, setRunOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [selectedCheck, setSelectedCheck] = useState<any | null>(null);
  const [lastResult, setLastResult] = useState<any | null>(null);
  const [selectedContractId, setSelectedContractId] = useState("");
  const [selectedInvoiceId, setSelectedInvoiceId] = useState("");

  // ── Data Queries ───────────────────────────────────────────────────────────
  const { data: contractsData } = useQuery({
    queryKey: ["contractsDropdown"],
    queryFn: async () => (await api.get("/contracts/", { params: { page: 1, page_size: 100 } })).data.contracts,
  });

  const { data: invoicesData } = useQuery({
    queryKey: ["invoicesDropdown"],
    queryFn: async () => (await api.get("/invoices/", { params: { page: 1, page_size: 100 } })).data.invoices,
  });

  const { data, isLoading, isError } = useQuery({
    queryKey: ["complianceChecksList", page, pageSize],
    queryFn: async () => (await api.get("/compliance/checks", { params: { page, page_size: pageSize } })).data,
  });

  // ── Run Check Mutation ─────────────────────────────────────────────────────
  const runMutation = useMutation({
    mutationFn: async (body: { contract_id: number; invoice_id: number }) =>
      (await api.post("/compliance/run", body)).data,
    onSuccess: (newCheck) => {
      setLastResult(newCheck);
      showToast(
        `Check completed — ${newCheck.status === "passed" ? "✓ Passed" : "✗ Failed"}`,
        newCheck.status === "passed" ? "success" : "error",
      );
      queryClient.invalidateQueries({ queryKey: ["complianceChecksList"] });
      queryClient.invalidateQueries({ queryKey: ["complianceChecks"] });
      queryClient.invalidateQueries({ queryKey: ["checksFull"] });
      queryClient.invalidateQueries({ queryKey: ["violationsList"] });
    },
    onError: (err: any) => {
      showToast(err.response?.data?.detail || "Failed to execute compliance check.", "error");
    },
  });

  const handleRunSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedContractId || !selectedInvoiceId) {
      showToast("Please select both a contract and an invoice.", "warning");
      return;
    }
    runMutation.mutate({
      contract_id: Number(selectedContractId),
      invoice_id: Number(selectedInvoiceId),
    });
  };

  const selectedContract = contractsData?.find((c: any) => String(c.id) === selectedContractId);
  const selectedInvoice  = invoicesData?.find((i: any) => String(i.id) === selectedInvoiceId);

  return (
    <div className="compliance-layout">
      {/* ── LEFT: Run Panel ── */}
      <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
        <div className="compliance-panel">
          <div className="compliance-panel-header">
            <Shield size={15} style={{ color: "var(--primary)" }} />
            <span className="compliance-panel-title">Run Compliance Check</span>
          </div>
          <div className="compliance-panel-body">
            <form onSubmit={handleRunSubmit} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div className="form-group">
                <label className="form-label">Select Contract <span style={{ color: "var(--error)" }}>*</span></label>
                <select
                  className="form-input"
                  value={selectedContractId}
                  onChange={e => setSelectedContractId(e.target.value)}
                  required
                >
                  <option value="">— Choose contract —</option>
                  {contractsData?.map((c: any) => (
                    <option key={c.id} value={c.id}>
                      {c.contract_number} · {c.vendor_name}
                    </option>
                  ))}
                </select>
                {selectedContract && (
                  <div style={{ fontSize: "11.5px", color: "var(--text-secondary)", marginTop: "4px" }}>
                    Amount: ${Number(selectedContract.contract_amount || 0).toLocaleString()} · Ends: {selectedContract.end_date || "N/A"}
                  </div>
                )}
              </div>

              <div className="form-group">
                <label className="form-label">Select Invoice <span style={{ color: "var(--error)" }}>*</span></label>
                <select
                  className="form-input"
                  value={selectedInvoiceId}
                  onChange={e => setSelectedInvoiceId(e.target.value)}
                  required
                >
                  <option value="">— Choose invoice —</option>
                  {invoicesData?.map((i: any) => (
                    <option key={i.id} value={i.id}>
                      {i.invoice_number} · {i.vendor_name} · ${Number(i.total_amount).toLocaleString()}
                    </option>
                  ))}
                </select>
                {selectedInvoice && (
                  <div style={{ fontSize: "11.5px", color: "var(--text-secondary)", marginTop: "4px" }}>
                    Date: {selectedInvoice.invoice_date} · Amount: ${Number(selectedInvoice.total_amount).toLocaleString()}
                  </div>
                )}
              </div>

              <div style={{ padding: "10px 12px", background: "var(--bg-app)", borderRadius: "6px", border: "1px solid var(--border)", fontSize: "12px", color: "var(--text-secondary)", lineHeight: 1.6 }}>
                <strong style={{ color: "var(--text-primary)" }}>Audit Rules Applied:</strong>
                <ul style={{ marginLeft: "16px", marginTop: "4px", display: "flex", flexDirection: "column", gap: "2px" }}>
                  <li>Vendor name match (case-insensitive)</li>
                  <li>Invoice date within contract lifespan</li>
                  <li>Invoice amount within contract limit</li>
                </ul>
              </div>

              <button
                type="submit"
                className="btn-primary"
                style={{ justifyContent: "center", padding: "10px" }}
                disabled={runMutation.isPending}
              >
                {runMutation.isPending ? (
                  <><Clock size={15} style={{ animation: "spin 1s linear infinite" }} /> Evaluating…</>
                ) : (
                  <><Play size={15} /> Execute Check</>
                )}
              </button>
            </form>
          </div>
        </div>

        {/* ── Last Result Panel ── */}
        {lastResult && (
          <div className="compliance-panel">
            <div className="compliance-panel-header">
              <ShieldCheck size={15} style={{ color: lastResult.status === "passed" ? "var(--success)" : "var(--error)" }} />
              <span className="compliance-panel-title">Last Check Result</span>
            </div>
            <div className="compliance-panel-body">
              <div className={`result-banner ${lastResult.status === "passed" ? "passed" : "failed"}`}>
                {lastResult.status === "passed"
                  ? <CheckCircle2 size={16} />
                  : <XCircle size={16} />
                }
                <span>
                  Check #{lastResult.id} — {lastResult.status === "passed" ? "All rules passed" : "Violations detected"}
                </span>
              </div>
              <div className="rule-list" style={{ marginTop: "4px" }}>
                <RuleRow name="Vendor Verification"   rule={lastResult.details?.vendor_mismatch} />
                <RuleRow name="Contract Expiry Check" rule={lastResult.details?.contract_expired} />
                <RuleRow name="Budget Limit Check"    rule={lastResult.details?.amount_exceeded} />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── RIGHT: History Table ── */}
      <div>
        <div className="table-section">
          <div className="table-toolbar">
            <span className="table-title">
              <Shield size={15} style={{ color: "var(--primary)" }} />
              Compliance History
            </span>
            <button className="btn-primary" onClick={() => setRunOpen(true)}>
              <Play size={14} /><span>Run Check</span>
            </button>
          </div>

          {isLoading ? (
            <TableSkeleton rows={6} cols={6} />
          ) : isError ? (
            <div className="error-state" style={{ margin: "24px" }}>
              <span>Failed to retrieve compliance records.</span>
            </div>
          ) : !data?.checks?.length ? (
            <div className="empty-state">
              <Shield size={36} className="empty-state-icon" />
              <div className="empty-state-title">No checks yet</div>
              <div className="empty-state-text">Select a contract and invoice in the left panel to run your first verification.</div>
            </div>
          ) : (
            <div className="enterprise-table-container">
              <table className="enterprise-table">
                <thead>
                  <tr>
                    <th>Check ID</th>
                    <th>Contract</th>
                    <th>Invoice</th>
                    <th>Method</th>
                    <th>Result</th>
                    <th>Date</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {data.checks.map((check: any) => (
                    <tr key={check.id} onClick={() => { setSelectedCheck(check); setDetailOpen(true); }}>
                      <td style={{ fontWeight: 700, color: "var(--primary)" }}>#{check.id}</td>
                      <td>Contract #{check.contract_id}</td>
                      <td>Invoice #{check.invoice_id}</td>
                      <td><span className="font-mono" style={{ background: "var(--bg-app)", padding: "2px 6px", borderRadius: "4px", border: "1px solid var(--border)" }}>{check.check_type}</span></td>
                      <td>
                        <span className={`badge ${check.status === "passed" ? "success" : "error"}`}>
                          {check.status === "passed" ? "Passed" : "Failed"}
                        </span>
                      </td>
                      <td style={{ color: "var(--text-secondary)", fontSize: "12px" }}>{formatDateTime(check.created_at)}</td>
                      <td onClick={e => e.stopPropagation()}>
                        <button className="action-btn view" title="View Details" onClick={() => { setSelectedCheck(check); setDetailOpen(true); }}>
                          <Eye size={14} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="table-pagination">
                <span className="pagination-info">Page {data.page} of {data.total_pages || 1} — {data.total} runs</span>
                <div className="pagination-controls">
                  <button className="page-btn" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>Previous</button>
                  <button className="page-btn" onClick={() => setPage(p => p + 1)} disabled={page >= data.total_pages}>Next</button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Quick-run modal (from header button) ── */}
      {runOpen && (
        <div className="modal-overlay">
          <div className="modal-card" style={{ width: "500px" }}>
            <div className="modal-header">
              <span className="modal-title"><Shield size={15} /> Trigger Compliance Check</span>
              <button className="modal-close" onClick={() => setRunOpen(false)}><X size={15} /></button>
            </div>
            <form onSubmit={(e) => { handleRunSubmit(e); if (!runMutation.isPending) setRunOpen(false); }}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">Contract</label>
                  <select className="form-input" value={selectedContractId} onChange={e => setSelectedContractId(e.target.value)} required>
                    <option value="">— Choose contract —</option>
                    {contractsData?.map((c: any) => (
                      <option key={c.id} value={c.id}>#{c.id} — {c.contract_number} ({c.vendor_name})</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Invoice</label>
                  <select className="form-input" value={selectedInvoiceId} onChange={e => setSelectedInvoiceId(e.target.value)} required>
                    <option value="">— Choose invoice —</option>
                    {invoicesData?.map((i: any) => (
                      <option key={i.id} value={i.id}>#{i.id} — {i.invoice_number} ({i.vendor_name})</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn-secondary" onClick={() => setRunOpen(false)} disabled={runMutation.isPending}>Cancel</button>
                <button type="submit" className="btn-primary" disabled={runMutation.isPending}>
                  {runMutation.isPending ? "Evaluating…" : "Execute Check"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Detail Modal ── */}
      {detailOpen && selectedCheck && (
        <div className="modal-overlay">
          <div className="modal-card" style={{ width: "520px" }}>
            <div className="modal-header">
              <span className="modal-title">
                <ShieldCheck size={15} style={{ color: selectedCheck.status === "passed" ? "var(--success)" : "var(--error)" }} />
                Audit Check #{selectedCheck.id}
              </span>
              <button className="modal-close" onClick={() => setDetailOpen(false)}><X size={15} /></button>
            </div>
            <div className="modal-body">
              <div className={`result-banner ${selectedCheck.status === "passed" ? "passed" : "failed"}`}>
                {selectedCheck.status === "passed" ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
                <span>Contract #{selectedCheck.contract_id} · Invoice #{selectedCheck.invoice_id} — <strong>{selectedCheck.status === "passed" ? "All rules passed" : "Violations detected"}</strong></span>
              </div>
              <div className="rule-list">
                <RuleRow name="Vendor Verification"   rule={selectedCheck.details?.vendor_mismatch} />
                <RuleRow name="Contract Expiry Check" rule={selectedCheck.details?.contract_expired} />
                <RuleRow name="Budget Limit Check"    rule={selectedCheck.details?.amount_exceeded} />
              </div>
              <div style={{ fontSize: "11.5px", color: "var(--text-secondary)", textAlign: "right" }}>
                Executed: {formatDateTime(selectedCheck.created_at)}
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
