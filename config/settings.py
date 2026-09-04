"""
config/settings.py
Centralized, typed configuration.

All values come from environment variables (or a local .env file). Nothing
machine-specific is baked in: the previous revision hardcoded an absolute
Windows path as the default DATABASE_URL, which made the app unrunnable
anywhere except the machine it was written on.
"""

from __future__ import annotations

import json
import secrets
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Repo root, used to anchor relative on-disk defaults.
BASE_DIR = Path(__file__).resolve().parent.parent

INSECURE_SECRET = "changeme-in-production"  # noqa: S105 - sentinel compared against, not a credential


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM providers ────────────────────────────────────────────────────────
    # Optional at import time so the app, its tests and `--help` can load
    # without credentials. Presence is enforced by require_llm_credentials()
    # at the point of first use, and by validate_production_settings().
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    default_model: str = "gpt-4o-mini"
    fallback_model: str | None = "claude-3-5-haiku-latest"
    llm_timeout_seconds: float = 30.0
    llm_max_retries: int = 2

    # ── External integrations ────────────────────────────────────────────────
    apollo_api_key: str | None = None
    hubspot_access_token: str | None = None
    slack_bot_token: str | None = None
    gmail_client_secret_file: str | None = None

    # ── Infrastructure ───────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    database_url: str = Field(
        default_factory=lambda: f"sqlite:///{(BASE_DIR / 'salesiq.db').as_posix()}"
    )
    checkpoint_db_path: str = Field(
        default_factory=lambda: (BASE_DIR / "checkpoints.sqlite").as_posix()
    )
    cache_ttl_seconds: int = 604_800  # 7 days

    # ── Application ──────────────────────────────────────────────────────────
    api_secret_key: str = INSECURE_SECRET
    use_mock_integrations: bool = True
    environment: Literal["development", "testing", "staging", "production"] = "development"
    log_level: str = "INFO"
    # NoDecode: pydantic-settings JSON-decodes complex types at the env source,
    # before any validator runs, so a plain `CORS_ALLOW_ORIGINS=https://a.com`
    # raised SettingsError. NoDecode hands the raw string to _split_origins.
    cors_allow_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)

    # ── Observability ────────────────────────────────────────────────────────
    sentry_dsn: str | None = None
    langchain_tracing_v2: bool = False
    langchain_api_key: str | None = None
    langchain_project: str = "salesiq-crm"

    # ── Rate limits ──────────────────────────────────────────────────────────
    rate_limit_per_minute: int = 10
    apollo_max_enrichments_per_hour: int = 50
    gmail_max_emails_per_day: int = 500
    linkedin_max_connections_per_day: int = 20

    @field_validator("log_level")
    @classmethod
    def _upper_log_level(cls, v: str) -> str:
        v = v.upper()
        allowed = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"}
        if v not in allowed:
            raise ValueError(f"log_level must be one of {sorted(allowed)}, got {v!r}")
        return v

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def _split_origins(cls, v):
        """
        Accept a comma-separated string, a JSON array, or a real list.

        The field is annotated NoDecode, so pydantic-settings hands the raw
        environment string here instead of trying (and failing) to json.loads
        it at the source. Both shapes are supported so an existing JSON-style
        value keeps working.
        """
        if not isinstance(v, str):
            return v
        raw = v.strip()
        if not raw:
            return []
        if raw.startswith("{"):
            raise ValueError("CORS_ALLOW_ORIGINS JSON value must be an array, not an object")
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"CORS_ALLOW_ORIGINS looks like JSON but does not parse: {exc}"
                ) from exc
            if not isinstance(parsed, list):
                raise ValueError("CORS_ALLOW_ORIGINS JSON value must be an array")
            return [str(o).strip() for o in parsed if str(o).strip()]
        return [o.strip() for o in raw.split(",") if o.strip()]

    @model_validator(mode="after")
    def _guard_production(self) -> Settings:
        if self.environment == "production":
            self.validate_production_settings()
        return self

    # ── Derived properties ───────────────────────────────────────────────────
    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_mock_mode(self) -> bool:
        return self.use_mock_integrations

    @property
    def has_insecure_secret(self) -> bool:
        return self.api_secret_key == INSECURE_SECRET

    # ── Explicit checks ──────────────────────────────────────────────────────
    def require_llm_credentials(self) -> None:
        """Raise if no LLM provider is configured. Call before building agents."""
        if not (self.openai_api_key or self.anthropic_api_key):
            raise RuntimeError(
                "No LLM provider configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY."
            )

    def validate_production_settings(self) -> None:
        """Fail fast on unsafe or incomplete production configuration."""
        problems: list[str] = []

        if self.has_insecure_secret:
            problems.append(
                "API_SECRET_KEY is still the default placeholder. "
                'Generate one with: python -c "import secrets;print(secrets.token_urlsafe(32))"'
            )
        if not (self.openai_api_key or self.anthropic_api_key):
            problems.append("No LLM provider key set (OPENAI_API_KEY or ANTHROPIC_API_KEY).")
        if self.use_mock_integrations:
            problems.append("USE_MOCK_INTEGRATIONS is true in production.")
        if not self.cors_allow_origins:
            problems.append(
                "CORS_ALLOW_ORIGINS is empty; the API would reject all browser origins."
            )

        missing = [
            name
            for name in ("apollo_api_key", "hubspot_access_token", "slack_bot_token")
            if not getattr(self, name)
        ]
        if missing:
            problems.append(f"Missing integration credentials: {missing}")

        if problems:
            raise ValueError("Invalid production configuration:\n  - " + "\n  - ".join(problems))


def generate_secret() -> str:
    """Convenience helper used by docs and the Makefile."""
    return secrets.token_urlsafe(32)


settings = Settings()
