# Release Notes — v0.5-foundation-stable

This release stamps the foundational layers of the Contract-to-Payment (C2P) Compliance Platform. The codebase comprises secure core modules, automated compliance rule execution, and a responsive enterprise design system.

---

## 🚀 Key Modules & Feature Highlights

### 🔒 1. Authentication & Security
* JWT Bearer token authentication architecture with HTTP headers interception in the UI.
* Safe password hashing with `bcrypt` (12 rounds standard).
* UUID-obfuscated contract and invoice file uploads stored securely on disk to prevent document traversal attacks.
* Explicit `.env` isolation (untracked and ignored).

### 📄 2. Contracts Management
* Streamlined upload form supporting PDF format restrictions (max 20 MB).
* Dynamic contract table view supporting vendor and reference ID matching, page navigation, and detail drawers showing metadata and status fields.
* API endpoints to download contract files from secure storage or delete them from both the database and file system.

### 🧾 3. Invoices Management
* High-volume invoice PDF uploader integrating vendor, billing date, and monetary attributes.
* Invoices table listing supporting vendor filters, status, page selectors, and modal metadata details.
* Automated file cleaner removing related PDFs from disk upon invoice deletion.

### ⚙️ 4. Compliance Rules Engine
* Trigger-based compliance audits executed on contract-invoice matching pairs.
* Checks three core procurement compliance rules:
  1. **Vendor Mismatch:** Cross-references invoice vendor names against contract vendor names (case-insensitive, whitespace trimmed).
  2. **Contract Expired:** Checks if billing dates fall outside contract validity boundaries.
  3. **Invoice Amount Exceeded:** Accumulates already approved invoice sums to verify they do not breach the contract limit.
* Outputs instant colour-coded violations lists and detailed severity indicators (Low, Medium, High).

### 📊 5. Dashboard & Analytics
* Clean, non-distracting light mode layout following enterprise design paradigms.
* 4 Key Performance Indicators (KPIs) showing active contracts, invoice volumes, violations flagged, and spend audit totals.
* 3 interactive analytical charts:
  - Spend & Violation Trend Lines (Compliance trend over time).
  - Spend Distribution by Vendor (Horizontal bar charts).
  - Audit Pipeline status (Donut charts highlighting pending vs. flag ratios).
* Unified, real-time activity feeds showing recent checks and updates.

### 📈 6. Advanced Reports (New)
* Multi-axis spend analysis charts.
* CSV downloads for one-click reports exporting on contracts, invoices, and violations registers.

---

## 🛠️ Verification & Test Status
* **FastAPI Backend Tests:** **67 / 67 Tests Passed** (Pytest test suite completes successfully with 100% pass rate).
* **Vite Frontend Compilation:** **0 TypeScript compile errors** on optimized production builds (`tsc -b && vite build` compiled successfully).
* **Data Integrity:** **100% Dynamic API Integration** (no hardcoded mock placeholders or static hooks are present in the frontend UI).
