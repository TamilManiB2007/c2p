import React, { useState, useEffect } from "react";
import { X, Check, RotateCcw, AlertTriangle, Shield, Calendar, DollarSign, FileText } from "lucide-react";
import api from "../services/api";

export interface ExtractionResult {
  fields: Record<string, any>;
  confidence: Record<string, number>;
  warnings: string[];
  raw_text: string;
  doc_type: string;
  temp_file_id: string;
}

interface DocumentReviewDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  docType: "contract" | "invoice";
  extractionResult: ExtractionResult | null;
  onConfirm: (fields: Record<string, any>) => Promise<void>;
  onRetry: () => void;
}

export const DocumentReviewDrawer: React.FC<DocumentReviewDrawerProps> = ({
  isOpen,
  onClose,
  docType,
  extractionResult,
  onConfirm,
  onRetry,
}) => {
  const [formFields, setFormFields] = useState<Record<string, any>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    if (extractionResult) {
      setFormFields(extractionResult.fields);
      setErrorMsg("");
    }
  }, [extractionResult]);

  // Close on Escape key
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [isOpen, onClose]);

  if (!isOpen || !extractionResult) return null;

  // Compute PDF Url using api base URL
  const apiBase = api.defaults.baseURL || "http://127.0.0.1:8000/api/v1";
  const pdfUrl = `${apiBase}/documents/temp/${extractionResult.temp_file_id}`;

  const handleFieldChange = (key: string, val: any) => {
    setFormFields((prev) => ({ ...prev, [key]: val }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMsg("");
    try {
      await onConfirm(formFields);
      onClose();
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || "Failed to confirm extraction values.");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Helper to resolve confidence class and styles
  const getConfidenceLevel = (field: string): "high" | "medium" | "low" => {
    const score = extractionResult.confidence[field] ?? 0;
    if (score >= 0.8) return "high";
    if (score >= 0.5) return "medium";
    return "low";
  };

  const getFieldStyles = (field: string) => {
    const level = getConfidenceLevel(field);
    switch (level) {
      case "high":
        return {
          borderColor: "#12B76A",
          backgroundColor: "#F0FDF4",
          badgeBg: "#D1FADF",
          badgeText: "#027A48",
          label: "High Confidence",
        };
      case "medium":
        return {
          borderColor: "#F79009",
          backgroundColor: "#FFFAEB",
          badgeBg: "#FEF0C7",
          badgeText: "#B54708",
          label: "Medium Confidence",
        };
      case "low":
      default:
        return {
          borderColor: "#D92D20",
          backgroundColor: "#FEF3F2",
          badgeBg: "#FEE4E2",
          badgeText: "#B42318",
          label: "Low Confidence",
        };
    }
  };

  // Expected fields based on docType
  const fieldsMeta = docType === "contract" 
    ? [
        { key: "vendor_name", label: "Vendor Name", type: "text", required: true, icon: <Shield size={14} /> },
        { key: "contract_number", label: "Contract Number", type: "text", required: true, icon: <FileText size={14} /> },
        { key: "contract_amount", label: "Contract Amount ($)", type: "number", required: false, icon: <DollarSign size={14} /> },
        { key: "start_date", label: "Start Date", type: "date", required: false, icon: <Calendar size={14} /> },
        { key: "end_date", label: "End Date (Expiration)", type: "date", required: false, icon: <Calendar size={14} /> },
      ]
    : [
        { key: "vendor_name", label: "Vendor Name", type: "text", required: true, icon: <Shield size={14} /> },
        { key: "invoice_number", label: "Invoice Number", type: "text", required: true, icon: <FileText size={14} /> },
        { key: "invoice_date", label: "Invoice Date", type: "date", required: true, icon: <Calendar size={14} /> },
        { key: "invoice_amount", label: "Invoice Amount ($)", type: "number", required: true, icon: <DollarSign size={14} /> },
      ];

  return (
    <>
      {/* Backdrop */}
      <div className="drawer-backdrop" onClick={onClose} />
      
      {/* Split Review Drawer */}
      <div className="drawer open" style={{ width: "85%", maxWidth: "1350px", display: "flex", flexDirection: "column" }}>
        
        {/* Header */}
        <div className="drawer-header" style={{ flexShrink: 0 }}>
          <div>
            <div className="drawer-title" style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <span>Document Intelligence Review</span>
              <span className="badge" style={{ backgroundColor: "#2F6BFF", color: "#FFFFFF", fontSize: "11px", textTransform: "uppercase" }}>
                {docType}
              </span>
            </div>
            <div className="drawer-subtitle">
              Verify and adjust the deterministic extractions below before saving to lists.
            </div>
          </div>
          <button className="modal-close" onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </div>

        {/* Content body split pane */}
        <div style={{ display: "flex", flex: 1, overflow: "hidden", minHeight: 0 }}>
          
          {/* Left Pane: PDF Preview */}
          <div style={{ width: "55%", borderRight: "1px solid #E5E7EB", backgroundColor: "#F3F4F6", display: "flex", flexDirection: "column" }}>
            <iframe 
              src={pdfUrl} 
              title="PDF Preview"
              style={{ width: "100%", height: "100%", border: "none" }}
            />
          </div>

          {/* Right Pane: Review & Edits Form */}
          <div style={{ width: "45%", display: "flex", flexDirection: "column", overflowY: "auto", backgroundColor: "#FFFFFF" }}>
            <form onSubmit={handleSubmit} style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "20px", flex: 1 }}>
              
              {/* Warnings List */}
              {extractionResult.warnings.length > 0 && (
                <div style={{ backgroundColor: "#FFFAEB", borderLeft: "4px solid #F79009", padding: "12px 16px", borderRadius: "6px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: 600, color: "#B54708", marginBottom: "6px" }}>
                    <AlertTriangle size={16} />
                    <span>Parser Warnings ({extractionResult.warnings.length})</span>
                  </div>
                  <ul style={{ margin: 0, paddingLeft: "20px", fontSize: "12px", color: "#B54708", display: "flex", flexDirection: "column", gap: "3px" }}>
                    {extractionResult.warnings.map((w, idx) => (
                      <li key={idx}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}

              {errorMsg && (
                <div style={{ backgroundColor: "#FEF3F2", borderLeft: "4px solid #D92D20", padding: "12px 16px", borderRadius: "6px", color: "#B42318", fontSize: "13px" }}>
                  {errorMsg}
                </div>
              )}

              {/* Extraction Fields */}
              <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
                {fieldsMeta.map((f) => {
                  const styles = getFieldStyles(f.key);
                  const val = formFields[f.key] ?? "";
                  return (
                    <div key={f.key} style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <label className="form-label" style={{ display: "flex", alignItems: "center", gap: "6px", margin: 0 }}>
                          {f.icon}
                          <span>{f.label} {f.required && <span style={{ color: "#D92D20" }}>*</span>}</span>
                        </label>
                        <span 
                          style={{ 
                            fontSize: "11px", 
                            fontWeight: 500, 
                            padding: "2px 8px", 
                            borderRadius: "12px", 
                            backgroundColor: styles.badgeBg, 
                            color: styles.badgeText 
                          }}
                        >
                          {styles.label}
                        </span>
                      </div>
                      
                      <input
                        type={f.type}
                        required={f.required}
                        value={val}
                        step={f.type === "number" ? "0.01" : undefined}
                        onChange={(e) => handleFieldChange(f.key, e.target.value)}
                        style={{
                          border: `1.5px solid ${styles.borderColor}`,
                          borderRadius: "6px",
                          padding: "10px 12px",
                          fontSize: "14px",
                          width: "100%",
                          outline: "none",
                          boxSizing: "border-box",
                        }}
                      />
                    </div>
                  );
                })}
              </div>

              {/* Push Actions Spacer */}
              <div style={{ flexGrow: 1 }} />

              {/* Action Buttons */}
              <div style={{ display: "flex", gap: "12px", borderTop: "1px solid #E5E7EB", paddingTop: "20px", marginTop: "20px" }}>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="btn btn-primary"
                  style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "8px", flex: 1, height: "42px" }}
                >
                  <Check size={16} />
                  <span>{isSubmitting ? "Confirming..." : "Confirm & Save"}</span>
                </button>
                <button
                  type="button"
                  onClick={onRetry}
                  disabled={isSubmitting}
                  className="btn btn-secondary"
                  style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "8px", flexShrink: 0, padding: "0 16px", height: "42px" }}
                  title="Upload another file"
                >
                  <RotateCcw size={16} />
                  <span>Retry</span>
                </button>
                <button
                  type="button"
                  onClick={onClose}
                  disabled={isSubmitting}
                  className="btn btn-secondary"
                  style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "8px", flexShrink: 0, padding: "0 16px", height: "42px" }}
                >
                  <X size={16} />
                  <span>Cancel</span>
                </button>
              </div>

            </form>
          </div>

        </div>

      </div>
    </>
  );
};
