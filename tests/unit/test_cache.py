"""
Regression tests for integrations.cache.

The defect these pin: the module held a stdlib ``logging.Logger`` but called it
with structlog's keyword style (``logger.info("cache_hit", key=key)``). At the
application's own default ``LOG_LEVEL=INFO`` that raises

    TypeError: Logger._log() got an unexpected keyword argument 'key'

so every cache read and every cache write failed the moment Redis became
reachable. It stayed hidden because ``Logger.info`` returns early when the
level is above INFO, and because no test ever ran with a live Redis.

The ``live_cache`` fixture therefore skips rather than passes when Redis is
absent -- a green run with no Redis proves nothing about this bug.
"""

from __future__ import annotations

import logging

import pytest

from integrations.cache import SalesIQCacher, cache_lead_enrichment, hash_identifier


class TestDegradedMode:
    """With no Redis the cache must be a silent no-op, never an exception."""

    def test_disabled_cache_reports_not_enabled(self):
        c = SalesIQCacher(connect=False)
        assert c.enabled is False

    def test_get_returns_none(self):
        assert SalesIQCacher(connect=False).get("any-key") is None

    def test_set_returns_false_and_does_not_raise(self):
        assert SalesIQCacher(connect=False).set("k", {"a": 1}) is False

    def test_ping_is_false_not_an_exception(self):
        assert SalesIQCacher(connect=False).ping() is False

    def test_unreachable_host_degrades_instead_of_raising(self):
        c = SalesIQCacher(url="redis://127.0.0.1:1/0")
        assert c.enabled is False
        assert c.get("k") is None


class TestLiveCache:
    """These exercise the code path that used to raise TypeError."""

    def test_set_then_get_roundtrip(self, live_cache, caplog):
        with caplog.at_level(logging.INFO):
            assert live_cache.set("lead:1", {"name": "Acme"}) is True
            assert live_cache.get("lead:1") == {"name": "Acme"}

    def test_cache_hit_at_info_level_does_not_raise(self, live_cache, caplog):
        """The exact regression: logging a hit at INFO used to be fatal."""
        live_cache.set("lead:2", {"x": 1})
        with caplog.at_level(logging.INFO):
            assert live_cache.get("lead:2") == {"x": 1}

    def test_miss_returns_none(self, live_cache):
        assert live_cache.get("definitely-absent") is None

    def test_ttl_is_applied(self, live_cache):
        live_cache.set("ttl-key", {"a": 1}, ttl=60)
        assert 0 < live_cache.redis.ttl("ttl-key") <= 60

    def test_corrupt_entry_is_evicted_and_reported_as_miss(self, live_cache):
        live_cache.redis.set("bad", "{not valid json")
        assert live_cache.get("bad") is None
        assert live_cache.redis.get("bad") is None, "corrupt entry should be deleted"

    def test_unserialisable_value_is_rejected_not_raised(self, live_cache):
        assert live_cache.set("obj", {"fn": lambda: 1}) is False


class TestKeyHashing:
    def test_identifier_is_not_stored_in_plaintext(self):
        assert "jane@acme.com" not in hash_identifier("jane@acme.com")

    def test_hash_is_stable(self):
        assert hash_identifier("a@b.com") == hash_identifier("a@b.com")

    def test_distinct_inputs_differ(self):
        assert hash_identifier("a@b.com") != hash_identifier("c@d.com")


class TestDecorator:
    """The old decorator read args[0] and broke on keyword calls."""

    def _make(self):
        class Service:
            calls = 0

            @cache_lead_enrichment("lead")
            def enrich(self, email, depth=1):
                Service.calls += 1
                return {"email": email, "depth": depth}

        return Service

    def test_positional_call_works(self):
        Service = self._make()
        assert Service().enrich("a@b.com")["email"] == "a@b.com"

    def test_keyword_call_works(self):
        """Regression: args[0] raised IndexError for a keyword call."""
        Service = self._make()
        assert Service().enrich(email="a@b.com")["email"] == "a@b.com"

    def test_wrapper_preserves_metadata(self):
        Service = self._make()
        assert Service.enrich.__name__ == "enrich"

    def test_second_call_is_served_from_cache(self, live_cache, monkeypatch):
        import integrations.cache as cache_mod

        monkeypatch.setattr(cache_mod, "cache", live_cache)
        Service = self._make()
        svc = Service()
        first = svc.enrich("hit@example.com")
        calls_after_first = Service.calls
        second = svc.enrich("hit@example.com")
        assert second == first
        assert Service.calls == calls_after_first, "second call should not re-execute"

    def test_undecoratable_function_is_rejected_at_definition(self):
        with pytest.raises(TypeError, match="no identifying argument"):

            class Bad:
                @cache_lead_enrichment("x")
                def no_args(self):
                    return 1
