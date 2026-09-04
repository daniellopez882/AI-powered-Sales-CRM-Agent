"""
graph/state.py
Shared TypedDict state for the SalesIQ LangGraph workflow.
All agents read from and write to this single state object.
"""

import datetime
from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class CRMAgentState(TypedDict):
    # ── Core ──────────────────────────────────────────────
    messages: Annotated[list, add_messages]  # Full conversation history
    task_type: str  # Classified intent from Orchestrator

    # ── Lead Pipeline ─────────────────────────────────────
    raw_lead: dict | None  # Input: name/email/company/LinkedIn
    enriched_lead: dict | None  # After LeadEnricher runs
    icp_score: float | None  # 1.0–10.0
    priority: str | None  # HOT | WARM | COLD

    # ── Outreach ──────────────────────────────────────────
    email_draft: dict | None  # After EmailPersonalizer runs
    sequence: dict | None  # After FollowUpScheduler runs
    engagement_signals: dict | None  # Opened, clicked, replied signals

    # ── Deal Analysis ─────────────────────────────────────
    deal_data: list | None  # Raw deals from CRM
    deal_analysis: dict | None  # After DealAnalyzer runs
    pipeline_report: dict | None  # After PipelineReporter runs

    # ── Competitor Intel ──────────────────────────────────
    competitor_name: str | None  # Competitor being analyzed
    competitor_battle_card: dict | None  # After CompetitorIntel runs

    # ── Campaign Context ──────────────────────────────────
    product_description: str | None  # Sender's product/service info
    campaign_goal: str | None  # demo | call | trial | intro
    tone_preference: str | None  # formal | conversational | direct

    # ── Control Flow ──────────────────────────────────────
    next_agent: str | None  # Routing signal from Orchestrator
    requires_human: bool  # Human escalation flag
    confidence: float  # Orchestrator confidence score (0.0–1.0)
    next_recommended_action: str  # Suggested next step for the user
    errors: list[str]  # Accumulated error messages

    # ── Metadata ──────────────────────────────────────────
    session_id: str  # Unique session identifier
    timestamp: str  # ISO8601 creation timestamp
    data_sources: list[str]  # Which integrations were used


def get_initial_state(
    session_id: str,
    product_description: str | None = None,
    campaign_goal: str | None = "demo",
    tone_preference: str | None = "conversational",
) -> CRMAgentState:
    """
    Returns a fully initialized, empty CRMAgentState.
    Always use this factory function — never build the dict manually.
    """
    return {
        # Core
        "messages": [],
        "task_type": "",
        # Lead Pipeline
        "raw_lead": None,
        "enriched_lead": None,
        "icp_score": None,
        "priority": None,
        # Outreach
        "email_draft": None,
        "sequence": None,
        "engagement_signals": {},
        # Deal Analysis
        "deal_data": None,
        "deal_analysis": None,
        "pipeline_report": None,
        # Competitor Intel
        "competitor_name": None,
        "competitor_battle_card": None,
        # Campaign Context
        "product_description": product_description,
        "campaign_goal": campaign_goal,
        "tone_preference": tone_preference,
        # Control Flow
        "next_agent": None,
        "requires_human": False,
        "confidence": 0.0,
        "next_recommended_action": "",
        "errors": [],
        # Metadata
        "session_id": session_id,
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z"),
        "data_sources": [],
    }
