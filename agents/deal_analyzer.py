"""
agents/deal_analyzer.py
DealAnalyzer — revenue science engine.
Fetches real CRM data and performs Won/Lost DNA analysis + predictive scoring.
"""
from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
from agents.prompts import DEAL_ANALYZER_PROMPT
from integrations import get_crm_provider
from graph.state import CRMAgentState
from config.settings import settings
import logging
import json

logger = logging.getLogger(__name__)


class DealAnalyzerAgent:
    def __init__(self, model_name: str = None):
        model = model_name or settings.default_model
        self.llm = ChatOpenAI(
            model=model,
            temperature=0,   # Deterministic analysis
            openai_api_key=settings.openai_api_key,
        )
        self.crm_provider = get_crm_provider()
        self.agent = Agent(
            role="DealAnalyzer",
            goal="Extract data-driven patterns from CRM data to maximize win rates and forecast accuracy.",
            backstory=(
                "You are SalesIQ's revenue intelligence engine — part data scientist, part sales strategist. "
                "You turn CRM data into actionable pipeline insights, win/loss patterns, and AI-powered "
                "deal scoring that helps teams focus on deals that can actually close."
            ),
            verbose=False,
            allow_delegation=False,
            llm=self.llm,
        )

    def get_task(self, deal_data: list) -> Task:
        won = [d for d in deal_data if "won" in d.get("stage", "").lower()]
        lost = [d for d in deal_data if "lost" in d.get("stage", "").lower()]
        active = [d for d in deal_data if d.get("stage", "").lower() not in ("closed won", "closed lost")]

        return Task(
            description=f"""
CRM DEAL DATA:
Total deals: {len(deal_data)} | Won: {len(won)} | Lost: {len(lost)} | Active: {len(active)}

FULL DATASET:
{json.dumps(deal_data, indent=2)}

YOUR TASK — Run the full ANALYSIS FRAMEWORK:

MODULE A — WON DEAL DNA
From won deals, extract patterns:
- Most common company size, industry, funding stage
- Average sales cycle length (days) and ACV
- Most common champion title / seniority
- Number of stakeholders in won deals
- Tech stack signals correlated with wins

MODULE B — LOST DEAL AUTOPSY
From lost deals, calculate:
- Which pipeline stage has highest drop-off
- Loss reason taxonomy with % breakdown:
  Price | Competitor | No Budget | No Champion | Timing | Product Gap | Status Quo
- Identify the most common competitor wins
- Flag "recoverable" losses (Timing = yes, Product Gap = depends)

MODULE C — ACTIVE DEAL SCORING
For EVERY active deal, calculate:
- Base win probability from stage: 
  Prospecting=10% | Qualified=25% | Demo=40% | Proposal=60% | Negotiation=80%
- Adjust UP for: multi-stakeholder, recent activity, budget confirmed, ideal company size
- Adjust DOWN for: no activity 14+ days, single contact, budget unconfirmed, competitor engaged
- Assign risk flag: 🔴 CRITICAL | 🟡 MODERATE | 🟢 ON TRACK

MODULE D — REVENUE FORECAST (3 scenarios)
- Conservative: 70% of stated probability, confirmed close dates only
- Base Case: stated probabilities as-is
- Optimistic: 120% probability, include deals within 30-day buffer

DATA INTEGRITY:
- If fewer than 10 closed deals: flag small sample size warning
- Separate correlation from causation
- Flag any deals with missing critical fields

Return ONLY a valid JSON matching the defined OUTPUT FORMAT.
""",
            agent=self.agent,
            expected_output=(
                "A valid JSON with: analysis_period, deals_analyzed, overall_win_rate, "
                "won_deal_patterns, loss_reasons, active_deals_at_risk, revenue_forecast, "
                "icp_refinement_suggestions, playbook_updates_recommended, data_quality_warnings."
            ),
        )

    def run(self, deal_data: list = None) -> dict:
        """
        1. Fetch real deals from HubSpot (or mock).
        2. Run LLM analysis on the full dataset.
        """
        logger.info("DealAnalyzer starting")

        # Use provided data OR fetch from CRM
        if not deal_data:
            try:
                deal_data = self.crm_provider.get_deal_data()
                logger.info(f"Fetched {len(deal_data)} deals from CRM")
            except Exception as e:
                logger.error(f"CRM fetch failed: {e}")
                deal_data = []

        if not deal_data:
            return {"error": "No deal data available from CRM or state."}

        task = self.get_task(deal_data)
        crew = Crew(
            agents=[self.agent],
            tasks=[task],
            process=Process.sequential,
            verbose=False,
        )
        return crew.kickoff()


# ── LangGraph node function ───────────────────────────────────────────────────

def deal_analyzer_node(state: CRMAgentState, agent: DealAnalyzerAgent) -> dict:
    """Named LangGraph node for DealAnalyzer with error handling."""
    try:
        deal_data = state.get("deal_data")  # May be None — agent will fetch from CRM
        result = agent.run(deal_data)

        return {
            "deal_analysis": result,
            "next_agent": "pipeline_reporter",
            "data_sources": state.get("data_sources", []) + ["deal_analyzer", "hubspot"],
        }
    except Exception as e:
        logger.error(f"DealAnalyzer node failed: {e}", exc_info=True)
        return {
            "errors": state.get("errors", []) + [f"DealAnalyzer failed: {str(e)}"],
            "requires_human": True,
        }
