import React from "react";

export const MetricSkeleton: React.FC = () => (
  <div className="metric-card" style={{ gap: "14px" }}>
    <div className="skeleton" style={{ width: "38px", height: "38px", borderRadius: "6px", flexShrink: 0 }} />
    <div style={{ display: "flex", flexDirection: "column", gap: "7px", flex: 1 }}>
      <div className="skeleton" style={{ width: "72px", height: "11px" }} />
      <div className="skeleton" style={{ width: "44px", height: "22px" }} />
      <div className="skeleton" style={{ width: "56px", height: "10px" }} />
    </div>
  </div>
);

export const TableSkeleton: React.FC<{ rows?: number; cols?: number }> = ({
  rows = 6,
  cols = 6,
}) => (
  <div className="table-section">
    <div className="table-toolbar">
      <div style={{ display: "flex", gap: "8px" }}>
        <div className="skeleton" style={{ width: "200px", height: "32px", borderRadius: "6px" }} />
        <div className="skeleton" style={{ width: "100px", height: "32px", borderRadius: "6px" }} />
      </div>
      <div className="skeleton" style={{ width: "130px", height: "32px", borderRadius: "6px" }} />
    </div>
    <div className="enterprise-table-container">
      <table className="enterprise-table">
        <thead>
          <tr>
            {Array.from({ length: cols }).map((_, i) => (
              <th key={i}>
                <div className="skeleton" style={{ width: `${40 + i * 12}px`, height: "11px" }} />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: rows }).map((_, r) => (
            <tr key={r}>
              {Array.from({ length: cols }).map((_, c) => (
                <td key={c}>
                  <div className="skeleton" style={{ width: c === 0 ? "60px" : "75%", height: "13px" }} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </div>
);

export const ChartSkeleton: React.FC = () => (
  <div className="chart-card">
    <div className="chart-header">
      <div>
        <div className="skeleton" style={{ width: "140px", height: "14px", marginBottom: "6px" }} />
        <div className="skeleton" style={{ width: "80px", height: "11px" }} />
      </div>
    </div>
    <div className="skeleton" style={{ width: "100%", height: "240px", borderRadius: "6px" }} />
  </div>
);

export const ActivitySkeleton: React.FC = () => (
  <div className="activity-card">
    <div className="activity-header">
      <div className="skeleton" style={{ width: "120px", height: "13px" }} />
      <div className="skeleton" style={{ width: "24px", height: "18px", borderRadius: "10px" }} />
    </div>
    <div className="activity-list">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="activity-item">
          <div className="skeleton" style={{ width: "7px", height: "7px", borderRadius: "50%", flexShrink: 0, marginTop: "5px" }} />
          <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "5px" }}>
            <div className="skeleton" style={{ width: "80%", height: "12px" }} />
            <div className="skeleton" style={{ width: "50%", height: "10px" }} />
          </div>
        </div>
      ))}
    </div>
  </div>
);

export const DrawerSkeleton: React.FC = () => (
  <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
      <div className="skeleton" style={{ width: "80px", height: "10px" }} />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
        {[1, 2, 3, 4].map((i) => (
          <div key={i} style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
            <div className="skeleton" style={{ width: "60px", height: "10px" }} />
            <div className="skeleton" style={{ width: "100%", height: "14px" }} />
          </div>
        ))}
      </div>
    </div>
    <div className="skeleton" style={{ width: "100%", height: "1px" }} />
    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
      <div className="skeleton" style={{ width: "100px", height: "10px" }} />
      {[1, 2, 3].map((i) => (
        <div key={i} className="skeleton" style={{ width: "100%", height: "60px", borderRadius: "6px" }} />
      ))}
    </div>
  </div>
);
