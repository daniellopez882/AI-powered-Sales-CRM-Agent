# ADR-002 — Checkpoint storage

- **Status:** Accepted for single-node; blocks horizontal scaling
- **Date:** 2026-09-03

## Problem

A sales cycle spans days. A user should be able to resume a session by
`session_id` after the process restarts, so graph state has to outlive memory.

## Alternatives considered

**In-memory only.** Zero setup, and every restart loses every session. Rejected.

**SQLite (`langgraph-checkpoint-sqlite`).** No service to run, no credentials,
one file. Works offline, which keeps the clone-and-run path honest.

**Postgres.** Concurrent writers, real connection pooling, survives replicas.
Costs a service dependency for what is currently a single-process app.

**Redis.** Already a dependency for caching. Rejected for checkpoints: the
cache is explicitly optional and disposable — it is configured with
`allkeys-lru` eviction — and eviction losing session state would be a silent
correctness bug rather than a cache miss.

## Decision

SQLite, at `CHECKPOINT_DB_PATH`, defaulting to a path anchored to the repo (and
to `/app/data` in the container, on a named volume).

The deciding factor is the first-run experience: `docker compose up` must work
with no external database. A reviewer who cannot start the project learns
nothing from its architecture.

## Consequences

Good:

- `git clone && docker compose up` works with no database setup.
- Sessions survive restarts and redeploys, given a persistent volume.
- Backup is a file copy.

Bad:

- **Multiple replicas against one SQLite file will corrupt state.** SQLite's
  locking does not survive concurrent writers over a shared volume. This caps
  the service at one instance.
- Writer throughput is serialised.
- No cross-region story.

## Migration trigger

Move to Postgres when any of these becomes true: a second replica is needed;
sustained write concurrency exceeds roughly 50 sessions/second; or a managed
backup and PITR story is required. `langgraph-checkpoint-postgres` implements
the same interface, so the change is a checkpointer swap plus a state migration,
not a rewrite. `psycopg2-binary` is already in `requirements.txt` in
anticipation.
