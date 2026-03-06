"""
utils/logging_config.py
Structured logging configuration with PII masking and Sentry integration.
Uses structlog for JSON formatting in production.
"""
import logging
import sys
import re
from typing import Any, Dict
import structlog
from config.settings import settings

# ── PII Masking Patterns ──────────────────────────────────────────────
EMAIL_PATTERN = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+')
PHONE_PATTERN = re.compile(r'\+?\d{1,4}?[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}')

def mask_pii(value: Any) -> Any:
    """Masks emails and phone numbers in a string or nested structure."""
    if isinstance(value, str):
        # Mask emails: j***@domain.com
        def mask_email(match):
            email = match.group(0)
            user, domain = email.split('@')
            if len(user) > 1:
                return f"{user[0]}***@{domain}"
            return f"***@{domain}"
        
        value = EMAIL_PATTERN.sub(mask_email, value)
        # Mask phone numbers: +1***
        value = PHONE_PATTERN.sub(lambda m: f"{m.group(0)[:2]}***", value)
        return value
    elif isinstance(value, dict):
        return {k: mask_pii(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [mask_pii(i) for i in value]
    return value

def pii_masking_processor(logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """structlog processor that masks PII in the event dictionary."""
    return mask_pii(event_dict)

def setup_logging():
    """Sets up structured logging with PII masking and Sentry."""
    
    # ── Sentry Setup ──────────────────────────────────────────────
    if settings.sentry_dsn:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        
        sentry_logging = LoggingIntegration(
            level=logging.INFO,
            event_level=logging.ERROR
        )
        
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            integrations=[FastApiIntegration(), sentry_logging],
            traces_sample_rate=0.1 if settings.is_production else 1.0,
            environment=settings.environment,
        )

    # ── structlog Setup ───────────────────────────────────────────
    shared_processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        pii_masking_processor,
    ]

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Bridge standard logging
    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer() if settings.is_production else structlog.dev.ConsoleRenderer(),
        foreign_pre_processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            pii_masking_processor,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    # Configure root logger
    root_log = logging.getLogger()
    root_log.handlers = [handler]
    root_log.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    
    return structlog.get_logger()

# Singleton logger instance
logger = setup_logging()
