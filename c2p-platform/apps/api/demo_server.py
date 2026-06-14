"""
C2P Platform API — Demo Runner
===============================
Starts the FastAPI server with an in-process SQLite database.
No PostgreSQL required. Great for local demos and development.

Usage:
    python demo_server.py

Then open: http://127.0.0.1:8000/docs
"""
import asyncio
import os
import sys

# ── Override DATABASE_URL before any app import ─────────────────────────────
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./demo_c2p.db"
os.environ["SECRET_KEY"] = "c2p-demo-secret-key-32-chars-minimum-ok"
os.environ["BCRYPT_ROUNDS"] = "4"          # lower rounds = faster for demo
os.environ["UPLOAD_DIR"] = "uploads/contracts"
os.environ["INVOICES_UPLOAD_DIR"] = "uploads/invoices"
os.environ["MAX_FILE_SIZE_MB"] = "20"
os.environ["DEBUG"] = "True"

# ── Patch database.py engine creation for SQLite ────────────────────────────
import app.core.database as _db_module
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

_demo_engine = create_async_engine(
    "sqlite+aiosqlite:///./demo_c2p.db",
    echo=False,
    connect_args={"check_same_thread": False},
)

_DemoSession = async_sessionmaker(
    _demo_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Monkey-patch the module-level engine & session factory
_db_module.engine = _demo_engine
_db_module.AsyncSessionLocal = _DemoSession

# Patch get_db_session so FastAPI DI uses our SQLite session
async def _sqlite_get_db_session():
    async with _DemoSession() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

_db_module.get_db_session = _sqlite_get_db_session

# Also patch init_db to use demo engine
async def _sqlite_init_db():
    async with _demo_engine.begin() as conn:
        await conn.run_sync(_db_module.Base.metadata.create_all)

_db_module.init_db = _sqlite_init_db


# ── Now import and patch the FastAPI app ────────────────────────────────────
from app.main import app
from app.core.database import get_db_session

app.dependency_overrides[get_db_session] = _sqlite_get_db_session

# ── Start server ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    print("\n" + "="*60)
    print("  C2P Platform API -- Demo Server")
    print("="*60)
    print("  Swagger UI  ->  http://127.0.0.1:8000/docs")
    print("  ReDoc       ->  http://127.0.0.1:8000/redoc")
    print("  Health      ->  http://127.0.0.1:8000/health")
    print("="*60)
    print("  Database    : SQLite (demo_c2p.db in current dir)")
    print("  JWT Secret  : demo key")
    print("="*60 + "\n")

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
