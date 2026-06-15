from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.core.database import init_db, close_db
from app.core.logging import configure_logger, request_logging_middleware
from app.api import api_router

# ── 1. Initialise logger immediately — before anything else ─────────────────
configure_logger(console_level="INFO")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from loguru import logger
    logger.info("C2P Platform starting up | version={}", settings.APP_VERSION)
    await init_db()
    logger.info("Database connection pool ready")
    yield
    logger.info("C2P Platform shutting down")
    await close_db()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Contract-to-Payment Compliance Platform API",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── 2. Request logging middleware ────────────────────────────────────────────
app.add_middleware(BaseHTTPMiddleware, dispatch=request_logging_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.APP_VERSION}


@app.get("/")
async def root():
    return {
        "message": "Welcome to C2P Platform API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }