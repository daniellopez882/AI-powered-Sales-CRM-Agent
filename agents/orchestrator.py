"""
agents/orchestrator.py
SalesOrchestrator — the master controller node in the LangGraph StateGraph.
Uses Pydantic structured output to guarantee valid JSON routing decisions.
"""
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from typing import Optional, List
from graph.state import CRMAgentState
from agents.prompts import ORCHESTRATOR_PROMPT, build_agent_prompt
from config.settings import settings
import logging

logger = logging.getLogger(__name__)


# ── Pydantic schema for guaranteed structured output ──────────────────────────

class OrchestratorDecision(BaseModel):
    """Strict schema the LLM must conform to. No more json.loads() crashes."""
    task_type: str = Field(
        description="One of: enrichment | outreach | sequence | analysis | report | intel | unknown"
    )
    agents_invoked: List[str] = Field(
        default_factory=list,
        description="List of agent names to invoke, in order"
    )
    next_agent: Optional[str] = Field(
        None,
        description="The first specialist agent to route to: lead_enricher | email_personalizer | deal_analyzer | competitor_intel | pipeline_reporter"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence score between 0.0 and 1.0"
    )
    requires_human_review: bool = Field(
        False,
        description="True if any escalation trigger is met"
    )
    escalation_reason: Optional[str] = Field(
        None,
        description="Reason for human escalation if required"
    )
    next_recommended_action: str = Field(
        default="",
        description="Specific, actionable next step for the user"
    )


# ── Orchestrator Agent ────────────────────────────────────────────────────────

class SalesOrchestrator:
    def __init__(self, model_name: Optional[str] = None):
        model = model_name or settings.default_model
        # Bind the JSON schema to the LLM for guaranteed structured output
        base_llm = ChatOpenAI(
            model=model,
            temperature=0,  # Deterministic routing decisions
            openai_api_key=settings.openai_api_key,
        )
        self.llm = base_llm.with_structured_output(OrchestratorDecision)
        self.system_prompt = build_agent_prompt(ORCHESTRATOR_PROMPT)

    def process(self, state: CRMAgentState) -> dict:
        """
        LangGraph node function. Classifies the user request and sets routing.
        Returns partial state update — LangGraph merges this with existing state.
        """
        logger.info("Orchestrator processing", extra={
            "session_id": state.get("session_id"),
            "message_count": len(state.get("messages", [])),
        })

        try:
            messages = [SystemMessage(content=self.system_prompt)] + state["messages"]
            decision: OrchestratorDecision = self.llm.invoke(messages)

            logger.info("Orchestrator decision", extra={
                "task_type": decision.task_type,
                "next_agent": decision.next_agent,
                "confidence": decision.confidence,
                "requires_human": decision.requires_human_review,
            })

            return {
                "task_type": decision.task_type,
                "next_agent": decision.next_agent,
                "confidence": decision.confidence,
                "requires_human": decision.requires_human_review,
                "next_recommended_action": decision.next_recommended_action,
                "data_sources": state.get("data_sources", []) + ["orchestrator"],
            }

        except Exception as e:
            logger.error(f"Orchestrator failed: {e}", exc_info=True)
            return {
                "errors": state.get("errors", []) + [f"Orchestrator error: {str(e)}"],
                "requires_human": True,
                "confidence": 0.0,
                "next_recommended_action": "Human review required — orchestrator could not classify this request.",
            }
