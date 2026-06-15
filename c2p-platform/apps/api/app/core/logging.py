"""
app/core/logging.py
-------------------
Structured logging for the C2P Platform using loguru.

Inspired by the logger.py pattern from:
  Shubhamsaboo/awesome-llm-apps →
  ai_travel_planner_agent_team/backend/config/logger.py

Additions specific to C2P:
  - Request middleware (timestamp, method, path, duration_ms, status_code)
  - Document pipeline event helpers (upload_start, extract_*, confirm_*)
  - Compliance rule event helpers (rule_start, rule_pass, rule_fail)
  - Exception capture with request_id
"""

import sys
import logging
import uuid
from typing import Callable

from loguru import logger


# ---------------------------------------------------------------------------
# Internal – stdlib → loguru bridge
# ---------------------------------------------------------------------------

class _InterceptHandler(logging.Handler):
    """
    Redirect all stdlib `logging` calls (uvicorn, sqlalchemy, alembic,
    python-jose, passlib …) into loguru so every log line goes through
    the same pipeline.
    """

    def emit(self, record: logging.LogRecord) -> None:
        # Map stdlib level name to loguru level
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno  # type: ignore[assignment]

        # Walk up the call stack to find the real caller so loguru reports
        # the right source file / line number instead of this handler.
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back  # type: ignore[assignment]
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


# ---------------------------------------------------------------------------
# Public – configure once at startup
# ---------------------------------------------------------------------------

def configure_logger(
    console_level: str = "INFO",
    log_format: str | None = None,
) -> None:
    """
    Call once from main.py before the FastAPI app starts.

    - Removes the default loguru handler (stderr / no format).
    - Adds a colour-coded, human-readable console handler.
    - Installs _InterceptHandler on the root stdlib logger so that
      uvicorn, SQLAlchemy, alembic, and any third-party library that
      uses stdlib logging also flows through loguru.
    """
    if log_format is None:
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> "
            "- <level>{message}</level>"
        )

    # Remove default handler
    logger.remove()

    # Add formatted console handler
    logger.add(
        sys.stderr,
        format=log_format,
        level=console_level,
        colorize=True,
        backtrace=True,   # Show full traceback on exceptions
        diagnose=True,    # Show variable values in tracebacks
        enqueue=False,    # Synchronous — safe for uvicorn's async loop
    )

    # Bridge stdlib → loguru for uvicorn, sqlalchemy, alembic, etc.
    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)

    # Silence noisy third-party loggers we don't need at INFO level
    for noisy in ("uvicorn.access", "sqlalchemy.engine.base.Engine"):
        std_logger = logging.getLogger(noisy)
        std_logger.handlers = [_InterceptHandler()]
        std_logger.propagate = False

    logger.info("C2P Platform logger initialised | level={}", console_level)


# ---------------------------------------------------------------------------
# Request Logging Middleware
# ---------------------------------------------------------------------------

async def request_logging_middleware(request, call_next: Callable):
    """
    Starlette-compatible middleware that logs every HTTP request with:
      timestamp (implicit in loguru format)
      method, path, status_code, duration_ms, request_id
    """
    request_id = str(uuid.uuid4())[:8]
    # Attach request_id so exception handlers can reference it
    request.state.request_id = request_id

    import time
    start = time.perf_counter()

    logger.info(
        "REQUEST  | id={} method={} path={}",
        request_id,
        request.method,
        request.url.path,
    )

    try:
        response = await call_next(request)
    except Exception as exc:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.error(
            "EXCEPTION | id={} method={} path={} duration_ms={} exc={}",
            request_id,
            request.method,
            request.url.path,
            duration_ms,
            repr(exc),
            exc_info=True,
        )
        raise

    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    level = "WARNING" if response.status_code >= 400 else "INFO"

    logger.log(
        level,
        "RESPONSE | id={} method={} path={} status={} duration_ms={}",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )

    return response


# ---------------------------------------------------------------------------
# Document Pipeline Event Helpers
# ---------------------------------------------------------------------------

def log_upload_start(filename: str, doc_type: str, user_id: int) -> None:
    logger.info(
        "PIPELINE | upload_start | file={} doc_type={} user_id={}",
        filename, doc_type, user_id,
    )


def log_extract_start(temp_file_id: str, doc_type: str) -> None:
    logger.info(
        "PIPELINE | extract_start | temp_file_id={} doc_type={}",
        temp_file_id, doc_type,
    )


def log_extract_complete(
    temp_file_id: str,
    doc_type: str,
    field_count: int,
    warnings: list,
) -> None:
    warn_count = len(warnings)
    logger.info(
        "PIPELINE | extract_complete | temp_file_id={} doc_type={} fields={} warnings={}",
        temp_file_id, doc_type, field_count, warn_count,
    )
    for w in warnings:
        logger.warning("PIPELINE | extraction_warning | {}", w)


def log_confirm_start(temp_file_id: str, doc_type: str, user_id: int) -> None:
    logger.info(
        "PIPELINE | confirm_start | temp_file_id={} doc_type={} user_id={}",
        temp_file_id, doc_type, user_id,
    )


def log_confirm_complete(doc_type: str, record_id: int | None = None) -> None:
    logger.info(
        "PIPELINE | confirm_complete | doc_type={} record_id={}",
        doc_type, record_id,
    )


# ---------------------------------------------------------------------------
# Compliance Event Helpers
# ---------------------------------------------------------------------------

def log_rule_start(
    rule_name: str,
    contract_id: int,
    invoice_id: int,
) -> None:
    logger.info(
        "COMPLIANCE | rule_start | rule={} contract_id={} invoice_id={}",
        rule_name, contract_id, invoice_id,
    )


def log_rule_pass(rule_name: str, detail: str) -> None:
    logger.info(
        "COMPLIANCE | rule_pass  | rule={} detail={}",
        rule_name, detail,
    )


def log_rule_fail(rule_name: str, detail: str) -> None:
    logger.warning(
        "COMPLIANCE | rule_fail  | rule={} detail={}",
        rule_name, detail,
    )


# ---------------------------------------------------------------------------
# Error / Exception Helper
# ---------------------------------------------------------------------------

def log_exception(
    exc: Exception,
    context: str = "",
    request_id: str | None = None,
) -> None:
    """
    Capture an exception with full stacktrace into loguru.
    Use this in except blocks anywhere in the app.
    """
    logger.error(
        "EXCEPTION | request_id={} context={} exc={}",
        request_id or "unknown",
        context,
        repr(exc),
        exc_info=True,
    )
