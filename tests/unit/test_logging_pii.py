"""
Regression tests for utils.logging_config.

Two defects are pinned here:

1. ``setup_logging()`` raised ``TypeError`` because ``ProcessorFormatter`` was
   given ``foreign_pre_processors`` (the real parameter is
   ``foreign_pre_chain``). Since the module configured logging at import time,
   this made ``api.main`` unimportable.
2. The masking processor rewrote every string in the event dict with a phone
   pattern loose enough to match ISO timestamps, so ``timestamp`` and other
   structural fields were corrupted in the logs.
"""

from __future__ import annotations

import logging

import pytest

from utils.logging_config import (
    STRUCTURAL_KEYS,
    get_logger,
    mask_pii,
    pii_masking_processor,
    setup_logging,
)


class TestSetupLogging:
    def test_setup_logging_does_not_raise(self):
        """Regression: ProcessorFormatter got an invalid keyword argument."""
        assert setup_logging(force=True) is not None

    def test_importing_api_does_not_explode(self):
        """The whole app was unimportable while setup_logging() raised."""
        import api.main  # noqa: F401

    def test_structlog_keyword_style_works(self, caplog):
        log = get_logger("test.kwargs")
        with caplog.at_level(logging.INFO):
            log.info("event_name", key="value", count=3)


class TestEmailMasking:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("jane.doe@acme.com", "j***@acme.com"),
            ("contact a@b.io now", "contact a***@b.io now"),
            ("x@y.co and z@w.co", "x***@y.co and z***@w.co"),
        ],
    )
    def test_emails_are_masked(self, raw, expected):
        assert mask_pii(raw) == expected

    def test_local_part_is_not_recoverable(self):
        assert "jane.doe" not in mask_pii("jane.doe@acme.com")


class TestPhoneMasking:
    @pytest.mark.parametrize(
        "raw",
        ["+1 415 555 0132", "415-555-0132", "+44 20 7946 0958"],
    )
    def test_phone_numbers_are_masked(self, raw):
        masked = mask_pii(f"call {raw} today")
        assert raw not in masked
        assert "***" in masked

    @pytest.mark.parametrize(
        "raw",
        [
            "2026-09-03",  # ISO date
            "2026/09/03",  # slashed date
            "14:22:07",  # clock time
            "1.2.3",  # semantic version
            "3.14",  # decimal
            "12345",  # short id
        ],
    )
    def test_non_phone_digit_strings_are_left_alone(self, raw):
        """Regression: the old pattern masked dates, times and versions."""
        assert mask_pii(f"value {raw} here") == f"value {raw} here"


class TestStructuralFields:
    def test_timestamp_survives_masking(self):
        """Regression: masking corrupted the log's own timestamp field."""
        event = {"timestamp": "2026-09-03T14:22:07Z", "level": "info", "event": "hello"}
        assert pii_masking_processor(None, "info", event)["timestamp"] == "2026-09-03T14:22:07Z"

    def test_session_id_is_not_mangled(self):
        sid = "550e8400-e29b-41d4-a716-446655440000"
        out = pii_masking_processor(None, "info", {"session_id": sid, "event": "x"})
        assert out["session_id"] == sid

    def test_user_content_is_still_masked(self):
        out = pii_masking_processor(None, "info", {"event": "lead jane@acme.com"})
        assert "jane@acme.com" not in out["event"]

    def test_every_structural_key_is_passed_through(self):
        event = dict.fromkeys(STRUCTURAL_KEYS, "user@example.com")
        event["event"] = "user@example.com"
        out = pii_masking_processor(None, "info", event)
        for k in STRUCTURAL_KEYS:
            assert out[k] == "user@example.com", f"{k} should not be masked"
        assert out["event"] != "user@example.com"


class TestNestedStructures:
    def test_nested_dicts_and_lists_are_masked(self):
        payload = {"leads": [{"email": "a@b.com"}, {"email": "c@d.com"}]}
        out = mask_pii(payload)
        assert out["leads"][0]["email"] == "a***@b.com"
        assert out["leads"][1]["email"] == "c***@d.com"

    def test_non_string_scalars_pass_through(self):
        assert mask_pii({"n": 42, "f": 1.5, "b": True, "none": None}) == {
            "n": 42,
            "f": 1.5,
            "b": True,
            "none": None,
        }


class TestUvicornLoggerIntegration:
    """
    uvicorn installs its own handlers, so its access/error lines were emitted
    as plain text while application logs were JSON. Mixed formats defeat
    structured log ingestion.
    """

    def test_uvicorn_loggers_propagate_to_root(self):
        import logging as stdlib_logging

        setup_logging(force=True)
        for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
            lg = stdlib_logging.getLogger(name)  # noqa: TID251 - asserting stdlib state is the point
            assert lg.handlers == [], f"{name} still owns a handler"
            assert lg.propagate is True, f"{name} does not propagate to root"

    def test_root_has_exactly_one_handler(self):
        import logging as stdlib_logging

        setup_logging(force=True)
        root = stdlib_logging.getLogger()  # noqa: TID251 - asserting stdlib state is the point
        assert len(root.handlers) == 1
