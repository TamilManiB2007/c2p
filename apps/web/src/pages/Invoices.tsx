import React, { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Upload, Download, Trash2, Search, Plus, X,
  Receipt, ChevronUp, ChevronDown, ChevronsUpDown,
} from "lucide-react";
import api from "../services/api";
import { useToast } from "../components/Toast";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { TableSkeleton, DrawerSkeleton } from "../components/Skeletons";
import { Drawer } from "../components/Drawer";

type SortField = "vendor_name" | "invoice_number" | "invoice_date" | "total_amount" | "status";
type SortDir = "asc" | "desc";

const SortIcon = ({ field, current, dir }: { field: string; current: string; dir: SortDir }) => {
  if (field !== current) return <ChevronsUpDown size={12} style={{ opacity: 0.4 }} />;
  return dir === "asc" ? <ChevronUp size={12} /> : <ChevronDown size={12} />;
};

function formatAmount(val: any) {
  if (!val && val !== 0) return "—";
  return `$${Number(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatDate(d: string | null | undefined) {
  if (!d) return "—";
  try { return new Date(d).toLocaleDateString([], { year: "numeric", month: "short", day: "numeric" }); }
  catch { return d; }
}

export const Invoices: React.FC = () => {
  const { showToast } = useToast();
  const queryClient = useQueryClient();

  // ── State ─────────────────────────────────────────────────────────────────
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [sortField, setSortField] = useState<SortField>("invoice_number");
  const [sortDir, setSortDir] = useState<SortDir>("asc");
  const [uploadOpen, setUploadOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [drawerInvoice, setDrawerInvoice] = useState<any | null>(null);

  // Upload Form
  const [invoiceNumber, setInvoiceNumber] = useState("");
  const [vendorName, setVendorName] = useState("");
  const [invoiceDate, setInvoiceDate] = useState("");
  const [totalAmount, setTotalAmount] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  // ── Query ──────────────────────────────────────────────────────────────────
  const { data, isLoading, isError } = useQuery({
    queryKey: ["invoicesList", page, pageSize, search, statusFilter],
    queryFn: async () => {
      const resp = await api.get("/invoices/", {
        params: { page, page_size: pageSize, search: search || undefined },
      });
      return resp.data;
    },
  });

  // ── Client-side sorting ────────────────────────────────────────────────────
  const sortedInvoices = useMemo(() => {
    if (!data?.invoices) return [];
    let rows = [...data.invoices];
    if (statusFilter) rows = rows.filter((i: any) => i.status === statusFilter);
    rows.sort((a: any, b: any) => {
      let av = a[sortField] ?? "";
      let bv = b[sortField] ?? "";
      if (sortField === "total_amount") {
        av = Number(av) || 0; bv = Number(bv) || 0;
      } else {
        av = String(av).toLowerCase(); bv = String(bv).toLowerCase();
      }
      if (av < bv) return sortDir === "asc" ? -1 : 1;
      if (av > bv) return sortDir === "asc" ? 1 : -1;
      return 0;
    });
    return rows;
  }, [data?.invoices, sortField, sortDir, statusFilter]);

  const toggleSort = (field: SortField) => {
    if (sortField === field) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortField(field); setSortDir("asc"); }
  };

  // ── Delete Mutation ────────────────────────────────────────────────────────
  const deleteMutation = useMutation({
    mutationFn: async (id: number) => (await api.delete(`/invoices/${id}`)).data,
    onSuccess: () => {
      showToast("Invoice deleted successfully.", "success");
      queryClient.invalidateQueries({ queryKey: ["invoicesList"] });
      queryClient.invalidateQueries({ queryKey: ["invoicesFull"] });
      queryClient.invalidateQueries({ queryKey: ["invoices", 1, 1] });
      queryClient.invalidateQueries({ queryKey: ["violationsList"] });
      setDeleteOpen(false); setSelectedId(null);
      if (drawerInvoice?.id === selectedId) setDrawerInvoice(null);
    },
    onError: (err: any) => {
      showToast(err.response?.data?.detail || "Failed to delete invoice.", "error");
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
      form.append("file", file); form.append("invoice_number", invoiceNumber);
      form.append("vendor_name", vendorName); form.append("invoice_date", invoiceDate);
      form.append("total_amount", totalAmount);
      await api.post("/invoices/upload", form, { headers: { "Content-Type": "multipart/form-data" } });
      showToast("Invoice uploaded successfully!", "success");
      queryClient.invalidateQueries({ queryKey: ["invoicesList"] });
      queryClient.invalidateQueries({ queryKey: ["invoicesFull"] });
      queryClient.invalidateQueries({ queryKey: ["invoices", 1, 1] });
      setInvoiceNumber(""); setVendorName(""); setInvoiceDate(""); setTotalAmount(""); setFile(null);
      setUploadOpen(false);
    } catch (err: any) {
      showToast(err.response?.data?.detail || "Failed to upload invoice.", "error");
    } finally {
      setUploading(false);
    }
  };

  const handleDownload = async (id: number) => {
    try {
      const resp = await api.get(`/invoices/${id}/download`, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([resp.data]));
      const a = document.createElement("a");
      a.href = url; a.setAttribute("download", `invoice_${id}.pdf`);
      document.body.appendChild(a); a.click(); a.remove();
      showToast("Download started", "success");
    } catch { showToast("Failed to download invoice PDF.", "error"); }
  };

  const exportCSV = () => {
    if (!sortedInvoices.length) { showToast("No data to export.", "warning"); return; }
    const headers = ["ID", "Invoice Number", "Vendor", "Date", "Amount", "Status", "Uploaded"];
    const rows = sortedInvoices.map((i: any) => [i.id, i.invoice_number, i.vendor_name, i.invoice_date, i.total_amount, i.status, i.created_at]);
    const csv = "data:text/csv;charset=utf-8," + [headers, ...rows].map(r => r.join(",")).join("\n");
    const a = document.createElement("a");
    a.setAttribute("href", encodeURI(csv)); a.setAttribute("download", "invoices_export.csv");
    document.body.appendChild(a); a.click(); a.remove();
  };

  return (
    <div>
      <div className="table-section">
        {/* Toolbar */}
        <div className="table-toolbar">
          <div className="toolbar-filters">
            <div style={{ position: "relative" }}>
              <input
                type="text" className="search-input"
                placeholder="Search vendor or invoice #…"
                value={search} onChange={e => { setSearch(e.target.value); setPage(1); }}
              />
              <Search size={14} style={{ position: "absolute", left: "10px", top: "50%", transform: "translateY(-50%)", color: "var(--text-secondary)", pointerEvents: "none" }} />
            </div>
            <select className="filter-select" value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1); }}>
              <option value="">All Statuses</option>
              <option value="passed">Passed</option>
              <option value="failed">Failed</option>
              <option value="pending">Pending</option>
            </select>
            <button className="btn-secondary" onClick={exportCSV}>Export CSV</button>
          </div>
          <div className="toolbar-actions">
            <button className="btn-primary" onClick={() => setUploadOpen(true)}>
              <Plus size={15} /><span>Upload Invoice</span>
            </button>
          </div>
        </div>

        {/* Table */}
        {isLoading ? (
          <TableSkeleton rows={6} cols={6} />
        ) : isError ? (
          <div className="error-state" style={{ margin: "24px" }}>
            <span>Failed to retrieve invoices. Check server connection.</span>
          </div>
        ) : sortedInvoices.length === 0 ? (
          <div className="empty-state">
            <Receipt size={36} className="empty-state-icon" />
            <div className="empty-state-title">No invoices found</div>
            <div className="empty-state-text">
              {search || statusFilter ? "Try adjusting your search or filters." : "Upload your first invoice to get started."}
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
                  <th className="sortable" onClick={() => toggleSort("invoice_number")}>
                    <span className="th-inner">Invoice # <SortIcon field="invoice_number" current={sortField} dir={sortDir} /></span>
                  </th>
                  <th className="sortable" onClick={() => toggleSort("total_amount")}>
                    <span className="th-inner">Amount <SortIcon field="total_amount" current={sortField} dir={sortDir} /></span>
                  </th>
                  <th className="sortable" onClick={() => toggleSort("invoice_date")}>
                    <span className="th-inner">Invoice Date <SortIcon field="invoice_date" current={sortField} dir={sortDir} /></span>
                  </th>
                  <th className="sortable" onClick={() => toggleSort("status")}>
                    <span className="th-inner">Status <SortIcon field="status" current={sortField} dir={sortDir} /></span>
                  </th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {sortedInvoices.map((i: any) => (
                  <tr key={i.id} onClick={() => setDrawerInvoice(i)}>
                    <td>
                      <div style={{ fontWeight: 600, fontSize: "13px" }}>{i.vendor_name}</div>
                      <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>ID #{i.id}</div>
                    </td>
                    <td><span className="font-mono">{i.invoice_number}</span></td>
                    <td style={{ fontWeight: 600 }}>{formatAmount(i.total_amount)}</td>
                    <td>{formatDate(i.invoice_date)}</td>
                    <td>
                      <span className={`badge ${i.status === "failed" ? "error" : i.status === "pending" ? "warning" : "success"}`}>
                        {i.status}
                      </span>
                    </td>
                    <td onClick={e => e.stopPropagation()}>
                      <div className="actions-cell">
                        <button className="action-btn view" title="View Details" onClick={() => setDrawerInvoice(i)}>
                          <Receipt size={14} />
                        </button>
                        <button className="action-btn" title="Download PDF" onClick={() => handleDownload(i.id)}>
                          <Download size={14} />
                        </button>
                        <button className="action-btn delete" title="Delete" onClick={() => { setSelectedId(i.id); setDeleteOpen(true); }}>
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {data && (
              <div className="table-pagination">
                <span className="pagination-info">
                  Page {data.page} of {data.total_pages || 1} — {data.total} invoices total
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
        isOpen={!!drawerInvoice}
        onClose={() => setDrawerInvoice(null)}
        title={drawerInvoice?.invoice_number ?? "Invoice Details"}
        subtitle={drawerInvoice?.vendor_name}
        footer={
          <div style={{ display: "flex", gap: "8px", width: "100%" }}>
            <button className="btn-secondary" style={{ flex: 1 }} onClick={() => drawerInvoice && handleDownload(drawerInvoice.id)}>
              <Download size={14} /> Download PDF
            </button>
            <button className="btn-danger" onClick={() => { setSelectedId(drawerInvoice?.id); setDeleteOpen(true); setDrawerInvoice(null); }}>
              <Trash2 size={14} /> Delete
            </button>
          </div>
        }
      >
        {drawerInvoice ? (
          <div>
            <div className="detail-section">
              <div className="detail-section-label">Invoice Information</div>
              <div className="detail-grid">
                <div className="detail-field">
                  <span className="detail-field-label">Vendor</span>
                  <span className="detail-field-value">{drawerInvoice.vendor_name}</span>
                </div>
                <div className="detail-field">
                  <span className="detail-field-label">Invoice Number</span>
                  <span className="detail-field-value font-mono">{drawerInvoice.invoice_number}</span>
                </div>
                <div className="detail-field">
                  <span className="detail-field-label">Total Amount</span>
                  <span className="detail-field-value" style={{ color: "var(--primary)", fontSize: "15px" }}>{formatAmount(drawerInvoice.total_amount)}</span>
                </div>
                <div className="detail-field">
                  <span className="detail-field-label">Invoice Date</span>
                  <span className="detail-field-value">{formatDate(drawerInvoice.invoice_date)}</span>
                </div>
                <div className="detail-field">
                  <span className="detail-field-label">Status</span>
                  <span>
                    <span className={`badge ${drawerInvoice.status === "failed" ? "error" : drawerInvoice.status === "pending" ? "warning" : "success"}`}>
                      {drawerInvoice.status}
                    </span>
                  </span>
                </div>
                <div className="detail-field">
                  <span className="detail-field-label">Uploaded</span>
                  <span className="detail-field-value">{formatDate(drawerInvoice.created_at)}</span>
                </div>
              </div>
            </div>
            <div className="detail-divider" />
            <div className="detail-section">
              <div className="detail-section-label">File Reference</div>
              <div style={{ padding: "12px 14px", background: "var(--bg-app)", borderRadius: "6px", border: "1px solid var(--border)", display: "flex", alignItems: "center", gap: "10px" }}>
                <Receipt size={20} style={{ color: "var(--primary)", flexShrink: 0 }} />
                <div>
                  <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-primary)" }}>invoice_{drawerInvoice.id}.pdf</div>
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
              <span className="modal-title"><Upload size={16} /> Upload Invoice</span>
              <button className="modal-close" onClick={() => setUploadOpen(false)}><X size={15} /></button>
            </div>
            <form onSubmit={handleUploadSubmit}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">Invoice Number <span style={{ color: "var(--error)" }}>*</span></label>
                  <input type="text" required className="form-input" value={invoiceNumber} onChange={e => setInvoiceNumber(e.target.value)} placeholder="e.g. INV-2026-001" />
                </div>
                <div className="form-group">
                  <label className="form-label">Vendor Name <span style={{ color: "var(--error)" }}>*</span></label>
                  <input type="text" required className="form-input" value={vendorName} onChange={e => setVendorName(e.target.value)} placeholder="e.g. Acme Corporation" />
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                  <div className="form-group">
                    <label className="form-label">Invoice Date <span style={{ color: "var(--error)" }}>*</span></label>
                    <input type="date" required className="form-input" value={invoiceDate} onChange={e => setInvoiceDate(e.target.value)} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Total Amount <span style={{ color: "var(--error)" }}>*</span></label>
                    <input type="number" step="0.01" min="0" required className="form-input" value={totalAmount} onChange={e => setTotalAmount(e.target.value)} placeholder="1500.00" />
                  </div>
                </div>
                <div className="form-group">
                  <label className="form-label">PDF Document <span style={{ color: "var(--error)" }}>*</span></label>
                  <div className="file-upload-area" onClick={() => document.getElementById("invoiceFile")?.click()}>
                    <Upload size={22} style={{ color: "var(--text-secondary)" }} />
                    <span className="file-upload-text">Click to select PDF (max 20 MB)</span>
                    {file && <span className="file-upload-name">{file.name}</span>}
                  </div>
                  <input id="invoiceFile" type="file" accept=".pdf,application/pdf" style={{ display: "none" }} onChange={e => setFile(e.target.files?.[0] ?? null)} />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn-secondary" onClick={() => setUploadOpen(false)} disabled={uploading}>Cancel</button>
                <button type="submit" className="btn-primary" disabled={uploading}>
                  {uploading ? "Uploading…" : "Upload Invoice"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── DELETE CONFIRM ── */}
      <ConfirmDialog
        isOpen={deleteOpen}
        title="Delete Invoice"
        message="Permanently delete this invoice? The file and associated compliance records will be removed."
        onConfirm={() => selectedId !== null && deleteMutation.mutate(selectedId)}
        onCancel={() => setDeleteOpen(false)}
        isLoading={deleteMutation.isPending}
      />
    </div>
  );
};
