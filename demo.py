from graph.workflow import create_sales_graph
from graph.state import get_initial_state
from langchain_core.messages import HumanMessage
import asyncio
import json

async def run_demo():
    print("🚀 Starting SalesIQ AI Agent Demo...")
    
    # Initialize the graph
    app = create_sales_graph()
    
    # 1. Test Lead Enrichment & Outreach
    print("\n--- Test 1: Lead Enrichment & Outreach ---")
    state_1 = get_initial_state("session_1")
    state_1["messages"].append(HumanMessage(content="Enrich the lead john@techcorp.com and draft a cold email."))
    state_1["raw_lead"] = {"email": "john@techcorp.com"}
    state_1["next_agent"] = "lead_enricher"
    
    # In a real run, the orchestrator would set the next_agent
    # Here we skip the orchestrator for direct node testing
    
    result_1 = app.invoke(state_1)
    print(f"Result: {json.dumps(result_1.get('email_draft'), indent=2)}")

    # 2. Test Pipeline Analysis
    print("\n--- Test 2: Pipeline Analysis ---")
    state_2 = get_initial_state("session_2")
    state_2["messages"].append(HumanMessage(content="Analyze my current pipeline and generate a report."))
    state_2["deal_data"] = [
        {"name": "Big Deal", "value": 100000, "stage": "Qualified"},
        {"name": "Small Deal", "value": 5000, "stage": "Closed Won"}
    ]
    state_2["next_agent"] = "deal_analyzer"
    
    result_2 = app.invoke(state_2)
    print(f"Report: {result_2.get('pipeline_report')}")

if __name__ == "__main__":
    asyncio.run(run_demo())
