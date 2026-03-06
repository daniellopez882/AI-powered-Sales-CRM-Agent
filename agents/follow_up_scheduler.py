from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import json

class FollowUpScheduler:
    def __init__(self, model_name: str = "gpt-4-turbo-preview"):
        self.llm = ChatOpenAI(model=model_name)
        self.system_prompt = """
You are FollowUpScheduler, a behavioral sales psychology expert who 
designs intelligent follow-up sequences that feel helpful, not pushy.

## YOUR ROLE
Design a complete follow-up sequence for a prospect based on their 
enrichment profile, the initial email sent, and their engagement signals.

## SEQUENCE LOGIC — DECISION TREE
IF prospect opened email 3+ times but no reply → HIGH INTENT
IF prospect clicked a link → ENGAGED
IF no open after 48 hours → Try different subject line
IF reply received (positive) → Notify human
IF reply received (negative) → Graceful exit

## SEQUENCE TEMPLATE
Touch 1 (Day 0):   Initial personalized email
Touch 2 (Day 3):   Value-add
Touch 3 (Day 7):   Case study
Touch 4 (Day 14):  Different angle
Touch 5 (Day 21):  "Break up" email
Touch 6 (Day 60):  Nurture re-engage

## RULES
- Maximum 6 touches per sequence
- Always pause automation if human reply received
- LinkedIn touches should not mirror email content exactly
- Never send on Friday after 3pm or Monday before 10am
- Timezone-aware scheduling mandatory
"""

    def process(self, state: dict):
        # In a real LangGraph setup, 'state' would be the CRMAgentState
        context = {
            "enriched_lead": state.get("enriched_lead"),
            "email_draft": state.get("email_draft")
        }
        
        message = HumanMessage(content=f"Generate a follow-up sequence for this prospect: {json.dumps(context)}")
        response = self.llm.invoke([SystemMessage(content=self.system_prompt), message])
        
        return {
            "sequence": response.content, # Ideally parsed JSON
            "next_agent": None # End of this branch usually
        }
