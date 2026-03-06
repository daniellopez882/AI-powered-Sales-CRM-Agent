"""
graph/state.py
Shared TypedDict state for the SalesIQ LangGraph workflow.
All agents read from and write to this single state object.
"""
from typing import TypedDict, List, Optional, Annotated
from langgraph.graph.message import add_messages
import datetime


class CRMAgentState(TypedDict):
    # ── Core ──────────────────────────────────────────────
    messages: Annotated[list, add_messages]  # Full conversation history
    task_type: str                           # Classified intent from Orchestrator

    # ── Lead Pipeline ─────────────────────────────────────
    raw_lead: Optional[dict]                 # Input: name/email/company/LinkedIn
    enriched_lead: Optional[dict]            # After LeadEnricher runs
    icp_score: Optional[float]              # 1.0–10.0
    priority: Optional[str]                 # HOT | WARM | COLD

    # ── Outreach ──────────────────────────────────────────
    email_draft: Optional[dict]              # After EmailPersonalizer runs
    sequence: Optional[dict]                # After FollowUpScheduler runs
    engagement_signals: Optional[dict]      # Opened, clicked, replied signals

    # ── Deal Analysis ─────────────────────────────────────
    deal_data: Optional[list]               # Raw deals from CRM
    deal_analysis: Optional[dict]           # After DealAnalyzer runs
    pipeline_report: Optional[dict]         # After PipelineReporter runs

    # ── Competitor Intel ──────────────────────────────────
    competitor_name: Optional[str]          # Competitor being analyzed
    competitor_battle_card: Optional[dict]  # After CompetitorIntel runs

    # ── Campaign Context ──────────────────────────────────
    product_description: Optional[str]     # Sender's product/service info
    campaign_goal: Optional[str]           # demo | call | trial | intro
    tone_preference: Optional[str]         # formal | conversational | direct

    # ── Control Flow ──────────────────────────────────────
    next_agent: Optional[str]              # Routing signal from Orchestrator
    requires_human: bool                   # Human escalation flag
    confidence: float                      # Orchestrator confidence score (0.0–1.0)
    next_recommended_action: str           # Suggested next step for the user
    errors: List[str]                      # Accumulated error messages

    # ── Metadata ──────────────────────────────────────────
    session_id: str                        # Unique session identifier
    timestamp: str                         # ISO8601 creation timestamp
    data_sources: List[str]               # Which integrations were used


def get_initial_state(
    session_id: str,
    product_description: Optional[str] = None,
    campaign_goal: Optional[str] = "demo",
    tone_preference: Optional[str] = "conversational",
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
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "data_sources": [],
    }
