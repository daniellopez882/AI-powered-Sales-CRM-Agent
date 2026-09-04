"""
Shared pytest fixtures.

Every test runs against an explicit configuration so results do not depend on
whatever happens to be in the developer's real .env file.
"""

from __future__ import annotations

import os

import pytest

# Set before any application module is imported: config.settings builds its
# singleton at import time.
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("API_SECRET_KEY", "test-secret-key-not-a-real-one")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-placeholder")
os.environ.setdefault("USE_MOCK_INTEGRATIONS", "true")
os.environ.setdefault("LOG_LEVEL", "INFO")

TEST_API_KEY = os.environ["API_SECRET_KEY"]


@pytest.fixture(scope="session")
def api_key() -> str:
    return TEST_API_KEY


@pytest.fixture
def client():
    """FastAPI test client. Imported lazily so env vars above are applied."""
    from fastapi.testclient import TestClient

    from api.main import app, reset_graph

    reset_graph()
    with TestClient(app) as c:
        yield c
    reset_graph()


@pytest.fixture
def redis_url() -> str:
    return os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/15")


@pytest.fixture
def live_cache(redis_url):
    """
    A SalesIQCacher backed by a real Redis, or skip.

    The cache logging defect this suite regresses against was invisible without
    a reachable Redis, so these tests are explicitly skipped rather than
    silently passing when Redis is absent.
    """
    from integrations.cache import SalesIQCacher

    cacher = SalesIQCacher(url=redis_url)
    if not cacher.enabled:
        pytest.skip(f"no Redis at {redis_url}")
    cacher.redis.flushdb()
    yield cacher
    cacher.redis.flushdb()
