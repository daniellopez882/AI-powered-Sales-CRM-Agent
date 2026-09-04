"""
api/main.py
SalesIQ HTTP API.

Security and operability changes over the previous revision:

* API keys are compared with ``secrets.compare_digest`` rather than ``!=``,
  which leaked key material through response timing.
* CORS origins come from configuration. The previous setting paired
  ``allow_origins=["*"]`` with ``allow_credentials=True`` -- a combination
  browsers reject outright -- and then sent an empty list in production,
  which blocked every browser client with no way to configure it.
* ``/ready`` probes dependencies. The old ``/health`` returned
  ``{"status": "healthy"}`` unconditionally, so an orchestrator would route
  traffic to an instance whose Redis and graph were both broken.
* 500 responses no longer echo the raw exception string back to the caller;
  they carry a correlation id that ties the response to a structured log line.
* The heavy ``graph.workflow`` import happens on first use, not at module
  import, so the process can serve ``/health`` and ``/metrics`` even when the
  agent stack is misconfigured.
"""

from __future__ import annotations

import secrets
import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.security import APIKeyHeader
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from config.settings import settings
from graph.state import get_initial_state
from observability.metrics import (
    AGENT_RUNS,
    ERRORS,
    REQUEST_LATENCY,
    REQUESTS,
    metrics_payload,
)
from utils.logging_config import get_logger

logger = get_logger("api")

API_VERSION = "v1"
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="SalesIQ AI Agent API",
    description="Autonomous B2B revenue engine built on LangGraph.",
    version="1.0.0",
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_default_dev_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins
    or ([] if settings.is_production else _default_dev_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["X-API-Key", "Content-Type", "X-Request-ID"],
)

_sales_graph = None


def get_graph():
    """Compile the LangGraph workflow once, on first use."""
    global _sales_graph
    if _sales_graph is None:
        # Imported late: this pulls in the whole agent/LLM stack.
        from graph.workflow import create_sales_graph

        settings.require_llm_credentials()
        logger.info("graph_compiling")
        _sales_graph = create_sales_graph()
        logger.info("graph_ready")
    return _sales_graph


def reset_graph() -> None:
    """Drop the compiled graph. Used by tests."""
    global _sales_graph
    _sales_graph = None


# ---------------------------------------------------------------- middleware
@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        ERRORS.labels(route=request.url.path, kind="unhandled").inc()
        logger.error("unhandled_error", request_id=request_id, path=request.url.path, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "Internal server error.",
                    "request_id": request_id,
                }
            },
            headers={"X-Request-ID": request_id},
        )
    REQUEST_LATENCY.labels(route=request.url.path).observe(time.perf_counter() - started)
    REQUESTS.labels(
        route=request.url.path, method=request.method, status=str(response.status_code)
    ).inc()
    response.headers["X-Request-ID"] = request_id
    return response


# ------------------------------------------------------------ authentication
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str | None = Depends(api_key_header)) -> str:
    """Constant-time API key check."""
    if not api_key or not secrets.compare_digest(api_key, settings.api_secret_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
            headers={"WWW-Authenticate": "X-API-Key"},
        )
    return api_key


# ------------------------------------------------------------------- schemas
class SalesRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128)
    session_id: str | None = Field(None, description="Existing session ID to resume")
    message: str = Field(..., min_length=1, max_length=4000)
    raw_lead: dict | None = None
    deal_data: list | None = None
    competitor_name: str | None = Field(None, max_length=128)
    product_description: str | None = Field(None, max_length=1000)
    campaign_goal: str | None = Field("demo", max_length=128)
    tone_preference: str | None = Field("conversational", max_length=64)

    @field_validator("message")
    @classmethod
    def sanitize_message(cls, v: str) -> str:
        # Strip C0/C1 control characters except tab and newline. They are a
        # common way to smuggle text past a prompt boundary or to corrupt log
        # output downstream.
        cleaned = "".join(c for c in v if c in "\t\n" or 0x20 <= ord(c) < 0x7F or ord(c) > 0x9F)
        cleaned = cleaned.strip()
        if not cleaned:
            raise ValueError("message must contain printable characters")
        return cleaned

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            uuid.UUID(v)
        except ValueError as exc:
            raise ValueError("session_id must be a UUID") from exc
        return v


class SalesResponse(BaseModel):
    session_id: str
    task_type: str
    confidence: float
    result: dict
    next_recommended_action: str
    requires_human: bool
    errors: list[str]


