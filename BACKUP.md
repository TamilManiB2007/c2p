# Disaster Recovery & Repository Backup Guide

This guide describes how to clone, migrate, back up, recover, and provision environment parameters for the C2P platform from zero.

---

## 🔗 Repository Registry
* **Repository URL:** [https://github.com/TamilManiB2007/c2p.git](https://github.com/TamilManiB2007/c2p.git)
* **Default Branch:** `main`
* **Release Freeze Tag:** `v0.5-foundation-stable`

---

## 📥 Local Replication & Setup (Clone)
To replicate the environment on a fresh machine:
```bash
# 1. Clone the repository
git clone https://github.com/TamilManiB2007/c2p.git
cd c2p

# 2. Checkout the stable foundation tag
git checkout tags/v0.5-foundation-stable
```

For package setup and running parameters on both backend and frontend, see **[Setup.md](file:///c:/Users/Prashanth/Downloads/C2P-Platform/C2P-Platform/Setup.md)**.

---

## 🗄️ Database Migrations
If migrating or deploying to a fresh SQL engine (PostgreSQL or local SQLite):
```bash
cd c2p-platform/apps/api

# Apply latest migrations via Alembic
alembic upgrade head
```

---

## ⚙️ Environment Profile Registry

Inject these environment settings inside your local configuration files (e.g., `.env`) or cloud environment store:

### 🐍 Backend API Config (`c2p-platform/apps/api/.env`)
```ini
# Core
APP_NAME="C2P Platform API"
APP_VERSION="0.1.0"
DEBUG=True

# Database connection
DATABASE_URL="sqlite+aiosqlite:///./demo_c2p.db"

# Security (JWT token generation)
SECRET_KEY="c2p-demo-secret-key-32-chars-minimum-ok"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=43200
BCRYPT_ROUNDS=4

# Storage
UPLOAD_DIR="uploads/contracts"
INVOICES_UPLOAD_DIR="uploads/invoices"
MAX_FILE_SIZE_MB=20
```

---

## 🚨 Recovery Procedures (Disaster Recovery)

### 1. File Uploads Recovery
* **Issue:** Uploaded PDF documents are missing or corrupted on the server disk.
* **Resolution:** 
  1. Retrieve contract or invoice attachments from your storage backup bucket.
  2. Restore files to the directory defined in the `UPLOAD_DIR` and `INVOICES_UPLOAD_DIR` environment variables.
  3. Ensure that the filenames match the UUID strings stored in the `file_name` column of the `contracts` and `invoices` database tables.

### 2. Database Corruption or Restoration
* **Issue:** Local database (`demo_c2p.db` SQLite) is corrupted or database tables fail to load.
* **Resolution:**
  1. Terminate any active FastAPI or Uvicorn servers.
  2. Delete the corrupted `demo_c2p.db` file from the `c2p-platform/apps/api` folder.
  3. Re-launch the API server using `python demo_server.py`. The server will automatically initialize a fresh, clean SQLite database and re-seed all base tables.
