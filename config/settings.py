"""
config/settings.py
Centralized configuration management using pydantic-settings.
All settings read from environment variables or .env file.
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os


class Settings(BaseSettings):
    # ── LLM Providers ─────────────────────────────────────
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    default_model: str = Field("gpt-4-turbo-preview", env="DEFAULT_MODEL")

    # ── External Integrations ─────────────────────────────
    apollo_api_key: Optional[str] = Field(None, env="APOLLO_API_KEY")
    hubspot_access_token: Optional[str] = Field(None, env="HUBSPOT_ACCESS_TOKEN")
    slack_bot_token: Optional[str] = Field(None, env="SLACK_BOT_TOKEN")
    gmail_client_secret_file: Optional[str] = Field(None, env="GMAIL_CLIENT_SECRET_FILE")

    # ── Application ───────────────────────────────────────
    api_secret_key: str = Field("changeme-in-production", env="API_SECRET_KEY")
    use_mock_integrations: bool = Field(True, env="USE_MOCK_INTEGRATIONS")
    environment: str = Field("development", env="ENVIRONMENT")  # development | staging | production
    log_level: str = Field("INFO", env="LOG_LEVEL")

    # ── Observability ─────────────────────────────────────
    sentry_dsn: Optional[str] = Field(None, env="SENTRY_DSN")
    langchain_tracing_v2: bool = Field(False, env="LANGCHAIN_TRACING_V2")
    langchain_api_key: Optional[str] = Field(None, env="LANGCHAIN_API_KEY")
    langchain_project: str = Field("salesiq-crm", env="LANGCHAIN_PROJECT")

    # ── Rate Limits ───────────────────────────────────────
    apollo_max_enrichments_per_hour: int = 50
    gmail_max_emails_per_day: int = 500
    linkedin_max_connections_per_day: int = 20

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_mock_mode(self) -> bool:
        return self.use_mock_integrations

    def validate_production_settings(self):
        """Called at startup in production to ensure all keys are present."""
        if self.is_production:
            required = ["apollo_api_key", "hubspot_access_token", "slack_bot_token"]
            missing = [k for k in required if not getattr(self, k)]
            if missing:
                raise ValueError(f"Missing required production env vars: {missing}")


# Singleton instance — import this everywhere
settings = Settings()