class HealthResponse(BaseModel):
    status: str
    environment: str
    version: str


# ------------------------------------------- operational endpoints (probes)
@app.get("/health", response_model=HealthResponse, tags=["ops"])
async def health() -> HealthResponse:
    """Liveness: the process is up. Deliberately touches no dependency."""
    return HealthResponse(status="healthy", environment=settings.environment, version=app.version)


@app.get("/ready", tags=["ops"])
async def ready() -> JSONResponse:
    """Readiness: probe everything needed to serve real traffic."""
    from integrations.cache import cache

    checks: dict[str, Any] = {
        "redis": {"ok": cache.ping(), "required": False},
        "llm_credentials": {
            "ok": bool(settings.openai_api_key or settings.anthropic_api_key),
            "required": True,
        },
        "api_secret": {
            "ok": not (settings.is_production and settings.has_insecure_secret),
            "required": True,
        },
        "graph_compiled": {"ok": _sales_graph is not None, "required": False},
    }
    ready_now = all(c["ok"] for c in checks.values() if c["required"])
    return JSONResponse(
        status_code=200 if ready_now else 503,
        content={"ready": ready_now, "checks": checks},
    )


@app.get("/metrics", tags=["ops"])
async def metrics() -> PlainTextResponse:
    """Prometheus exposition format."""
    body, content_type = metrics_payload()
    return PlainTextResponse(body, media_type=content_type)


@app.get("/", tags=["ops"])
async def root() -> dict:
    return {
        "service": "SalesIQ AI Agent API",
        "status": "online",
        "version": app.version,
        "api_base": f"/api/{API_VERSION}",
        "mode": "mock" if settings.is_mock_mode else "live",
    }


# ------------------------------------------------------------- versioned API
v1 = APIRouter(prefix=f"/api/{API_VERSION}", tags=["agent"])


@v1.post("/chat", response_model=SalesResponse, dependencies=[Depends(verify_api_key)])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def chat(request: Request, body: SalesRequest) -> SalesResponse:
    """Run a user message through the LangGraph orchestration workflow."""
    session_id = body.session_id or str(uuid.uuid4())
    request_id = getattr(request.state, "request_id", "-")
    log = logger.bind(session_id=session_id, request_id=request_id)
    log.info("request_received", user_id=body.user_id, is_resume=bool(body.session_id))

    state = get_initial_state(
        session_id=session_id,
        product_description=body.product_description,
        campaign_goal=body.campaign_goal,
        tone_preference=body.tone_preference,
    )
    state["messages"].append(HumanMessage(content=body.message))
    if body.raw_lead:
        state["raw_lead"] = body.raw_lead
    if body.deal_data:
        state["deal_data"] = body.deal_data
    if body.competitor_name:
        state["competitor_name"] = body.competitor_name

    started = time.perf_counter()
    try:
        graph = get_graph()
        final_state = await graph.ainvoke(state, config={"configurable": {"thread_id": session_id}})
    except RuntimeError as exc:
        # Misconfiguration (e.g. no LLM key) -> actionable, not a 500.
        ERRORS.labels(route="/api/v1/chat", kind="unconfigured").inc()
        log.error("graph_unconfigured", error=str(exc))
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        ERRORS.labels(route="/api/v1/chat", kind="graph_failure").inc()
        AGENT_RUNS.labels(outcome="error").inc()
        log.error("graph_execution_failed", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": "agent_pipeline_failed",
                "message": "The agent pipeline failed. Retry, or contact support with the request id.",
                "request_id": request_id,
            },
        ) from exc

    AGENT_RUNS.labels(outcome="success").inc()
    log.info(
        "request_complete",
        task_type=final_state.get("task_type"),
        duration_s=round(time.perf_counter() - started, 3),
    )

    return SalesResponse(
        session_id=session_id,
        task_type=final_state.get("task_type", "unknown"),
        confidence=final_state.get("confidence", 0.0),
        result={
            "enriched_lead": final_state.get("enriched_lead"),
            "email_draft": final_state.get("email_draft"),
            "sequence": final_state.get("sequence"),
            "deal_analysis": final_state.get("deal_analysis"),
            "pipeline_report": final_state.get("pipeline_report"),
            "competitor_battle_card": final_state.get("competitor_battle_card"),
        },
        next_recommended_action=final_state.get("next_recommended_action", ""),
        requires_human=final_state.get("requires_human", False),
        errors=final_state.get("errors", []),
    )


app.include_router(v1)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=not settings.is_production)
