# 🤖 SalesIQ: The Autonomous Revenue Engine
### *The elite sales operations layer for B2B companies.*

[![License: ISC](https://img.shields.io/badge/License-ISC-blue.svg)](https://opensource.org/licenses/ISC)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-orange)](https://github.com/langchain-ai/langgraph)
[![CrewAI](https://img.shields.io/badge/Agents-CrewAI-red)](https://crewai.com)
[![MCP](https://img.shields.io/badge/Protocol-MCP-green)](https://modelcontextprotocol.io)

**SalesIQ** isn't just a CRM tool—it's a specialized revenue engine. Built on the **Model Context Protocol (MCP)** and powered by **LangGraph + CrewAI**, it automates the high-friction parts of the sales lifecycle, turning raw data into high-velocity pipeline.

---

## ✨ Why SalesIQ?
In the modern B2B landscape, speed and personalization are the only moats. SalesIQ provides a full autonomous crew that works 24/7 to:

*   **Eliminate Manual Research**: Complete lead profiles in seconds, not hours.
*   **Hyper-Personalize at Scale**: Emails that feel human because they *think* like experts.
*   **Predict Revenue with Science**: Move from "gut feeling" to data-driven win probabilities.
*   **Automate the "Follow-Up" Trap**: Behavioral sequences that build trust, not spam folders.

---

## 🧠 The Agentic Crew
SalesIQ orchestrates six elite AI agents, each a master of their domain:

| Agent | Mission | Specialization |
| :--- | :--- | :--- |
| **Orchestrator** | Supervisor | Task classification & recursive delegation. |
| **LeadEnricher** | Intelligence | Deep B2B data scraping & ICP scoring (1-10). |
| **EmailPersonalizer** | Copywriting | Proven hook-bridge-value-CTA frameworks. |
| **FollowUpScheduler** | Behavioral | Psychology-driven sequence triggers. |
| **DealAnalyzer** | Data Science | Win/Loss pattern recognition & risk flagging. |
| **PipelineReporter** | Executive | 90-second scannable summaries for leadership. |

---

## �️ The Technology Core
Built for performance and technical extensibility:

- **Stateful Orchestration**: LangGraph manages complex, circular sales workflows with total consistency.
- **MCP Integration**: Seamlessly connect to HubSpot, Apollo, LinkedIn, and Gmail via standardized tools.
- **Revenue Science**: Predictive algorithms calculate win probability and "Time-to-Close" based on historical CRM patterns.
- **Enterprise Guardrails**: GDPR/CAN-SPAM compliance baked into every agent's DNA.

---

## 📂 System Architecture
```text
sales-crm-agent/
├── agents/            # Specialized autonomous agents
├── mcp/               # Model Context Protocol server logic
├── graph/             # Stateful LangGraph workflow definitions
├── integrations/      # Sales tool connectors (HubSpot, Gmail, etc.)
├── api/               # FastAPI high-performance interface
└── dashboard/         # Real-time revenue monitoring
```

---

## � Deployment
### 1. Ready the Engine
```bash
git clone https://github.com/daniellopez882/AI-powered-Sales-CRM-Agent.git
cd AI-powered-Sales-CRM-Agent
pip install -r requirements.txt
```

### 2. Ignite the Agents
```bash
# Start the revenue API
python -m api.main

# Launch the MCP server
python -m mcp.server
```

---

## 🛡️ Guardrails & Ethics
We believe in **Human-in-the-Loop** AI. SalesIQ automatically escalates to a human operator when:
- Deal value exceeds **$50,000**.
- The contact is a **C-Suite executive** at a Fortune 500.
- Data confidence falls below **70%**.
- Legal or compliance keywords are detected in replies.

---

*Engineered by [Antigravity](https://github.com/antigravity) for the next generation of sales leaders.*
