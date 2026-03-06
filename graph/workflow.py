from langgraph.graph import StateGraph, END
from graph.state import CRMAgentState
from agents.orchestrator import SalesOrchestrator
from agents.lead_enricher import LeadEnricherAgent
from agents.email_personalizer import EmailPersonalizerAgent
from agents.follow_up_scheduler import FollowUpScheduler
from agents.deal_analyzer import DealAnalyzerAgent
from agents.pipeline_reporter import PipelineReporter

def create_sales_graph():
    # Initialize agents
    orchestrator = SalesOrchestrator()
    lead_enricher = LeadEnricherAgent()
    email_personalizer = EmailPersonalizerAgent()
    follow_up_scheduler = FollowUpScheduler()
    deal_analyzer = DealAnalyzerAgent()
    pipeline_reporter = PipelineReporter()

    # Define the graph
    workflow = StateGraph(CRMAgentState)

    # Add nodes
    workflow.add_node("orchestrator", orchestrator.process)
    
    # Lead Enrichment Branch
    workflow.add_node("lead_enricher", lambda state: {"enriched_lead": lead_enricher.run(state["raw_lead"]), "next_agent": "email_personalizer"})
    
    # Outreach Branch
    workflow.add_node("email_personalizer", lambda state: {"email_draft": email_personalizer.run(state), "next_agent": "follow_up_scheduler"})
    workflow.add_node("follow_up_scheduler", follow_up_scheduler.process)
    
    # Analysis Branch
    workflow.add_node("deal_analyzer", lambda state: {"deal_analysis": deal_analyzer.run(state.get("deal_data", [])), "next_agent": "pipeline_reporter"})
    workflow.add_node("pipeline_reporter", lambda state: pipeline_reporter.process(state.get("deal_analysis", {})))

    # Set entry point
    workflow.set_entry_point("orchestrator")

    # Add conditional edges from orchestrator
    def route_from_orchestrator(state: CRMAgentState):
        if state.get("requires_human"):
            return END
        next_agent = state.get("next_agent")
        if next_agent in ["lead_enricher", "email_personalizer", "deal_analyzer"]:
            return next_agent
        return END

    workflow.add_conditional_edges(
        "orchestrator",
        route_from_orchestrator,
        {
            "lead_enricher": "lead_enricher",
            "email_personalizer": "email_personalizer",
            "deal_analyzer": "deal_analyzer",
            END: END
        }
    )

    # Add simple sequence edges
    workflow.add_edge("lead_enricher", "email_personalizer")
    workflow.add_edge("email_personalizer", "follow_up_scheduler")
    workflow.add_edge("follow_up_scheduler", END)
    
    workflow.add_edge("deal_analyzer", "pipeline_reporter")
    workflow.add_edge("pipeline_reporter", END)

    return workflow.compile()

# Example usage
# app = create_sales_graph()
