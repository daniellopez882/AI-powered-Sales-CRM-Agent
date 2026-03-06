"""
api/main.py
SalesIQ FastAPI backend.
Includes: API key auth, request validation, rate limiting, proper error handling.
"""
import uuid
import logging
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from graph.workflow import create_sales_graph
from graph.state import get_initial_state
from config.settings import settings
from langchain_core.messages import HumanMessage
from utils.logging_config import logger

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# ── Rate Limiting ──────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

# ── App Bootstrap ──────────────────────────────────────────────────────────
app = FastAPI(
    title="SalesIQ AI Agent API",
    description="Autonomous B2B revenue engine powered by LangGraph + CrewAI",
    version="1.0.0",
    docs_url="/docs" if not settings.is_production else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if not settings.is_production else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy-init graph once at startup
_sales_graph = None

def get_graph():
    global _sales_graph
    if _sales_graph is None:
        logger.info("Initializing SalesIQ LangGraph workflow...")
        _sales_graph = create_sales_graph()
        logger.info("Graph compiled and ready.")
    return _sales_graph


# ── Authentication ─────────────────────────────────────────────────────────
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: Optional[str] = Depends(api_key_header)):
    if not api_key or api_key != settings.api_secret_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")
    return api_key


# ── Request / Response Models ──────────────────────────────────────────────
class SalesRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128)
    message: str = Field(..., min_length=1, max_length=4000)  # Prevent token bombs
    raw_lead: Optional[dict] = None
    deal_data: Optional[list] = None
    competitor_name: Optional[str] = Field(None, max_length=128)
    product_description: Optional[str] = Field(None, max_length=1000)
    campaign_goal: Optional[str] = Field("demo", max_length=128)
    tone_preference: Optional[str] = Field("conversational", max_length=64)

    @field_validator("message")
    @classmethod
    def sanitize_message(cls, v: str) -> str:
        # Strip control characters to reduce prompt injection risk
        return v.strip()


class SalesResponse(BaseModel):
    session_id: str
    task_type: str
    confidence: float
    result: dict
    next_recommended_action: str
    requires_human: bool
    errors: List[str]


# ── Endpoints ──────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "service": "SalesIQ AI Agent API",
        "status": "online",
        "version": "1.0.0",
        "mode": "mock" if settings.is_mock_mode else "live",
    }


@app.get("/health")
async def health():
    """Health check endpoint for load balancers / uptime monitors."""
    return {"status": "healthy", "environment": settings.environment}


@app.post("/chat", response_model=SalesResponse, dependencies=[Depends(verify_api_key)])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def chat(request: Request, body: SalesRequest):
    """
    Main SalesIQ agent endpoint.
    Accepts a user message + optional structured context.
    Routes through the LangGraph orchestration workflow.
    """
    session_id = str(uuid.uuid4())
    logger.info("new_request", session_id=session_id, user_id=body.user_id)

    state = get_initial_state(
        session_id=session_id,
        product_description=body.product_description,
        campaign_goal=body.campaign_goal,
        tone_preference=body.tone_preference,
    )

    # Populate state fields from request
    state["messages"].append(HumanMessage(content=body.message))
    if body.raw_lead:
        state["raw_lead"] = body.raw_lead
    if body.deal_data:
        state["deal_data"] = body.deal_data
    if body.competitor_name:
        state["competitor_name"] = body.competitor_name

    try:
        graph = get_graph()
        final_state = graph.invoke(state)

        logger.info("request_complete", session_id=session_id, task_type=final_state.get('task_type'))

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

    except Exception as e:
        logger.error("graph_execution_failed", session_id=session_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Agent pipeline failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=not settings.is_production)
