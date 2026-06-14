import React, { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Upload, Download, Trash2, Search, Plus, X,
  ChevronUp, ChevronDown, FileText, ChevronsUpDown,
} from "lucide-react";
import api from "../services/api";
import { useToast } from "../components/Toast";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { TableSkeleton, DrawerSkeleton } from "../components/Skeletons";
import { Drawer } from "../components/Drawer";

type SortField = "vendor_name" | "contract_number" | "end_date" | "contract_amount" | "status";
type SortDir = "asc" | "desc";

const SortIcon = ({ field, current, dir }: { field: string; current: string; dir: SortDir }) => {
  if (field !== current) return <ChevronsUpDown size={12} style={{ opacity: 0.4 }} />;
  return dir === "asc" ? <ChevronUp size={12} /> : <ChevronDown size={12} />;
};

function formatAmount(val: any) {
  if (!val) return "—";
  return `$${Number(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatDate(d: string | null | undefined) {
  if (!d) return "—";
  try { return new Date(d).toLocaleDateString([], { year: "numeric", month: "short", day: "numeric" }); }
  catch { return d; }
}

export const Contracts: React.FC = () => {
  const { showToast } = useToast();
  const queryClient = useQueryClient();

  // ── State ─────────────────────────────────────────────────────────────────
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [sortField, setSortField] = useState<SortField>("contract_number");
  const [sortDir, setSortDir] = useState<SortDir>("asc");
  const [uploadOpen, setUploadOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [drawerContract, setDrawerContract] = useState<any | null>(null);

  // Upload Form
  const [vendorName, setVendorName] = useState("");
  const [contractNumber, setContractNumber] = useState("");
  const [endDate, setEndDate] = useState("");
  const [contractAmount, setContractAmount] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  // ── Query ──────────────────────────────────────────────────────────────────
  const { data, isLoading, isError } = useQuery({
    queryKey: ["contractsList", page, pageSize, search, statusFilter],
    queryFn: async () => {
      const resp = await api.get("/contracts/", {
        params: { page, page_size: pageSize, search: search || undefined },
      });
      return resp.data;
    },
  });

  // ── Client-side sorting ────────────────────────────────────────────────────
  const sortedContracts = useMemo(() => {
    if (!data?.contracts) return [];
    let rows = [...data.contracts];
    if (statusFilter) rows = rows.filter((c: any) => c.status === statusFilter);
    rows.sort((a: any, b: any) => {
      let av = a[sortField] ?? "";
      let bv = b[sortField] ?? "";
      if (sortField === "contract_amount") {
        av = Number(av) || 0;
        bv = Number(bv) || 0;
      } else {
        av = String(av).toLowerCase();
        bv = String(bv).toLowerCase();
      }
      if (av < bv) return sortDir === "asc" ? -1 : 1;
      if (av > bv) return sortDir === "asc" ? 1 : -1;
      return 0;
    });
    return rows;
  }, [data?.contracts, sortField, sortDir, statusFilter]);

  const toggleSort = (field: SortField) => {
    if (sortField === field) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortField(field); setSortDir("asc"); }
  };

  // ── Delete Mutation ────────────────────────────────────────────────────────
  const deleteMutation = useMutation({
    mutationFn: async (id: number) => (await api.delete(`/contracts/${id}`)).data,
    onSuccess: () => {
      showToast("Contract deleted successfully.", "success");
      queryClient.invalidateQueries({ queryKey: ["contractsList"] });
      queryClient.invalidateQueries({ queryKey: ["contractsFull"] });
      queryClient.invalidateQueries({ queryKey: ["contracts", 1, 1] });
      setDeleteOpen(false);
      setSelectedId(null);
      if (drawerContract?.id === selectedId) setDrawerContract(null);
    },
    onError: (err: any) => {
      showToast(err.response?.data?.detail || "Failed to delete contract.", "error");
      setDeleteOpen(false);
    },
  });

  // ── Upload ─────────────────────────────────────────────────────────────────
  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) { showToast("Please select a PDF file.", "warning"); return; }
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("vendor_name", vendorName);
      form.append("contract_number", contractNumber);
      if (endDate) form.append("end_date", endDate);
      if (contractAmount) form.append("contract_amount", contractAmount);
      await api.post("/contracts/upload", form, { headers: { "Content-Type": "multipart/form-data" } });
      showToast("Contract uploaded successfully!", "success");
      queryClient.invalidateQueries({ queryKey: ["contractsList"] });
      queryClient.invalidateQueries({ queryKey: ["contractsFull"] });
      queryClient.invalidateQueries({ queryKey: ["contracts", 1, 1] });
      setVendorName(""); setContractNumber(""); setEndDate(""); setContractAmount(""); setFile(null);
      setUploadOpen(false);
    } catch (err: any) {
      showToast(err.response?.data?.detail || "Failed to upload contract.", "error");
    } finally {
      setUploading(false);
    }
  };

  const handleDownload = async (id: number) => {
    try {
      const resp = await api.get(`/contracts/${id}/download`, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([resp.data]));
      const a = document.createElement("a");
      a.href = url; a.setAttribute("download", `contract_${id}.pdf`);
      document.body.appendChild(a); a.click(); a.remove();
      showToast("Download started", "success");
    } catch { showToast("Failed to download contract PDF.", "error"); }
  };

  const exportCSV = () => {
    if (!sortedContracts.length) { showToast("No data to export.", "warning"); return; }
    const headers = ["ID", "Contract Number", "Vendor", "End Date", "Amount", "Status", "Uploaded"];
    const rows = sortedContracts.map((c: any) => [c.id, c.contract_number, c.vendor_name, c.end_date || "N/A", c.contract_amount || "N/A", c.status, c.created_at]);
    const csv = "data:text/csv;charset=utf-8," + [headers, ...rows].map(r => r.join(",")).join("\n");
    const a = document.createElement("a");
    a.setAttribute("href", encodeURI(csv));
    a.setAttribute("download", "contracts_export.csv");
    document.body.appendChild(a); a.click(); a.remove();
  };

  const openDrawer = (c: any) => setDrawerContract(c);

  return (
    <div>
      <div className="table-section">
        {/* Toolbar */}
        <div className="table-toolbar">
          <div className="toolbar-filters">
            <div style={{ position: "relative" }}>
              <input
                type="text" className="search-input"
                placeholder="Search vendor or number…"
                value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              />
              <Search size={14} style={{ position: "absolute", left: "10px", top: "50%", transform: "translateY(-50%)", color: "var(--text-secondary)", pointerEvents: "none" }} />
            </div>
            <select className="filter-select" value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1); }}>
              <option value="">All Statuses</option>
              <option value="active">Active</option>
              <option value="passed">Passed</option>
              <option value="failed">Failed</option>
            </select>
            <button className="btn-secondary" onClick={exportCSV}>
              Export CSV
            </button>
          </div>
          <div className="toolbar-actions">
            <button className="btn-primary" onClick={() => setUploadOpen(true)}>
              <Plus size={15} />
              <span>Upload Contract</span>
            </button>
          </div>
        </div>

        {/* Table */}
        {isLoading ? (
          <TableSkeleton rows={6} cols={6} />
        ) : isError ? (
          <div className="error-state" style={{ margin: "24px" }}>
            <span>Failed to retrieve contracts. Check server connection.</span>
          </div>
        ) : sortedContracts.length === 0 ? (
          <div className="empty-state">
            <FileText size={36} className="empty-state-icon" />
            <div className="empty-state-title">No contracts found</div>
            <div className="empty-state-text">
              {search || statusFilter ? "Try adjusting your search or filters." : "Upload your first contract to get started."}
            </div>
          </div>
        ) : (
          <div className="enterprise-table-container">
            <table className="enterprise-table">
              <thead>
                <tr>
                  <th className="sortable" onClick={() => toggleSort("vendor_name")}>
                    <span className="th-inner">Vendor <SortIcon field="vendor_name" current={sortField} dir={sortDir} /></span>
                  </th>
                  <th className="sortable" onClick={() => toggleSort("contract_number")}>
                    <span className="th-inner">Contract # <SortIcon field="contract_number" current={sortField} dir={sortDir} /></span>
                  </th>
                  <th className="sortable" onClick={() => toggleSort("contract_amount")}>
                    <span className="th-inner">Amount <SortIcon field="contract_amount" current={sortField} dir={sortDir} /></span>
                  </th>
                  <th className="sortable" onClick={() => toggleSort("end_date")}>
                    <span className="th-inner">End Date <SortIcon field="end_date" current={sortField} dir={sortDir} /></span>
                  </th>
                  <th className="sortable" onClick={() => toggleSort("status")}>
                    <span className="th-inner">Status <SortIcon field="status" current={sortField} dir={sortDir} /></span>
                  </th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {sortedContracts.map((c: any) => (
                  <tr key={c.id} onClick={() => openDrawer(c)}>
                    <td>
                      <div style={{ fontWeight: 600, fontSize: "13px" }}>{c.vendor_name}</div>
                      <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>ID #{c.id}</div>
                    </td>
                    <td><span className="font-mono">{c.contract_number}</span></td>
                    <td style={{ fontWeight: 600 }}>{formatAmount(c.contract_amount)}</td>
                    <td>{formatDate(c.end_date)}</td>
                    <td>
                      <span className={`badge ${c.status === "failed" ? "error" : c.status === "active" ? "info" : "success"}`}>
                        {c.status}
                      </span>
                    </td>
                    <td onClick={e => e.stopPropagation()}>
                      <div className="actions-cell">
                        <button className="action-btn view" title="View Details" onClick={() => openDrawer(c)}>
                          <FileText size={14} />
                        </button>
                        <button className="action-btn" title="Download PDF" onClick={() => handleDownload(c.id)}>
                          <Download size={14} />
                        </button>
                        <button className="action-btn delete" title="Delete" onClick={() => { setSelectedId(c.id); setDeleteOpen(true); }}>
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Pagination */}
            {data && (
              <div className="table-pagination">
                <span className="pagination-info">
                  Page {data.page} of {data.total_pages || 1} — {data.total} contracts total
                </span>
                <div className="pagination-controls">
                  <button className="page-btn" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>Previous</button>
                  <button className="page-btn" onClick={() => setPage(p => p + 1)} disabled={page >= data.total_pages}>Next</button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── DETAIL DRAWER ── */}
      <Drawer
        isOpen={!!drawerContract}
        onClose={() => setDrawerContract(null)}
        title={drawerContract?.contract_number ?? "Contract Details"}
        subtitle={drawerContract?.vendor_name}
        footer={
          <div style={{ display: "flex", gap: "8px", width: "100%" }}>
            <button className="btn-secondary" style={{ flex: 1 }} onClick={() => drawerContract && handleDownload(drawerContract.id)}>
              <Download size={14} /> Download PDF
            </button>
            <button className="btn-danger" onClick={() => { setSelectedId(drawerContract?.id); setDeleteOpen(true); setDrawerContract(null); }}>
              <Trash2 size={14} /> Delete
            </button>
          </div>
        }
      >
        {drawerContract ? (
          <div>
            <div className="detail-section">
              <div className="detail-section-label">Contract Information</div>
              <div className="detail-grid">
                <div className="detail-field">
                  <span className="detail-field-label">Vendor</span>
                  <span className="detail-field-value">{drawerContract.vendor_name}</span>
                </div>
                <div className="detail-field">
                  <span className="detail-field-label">Contract Number</span>
                  <span className="detail-field-value font-mono">{drawerContract.contract_number}</span>
                </div>
                <div className="detail-field">
                  <span className="detail-field-label">Amount</span>
                  <span className="detail-field-value" style={{ color: "var(--primary)" }}>{formatAmount(drawerContract.contract_amount)}</span>
                </div>
                <div className="detail-field">
                  <span className="detail-field-label">End Date</span>
                  <span className="detail-field-value">{formatDate(drawerContract.end_date)}</span>
                </div>
                <div className="detail-field">
                  <span className="detail-field-label">Status</span>
                  <span>
                    <span className={`badge ${drawerContract.status === "failed" ? "error" : drawerContract.status === "active" ? "info" : "success"}`}>
                      {drawerContract.status}
                    </span>
                  </span>
                </div>
                <div className="detail-field">
                  <span className="detail-field-label">Uploaded</span>
                  <span className="detail-field-value">{formatDate(drawerContract.created_at)}</span>
                </div>
              </div>
            </div>

            <div className="detail-divider" />

            <div className="detail-section">
              <div className="detail-section-label">File Reference</div>
              <div style={{ padding: "12px 14px", background: "var(--bg-app)", borderRadius: "6px", border: "1px solid var(--border)", display: "flex", alignItems: "center", gap: "10px" }}>
                <FileText size={20} style={{ color: "var(--primary)", flexShrink: 0 }} />
                <div>
                  <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-primary)" }}>contract_{drawerContract.id}.pdf</div>
                  <div style={{ fontSize: "11.5px", color: "var(--text-secondary)" }}>Stored on server · Click Download to retrieve</div>
                </div>
              </div>
            </div>
          </div>
        ) : <DrawerSkeleton />}
      </Drawer>

      {/* ── UPLOAD MODAL ── */}
      {uploadOpen && (
        <div className="modal-overlay">
          <div className="modal-card" style={{ width: "500px" }}>
            <div className="modal-header">
              <span className="modal-title"><Upload size={16} /> Upload Contract</span>
              <button className="modal-close" onClick={() => setUploadOpen(false)}><X size={15} /></button>
            </div>
            <form onSubmit={handleUploadSubmit}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">Vendor Name <span style={{ color: "var(--error)" }}>*</span></label>
                  <input type="text" required className="form-input" value={vendorName} onChange={e => setVendorName(e.target.value)} placeholder="e.g. Acme Corporation" />
                </div>
                <div className="form-group">
                  <label className="form-label">Contract Number <span style={{ color: "var(--error)" }}>*</span></label>
                  <input type="text" required className="form-input" value={contractNumber} onChange={e => setContractNumber(e.target.value)} placeholder="e.g. CTR-2026-001" />
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                  <div className="form-group">
                    <label className="form-label">End Date <span className="form-label-optional">(optional)</span></label>
                    <input type="date" className="form-input" value={endDate} onChange={e => setEndDate(e.target.value)} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Contract Amount <span className="form-label-optional">(optional)</span></label>
                    <input type="number" step="0.01" min="0" className="form-input" value={contractAmount} onChange={e => setContractAmount(e.target.value)} placeholder="50000.00" />
                  </div>
                </div>
                <div className="form-group">
                  <label className="form-label">PDF Document <span style={{ color: "var(--error)" }}>*</span></label>
                  <div className="file-upload-area" onClick={() => document.getElementById("contractFile")?.click()}>
                    <Upload size={22} style={{ color: "var(--text-secondary)" }} />
                    <span className="file-upload-text">Click to select PDF (max 20 MB)</span>
                    {file && <span className="file-upload-name">{file.name}</span>}
                  </div>
                  <input id="contractFile" type="file" accept=".pdf,application/pdf" style={{ display: "none" }} onChange={e => setFile(e.target.files?.[0] ?? null)} />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn-secondary" onClick={() => setUploadOpen(false)} disabled={uploading}>Cancel</button>
                <button type="submit" className="btn-primary" disabled={uploading}>
                  {uploading ? "Uploading…" : "Upload Contract"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── DELETE CONFIRM ── */}
      <ConfirmDialog
        isOpen={deleteOpen}
        title="Delete Contract"
        message="Permanently delete this contract? The file and all associated compliance records will be removed."
        onConfirm={() => selectedId !== null && deleteMutation.mutate(selectedId)}
        onCancel={() => setDeleteOpen(false)}
        isLoading={deleteMutation.isPending}
      />
    </div>
  );
};
