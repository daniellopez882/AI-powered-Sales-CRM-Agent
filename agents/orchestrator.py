from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from graph.state import CRMAgentState
from agents.prompts import ORCHESTRATOR_PROMPT, build_agent_prompt
import json

class SalesOrchestrator:
    def __init__(self, model_name: str = "gpt-4-turbo-preview"):
        self.llm = ChatOpenAI(model=model_name)
        self.system_prompt = build_agent_prompt(ORCHESTRATOR_PROMPT)

    def process(self, state: CRMAgentState):
        messages = [SystemMessage(content=self.system_prompt)] + state["messages"]
        response = self.llm.invoke(messages)
        
        try:
            # Parse the JSON response from the LLM
            result = json.loads(response.content)
            
            return {
                "task_type": result.get("task_type", "unknown"),
                "next_agent": result.get("next_agent", result.get("agents_invoked", [None])[0]),
                "confidence": result.get("confidence", 0.0),
                "messages": [response],
                "requires_human": result.get("requires_human_review", False),
                "next_recommended_action": result.get("next_recommended_action", "")
            }
        except Exception as e:
            return {
                "errors": [f"Error in Orchestrator parsing: {str(e)}"],
                "requires_human": True,
                "messages": [response]
            }
