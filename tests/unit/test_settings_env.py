"""
Settings tests that go through the *environment*, not init kwargs.

Why this file exists separately from test_settings.py:

`test_settings.py` constructs `Settings(cors_allow_origins="a,b")`. That path
runs the field validator directly and passed happily. The environment path did
not: pydantic-settings JSON-decodes complex types (`list[str]`) inside
`EnvSettingsSource.prepare_field_value`, *before* any validator runs, so a
perfectly ordinary

    CORS_ALLOW_ORIGINS=https://app.example.com

raised `SettingsError: error parsing value for field "cors_allow_origins"` and
the container never started. The value shipped in `.env.example` had the same
shape, so local development was broken too.

The bug was found by running the built image, not by the suite. These tests
close that gap: every one of them sets a real environment variable.
"""

from __future__ import annotations

import pytest

from config.settings import Settings


def build(monkeypatch, **env) -> Settings:
    """Construct Settings purely from the environment, ignoring any .env file."""
    for key in ("CORS_ALLOW_ORIGINS", "ENVIRONMENT", "API_SECRET_KEY", "LOG_LEVEL"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return Settings(_env_file=None)


class TestCorsFromEnvironment:
    def test_single_origin(self, monkeypatch):
        """The exact value that broke the container."""
        s = build(monkeypatch, CORS_ALLOW_ORIGINS="https://app.example.com")
        assert s.cors_allow_origins == ["https://app.example.com"]

    def test_comma_separated(self, monkeypatch):
        s = build(monkeypatch, CORS_ALLOW_ORIGINS="https://a.com,https://b.com")
        assert s.cors_allow_origins == ["https://a.com", "https://b.com"]

    def test_whitespace_is_trimmed(self, monkeypatch):
        s = build(monkeypatch, CORS_ALLOW_ORIGINS="  https://a.com ,  https://b.com  ")
        assert s.cors_allow_origins == ["https://a.com", "https://b.com"]

    def test_json_array_still_supported(self, monkeypatch):
        s = build(monkeypatch, CORS_ALLOW_ORIGINS='["https://a.com","https://b.com"]')
        assert s.cors_allow_origins == ["https://a.com", "https://b.com"]

    def test_empty_string_yields_empty_list(self, monkeypatch):
        assert build(monkeypatch, CORS_ALLOW_ORIGINS="").cors_allow_origins == []

    def test_unset_yields_empty_list(self, monkeypatch):
        assert build(monkeypatch).cors_allow_origins == []

    def test_trailing_comma_is_ignored(self, monkeypatch):
        s = build(monkeypatch, CORS_ALLOW_ORIGINS="https://a.com,")
        assert s.cors_allow_origins == ["https://a.com"]

    def test_malformed_json_is_a_clear_error(self, monkeypatch):
        with pytest.raises(ValueError, match="looks like JSON but does not parse"):
            build(monkeypatch, CORS_ALLOW_ORIGINS="[not json")

    def test_json_object_is_rejected(self, monkeypatch):
        with pytest.raises(ValueError, match="must be an array"):
            build(monkeypatch, CORS_ALLOW_ORIGINS='{"origin": "https://a.com"}')


class TestDotEnvExampleIsUsable:
    """The shipped example must actually load; it previously did not."""

    def test_example_cors_value_parses(self, monkeypatch):
        import re
        from pathlib import Path

        example = Path(__file__).resolve().parents[2] / ".env.example"
        text = example.read_text(encoding="utf-8")
        match = re.search(r"^CORS_ALLOW_ORIGINS=(.*)$", text, re.M)
        assert match, "CORS_ALLOW_ORIGINS missing from .env.example"
        value = match.group(1).strip()
        s = build(monkeypatch, CORS_ALLOW_ORIGINS=value)
        assert s.cors_allow_origins, f"example value {value!r} parsed to an empty list"


class TestOtherScalarsFromEnvironment:
    def test_environment_is_read(self, monkeypatch):
        assert build(monkeypatch, ENVIRONMENT="staging").environment == "staging"

    def test_log_level_is_normalised(self, monkeypatch):
        assert build(monkeypatch, LOG_LEVEL="debug").log_level == "DEBUG"

    def test_invalid_environment_is_rejected(self, monkeypatch):
        with pytest.raises(ValueError):
            build(monkeypatch, ENVIRONMENT="prod")

    def test_boolean_is_coerced(self, monkeypatch):
        monkeypatch.setenv("USE_MOCK_INTEGRATIONS", "false")
        assert Settings(_env_file=None).use_mock_integrations is False
