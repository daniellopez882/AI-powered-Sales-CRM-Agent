from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
from agents.prompts import DEAL_ANALYZER_PROMPT, build_agent_prompt

class DealAnalyzerAgent:
    def __init__(self, model_name: str = "gpt-4-turbo-preview"):
        self.llm = ChatOpenAI(model=model_name)
        self.agent = Agent(
            role="DealAnalyzer",
            goal="Analyze historical deals to extract actionable patterns that improve win rates.",
            backstory=build_agent_prompt(DEAL_ANALYZER_PROMPT),
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )

    def get_task(self, deal_data: list):
        return Task(
            description=f"Analyze these historical and active deals: {deal_data}. Follow the ANALYSIS FRAMEWORK to extract Won/Loss DNA and provide Predictive Scoring.",
            agent=self.agent,
            expected_output="A comprehensive analysis report in JSON format matching the defined OUTPUT FORMAT, including revenue forecast and risk flags."
        )

    def run(self, deal_data: list):
        task = self.get_task(deal_data)
        crew = Crew(
            agents=[self.agent],
            tasks=[task],
            process=Process.sequential
        )
        return crew.kickoff()
