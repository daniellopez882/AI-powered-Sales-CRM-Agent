"""
agents/email_personalizer.py
EmailPersonalizer — writes hyper-personalized cold outreach emails.
Receives enriched lead from LeadEnricher and generates subject lines + body.
"""
from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
from agents.prompts import EMAIL_PERSONALIZER_PROMPT
from graph.state import CRMAgentState
from config.settings import settings
import logging
import json

logger = logging.getLogger(__name__)


class EmailPersonalizerAgent:
    def __init__(self, model_name: str = None):
        model = model_name or settings.default_model
        self.llm = ChatOpenAI(
            model=model,
            temperature=0.7,  # Higher temp for creative copy
            openai_api_key=settings.openai_api_key,
        )
        self.agent = Agent(
            role="EmailPersonalizer",
            goal="Draft hyper-personalized cold emails that get replies by proving genuine research.",
            backstory=(
                "You are SalesIQ's elite B2B copywriter. You have written cold emails that "
                "generated over $50M in qualified pipeline. You obsess over every word because "
                "you know: a bad first email destroys a perfectly good lead forever."
            ),
            verbose=False,
            allow_delegation=False,
            llm=self.llm,
        )

    def get_task(self, context: dict) -> Task:
        enriched = context.get("enriched_lead", {})
        product_desc = context.get("product_description", "a B2B SaaS solution")
        goal = context.get("campaign_goal", "schedule a discovery call")
        tone = context.get("tone_preference", "conversational")

        return Task(
            description=f"""
PROSPECT PROFILE (from LeadEnricher):
{json.dumps(enriched, indent=2)}

SENDER CONTEXT:
- Product/Service: {product_desc}
- Campaign Goal: {goal}
- Tone: {tone}

YOUR TASK — Follow THE PROVEN EMAIL FRAMEWORK exactly:

LINE 1 — THE HOOK (Most important)
  Reference something SPECIFIC and RECENT about THEM.
  Use the "why_now_trigger" and "recent_activity" from the enrichment data.
  NEVER start with "I", "We", "My name is", or empty flattery.

LINES 2–3 — THE BRIDGE
  Connect THEIR situation to ONE problem your product solves.
  Use their industry's own language. Be specific, not generic.

LINES 4–5 — THE VALUE PROPOSITION
  ONE specific, quantified outcome. Lead with a number.
  Reference a similar customer if possible.

LINE 6 — THE CTA
  ONE clear, low-friction ask. 
  Examples: "Worth a 15-min chat?" or "Want me to send a 2-min overview?"

QUALITY STANDARDS (verify before output):
  ✓ Total word count: 75–125 words MAX
  ✓ Does NOT start with "I" or "We"
  ✓ Zero filler phrases: "hope this finds you", "touching base", "synergy"
  ✓ Exactly ONE CTA
  ✓ At least 2 personalization elements from enrichment data
  ✓ No ALL CAPS, no excessive punctuation

SUBJECT LINES — Generate exactly 3:
  A) Curiosity-driven (reference their specific situation)
  B) Direct benefit (outcome-focused, with a number)
  C) Pattern interrupt (unexpected, stops the scroll)
  Rules: 6 words or fewer | No spam trigger words | Personalize naturally

Return ONLY a valid JSON object matching the defined OUTPUT FORMAT.
""",
            agent=self.agent,
            expected_output=(
                "A valid JSON object with keys: prospect_id, subject_lines, "
                "recommended_subject, email_body, word_count, personalization_elements, "
                "estimated_reply_rate, spam_score, quality_checklist_passed."
            ),
        )

    def run(self, context: dict) -> dict:
        logger.info("EmailPersonalizer starting")
        task = self.get_task(context)
        crew = Crew(
            agents=[self.agent],
            tasks=[task],
            process=Process.sequential,
            verbose=False,
        )
        return crew.kickoff()


# ── LangGraph node function ───────────────────────────────────────────────────

def email_personalizer_node(state: CRMAgentState, agent: EmailPersonalizerAgent) -> dict:
    """Named LangGraph node for EmailPersonalizer with input validation + error handling."""
    enriched_lead = state.get("enriched_lead")

    if not enriched_lead:
        logger.error("email_personalizer_node: no enriched_lead in state")
        return {
            "errors": state.get("errors", []) + ["EmailPersonalizer: Missing enriched lead. Run LeadEnricher first."],
            "requires_human": True,
        }

    context = {
        "enriched_lead": enriched_lead,
        "product_description": state.get("product_description"),
        "campaign_goal": state.get("campaign_goal"),
        "tone_preference": state.get("tone_preference"),
    }

    try:
        result = agent.run(context)
        return {
            "email_draft": result,
            "next_agent": "follow_up_scheduler",
            "data_sources": state.get("data_sources", []) + ["email_personalizer"],
        }
    except Exception as e:
        logger.error(f"EmailPersonalizer node failed: {e}", exc_info=True)
        return {
            "errors": state.get("errors", []) + [f"EmailPersonalizer failed: {str(e)}"],
            "requires_human": True,
        }
