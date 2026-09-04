# ADR-004 — Configuration and startup validation

- **Status:** Accepted
- **Date:** 2026-09-03

## Problem

The previous configuration had four distinct faults:

1. The default `DATABASE_URL` was
   `sqlite:///c:/Users/<name>/Desktop/AI-powered Sales CRM Agent/salesiq.db` —
   an absolute path from one developer's desktop. The project could not run
   anywhere else without an override, and the path leaked a username.
2. `openai_api_key` was a required field, so *importing* any module transitively
   touching settings raised without credentials present. Tests could not run.
3. `api_secret_key` defaulted to `"changeme-in-production"` and nothing checked
   it. Deploying with the default was silent, and that value authenticated
   every request.
4. `validate_production_settings()` existed but checked only three vendor keys,
   ignored the placeholder secret, and was never called from anywhere.

## Alternatives considered

**Validate on first use.** Cheap, but the failure surfaces on a user's request
rather than at deploy time, and only on the code path that happens to read the
bad value.

**Validate in the container entrypoint.** Catches deploys, misses local runs
and tests, and splits the rules between a shell script and Python.

**Validate at construction, gated on environment.** Wrong configuration cannot
produce a `Settings` object at all when `ENVIRONMENT=production`.

## Decision

A pydantic-settings v2 model with a `model_validator(mode="after")` that calls
`validate_production_settings()` when `environment == "production"`. It rejects,
with every problem listed at once:

- the placeholder `API_SECRET_KEY`
- no LLM provider key
- `USE_MOCK_INTEGRATIONS=true`
- empty `CORS_ALLOW_ORIGINS`
- missing Apollo / HubSpot / Slack credentials

Credentials are optional fields, so the app imports without them. Presence is
enforced at the boundary that needs them: `require_llm_credentials()` before the
graph compiles, and the production validator at construction.

On-disk defaults are derived from `BASE_DIR`, computed from `__file__`.

## Consequences

Good:

- A misconfigured production deploy fails immediately and loudly, listing every
  problem rather than one at a time.
- Tests and CI run without credentials.
- The repo is portable; no machine-specific paths.
- `/ready` reports the same checks, so an orchestrator can act on them.

Bad:

- Production config is strict enough to be annoying for a staging environment
  that legitimately wants mocks. `staging` is a separate environment value for
  exactly that reason, and is not subject to the production validator.
- Fail-fast means a single missing vendor key blocks startup entirely, even for
  request types that would never call that vendor. Accepted deliberately:
  discovering a missing credential at deploy time beats discovering it on a
  customer's request.
