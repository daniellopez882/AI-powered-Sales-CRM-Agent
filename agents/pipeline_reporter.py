from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from agents.prompts import PIPELINE_REPORTER_PROMPT, build_agent_prompt
import json

class PipelineReporter:
    def __init__(self, model_name: str = "gpt-4-turbo-preview"):
        self.llm = ChatOpenAI(model=model_name)
        self.system_prompt = build_agent_prompt(PIPELINE_REPORTER_PROMPT)

    def process(self, pipeline_data: dict):
        message = HumanMessage(content=f"Generate a weekly report based on this data: {json.dumps(pipeline_data)}. Follow the REPORT STRUCTURE and provide MULTI-FORMAT OUTPUT.")
        response = self.llm.invoke([SystemMessage(content=self.system_prompt), message])
        
        return {
            "pipeline_report": response.content, # Matches the multi-format JSON structure
            "next_agent": None
        }
