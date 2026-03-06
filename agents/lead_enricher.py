from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
from agents.prompts import LEAD_ENRICHER_PROMPT, build_agent_prompt
import os

class LeadEnricherAgent:
    def __init__(self, model_name: str = "gpt-4-turbo-preview"):
        self.llm = ChatOpenAI(model=model_name)
        self.agent = Agent(
            role="LeadEnricher",
            goal="Enrich raw leads into complete, actionable sales intelligence profiles.",
            backstory=build_agent_prompt(LEAD_ENRICHER_PROMPT),
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )

    def get_task(self, lead_data: dict):
        return Task(
            description=f"Given a raw lead: {lead_data}, follow the ENRICHMENT PROTOCOL to gather company and contact intelligence, intent signals, and calculate the ICP score.",
            agent=self.agent,
            expected_output="A structured JSON object matching the defined OUTPUT FORMAT, containing verified and inferred data points."
        )

    def run(self, lead_data: dict):
        task = self.get_task(lead_data)
        crew = Crew(
            agents=[self.agent],
            tasks=[task],
            process=Process.sequential
        )
        return crew.kickoff()
