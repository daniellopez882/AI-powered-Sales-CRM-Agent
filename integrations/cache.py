"""
integrations/cache.py
Redis caching layer for expensive API enrichment results.
Reduces latency and saves API credits.
"""
import json
import logging
from typing import Optional, Any
from redis import Redis
from config.settings import settings

logger = logging.getLogger(__name__)

class SalesIQCacher:
    def __init__(self):
        try:
            self.redis = Redis.from_url(settings.redis_url, decode_responses=True)
            # Test connection
            self.redis.ping()
            self.enabled = True
            logger.info(f"Redis cache initialized at {settings.redis_url}")
        except Exception as e:
            logger.warning(f"Redis not available, caching disabled: {e}")
            self.redis = None
            self.enabled = False

    def get(self, key: str) -> Optional[Any]:
        if not self.enabled:
            return None
        try:
            data = self.redis.get(key)
            if data:
                logger.info("cache_hit", key=key)
                return json.loads(data)
        except Exception as e:
            logger.error("cache_get_failed", key=key, error=str(e))
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        if not self.enabled:
            return
        try:
            ttl = ttl or settings.cache_ttl_seconds
            self.redis.set(key, json.dumps(value), ex=ttl)
            logger.info("cache_set", key=key, ttl=ttl)
        except Exception as e:
            logger.error("cache_set_failed", key=key, error=str(e))

# Singleton instance
cache = SalesIQCacher()

def cache_lead_enrichment(key_prefix: str):
    """Decorator for caching lead enrichment results."""
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            # First argument is usually the identifier (email/domain)
            key = f"enrichment:{key_prefix}:{args[0]}"
            cached = cache.get(key)
            if cached:
                return cached
            
            result = func(self, *args, **kwargs)
            if result:
                cache.set(key, result)
            return result
        return wrapper
    return decorator
