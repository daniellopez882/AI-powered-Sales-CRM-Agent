"""
observability/metrics.py
Prometheus metrics for the SalesIQ service.

Counters and histograms are defined once, at module scope, against a private
registry so importing this module twice (or importing it from a test) does not
raise ``Duplicated timeseries in CollectorRegistry``.

Only operational signals are recorded here. Prompt text, lead payloads and
model output never become label values: label cardinality would explode and
the values would carry customer PII into the metrics store.
"""

from __future__ import annotations

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

REGISTRY = CollectorRegistry()

# ── HTTP ─────────────────────────────────────────────────────────────────────
REQUESTS = Counter(
    "salesiq_requests_total",
    "HTTP requests handled, by route, method and status.",
    ["route", "method", "status"],
    registry=REGISTRY,
)

REQUEST_LATENCY = Histogram(
    "salesiq_request_latency_seconds",
    "Wall-clock time to serve an HTTP request.",
    ["route"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
    registry=REGISTRY,
)

ERRORS = Counter(
    "salesiq_errors_total",
    "Errors, by route and error kind.",
    ["route", "kind"],
    registry=REGISTRY,
)

# ── Agent pipeline ───────────────────────────────────────────────────────────
AGENT_RUNS = Counter(
    "salesiq_agent_runs_total",
    "Completed agent pipeline runs, by outcome.",
    ["outcome"],  # success | error
    registry=REGISTRY,
)

AGENT_NODE_LATENCY = Histogram(
    "salesiq_agent_node_latency_seconds",
    "Execution time of an individual LangGraph node.",
    ["node"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
    registry=REGISTRY,
)

TOOL_CALLS = Counter(
    "salesiq_tool_calls_total",
    "External integration calls, by integration and outcome.",
    ["integration", "outcome"],
    registry=REGISTRY,
)

# ── LLM usage ────────────────────────────────────────────────────────────────
TOKENS_USED = Counter(
    "salesiq_tokens_total",
    "Tokens consumed, by model and direction.",
    ["model", "direction"],  # direction: prompt | completion
    registry=REGISTRY,
)

MODEL_FALLBACKS = Counter(
    "salesiq_model_fallbacks_total",
    "Times the primary model failed and a fallback was used.",
    ["primary", "fallback"],
    registry=REGISTRY,
)

# ── Cache ────────────────────────────────────────────────────────────────────
CACHE_EVENTS = Counter(
    "salesiq_cache_events_total",
    "Cache outcomes.",
    ["event"],  # hit | miss | set | error
    registry=REGISTRY,
)

CACHE_UP = Gauge(
    "salesiq_cache_up",
    "1 when Redis answered its last health check, 0 otherwise.",
    registry=REGISTRY,
)


def metrics_payload() -> tuple[bytes, str]:
    """Return the Prometheus exposition body and its content type."""
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
