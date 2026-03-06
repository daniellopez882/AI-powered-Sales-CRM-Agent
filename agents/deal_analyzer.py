from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI

class DealAnalyzerAgent:
    def __init__(self, model_name: str = "gpt-4-turbo-preview"):
        self.llm = ChatOpenAI(model=model_name)
        self.agent = Agent(
            role="DealAnalyzer",
            goal="Analyze historical deals to extract actionable patterns that improve win rates.",
            backstory="""You are a revenue intelligence expert with deep 
expertise in win/loss analysis and sales pattern recognition. You think like a revenue scientist.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )

    def get_task(self, deal_data: list):
        return Task(
            description=f"""
Analyze these historical deals: {deal_data}

## ANALYSIS FRAMEWORK
WON DEAL PATTERNS: Company size, Industry, Cycle length, Decision makers, Objections overcome.
LOST DEAL PATTERNS: Stage of death, Stated objections, Competitor, Price sensitivity.

PREDICTIVE SCORING:
Calculate Win probability, Risk factors, Recommended actions, and Days to close.

## RULES
- Base analysis only on verifiable CRM data
- Minimum 10 deals needed for pattern analysis
- Clearly separate correlation from causation
- Flag data quality issues
""",
            agent=self.agent,
            expected_output="A comprehensive analysis report in JSON format including win/loss patterns, predictive scoring for active deals, and revenue forecast."
        )

    def run(self, deal_data: list):
        task = self.get_task(deal_data)
        crew = Crew(
            agents=[self.agent],
            tasks=[task],
            process=Process.sequential
        )
        return crew.kickoff()
