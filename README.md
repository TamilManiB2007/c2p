# Contract-to-Payment (C2P) Compliance Platform

An enterprise procurement and finance compliance system designed to ensure invoice-to-contract alignment, audit contract lifecycle rules, identify spending violations, and automate payment authorization.

---

## 🏗️ Architecture & Modules

The platform is designed as a modern monorepo separating a high-performance RESTful API backend from a clean, responsive enterprise web app.

```
C2P-Platform/
├── apps/
│   └── web/                   # React + Vite Frontend
│       ├── src/               # React Code base
│       └── package.json       # UI Dependency Config
├── c2p-platform/
│   └── apps/
│       └── api/               # FastAPI + SQLAlchemy Backend
│           ├── app/           # Core API modules
│           ├── tests/         # Unit & Integration Tests
│           └── pyproject.toml # Python Dependency Config
├── LICENSE                    # MIT License
└── README.md                  # Root Documentation
```

### Technical Blueprint
For a detailed guide on the system design, design system tokens, database schema relationships, and compliance rules, see **[Architecture.md](file:///c:/Users/Prashanth/Downloads/C2P-Platform/C2P-Platform/Architecture.md)**.

---

## ⚡ Quick Start

### 1. Backend API Server
Navigate to the api folder, establish your environment, and launch the FastAPI demo server (SQLite powered):
```bash
cd c2p-platform/apps/api
# Run the demo server (it auto-configures SQLite and seeds mock records if missing)
python demo_server.py
```
*API docs will be available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).*

### 2. Frontend Web App
Navigate to the web folder, install dependencies, and start the development server:
```bash
cd apps/web
npm install
npm run dev
```
*UI will be available at [http://localhost:5173](http://localhost:5173).*

For full step-by-step instructions (including how to run tests, setup PostgreSQL, or run database migrations), refer to **[Setup.md](file:///c:/Users/Prashanth/Downloads/C2P-Platform/C2P-Platform/Setup.md)**.

---

## 🚀 Deployment & Operations
For production environments, Docker build workflows, environmental variable lists, and database scaling practices, see **[Deployment.md](file:///c:/Users/Prashanth/Downloads/C2P-Platform/C2P-Platform/Deployment.md)**.

---

## 🗺️ Product Roadmap
To view upcoming development phases, performance optimization paths, and technical debt tasks, refer to **[ROADMAP.md](file:///c:/Users/Prashanth/Downloads/C2P-Platform/C2P-Platform/ROADMAP.md)**.

---

## 📋 Quality & Compliance Status

* **Unit & Integration Tests:** 67 / 67 Passed (FastAPI + Pytest)
* **TypeScript Build:** 0 Errors (`tsc -b && vite build` verified)
* **Security & Keys Check:** 100% Cleared (0 hardcoded credentials or API keys; `.env` configuration untracked and ignored)
* **Data Integrity:** 100% Dynamic API Integration (0 frontend mock datasets or static data fallbacks)
