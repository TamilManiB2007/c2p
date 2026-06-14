# System Architecture Documentation

This document describes the architectural patterns, database schemas, frontend design tokens, and compliance engine rules of the Contract-to-Payment (C2P) Compliance Platform.

---

## 🏛️ Overall System Architecture

The C2P Platform is structured as a decoupled monorepo:
1. **Frontend (`apps/web`):** A single-page React application built with Vite and TypeScript.
2. **Backend (`c2p-platform/apps/api`):** A high-performance async REST API built with FastAPI and Python 3.13.

```
                    ┌─────────────────────────┐
                    │     React Web App       │
                    │      (Port 5173)        │
                    └────────────┬────────────┘
                                 │ HTTP / JSON
                                 ▼
                    ┌─────────────────────────┐
                    │      FastAPI API        │
                    │      (Port 8000)        │
                    └────────────┬────────────┘
                                 │ SQLAlchemy (Async)
                                 ▼
                    ┌─────────────────────────┐
                    │      Database           │
                    │   (SQLite / Postgres)   │
                    └─────────────────────────┘
```

---

## 💻 Frontend Architecture

### 1. Unified Enterprise Design System
The frontend UI follows an enterprise-procurement design system (inspired by Coupa, SAP Ariba, and AppZen) defined strictly through CSS custom properties (variables) in **[index.css](file:///c:/Users/Prashanth/Downloads/C2P-Platform/C2P-Platform/apps/web/src/index.css)**:

* **Background:** `#F7F8FA` (Soft neutral gray)
* **Sidebar:** `#FFFFFF` (Solid white, elevated)
* **Primary color:** `#2F6BFF` (Royal blue for primary buttons and actions)
* **Success color:** `#12B76A` (Bright green for compliant badges)
* **Warning color:** `#F79009` (Amber for low/medium risk compliance flags)
* **Error/Danger color:** `#D92D20` (True red for severe violations and errors)
* **Text:** `#111827` (Dark slate gray for readability)
* **Secondary Text:** `#6B7280` (Medium gray for metadata)
* **Borders:** `#E5E7EB` (Subtle light gray)
* **Radius:** `8px` maximum (Strict enterprise corners, no bubble cards)
* **Shadows:** No heavy ambient shadows; only a subtle `1px` stroke or very soft boundary shadow.

### 2. File Organization
* **`App.tsx`:** Standard shell holding the layout, sidebar navigation, top header, user menu, and route definitions.
* **`App.css`:** Contains layout grid definitions (280px left sidebar, 72px top header), scroll areas, modal/drawer animations, card states, and form controls.
* **`src/pages/`:** Page components directly corresponding to routes (`Dashboard`, `Contracts`, `Invoices`, `Compliance`, `Violations`, `Reports`, `Settings`, `Login`).
* **`src/components/`:** Clean presentation components (`Drawer`, `Skeletons` with shimmer animations, `Toast` with manual dismiss and status-color styles, `ConfirmDialog` with confirmation prompts).
* **`src/services/api.ts`:** Centralized Axios instance with request/response interceptors to automatically append JWT bearer tokens from local storage and intercept HTTP authorization errors.

---

## 🐍 Backend Architecture

The API uses standard FastAPI patterns utilizing dependency injection for database sessions and user authorization.

### 1. Database Schema (Entities)
All database interactions are managed by SQLAlchemy (declarative mapping). Below are the core tables:

#### **User** (`users` table)
* `id`: Integer (PK)
* `email`: String (Unique, Indexed)
* `full_name`: String
* `hashed_password`: String
* `is_active`: Boolean

#### **Contract** (`contracts` table)
* `id`: Integer (PK)
* `vendor_name`: String (Indexed)
* `contract_number`: String (Unique, Indexed)
* `contract_amount`: Numeric(12, 2)
* `start_date`: Date
* `end_date`: Date
* `status`: String (e.g., `"uploaded"`, `"active"`)
* `file_name`: String
* `file_path`: String
* `file_size`: Integer
* `mime_type`: String
* `created_by`: Integer (FK -> users.id)
* `created_at` / `updated_at`: DateTime

#### **Invoice** (`invoices` table)
* `id`: Integer (PK)
* `vendor_name`: String (Indexed)
* `invoice_number`: String (Unique, Indexed)
* `total_amount`: Numeric(12, 2)
* `invoice_date`: Date
* `status`: String (e.g., `"pending"`, `"approved"`)
* `file_name`: String
* `file_path`: String
* `file_size`: Integer
* `mime_type`: String
* `created_by`: Integer (FK -> users.id)
* `created_at` / `updated_at`: DateTime

#### **ComplianceCheck** (`compliance_checks` table)
* `id`: Integer (PK)
* `invoice_id`: Integer (FK -> invoices.id)
* `contract_id`: Integer (FK -> contracts.id, Nullable)
* `check_date`: DateTime
* `is_compliant`: Boolean
* `run_by`: Integer (FK -> users.id)

#### **Violation** (`violations` table)
* `id`: Integer (PK)
* `compliance_check_id`: Integer (FK -> compliance_checks.id)
* `rule_name`: String (e.g., `"vendor_mismatch"`)
* `severity`: String (`"low"`, `"medium"`, `"high"`)
* `description`: String

---

## ⚙️ Compliance Rules Engine

The compliance engine evaluates every invoice against a target contract. Evaluators check three main rules during a compliance run:

1. **Vendor Mismatch Check (`rule_name: "vendor_mismatch"`):**
   * **Logic:** Checks if the vendor name listed on the invoice matches the contract vendor name.
   * **Matching:** Evaluated case-insensitively with leading/trailing whitespaces trimmed.
   * **Severity:** **HIGH** if mismatched.

2. **Contract Expired Check (`rule_name: "contract_expired"`):**
   * **Logic:** Checks if the `invoice_date` is after the contract's `end_date`, or before the contract's `start_date`.
   * **Severity:** **HIGH** if expired.

3. **Invoice Amount Exceeded Check (`rule_name: "invoice_amount_exceeded"`):**
   * **Logic:** Queries all approved invoices associated with the contract, sums their totals (including the current invoice), and checks if it exceeds the contract's `contract_amount`.
   * **Severity:** **HIGH** if limit is exceeded.

---

## 🔒 Security Architecture

1. **Password Safety:** Hashed on registration using `bcrypt` (default `12` rounds in production, reduced to `4` rounds in test to accelerate test cycles).
2. **Access Security:** Restricted via HTTP JWT Bearer authentication headers. Tokens expire automatically after 30 days (`43200` minutes).
3. **Storage Security:** All uploaded contracts and invoice PDFs are placed in the `uploads/` directory on the server disk. Filenames are obfuscated into UUIDs (e.g., `51a2f6b8-4bc2-...pdf`) to prevent path traversal or document enumeration attacks.
