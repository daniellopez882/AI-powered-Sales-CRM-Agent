from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
from agents.prompts import COMPETITOR_INTEL_PROMPT, build_agent_prompt

class CompetitorIntelAgent:
    def __init__(self, model_name: str = "gpt-4-turbo-preview"):
        self.llm = ChatOpenAI(model=model_name)
        self.agent = Agent(
            role="CompetitorIntel",
            goal="Monitor the competitive landscape and arm the sales team with battle cards.",
            backstory=build_agent_prompt(COMPETITOR_INTEL_PROMPT),
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )

    def get_task(self, context: dict):
        return Task(
            description=f"Analyze the competitor: {context.get('competitor')}. Follow the COMPETITIVE ANALYSIS FRAMEWORK to build a Battle Card and historical win/loss baseline.",
            agent=self.agent,
            expected_output="A structured JSON object matching the defined OUTPUT FORMAT, including talking points, objection handling, and win/loss history."
        )

    def run(self, context: dict):
        task = self.get_task(context)
        crew = Crew(
            agents=[self.agent],
            tasks=[task],
            process=Process.sequential
        )
        return crew.kickoff()
