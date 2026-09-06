"""
integrations/cache.py
Redis cache for expensive enrichment lookups, with a safe no-op fallback.

Fixes carried in this revision:

* The module used a stdlib ``logging.Logger`` but called it with structlog's
  keyword style (``logger.info("cache_hit", key=key)``). At the application's
  default ``LOG_LEVEL=INFO`` that raises
  ``TypeError: Logger._log() got an unexpected keyword argument 'key'``, so
  every cache hit and every cache write crashed whenever Redis was reachable.
  It went unnoticed because ``info()`` short-circuits when the level is above
  INFO, and because CI never ran with a live Redis.
* The decorator read the cache key from ``args[0]``, so calling the wrapped
  method with a keyword argument raised ``IndexError``.
* Identifiers (emails, domains) were written into Redis keys verbatim. They
  are hashed now so PII does not sit in keyspace dumps or ``MONITOR`` output.
"""

from __future__ import annotations

import functools
import hashlib
import inspect
import json
from collections.abc import Callable
from typing import Any

from redis import Redis
from redis.exceptions import RedisError

from config.settings import settings
from utils.logging_config import get_logger

logger = get_logger(__name__)


def hash_identifier(value: Any) -> str:
    """Stable, non-reversible key fragment so PII stays out of Redis keys."""
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:32]


class SalesIQCacher:
    """Thin Redis wrapper that degrades to a no-op when Redis is unavailable."""

    def __init__(self, url: str | None = None, connect: bool = True) -> None:
        self.url = url or settings.redis_url
        self.redis: Redis | None = None
        self.enabled = False
        if connect:
            self.connect()

    def connect(self) -> bool:
        try:
            client = Redis.from_url(
                self.url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
                health_check_interval=30,
            )
            client.ping()
        except (RedisError, OSError, ValueError) as exc:
            logger.warning("cache_unavailable", url=self.url, error=str(exc))
            self.redis = None
            self.enabled = False
            return False
        self.redis = client
        self.enabled = True
        logger.info("cache_ready", url=self.url)
        return True

    def ping(self) -> bool:
        """Used by the readiness probe. Never raises."""
        if not self.redis:
            return False
        try:
            return bool(self.redis.ping())
        except (RedisError, OSError):
            self.enabled = False
            return False

    def get(self, key: str) -> Any | None:
        if not self.enabled or not self.redis:
            return None
        try:
            data = self.redis.get(key)
        except (RedisError, OSError) as exc:
            logger.error("cache_get_failed", key=key, error=str(exc))
            return None
        if data is None:
            logger.debug("cache_miss", key=key)
            return None
        try:
            value = json.loads(data)
        except json.JSONDecodeError as exc:
            logger.error("cache_corrupt_entry", key=key, error=str(exc))
            self.delete(key)
            return None
        logger.info("cache_hit", key=key)
        return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        if not self.enabled or not self.redis:
            return False
        ttl = ttl or settings.cache_ttl_seconds
        try:
            payload = json.dumps(value)
        except (TypeError, ValueError) as exc:
            logger.error("cache_serialize_failed", key=key, error=str(exc))
            return False
        try:
            self.redis.set(key, payload, ex=ttl)
        except (RedisError, OSError) as exc:
            logger.error("cache_set_failed", key=key, error=str(exc))
            return False
        logger.info("cache_set", key=key, ttl=ttl)
        return True

    def delete(self, key: str) -> bool:
        if not self.enabled or not self.redis:
            return False
        try:
            self.redis.delete(key)
            return True
        except (RedisError, OSError) as exc:
            logger.error("cache_delete_failed", key=key, error=str(exc))
            return False


cache = SalesIQCacher()


def cache_lead_enrichment(key_prefix: str) -> Callable:
    """
    Cache the result of a method whose first non-self parameter identifies
    the subject being enriched. Works with positional or keyword calls.
    """

    def decorator(func: Callable) -> Callable:
        sig = inspect.signature(func)
        params = [p for p in sig.parameters if p != "self"]
        if not params:
            raise TypeError(
                f"cache_lead_enrichment cannot wrap {func.__qualname__}: "
                "it takes no identifying argument."
            )
        id_param = params[0]

        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            bound = sig.bind_partial(self, *args, **kwargs)
            identifier = bound.arguments.get(id_param)
            if identifier is None:
                return func(self, *args, **kwargs)

            key = f"enrichment:{key_prefix}:{hash_identifier(identifier)}"
            cached = cache.get(key)
            if cached is not None:
                return cached

            result = func(self, *args, **kwargs)
            if result:
                cache.set(key, result)
            return result

        return wrapper

    return decorator
