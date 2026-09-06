# Deployment

Covers running SalesIQ outside a developer laptop. The single-node constraint
in [ADR-002](adr/002-checkpoint-storage.md) applies: **do not run more than one
replica** against the SQLite checkpointer.

## Prerequisites

| Requirement | Notes |
|---|---|
| Docker 24+ with Compose v2 | Or any OCI runtime |
| An LLM provider key | `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` |
| Persistent volume | For `/app/data` — checkpoints and the SQLite DB live there |
| Redis 7 (optional) | Caching only; absence is not fatal |
| Vendor credentials | Apollo, HubSpot, Slack — required when `USE_MOCK_INTEGRATIONS=false` |

Read the [threat model](threat-model.md) before pointing this at a real CRM or
mail account. Tool authorisation and output validation are **not** implemented,
so a live deployment can act on injected instructions.

## Environment variables

Full list in [.env.example](../.env.example). Production requires all of:

```bash
ENVIRONMENT=production
API_SECRET_KEY=<32+ random bytes>        # `make secret`
OPENAI_API_KEY=<key>                     # or ANTHROPIC_API_KEY
USE_MOCK_INTEGRATIONS=false
CORS_ALLOW_ORIGINS=https://app.example.com
APOLLO_API_KEY=<key>
HUBSPOT_ACCESS_TOKEN=<token>
SLACK_BOT_TOKEN=<token>
REDIS_URL=redis://cache:6379/0
```

Missing or unsafe values are rejected **at startup**, with every problem listed
at once. The process exits rather than serving in a degraded state:

```
ValueError: Invalid production configuration:
  - API_SECRET_KEY is still the default placeholder. ...
  - USE_MOCK_INTEGRATIONS is true in production.
  - CORS_ALLOW_ORIGINS is empty; the API would reject all browser origins.
```

Generate the secret with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Store it in your platform's secret manager. Do not bake it into the image —
`.dockerignore` excludes `.env` precisely so it cannot be.

## Build

```bash
docker build -t salesiq-api:$(git rev-parse --short HEAD) .
```

The image is multi-stage: a builder installs into `/opt/venv`, and the runtime
stage copies only that venv. It runs as UID 1001 and declares a `HEALTHCHECK`
against `/health`.

Verify before shipping:

```bash
docker run --rm --entrypoint sh salesiq-api:<tag> -c 'id -un'   # must not print root
```

## Database and migrations

There is no migration system, because there is no relational schema. State is:

| Store | Path | Purpose |
|---|---|---|
| LangGraph checkpoints | `CHECKPOINT_DB_PATH` (`/app/data/checkpoints.sqlite`) | Session resumption |
| Application SQLite | `DATABASE_URL` (`/app/data/salesiq.db`) | Reserved; unused today |
| Redis | `REDIS_URL` | Cache only, fully disposable |

Both SQLite files are created on first use. **Mount `/app/data` on a persistent
volume** — otherwise every restart drops all sessions.

Back up by stopping the container and copying the directory, or by using
`sqlite3 checkpoints.sqlite ".backup /backup/checkpoints.sqlite"` for a
consistent online copy.

When you outgrow single-node, ADR-002 has the Postgres migration trigger and
path.

## Deploy with Compose

```bash
cp .env.example .env    # then fill it in
docker compose up -d --build
docker compose ps       # both services should read "healthy"
```

Compose waits for Redis to pass its healthcheck before starting the API, and
binds Redis to `127.0.0.1` only.

## Deploy to a container platform

The image is a plain stateless-ish web container; anything that runs OCI images
works. Requirements, whatever the platform:

1. One replica only (ADR-002).
2. A persistent volume at `/app/data`.
3. Secrets injected as environment variables, not baked in.
4. Liveness probe → `GET /health`; readiness probe → `GET /ready`.
5. `SIGTERM` handling: uvicorn is PID 1 and drains for up to 20s. Give the
   platform a termination grace period of at least 30s.

Fly.io, Railway and Render all satisfy this with a volume attached. Kubernetes
works but is hard to justify for a single-replica service — see the note in
ADR-002 before reaching for it.

## Health checks

| Endpoint | Meaning | On failure |
|---|---|---|
| `GET /health` | Process is alive. Touches no dependency. | Restart the container |
| `GET /ready` | Every required dependency is usable. `503` otherwise. | Stop routing traffic; do **not** restart |

`/ready` reports each check with a `required` flag. Redis is `required: false`
by design — a cache outage degrades performance, not correctness, and must not
take the service out of rotation.

```bash
curl -s localhost:8000/ready | python -m json.tool
```

## Observability

Scrape `GET /metrics`. A minimal Prometheus job:

```yaml
scrape_configs:
  - job_name: salesiq
    scrape_interval: 15s
    static_configs:
      - targets: ["salesiq-api:8000"]
```

Alerts worth having from day one:

| Alert | Expression sketch |
|---|---|
| Error rate | `rate(salesiq_errors_total[5m]) > 0.05 * rate(salesiq_requests_total[5m])` |
| Latency regression | `histogram_quantile(0.95, rate(salesiq_request_latency_seconds_bucket[5m])) > 10` |
| Agent failures | `rate(salesiq_agent_runs_total{outcome="error"}[10m]) > 0` |
| Readiness flapping | `probe_success{job="salesiq-ready"} == 0` |

Logs are JSON on stdout when `ENVIRONMENT=production`. Ship them with whatever
collects container stdout. Every line carries `request_id`; the same value is
returned to clients as `X-Request-ID`, so a user-reported failure maps to exact
log lines.

## Rollback

Images are immutable and tagged by commit, and no schema migration runs, so
rollback is redeploying the previous tag:

```bash
docker compose down
docker run -d ... salesiq-api:<previous-sha>
```

Checkpoint state is forward- and backward-compatible across these versions
because the state shape has not changed. **If you change `CRMAgentState`, this
stops being true** — a rolled-back binary may read a checkpoint containing keys
it does not understand. Version the state or purge checkpoints when that
happens.

## Troubleshooting

**Container exits immediately with `ValueError: Invalid production configuration`**
Working as intended. Read the listed problems; every one must be fixed.

**`/ready` returns 503 with `llm_credentials: {"ok": false}`**
Neither `OPENAI_API_KEY` nor `ANTHROPIC_API_KEY` reached the process. Check the
secret is actually injected: `docker exec <c> printenv | grep -c API_KEY`.

**`/api/v1/chat` returns 503 "No LLM provider configured"**
Same cause, reported at request time because the graph compiles lazily.

**`/api/v1/chat` returns 500 with a `request_id`**
The agent graph raised. The detail is deliberately not in the response; find it:
`docker logs <c> 2>&1 | grep <request_id>`.

**Everything returns 401**
`X-API-Key` must match `API_SECRET_KEY` exactly. The comparison is constant-time
and does not trim whitespace — a trailing newline from `$(cat secret)` is the
usual culprit.

**Requests return 429**
`RATE_LIMIT_PER_MINUTE` (default 10) is per client IP. Behind a proxy, every
request may appear to come from one address; forward the real client IP or
raise the limit.

**Cache appears to do nothing**
Check `/ready` → `redis.ok`. If false, the service is running uncached by
design. Confirm with `docker exec <redis> redis-cli ping`.

**Sessions lost after redeploy**
`/app/data` was not on a persistent volume.
