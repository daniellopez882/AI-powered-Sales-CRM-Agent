"""
utils/logging_config.py
Structured logging with PII masking.

Two defects in the previous revision are fixed here:

1. ``ProcessorFormatter`` was constructed with ``foreign_pre_processors``,
   which is not a parameter it accepts (the real name is
   ``foreign_pre_chain``). Because ``setup_logging()`` ran at import time,
   this raised ``TypeError`` and made every module that imported this one —
   including ``api.main`` — fail to load.

2. The masking processor rewrote *every* string in the event dict. The phone
   pattern was loose enough to match ISO timestamps, so structural fields
   such as ``timestamp`` were corrupted. Masking is now confined to fields
   that can carry user data, and the phone pattern requires a plausible
   digit count.
"""

from __future__ import annotations

import logging
import re
import sys
from collections.abc import Iterable
from typing import Any

import structlog

from config.settings import settings

# ── PII patterns ─────────────────────────────────────────────────────────────
EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")

# Require 7-15 digits in a plausible phone shape. The previous pattern made
# every group optional and matched as few as two digits, so it mangled dates,
# IDs and durations.
PHONE_PATTERN = re.compile(
    r"(?<![\w.])"
    r"(?:\+\d{1,3}[\s.-]?)?"
    r"(?:\(\d{2,4}\)[\s.-]?)?"
    r"\d{2,4}(?:[\s.-]\d{2,4}){1,3}"
    r"(?![\w.])"
)

# Shapes that satisfy the phone heuristic but are not phone numbers.
_DATE_LIKE = re.compile(r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}")
_TIME_LIKE = re.compile(r"\d{1,2}[:.]\d{2}(?:[:.]\d{2})?")
_VERSION_LIKE = re.compile(r"\d+\.\d+\.\d+(?:\.\d+)?")

# Fields structlog/our own code adds for structure, never user content.
STRUCTURAL_KEYS = frozenset(
    {
        "timestamp",
        "level",
        "logger",
        "logger_name",
        "event_id",
        "func_name",
        "lineno",
        "filename",
        "pathname",
        "process",
        "thread",
        "exception",
        "stack",
        "exc_info",
        "session_id",
        "request_id",
        "trace_id",
    }
)


def _mask_str(value: str) -> str:
    def mask_email(match: re.Match) -> str:
        user, _, domain = match.group(0).partition("@")
        head = user[0] if user else ""
        return f"{head}***@{domain}"

    value = EMAIL_PATTERN.sub(mask_email, value)

    def mask_phone(match: re.Match) -> str:
        raw = match.group(0)
        if _DATE_LIKE.fullmatch(raw) or _TIME_LIKE.fullmatch(raw) or _VERSION_LIKE.fullmatch(raw):
            return raw  # calendar dates, clock times and versions are not phones
        digits = re.sub(r"\D", "", raw)
        if not (7 <= len(digits) <= 15):
            return raw  # not phone-shaped; leave it alone
        return f"{raw[:2]}***"

    return PHONE_PATTERN.sub(mask_phone, value)


def mask_pii(value: Any) -> Any:
    """Recursively mask emails and phone numbers in strings, dicts and lists."""
    if isinstance(value, str):
        return _mask_str(value)
    if isinstance(value, dict):
        return {k: (v if k in STRUCTURAL_KEYS else mask_pii(v)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return type(value)(mask_pii(v) for v in value)
    return value


def pii_masking_processor(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """structlog processor: mask PII without touching structural fields."""
    return {k: (v if k in STRUCTURAL_KEYS else mask_pii(v)) for k, v in event_dict.items()}


def _shared_processors() -> Iterable[Any]:
    return [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        pii_masking_processor,
    ]


_configured = False


def setup_logging(force: bool = False) -> structlog.stdlib.BoundLogger:
    """Configure structlog + stdlib logging. Idempotent."""
    global _configured
    if _configured and not force:
        return structlog.get_logger()

    if settings.sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            from sentry_sdk.integrations.logging import LoggingIntegration

            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                integrations=[
                    FastApiIntegration(),
                    LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
                ],
                traces_sample_rate=0.1 if settings.is_production else 1.0,
                environment=settings.environment,
            )
        except ImportError:  # sentry-sdk is an optional extra
            logging.getLogger(__name__).warning(
                "SENTRY_DSN is set but sentry-sdk is not installed; skipping Sentry."
            )

    structlog.configure(
        processors=[*_shared_processors(), structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    renderer = (
        structlog.processors.JSONRenderer()
        if settings.is_production
        else structlog.dev.ConsoleRenderer(colors=False)
    )
    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=list(_shared_processors()),
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(getattr(logging, settings.log_level, logging.INFO))

    # uvicorn installs its own handlers on these loggers, so its access and
    # error lines bypassed this formatter entirely and were emitted as plain
    # text while application logs were JSON. Mixed formats break structured log
    # ingestion, so hand them to the root handler instead.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "uvicorn.asgi"):
        uv = logging.getLogger(name)
        uv.handlers = []
        uv.propagate = True

    _configured = True
    return structlog.get_logger()


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Preferred accessor: configures on first use, then returns a bound logger."""
    setup_logging()
    return structlog.get_logger(name) if name else structlog.get_logger()


logger = get_logger("salesiq")
