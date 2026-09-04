# ADR-003 — One logging contract, and tests that can observe it

- **Status:** Accepted
- **Date:** 2026-09-03

## Problem

`integrations/cache.py` held a stdlib logger:

```python
logger = logging.getLogger(__name__)
```

and called it with structlog's keyword style:

```python
logger.info("cache_hit", key=key)
```

`logging.Logger.info` accepts only `exc_info`, `stack_info`, `stacklevel` and
`extra`. Anything else reaches `Logger._log()` and raises:

```
TypeError: Logger._log() got an unexpected keyword argument 'key'
```

So every cache hit and every cache write raised — but only sometimes:

1. `Logger.info` checks `isEnabledFor(INFO)` **before** touching kwargs. Above
   INFO the call returns before it can fail. The application's own default is
   `LOG_LEVEL=INFO`, so real deployments were in the failing range.
2. The failing lines are only reached when Redis is reachable. With Redis down
   the module degrades to a no-op and never logs a hit.

The result: enabling Redis, the feature meant to make the system faster, broke
every request that touched the cache. The repository had no tests at all, and
nothing in CI ran a Redis.

## Decision

**One logging contract.** Every module obtains its logger from
`utils.logging_config.get_logger()`, which returns a structlog `BoundLogger`.
Keyword-style event fields are correct everywhere; the stdlib style is not used.

**Tests that can observe the failure.** The `live_cache` fixture calls
`pytest.skip()` when Redis is unreachable rather than passing. A suite that
goes green with no Redis proves nothing about this class of bug.

**CI fails on skip.** The workflow runs a Redis service *and* asserts the cache
tests did not skip. Without that, losing the service container would silently
return the suite to proving nothing.

## Consequences

Good:

- The failure mode is now covered by tests that must run to pass.
- Structured fields survive to the JSON renderer instead of being interpolated
  into a message string.
- The same fix removed a second latent bug: the PII processor rewrote every
  string in the event dict, and its phone pattern matched ISO timestamps, so
  `timestamp` was being corrupted in production logs.

**Enforced by lint, not convention.** `logging.getLogger` is banned via ruff's
`TID251`, with `utils/logging_config.py` as the single exemption:

```toml
[tool.ruff.lint.flake8-tidy-imports.banned-api]
"logging.getLogger".msg = "Use utils.logging_config.get_logger() instead (ADR-003)."
```

This catches both `import logging; logging.getLogger(...)` and
`from logging import getLogger`. The five modules that still used stdlib
loggers (`agents/deal_analyzer`, `agents/email_personalizer`,
`agents/lead_enricher`, `agents/orchestrator`, `graph/workflow`) were migrated
when the rule went in, so the contract holds across the codebase rather than
just in the module where the bug was found.

Bad:

- Tests now need a Redis to be fully meaningful, so the local `make test`
  story depends on Docker (`make test-fast` skips those).
- The ban is on the symbol, not on the calling style. Someone could still
  obtain a structlog logger and format everything into one f-string, losing
  structure without tripping any rule.

## Wider lesson

Both defects were invisible to any test that did not exercise the dependency.
"The suite is green" and "the code works" diverge exactly where the tests stop
at the boundary. When a component degrades gracefully on failure, the degraded
path is the one that gets tested by default, and the working path is the one
that ships broken.
