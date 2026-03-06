from typing import TypedDict, List, Optional, Annotated
from langgraph.graph.message import add_messages
import datetime

class CRMAgentState(TypedDict):
    # Core
    messages: Annotated[list, add_messages]
    task_type: str
    
    # Lead data
    raw_lead: Optional[dict]
    enriched_lead: Optional[dict]
    icp_score: Optional[int]
    priority: Optional[str]
    
    # Outreach
    email_draft: Optional[dict]
    sequence: Optional[dict]
    
    # Analysis
    deal_analysis: Optional[dict]
    pipeline_report: Optional[dict]
    
    # Control flow
    next_agent: Optional[str]
    requires_human: bool
    confidence: float
    errors: List[str]
    
    # Metadata
    session_id: str
    timestamp: str
    data_sources: List[str]

def get_initial_state(session_id: str) -> CRMAgentState:
    return {
        "messages": [],
        "task_type": "",
        "raw_lead": None,
        "enriched_lead": None,
        "icp_score": None,
        "priority": None,
        "email_draft": None,
        "sequence": None,
        "deal_analysis": None,
        "pipeline_report": None,
        "next_agent": None,
        "requires_human": False,
        "confidence": 0.0,
        "errors": [],
        "session_id": session_id,
        "timestamp": datetime.datetime.now().isoformat(),
        "data_sources": []
    }
