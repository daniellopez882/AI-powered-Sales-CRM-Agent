from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from agents.prompts import FOLLOW_UP_SCHEDULER_PROMPT, build_agent_prompt
import json

class FollowUpScheduler:
    def __init__(self, model_name: str = "gpt-4-turbo-preview"):
        self.llm = ChatOpenAI(model=model_name)
        self.system_prompt = build_agent_prompt(FOLLOW_UP_SCHEDULER_PROMPT)

    def process(self, state: dict):
        # In a real LangGraph setup, 'state' would be the CRMAgentState
        context = {
            "enriched_lead": state.get("enriched_lead"),
            "email_draft": state.get("email_draft"),
            "engagement_signals": state.get("engagement_signals", {})
        }
        
        message = HumanMessage(content=f"Generate a behavioral follow-up sequence based on this context: {json.dumps(context)}")
        response = self.llm.invoke([SystemMessage(content=self.system_prompt), message])
        
        return {
            "sequence": response.content, # Matches the structure in prompts.py
            "next_agent": None
        }
