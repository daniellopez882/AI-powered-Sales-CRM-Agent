"""
API behaviour tests.

These run against the real FastAPI app with the agent graph left uncompiled,
which is itself a property worth pinning: before the late-import change, the
service could not even start unless the entire LLM stack imported cleanly.
"""

from __future__ import annotations

import uuid
from typing import ClassVar

import pytest


class TestOperationalEndpoints:
    def test_health_is_live_without_dependencies(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"

    def test_health_does_not_require_auth(self, client):
        assert client.get("/health").status_code == 200

    def test_ready_reports_individual_checks(self, client):
        body = client.get("/ready").json()
        assert set(body["checks"]) >= {"redis", "llm_credentials", "api_secret", "graph_compiled"}

    def test_ready_distinguishes_required_from_optional(self, client):
        """Redis being down must not make the service unready."""
        checks = client.get("/ready").json()["checks"]
        assert checks["redis"]["required"] is False
        assert checks["llm_credentials"]["required"] is True

    def test_metrics_exposes_prometheus_format(self, client):
        r = client.get("/metrics")
        assert r.status_code == 200
        assert "salesiq_requests_total" in r.text

    def test_metrics_counts_requests(self, client):
        client.get("/health")
        assert "salesiq_requests_total{" in client.get("/metrics").text

    def test_root_advertises_the_api_base(self, client):
        assert client.get("/").json()["api_base"] == "/api/v1"


class TestRequestCorrelation:
    def test_response_carries_a_request_id(self, client):
        assert client.get("/health").headers.get("X-Request-ID")

    def test_supplied_request_id_is_echoed(self, client):
        rid = str(uuid.uuid4())
        r = client.get("/health", headers={"X-Request-ID": rid})
        assert r.headers["X-Request-ID"] == rid

    def test_generated_ids_are_unique(self, client):
        a = client.get("/health").headers["X-Request-ID"]
        b = client.get("/health").headers["X-Request-ID"]
        assert a != b


class TestAuthentication:
    ENDPOINT: ClassVar[str] = "/api/v1/chat"
    BODY: ClassVar[dict] = {"user_id": "u1", "message": "hello"}

    def test_missing_key_is_rejected(self, client):
        assert client.post(self.ENDPOINT, json=self.BODY).status_code == 401

    def test_wrong_key_is_rejected(self, client):
        r = client.post(self.ENDPOINT, headers={"X-API-Key": "nope"}, json=self.BODY)
        assert r.status_code == 401

    def test_rejection_names_the_scheme(self, client):
        r = client.post(self.ENDPOINT, json=self.BODY)
        assert r.headers.get("WWW-Authenticate") == "X-API-Key"

    def test_error_body_does_not_leak_the_expected_key(self, client, api_key):
        r = client.post(self.ENDPOINT, headers={"X-API-Key": "nope"}, json=self.BODY)
        assert api_key not in r.text


class TestRequestValidation:
    ENDPOINT = "/api/v1/chat"

    def _headers(self, api_key):
        return {"X-API-Key": api_key}

    def test_empty_message_is_rejected(self, client, api_key):
        r = client.post(
            self.ENDPOINT, headers=self._headers(api_key), json={"user_id": "u", "message": ""}
        )
        assert r.status_code == 422

    def test_oversized_message_is_rejected(self, client, api_key):
        r = client.post(
            self.ENDPOINT,
            headers=self._headers(api_key),
            json={"user_id": "u", "message": "x" * 4001},
        )
        assert r.status_code == 422

    def test_missing_user_id_is_rejected(self, client, api_key):
        r = client.post(self.ENDPOINT, headers=self._headers(api_key), json={"message": "hi"})
        assert r.status_code == 422

    def test_non_uuid_session_id_is_rejected(self, client, api_key):
        r = client.post(
            self.ENDPOINT,
            headers=self._headers(api_key),
            json={"user_id": "u", "message": "hi", "session_id": "../../etc/passwd"},
        )
        assert r.status_code == 422

    def test_valid_uuid_session_id_passes_validation(self, client, api_key):
        """Should get past validation (401/422 would mean it did not)."""
        r = client.post(
            self.ENDPOINT,
            headers=self._headers(api_key),
            json={"user_id": "u", "message": "hi", "session_id": str(uuid.uuid4())},
        )
        assert r.status_code not in (401, 422)

    @pytest.mark.parametrize(
        "payload,expected",
        [
            ("a\x00b", "ab"),
            ("a\x07b", "ab"),
            ("hi\x1bthere", "hithere"),
            ("keep\ttab", "keep\ttab"),
            ("  trim  ", "trim"),
        ],
    )
    def test_control_characters_are_stripped(self, payload, expected):
        """Asserted at the model, so it does not depend on the agent stack."""
        from api.main import SalesRequest

        assert SalesRequest(user_id="u", message=payload).message == expected

    def test_unicode_content_is_preserved(self):
        from api.main import SalesRequest

        assert SalesRequest(user_id="u", message="café 日本語 —").message == "café 日本語 —"

    def test_message_of_only_control_characters_is_rejected(self, client, api_key):
        r = client.post(
            self.ENDPOINT,
            headers=self._headers(api_key),
            json={"user_id": "u", "message": "\x00\x01\x02"},
        )
        assert r.status_code == 422


class TestErrorContract:
    def test_unconfigured_graph_returns_503_not_500(self, client, api_key, monkeypatch):
        """A missing credential is an operator problem, not a server fault."""
        import api.main as main

        monkeypatch.setattr(
            main,
            "get_graph",
            lambda: (_ for _ in ()).throw(RuntimeError("No LLM provider configured.")),
        )
        r = client.post(
            "/api/v1/chat", headers={"X-API-Key": api_key}, json={"user_id": "u", "message": "hi"}
        )
        assert r.status_code == 503

    def test_graph_failure_returns_correlation_id_not_a_stack_trace(
        self, client, api_key, monkeypatch
    ):
        import api.main as main

        secret_detail = "psycopg2 connection string postgres://user:hunter2@db/prod"
        monkeypatch.setattr(
            main, "get_graph", lambda: (_ for _ in ()).throw(ValueError(secret_detail))
        )
        r = client.post(
            "/api/v1/chat", headers={"X-API-Key": api_key}, json={"user_id": "u", "message": "hi"}
        )
        assert r.status_code == 500
        assert "hunter2" not in r.text, "internal error detail leaked to the client"
        assert r.json()["detail"]["request_id"]
