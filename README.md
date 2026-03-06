# 🤖 SalesIQ: AI-Powered Sales CRM Agent

**SalesIQ** is a high-performance revenue engine built with LangGraph, CrewAI, and MCP. It automates the entire B2B sales lifecycle—from lead intelligence gathering and hyper-personalized outreach to behavioral follow-ups and deep pipeline analysis.

---

## 🚀 Key Features

- **LeadEnricher**: Autonomous B2B intelligence gathering (LinkedIn, Apollo, Clearbit).
- **EmailPersonalizer**: Generates irresistible cold outreach using proven sales psychology.
- **FollowUpScheduler**: Behavioral triggers for smart, non-pushy follow-up sequences.
- **DealAnalyzer**: Revenue science to extract win/loss patterns and predictive deal scoring.
- **PipelineReporter**: Scannable executive summaries delivered to Slack/Email.
- **MCP Native**: Extensible tool system via the Model Context Protocol.

---

## 🛠️ Technology Stack

| Component | Technology |
| :--- | :--- |
| **Agent Orchestration** | LangGraph + CrewAI |
| **LLM Framework** | LangChain |
| **Tools & APIs** | Model Context Protocol (MCP) |
| **API Backend** | FastAPI + Uvicorn |
| **Integrations** | Apollo, HubSpot, Gmail, Slack |
| **Data Flow** | Typed State Management |

---

## 📂 Project Structure

```text
sales-crm-agent/
├── agents/
│   ├── orchestrator.py      # LangGraph supervisor node
│   ├── lead_enricher.py     # CrewAI B2B specialist
│   ├── email_personalizer.py# Elite copywriter agent
│   ├── follow_up_scheduler.py# Psychology expert agent
│   ├── deal_analyzer.py     # Revenue scientist agent
│   └── pipeline_reporter.py # Executive communicator agent
├── mcp/
│   ├── server.py            # FastMCP server with sales tools
├── graph/
│   ├── state.py             # TypedDict CRMAgentState
│   └── workflow.py          # StateGraph construction
├── integrations/
│   └── mocks.py             # External API mock handlers
├── api/
│   └── main.py              # FastAPI endpoints
├── requirements.txt         # Project dependencies
└── README.md
```

---

## 🚦 Getting Started

### 1. Prerequisites
- Python 3.10+
- OpenAI API Key

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/your-repo/sales-crm-agent.git
cd sales-crm-agent

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration
Copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
```

### 4. Running the Agent
Start the FastAPI server:
```bash
python -m api.main
```

Start the MCP server (for Claude/LangChain consumption):
```bash
python -m mcp.server
```

---

## 🧠 Core Agent Logic: The Orchestrator

The `SalesOrchestrator` uses a specialized Decision Framework to classify tasks and delegate to the correct specialist. Every output includes:
- `task_type`: Classification
- `confidence`: AI certainty score (0.0 - 1.0)
- `next_agent`: Recommended next step in the flow
- `requires_human`: Flag for critical deals or ambiguous data

---

## 🛡️ Guardrails & Safety

- **Data Privacy**: Masking of PII in logs.
- **Compliance**: Built-in GDPR and CAN-SPAM logic.
- **Human-in-the-Loop**: Automatic escalation for deals > $50,000 or C-Suite contacts.
- **Rate Limiting**: Intelligent API throttling for HubSpot and Gmail.

---

*Built by [Antigravity](https://github.com/antigravity) for elite Sales Operations.*
