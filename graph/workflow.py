"""
graph/workflow.py
SalesIQ LangGraph StateGraph — the core orchestration engine.
All nodes are named functions with proper error handling (no anonymous lambdas).
"""
import functools
import logging
from langgraph.graph import StateGraph, END

from graph.state import CRMAgentState
from agents.orchestrator import SalesOrchestrator
from agents.lead_enricher import LeadEnricherAgent, lead_enricher_node
from agents.email_personalizer import EmailPersonalizerAgent, email_personalizer_node
from agents.follow_up_scheduler import FollowUpScheduler
from agents.deal_analyzer import DealAnalyzerAgent, deal_analyzer_node
from agents.pipeline_reporter import PipelineReporter
from agents.competitor_intel import CompetitorIntelAgent

logger = logging.getLogger(__name__)


# ── Named node wrappers for agents that don't yet have their own ──────────────

def follow_up_scheduler_node(state: CRMAgentState, agent: FollowUpScheduler) -> dict:
    """LangGraph node for FollowUpScheduler."""
    if not state.get("email_draft"):
        return {
            "errors": state.get("errors", []) + ["FollowUpScheduler: No email_draft in state."],
            "requires_human": True,
        }
    try:
        result = agent.process(state)
        return {
            **result,
            "data_sources": state.get("data_sources", []) + ["follow_up_scheduler"],
        }
    except Exception as e:
        logger.error(f"FollowUpScheduler failed: {e}", exc_info=True)
        return {
            "errors": state.get("errors", []) + [f"FollowUpScheduler failed: {str(e)}"],
            "requires_human": True,
        }


def pipeline_reporter_node(state: CRMAgentState, agent: PipelineReporter) -> dict:
    """LangGraph node for PipelineReporter."""
    deal_analysis = state.get("deal_analysis")
    if not deal_analysis:
        return {
            "errors": state.get("errors", []) + ["PipelineReporter: No deal_analysis in state."],
            "requires_human": True,
        }
    try:
        result = agent.process(deal_analysis)
        return {
            "pipeline_report": result,
            "data_sources": state.get("data_sources", []) + ["pipeline_reporter"],
        }
    except Exception as e:
        logger.error(f"PipelineReporter failed: {e}", exc_info=True)
        return {
            "errors": state.get("errors", []) + [f"PipelineReporter failed: {str(e)}"],
            "requires_human": True,
        }


def competitor_intel_node(state: CRMAgentState, agent: CompetitorIntelAgent) -> dict:
    """LangGraph node for CompetitorIntel."""
    context = {
        "competitor": state.get("competitor_name"),
        "enriched_lead": state.get("enriched_lead"),
    }
    if not context["competitor"]:
        return {
            "errors": state.get("errors", []) + ["CompetitorIntel: No competitor_name in state."],
            "requires_human": True,
        }
    try:
        result = agent.run(context)
        return {
            "competitor_battle_card": result,
            "next_agent": None,
            "data_sources": state.get("data_sources", []) + ["competitor_intel"],
        }
    except Exception as e:
        logger.error(f"CompetitorIntel failed: {e}", exc_info=True)
        return {
            "errors": state.get("errors", []) + [f"CompetitorIntel failed: {str(e)}"],
            "requires_human": True,
        }


# ── Router function ────────────────────────────────────────────────────────────

def route_from_orchestrator(state: CRMAgentState) -> str:
    """
    Conditional edge function — decides which agent node runs after orchestrator.
    Returns the node name to route to, or END.
    """
    if state.get("requires_human"):
        logger.info("Routing to END: human escalation required")
        return END

    if state.get("errors"):
        logger.warning(f"Routing to END: errors in state: {state['errors']}")
        return END

    next_agent = state.get("next_agent")
    valid_agents = {"lead_enricher", "email_personalizer", "deal_analyzer", "competitor_intel"}

    if next_agent in valid_agents:
        logger.info(f"Routing to: {next_agent} (confidence={state.get('confidence', 0):.2f})")
        return next_agent

    logger.info(f"No valid next_agent (got: {next_agent!r}), routing to END")
    return END


# ── Graph builder ─────────────────────────────────────────────────────────────

def create_sales_graph():
    """
    Build and compile the SalesIQ LangGraph StateGraph.
    All agents are instantiated once and bound into named node functions.
    Returns a compiled graph ready for .invoke() or .ainvoke().
    """
    # ── Instantiate all agents ──────────────────────────────
    orchestrator = SalesOrchestrator()
    lead_enricher = LeadEnricherAgent()
    email_personalizer = EmailPersonalizerAgent()
    follow_up_scheduler = FollowUpScheduler()
    deal_analyzer = DealAnalyzerAgent()
    pipeline_reporter = PipelineReporter()
    competitor_intel = CompetitorIntelAgent()

    # ── Bind agents into named node functions ───────────────
    # functools.partial binds the agent instance without anonymous lambdas
    _lead_enricher_node = functools.partial(lead_enricher_node, agent=lead_enricher)
    _email_personalizer_node = functools.partial(email_personalizer_node, agent=email_personalizer)
    _follow_up_scheduler_node = functools.partial(follow_up_scheduler_node, agent=follow_up_scheduler)
    _deal_analyzer_node = functools.partial(deal_analyzer_node, agent=deal_analyzer)
    _pipeline_reporter_node = functools.partial(pipeline_reporter_node, agent=pipeline_reporter)
    _competitor_intel_node = functools.partial(competitor_intel_node, agent=competitor_intel)

    # ── Build the graph ─────────────────────────────────────
    workflow = StateGraph(CRMAgentState)

    # Add all nodes
    workflow.add_node("orchestrator", orchestrator.process)
    workflow.add_node("lead_enricher", _lead_enricher_node)
    workflow.add_node("email_personalizer", _email_personalizer_node)
    workflow.add_node("follow_up_scheduler", _follow_up_scheduler_node)
    workflow.add_node("deal_analyzer", _deal_analyzer_node)
    workflow.add_node("pipeline_reporter", _pipeline_reporter_node)
    workflow.add_node("competitor_intel", _competitor_intel_node)

    # Entry point
    workflow.set_entry_point("orchestrator")

    # Orchestrator → conditional routing
    workflow.add_conditional_edges(
        "orchestrator",
        route_from_orchestrator,
        {
            "lead_enricher": "lead_enricher",
            "email_personalizer": "email_personalizer",
            "deal_analyzer": "deal_analyzer",
            "competitor_intel": "competitor_intel",
            END: END,
        },
    )

    # Fixed sequential edges within branches
    # Outreach branch: LeadEnricher → EmailPersonalizer → FollowUpScheduler
    workflow.add_edge("lead_enricher", "email_personalizer")
    workflow.add_edge("email_personalizer", "follow_up_scheduler")
    workflow.add_edge("follow_up_scheduler", END)

    # Analysis branch: DealAnalyzer → PipelineReporter
    workflow.add_edge("deal_analyzer", "pipeline_reporter")
    workflow.add_edge("pipeline_reporter", END)

    # Intel branch: CompetitorIntel → END
    workflow.add_edge("competitor_intel", END)

    return workflow.compile()
