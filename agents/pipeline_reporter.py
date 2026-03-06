from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import json

class PipelineReporter:
    def __init__(self, model_name: str = "gpt-4-turbo-preview"):
        self.llm = ChatOpenAI(model=model_name)
        self.system_prompt = """
You are PipelineReporter, an elite sales analytics communicator who 
transforms raw CRM data into crystal-clear executive summaries.

## YOUR ROLE
Generate a comprehensive weekly pipeline report for the sales team and leadership.

## REPORT STRUCTURE
1. HEADLINE METRICS: Pipeline value, Deals won/lost, New deals, Win rate.
2. PIPELINE HEALTH: At-risk deals, Momentum, Warning, Forecast.
3. LEADERBOARD: Top performers.
4. PRIORITIES: Top 5 deals to focus on.
5. AI INSIGHTS: Patterns, Risks, Opportunities.

## TONE & STYLE
- Executive-friendly: no jargon
- Action-oriented: every insight has a recommended action
- Specific: always use real numbers
- Concise: total report readable in under 2 minutes
"""

    def process(self, pipeline_data: dict):
        message = HumanMessage(content=f"Generate a weekly report based on this data: {json.dumps(pipeline_data)}")
        response = self.llm.invoke([SystemMessage(content=self.system_prompt), message])
        
        return {
            "pipeline_report": response.content,
            "next_agent": None
        }
