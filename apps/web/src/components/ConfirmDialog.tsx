import React from "react";
import { AlertTriangle } from "lucide-react";

interface ConfirmDialogProps {
  isOpen: boolean;
  title: string;
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
  isLoading?: boolean;
  confirmLabel?: string;
}

export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  isOpen,
  title,
  message,
  onConfirm,
  onCancel,
  isLoading = false,
  confirmLabel = "Delete",
}) => {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-card confirm-dialog">
        <div className="modal-header">
          <span className="modal-title" style={{ color: "var(--error)", display: "flex", alignItems: "center", gap: "8px" }}>
            <AlertTriangle size={16} />
            {title}
          </span>
          <button className="modal-close" onClick={onCancel}>
            <span style={{ fontSize: "16px", lineHeight: 1 }}>×</span>
          </button>
        </div>
        <div className="modal-body" style={{ gap: "0" }}>
          <p style={{ fontSize: "13.5px", color: "var(--text-secondary)", lineHeight: 1.65 }}>
            {message}
          </p>
        </div>
        <div className="modal-footer">
          <button className="btn-secondary" onClick={onCancel} disabled={isLoading}>
            Cancel
          </button>
          <button className="btn-danger" onClick={onConfirm} disabled={isLoading}>
            {isLoading ? "Deleting..." : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
};
