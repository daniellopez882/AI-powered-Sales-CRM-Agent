"""
Tests for config.settings.

Pins the removal of a hardcoded absolute Windows path that was the default
DATABASE_URL, and the production guards that previously did not exist
(the old validate_production_settings() checked three integration keys and
ignored the placeholder API secret entirely).
"""

from __future__ import annotations

import pytest

from config.settings import INSECURE_SECRET, Settings, generate_secret


class TestDefaults:
    def test_no_machine_specific_path_in_database_url(self):
        """Regression: default was sqlite:///c:/Users/<name>/Desktop/..."""
        url = Settings().database_url
        assert "Users" not in url
        assert "Desktop" not in url
        assert url.startswith("sqlite:///")

    def test_database_default_is_anchored_to_repo(self):
        assert Settings().database_url.endswith("salesiq.db")

    def test_development_is_the_default_environment(self, monkeypatch):
        """True default, with the test harness's env overrides removed."""
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        assert Settings(_env_file=None).environment == "development"

    def test_app_loads_without_any_llm_key(self):
        """Import must not require credentials, or tests cannot run."""
        s = Settings(openai_api_key=None, anthropic_api_key=None)
        assert s.openai_api_key is None


class TestValidation:
    def test_invalid_log_level_is_rejected(self):
        with pytest.raises(ValueError, match="log_level"):
            Settings(log_level="chatty")

    def test_log_level_is_normalised_to_upper(self):
        assert Settings(log_level="debug").log_level == "DEBUG"

    def test_invalid_environment_is_rejected(self):
        with pytest.raises(ValueError):
            Settings(environment="prod")

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("https://a.com,https://b.com", ["https://a.com", "https://b.com"]),
            ("https://a.com , https://b.com ", ["https://a.com", "https://b.com"]),
            ("", []),
        ],
    )
    def test_cors_origins_accept_comma_separated_env_value(self, raw, expected):
        assert Settings(cors_allow_origins=raw).cors_allow_origins == expected


class TestLlmCredentialCheck:
    def test_raises_when_no_provider_configured(self):
        s = Settings(openai_api_key=None, anthropic_api_key=None)
        with pytest.raises(RuntimeError, match="No LLM provider"):
            s.require_llm_credentials()

    def test_passes_with_anthropic_only(self):
        Settings(openai_api_key=None, anthropic_api_key="sk-ant-x").require_llm_credentials()


class TestProductionGuards:
    """Production configuration must fail loudly at construction time."""

    def _prod(self, **kw):
        base = {
            "environment": "production",
            "api_secret_key": "a-real-secret",
            "openai_api_key": "sk-real",
            "use_mock_integrations": False,
            "cors_allow_origins": ["https://app.example.com"],
            "apollo_api_key": "k",
            "hubspot_access_token": "k",
            "slack_bot_token": "k",
        }
        base.update(kw)
        return Settings(**base)

    def test_valid_production_config_constructs(self):
        assert self._prod().is_production is True

    def test_placeholder_secret_is_rejected(self):
        with pytest.raises(ValueError, match="API_SECRET_KEY"):
            self._prod(api_secret_key=INSECURE_SECRET)

    def test_mock_integrations_in_production_are_rejected(self):
        with pytest.raises(ValueError, match="USE_MOCK_INTEGRATIONS"):
            self._prod(use_mock_integrations=True)

    def test_empty_cors_in_production_is_rejected(self):
        with pytest.raises(ValueError, match="CORS_ALLOW_ORIGINS"):
            self._prod(cors_allow_origins=[])

    def test_missing_llm_key_in_production_is_rejected(self):
        with pytest.raises(ValueError, match="LLM provider"):
            self._prod(openai_api_key=None, anthropic_api_key=None)

    def test_missing_integration_credentials_are_reported(self):
        with pytest.raises(ValueError, match="integration credentials"):
            self._prod(apollo_api_key=None)

    def test_development_does_not_enforce_production_rules(self, monkeypatch):
        """A placeholder secret is tolerated outside production."""
        monkeypatch.delenv("API_SECRET_KEY", raising=False)
        s = Settings(_env_file=None, environment="development")
        assert s.has_insecure_secret is True  # construction did not raise


class TestSecretHelper:
    def test_generated_secret_is_long_and_unique(self):
        a, b = generate_secret(), generate_secret()
        assert a != b and len(a) >= 32
