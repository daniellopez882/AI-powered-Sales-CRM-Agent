"""
agents/lead_enricher.py
LeadEnricher — B2B intelligence gathering agent.
Uses the real (or mock) Apollo integration via the factory.
The enrichment PROTOCOL lives in the Task description where CrewAI actually uses it.
"""
from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
from agents.prompts import LEAD_ENRICHER_PROMPT
from integrations import get_lead_provider
from graph.state import CRMAgentState
from config.settings import settings
import logging
import json
from integrations.cache import cache

logger = logging.getLogger(__name__)


class LeadEnricherAgent:
    def __init__(self, model_name: str = None):
        model = model_name or settings.default_model
        self.llm = ChatOpenAI(
            model=model,
            temperature=0.1,
            openai_api_key=settings.openai_api_key,
        )
        self.lead_provider = get_lead_provider()

        # NOTE: backstory = short biographical identity of this agent (CrewAI convention)
        # The full ENRICHMENT PROTOCOL belongs in Task.description, not here.
        self.agent = Agent(
            role="LeadEnricher",
            goal="Transform raw lead signals into complete, verified, ICP-scored B2B intelligence profiles.",
            backstory=(
                "You are SalesIQ's B2B intelligence specialist with 15 years mastering data sourcing, "
                "signal detection, and lead qualification. You are the gatekeeper of the pipeline — "
                "your output quality directly determines the success of every downstream agent."
            ),
            verbose=False,
            allow_delegation=False,
            llm=self.llm,
        )

    def get_task(self, lead_data: dict, pre_enriched: dict = None) -> Task:
        """
        Build the CrewAI Task with the full enrichment protocol in the description.
        pre_enriched: Data already fetched from real API (Apollo) to include as context.
        """
        api_context = ""
        if pre_enriched:
            api_context = f"\n\nADDITIONAL VERIFIED DATA FROM APOLLO API:\n{json.dumps(pre_enriched, indent=2)}"

        return Task(
            description=f"""
RAW LEAD INPUT:
{json.dumps(lead_data, indent=2)}
{api_context}

YOUR TASK — Follow the ENRICHMENT PROTOCOL exactly:

LAYER 1 — COMPANY INTELLIGENCE
Gather: company name, website, industry, sub-vertical, employee count, revenue range,
funding stage, last funding round, tech stack (from job postings/signals), 
recent company news (last 90 days), top 3 competitors, open job count.

LAYER 2 — CONTACT INTELLIGENCE
Gather: full name, verified title, seniority level, department, email (mark confidence),
LinkedIn URL, years in current role, decision-making authority score (1–5),
recent LinkedIn activity, previous 2 companies.

LAYER 3 — INTENT & TIMING SIGNALS
Identify ONE specific "Why Now" trigger from: recent funding, new role, 
hiring surge, competitor activity, fiscal year, product launch, negative press.
Map the buying committee: who else is involved in this decision?

LAYER 4 — ICP SCORING (Weighted Formula)
Score each dimension 1–10 and compute weighted average:
  Company size match      20%
  Industry match          20%
  Tech stack compat.      15%
  Budget/revenue signals  15%
  Seniority/authority     15%
  Timing/intent signals   15%

Priority thresholds: 8–10 = HOT 🔴 | 5–7 = WARM 🟡 | 1–4 = COLD 🔵

DATA QUALITY STANDARDS:
- Mark every field: ✅ VERIFIED | 🔶 INFERRED | ❓ UNAVAILABLE
- NEVER fabricate email addresses
- If data older than 6 months → append [STALE]
- If overall confidence < 55% → set requires_human_verification: true

Return ONLY a valid JSON object matching the defined OUTPUT FORMAT.
""",
            agent=self.agent,
            expected_output=(
                "A valid JSON object with keys: company, contact, intent_signals, "
                "icp_scoring, and data_quality. All fields confidence-tagged."
            ),
        )

    def run(self, lead_data: dict) -> dict:
        """
        1. Fetch real API data from Apollo (or mock).
        2. Pass both raw lead + API data to the LLM for deep enrichment.
        3. Return structured enrichment profile.
        """
        logger.info(f"LeadEnricher starting for: {lead_data.get('email', lead_data.get('company', 'unknown'))}")

        # Step 1: Get pre-enriched data (Check cache first)
        cache_key = f"enrichment:apollo:{lead_data.get('email', '')}"
        pre_enriched = cache.get(cache_key) if lead_data.get("email") else None

        if not pre_enriched and (email := lead_data.get("email")):
            try:
                pre_enriched = self.lead_provider.enrich_contact(email)
                if pre_enriched:
                    cache.set(cache_key, pre_enriched)
                logger.info("Apollo enrichment successful (live)")
            except Exception as e:
                logger.warning(f"Apollo enrichment failed, proceeding with LLM only: {e}")

        # Step 2: LLM deep enrichment
        task = self.get_task(lead_data, pre_enriched)
        crew = Crew(
            agents=[self.agent],
            tasks=[task],
            process=Process.sequential,
            verbose=False,
        )
        result = crew.kickoff()
        return result


# ── LangGraph node function (testable, named, with error handling) ────────────

def lead_enricher_node(state: CRMAgentState, agent: LeadEnricherAgent) -> dict:
    """
    Named LangGraph node for LeadEnricher. Replaces the anonymous lambda.
    Validates input, calls agent, handles errors, returns state update.
    """
    raw_lead = state.get("raw_lead")

    if not raw_lead:
        logger.error("lead_enricher_node called with no raw_lead in state")
        return {
            "errors": state.get("errors", []) + ["LeadEnricher: No raw_lead provided in state."],
            "requires_human": True,
        }

    try:
        result = agent.run(raw_lead)

        # Extract ICP score for top-level state field
        icp_data = {}
        if isinstance(result, dict):
            icp_data = result.get("icp_scoring", {})
        elif hasattr(result, "raw"):
            import json as _json
            try:
                parsed = _json.loads(result.raw)
                icp_data = parsed.get("icp_scoring", {})
                result = parsed
            except Exception:
                result = {"raw_output": str(result)}

        return {
            "enriched_lead": result,
            "icp_score": icp_data.get("total_score"),
            "priority": icp_data.get("priority"),
            "next_agent": "email_personalizer",
            "data_sources": state.get("data_sources", []) + ["lead_enricher"],
        }

    except Exception as e:
        logger.error(f"LeadEnricher node failed: {e}", exc_info=True)
        return {
            "errors": state.get("errors", []) + [f"LeadEnricher failed: {str(e)}"],
            "requires_human": True,
        }
