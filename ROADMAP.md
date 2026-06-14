# Technical Roadmap & Technical Debt Registry

This document outlines future development phases, scaling strategies, and plans to resolve architectural technical debt for the C2P Platform.

---

## 🗺️ Product Roadmap

```
  Phase 1: Security          Phase 2: Performance       Phase 3: Refactoring       Phase 4: Advanced
┌──────────────────────┐   ┌──────────────────────┐   ┌──────────────────────┐   ┌──────────────────────┐
│ • Token Expirations  │   │ • Code-splitting JS  │   │ • Merge monorepos    │   │ • Custom Rule Editor │
│ • Endpoint Limiting  │   │ • Redis Query Cache  │   │ • 90%+ Test Coverage │   │ • Payment Gateway    │
│ • Secure CORS Scope  │   │ • Cloud S3 Storage   │   │ • Standard Logger    │   │ • Multi-Currency     │
└──────────┬───────────┘   └──────────┬───────────┘   └──────────┬───────────┘   └──────────┬───────────┘
           │                          │                          │                          │
           ▼                          ▼                          ▼                          ▼
```

### Phase 1: Security Hardening
* **Token Lifetimes:** Transition `ACCESS_TOKEN_EXPIRE_MINUTES` to short-lived window (30-60 mins) and implement Refresh Token rotation flows.
* **Rate Limiting:** Implement rate limiting middleware (e.g., sliding window limits using FastAPI Limiter/Redis) on critical entryways like `/auth/login`.
* **CORS Hardening:** Swap wildcard allow rules for domain specific whitelisting in production builds.
* **Password Auditing:** Integrate library-backed password complexity validators (e.g., zxcvbn) to verify user password strength during sign-up.

### Phase 2: Performance & Scalability
* **Frontend Bundle Splitting:** Refactor routing in `apps/web/src/App.tsx` using `React.lazy` and `React.Suspense` to code-split dashboard, compliance, and reports pages into dedicated lazy chunks. This addresses the 750kB JS bundle size warning.
* **Database Optimization:** Review query execution plans and add database indexes on columns frequently used in filtering/searching, such as `contracts.vendor_name` and `invoices.invoice_number`.
* **Distributed Query Caching:** Introduce Redis to cache compliance execution histories and dashboard KPIs, reducing load on SQLAlchemy queries.
* **Cloud File Storage:** Connect backend files handlers to secure cloud bucket endpoints (e.g., AWS S3 or Google Cloud Storage) instead of storing uploads on local application container disks.

### Phase 3: Architecture & Technical Debt Resolution
* **Monorepo Directory Alignment:** Merge the nested folder structure. Currently, the React application is at `/apps/web` but the backend is nested under `/c2p-platform/apps/api`. We recommend moving the api folder to `/apps/api` at the root, making it a clean, standardized monorepo.
* **Test Coverage Extension:** Increase unit/integration test coverage from 67 tests (~85% coverage) to 90%+ coverage. Add mock performance load tests.
* **Production Logging:** Transition FastAPI printing lines to standard structured JSON logging utilities (e.g., `structlog`) to facilitate centralized log aggregation (Elasticsearch/Splunk).

### Phase 4: Advanced Product Features
* **Custom Rule Editor:** Allow procurement managers to write custom compliance validation rules using a UI rule editor, without writing Python code.
* **Payment Gateway Integration:** Build payment webhooks (Stripe/Wise) to automatically trigger disbursements for fully compliant invoices.
* **Multi-Currency Support:** Add currency conversion APIs to audit invoices billed in currencies different from the master contract.

---

## 🛠️ Technical Debt Registry

| Debt Area | Severity | Impact | Plan for Resolution |
|---|---|---|---|
| Folder Nesting | **Medium** | Increases setup confusion due to `/c2p-platform/apps/api` and `/apps/web` asymmetry. | Relocate `/c2p-platform/apps/api` to `/apps/api` and update workspaces configuration. |
| Large JS Bundle Size | **Low** | Extends initial page load latency slightly (~750kB index chunk). | Implement route-based code-splitting using dynamic React lazy imports. |
| Local Disk Uploads | **High** | Files uploaded in containers will be lost on container restarts. | Integrate SQLAlchemy storage handlers with AWS S3 / GCP Storage API. |
| Password Hashing Sync | **Low** | Reduced bcrypt rounds in testing environment might seep to production. | Force `BCRYPT_ROUNDS=12` in production config file checks. |
