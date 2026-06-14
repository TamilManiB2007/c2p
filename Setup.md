# Development Setup Guide

Follow these instructions to clone, configure, build, and run the C2P Platform on your local environment.

---

## 📋 Prerequisites
Ensure you have the following software installed:
* **Python 3.10 to 3.13**
* **Node.js (LTS version 18 or 20)**
* **Git**

---

## 🐍 Backend Setup (FastAPI)

All commands are run from the backend directory:
```bash
cd c2p-platform/apps/api
```

### 1. Set Up Virtual Environment
Create and activate a Python virtual environment:
```bash
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies
Install dependencies using standard pip or `uv`:
```bash
pip install -e .
```
*(Alternatively, if using `uv`):*
```bash
uv pip install -e .
```

### 3. Environment Variables
Copy the example configuration to create your local `.env` file:
```bash
copy .env.example .env   # Windows
cp .env.example .env     # macOS / Linux
```

### 4. Database Initialization & Migrations
Initialize your database and run Alembic migrations to construct the schema:
```bash
# Run database migrations
alembic upgrade head
```

### 5. Running the Application (Local Demo Mode)
For quick local verification without manual PostgreSQL configuration, use the built-in SQLite demo server:
```bash
# This starts the server on http://127.0.0.1:8000, 
# auto-creating and seeding the 'demo_c2p.db' SQLite database.
python demo_server.py
```

### 6. Verify with Test Suite
Ensure that the entire API functionality is working as expected by running `pytest`:
```bash
python -m pytest
```

---

## 💻 Frontend Setup (React + Vite)

All commands are run from the frontend directory:
```bash
cd apps/web
```

### 1. Install Dependencies
Install packages listed in `package.json`:
```bash
npm install
```

### 2. Run the Development Server
Launch Vite's hot-reloading development server:
```bash
npm run dev
```
*The web app will boot up on [http://localhost:5173](http://localhost:5173).*

### 3. Compile a Production Build
Verify the TypeScript compiler and bundler are clean:
```bash
npm run build
```
*This generates a optimized production-ready bundle in the `apps/web/dist` folder.*
