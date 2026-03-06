from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from graph.workflow import create_sales_graph
from graph.state import get_initial_state
import uuid

app = FastAPI(title="SalesIQ AI Agent API")
sales_graph = create_sales_graph()

class SalesRequest(BaseModel):
    user_id: str
    message: str
    context: Optional[dict] = {}

class SalesResponse(BaseModel):
    session_id: str
    result: dict
    next_steps: List[str]

@app.get("/")
async def root():
    return {"message": "SalesIQ CRM AI Agent is online"}

@app.post("/chat", response_model=SalesResponse)
async def chat(request: SalesRequest):
    session_id = str(uuid.uuid4())
    state = get_initial_state(session_id)
    
    # Add user message to state
    from langchain_core.messages import HumanMessage
    state["messages"].append(HumanMessage(content=request.message))
    
    # Process through the graph
    try:
        final_state = sales_graph.invoke(state)
        
        return SalesResponse(
            session_id=session_id,
            result=final_state,
            next_steps=["Check lead enrichment", "Review email draft"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
