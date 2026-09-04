"""
benchmarks/bench.py
Reproducible microbenchmarks for the components on SalesIQ's hot paths.

Run:
    python benchmarks/bench.py                # all suites
    python benchmarks/bench.py --suite cache  # one suite
    python benchmarks/bench.py --json out.json

What is measured and what is deliberately not:

* Redis cache round-trip. This is the cost the cache *adds*; whether it is a
  net win depends on the latency of the upstream it replaces.
* HTTP overhead for the operational endpoints, which touch no LLM.
* PII masking throughput. It runs on every log record, so a slow
  implementation taxes the whole service.

Not measured here: end-to-end agent latency, token usage and cost. Those
require live LLM and vendor credentials, so any number produced without them
would be fabricated. See the Performance section of the README.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import sys
import time
from collections.abc import Callable

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("API_SECRET_KEY", "bench-secret")
os.environ.setdefault("OPENAI_API_KEY", "sk-bench-placeholder")


def measure(fn: Callable[[], object], n: int, warmup: int = 50) -> dict:
    """Run fn n times, return latency percentiles in milliseconds."""
    for _ in range(warmup):
        fn()
    samples: list[float] = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t0) * 1000.0)
    samples.sort()

    def pct(p: float) -> float:
        idx = min(len(samples) - 1, int(len(samples) * p))
        return round(samples[idx], 4)

    return {
        "n": n,
        "mean_ms": round(statistics.fmean(samples), 4),
        "p50_ms": pct(0.50),
        "p95_ms": pct(0.95),
        "p99_ms": pct(0.99),
        "min_ms": round(samples[0], 4),
        "max_ms": round(samples[-1], 4),
        "ops_per_sec": round(1000.0 / statistics.fmean(samples), 1),
    }


def bench_cache(n: int = 2000) -> dict:
    from integrations.cache import SalesIQCacher

    url = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/14")
    c = SalesIQCacher(url=url)
    if not c.enabled:
        return {"skipped": f"no Redis at {url}"}
    c.redis.flushdb()

    payload = {
        "name": "Sarah Chen",
        "title": "VP of Sales Operations",
        "company": "TechScale Inc.",
        "employee_count": 350,
        "tech_stack": ["Salesforce", "Outreach", "Gong", "Slack", "AWS"],
    }
    c.set("bench:hit", payload)

    out = {
        "payload_bytes": len(json.dumps(payload)),
        "set": measure(lambda: c.set("bench:set", payload), n),
        "get_hit": measure(lambda: c.get("bench:hit"), n),
        "get_miss": measure(lambda: c.get("bench:absent"), n),
    }
    c.redis.flushdb()
    return out


def bench_pii(n: int = 20000) -> dict:
    from utils.logging_config import mask_pii

    short = "lead jane.doe@acme.com called +1 415 555 0132"
    long_line = (
        "Enriched contact jane.doe@acme.com (VP Sales, TechScale Inc.), "
        "direct +1 415 555 0132, assistant +1 415 555 0199, "
        "recorded 2026-09-03T14:22:07Z on build v1.4.2 in 350ms"
    )
    nested = {"leads": [{"email": f"user{i}@example.com"} for i in range(10)]}
    return {
        "short_string": measure(lambda: mask_pii(short), n),
        "long_string": measure(lambda: mask_pii(long_line), n // 2),
        "nested_10_records": measure(lambda: mask_pii(nested), n // 10),
    }


def bench_http(n: int = 1000) -> dict:
    from fastapi.testclient import TestClient

    from api.main import app

    with TestClient(app) as c:
        return {
            "note": "in-process ASGI; excludes network and TLS",
            "health": measure(lambda: c.get("/health"), n),
            "ready": measure(lambda: c.get("/ready"), n // 2),
            "metrics": measure(lambda: c.get("/metrics"), n // 2),
            "chat_unauthenticated_401": measure(
                lambda: c.post("/api/v1/chat", json={"user_id": "u", "message": "hi"}), n // 2
            ),
        }


def bench_validation(n: int = 20000) -> dict:
    from api.main import SalesRequest

    return {
        "request_model_validation": measure(
            lambda: SalesRequest(user_id="u", message="Find me leads at TechScale"), n
        )
    }


SUITES: dict[str, Callable[[], dict]] = {
    "cache": bench_cache,
    "pii": bench_pii,
    "http": bench_http,
    "validation": bench_validation,
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--suite", choices=[*SUITES, "all"], default="all")
    ap.add_argument("--json", metavar="PATH", help="write results as JSON")
    args = ap.parse_args()

    env = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor() or "unknown",
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    chosen = SUITES if args.suite == "all" else {args.suite: SUITES[args.suite]}

    print("SalesIQ benchmarks")
    print(f"  python   {env['python']}")
    print(f"  platform {env['platform']}")
    print(f"  utc      {env['utc']}\n")

    results: dict = {"environment": env, "suites": {}}
    for name, fn in chosen.items():
        print(f"[{name}]")
        res = fn()
        results["suites"][name] = res
        for key, val in res.items():
            if isinstance(val, dict) and "p50_ms" in val:
                print(
                    f"  {key:<26} p50={val['p50_ms']:>8.4f}ms  p95={val['p95_ms']:>8.4f}ms  "
                    f"p99={val['p99_ms']:>8.4f}ms  {val['ops_per_sec']:>10,.0f} ops/s  (n={val['n']})"
                )
            else:
                print(f"  {key:<26} {val}")
        print()

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=2)
        print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
