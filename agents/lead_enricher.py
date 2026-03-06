from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
import os

class LeadEnricherAgent:
    def __init__(self, model_name: str = "gpt-4-turbo-preview"):
        self.llm = ChatOpenAI(model=model_name)
        self.agent = Agent(
            role="LeadEnricher",
            goal="Enrich raw leads into complete, actionable sales intelligence profiles.",
            backstory="""You are a world-class B2B intelligence specialist with 
deep expertise in sales prospecting and data enrichment. You excel at gathering 
company and contact intelligence to score leads against Ideal Customer Profiles (ICP).""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )

    def get_task(self, lead_data: dict):
        return Task(
            description=f"""
Given a raw lead: {lead_data}, enrich it into a 
complete, actionable sales intelligence profile.

## ENRICHMENT CHECKLIST
For every lead, gather and structure:

COMPANY INTELLIGENCE:
- Company name, industry, sub-vertical
- Employee count, revenue range (estimate if needed)
- Tech stack (BuiltWith data)
- Recent funding rounds or news (last 90 days)
- Key business challenges based on industry signals
- Primary competitors

CONTACT INTELLIGENCE:
- Full name, verified title, seniority level
- Direct email (verified) + LinkedIn URL
- Reporting structure (who they report to, who reports to them)
- Recent activity signals (job changes, posts, company news)
- Estimated decision-making authority (1-5 scale)

ICP SCORING:
Score this lead 1-10 against Ideal Customer Profile:
- Company size match
- Industry match  
- Tech stack compatibility
- Budget signals
- Timing signals (hiring, expansion, funding)

## RULES
- Mark every field as "verified" | "inferred" | "unavailable"
- Never fabricate email addresses
- If data is older than 6 months, flag as "stale"
- Always include a "why now" signal if found
""",
            agent=self.agent,
            expected_output="A structured JSON object containing complete lead enrichment data including company intelligence, contact intelligence, and ICP scoring."
        )

    def run(self, lead_data: dict):
        task = self.get_task(lead_data)
        crew = Crew(
            agents=[self.agent],
            tasks=[task],
            process=Process.sequential
        )
        return crew.kickoff()
