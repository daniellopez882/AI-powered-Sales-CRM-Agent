<div align="center">

# ⚡ SalesIQ
### The Autonomous Revenue Engine for Elite B2B Teams.

*Stop managing your CRM. Let your CRM manage your pipeline.*

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-Orchestration-FF6B35?style=for-the-badge)](https://github.com/langchain-ai/langgraph)
[![CrewAI](https://img.shields.io/badge/CrewAI-Agents-6C63FF?style=for-the-badge)](https://crewai.com)
[![MCP](https://img.shields.io/badge/MCP-Protocol-00C896?style=for-the-badge)](https://modelcontextprotocol.io)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License: ISC](https://img.shields.io/badge/License-ISC-blue?style=for-the-badge)](https://opensource.org/licenses/ISC)

<br/>

**[🚀 Get Started](#-deployment)** · **[📖 Architecture](#-system-architecture)** · **[🧠 The Agents](#-the-agentic-crew)** · **[🛡️ Guardrails](#-guardrails--compliance)**

</div>

---

## The Problem with B2B Sales Today

Your best reps spend **67% of their time** on tasks that don't require intelligence — logging CRM data, researching prospects, writing follow-ups, and generating reports.

Meanwhile, the deals that matter are stalling because no one has bandwidth to think.

**SalesIQ fixes this.**

---

## What is SalesIQ?

SalesIQ is a **fully autonomous B2B revenue engine** built on the Model Context Protocol (MCP), powered by a crew of specialized AI agents that work in coordinated sequence.

It doesn't assist your sales team. It *amplifies* them.

From a single lead input to a booked meeting — SalesIQ handles research, outreach, follow-up, competitive intelligence, and executive reporting. Automatically. In seconds.

> *"The first AI system that doesn't just generate content — it executes a full sales motion."*

---

## 🧠 The Agentic Crew

Seven elite agents. One shared mission: **close more revenue, faster.**

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SALESIQ ORCHESTRATOR                         │
│              Classifies · Delegates · Validates · Synthesizes       │
└──────┬─────────┬──────────┬───────────┬─────────────┬──────────────┘
       │         │          │           │             │
       ▼         ▼          ▼           ▼             ▼
  LeadEnricher  Email    FollowUp    Deal        Pipeline     Competitor
               Personalizer Scheduler Analyzer   Reporter     Intel
```

| Agent | Role | Output |
| :--- | :--- | :--- |
| 🎯 **Orchestrator** | Central command. Routes tasks across the crew. | Structured execution chain + confidence score |
| 🔍 **LeadEnricher** | 4-layer B2B intelligence gathering & ICP scoring. | Verified prospect profile with intent signals |
| ✍️ **EmailPersonalizer** | Hook-Bridge-Value-CTA framework copywriting. | 3 subject line variants + 75-125 word body |
| 🔁 **FollowUpScheduler** | Behavioral trigger-based sequence design. | 6-touch sequence with channel routing logic |
| 📊 **DealAnalyzer** | Win/Loss DNA + predictive deal scoring. | Risk flags, win probability, 3-scenario forecast |
| 📋 **PipelineReporter** | 90-second executive pipeline summary. | Slack + HTML + JSON multi-format output |
| ⚔️ **CompetitorIntel** | Real-time battle cards & objection handling. | Rep-ready talk tracks per competitor |

---

## ✨ What SalesIQ Does Differently

**Other tools give your reps a copilot.**  
SalesIQ gives your revenue org an autonomous crew.

### 🔍 Intelligence That Rivals a Team of Analysts
- Pulling company funding data, tech stack, open headcount, and LinkedIn signals
- Scoring every lead 1-10 against your exact ICP with a weighted formula
- Tagging emails as VERIFIED, INFERRED, or UNAVAILABLE — never fabricated

### ✉️ Emails That Actually Get Replies
- Hook sourced directly from enrichment data (funding news, job posts, LinkedIn activity)
- 75-125 words. Grade 6 reading level. Zero filler phrases.
- Built-in spam score + quality checklist before every send

### 🔁 Follow-Ups That Feel Human
- Behavioral routing: opened 3x? Accelerate. Clicked a link? Reference it. No open? Switch channels.
- Touch 5 is a break-up email — historically the highest reply rate in the sequence
- Timezone-aware scheduling. Never on Friday after 2pm.

### 📊 Revenue Science, Not Gut Feelings
- Win probability formula with stage-based baseline + 12 adjustment signals
- Conservative / Base / Optimistic forecast scenarios per quarter
- 🔴 CRITICAL / 🟡 MODERATE / 🟢 ON TRACK risk classification per deal

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        API LAYER                            │
│               FastAPI  ·  REST Endpoints                    │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                   LANGGRAPH ORCHESTRATION                   │
│        Stateful StateGraph  ·  Conditional Routing          │
│              CRMAgentState (TypedDict)                      │
└──────┬──────────┬──────────────┬───────────────────┬────────┘
       │          │              │                   │
┌──────▼──┐  ┌───▼─────┐  ┌────▼────┐  ┌───────────▼───────┐
│  CrewAI │  │ LangChain│  │  MCP    │  │  Integrations     │
│ Agents  │  │  Chains  │  │ Server  │  │ HubSpot · Apollo  │
│         │  │          │  │ (Tools) │  │ Gmail · Slack      │
└─────────┘  └──────────┘  └─────────┘  └───────────────────┘
```

```
sales-crm-agent/
├── agents/
│   ├── prompts.py           # All 8 production system prompts
│   ├── orchestrator.py      # LangGraph supervisor node
│   ├── lead_enricher.py     # CrewAI — B2B intelligence layer
│   ├── email_personalizer.py# CrewAI — Copywriting engine
│   ├── follow_up_scheduler.py# LangGraph — Behavioral sequences
│   ├── deal_analyzer.py     # CrewAI — Revenue science
│   ├── pipeline_reporter.py # LangGraph — Executive summaries
│   └── competitor_intel.py  # CrewAI — Battle cards
├── mcp/
│   └── server.py            # FastMCP tool definitions
├── graph/
│   ├── state.py             # TypedDict CRMAgentState
│   └── workflow.py          # StateGraph builder
├── integrations/
│   └── mocks.py             # Apollo · HubSpot · Gmail · Slack
├── api/
│   └── main.py              # FastAPI endpoints
├── requirements.txt
└── README.md
```

---

## 🚀 Deployment

### Prerequisites
- Python 3.10+
- OpenAI or Anthropic API key
- (Optional) Apollo, HubSpot, Gmail, Slack credentials for live integrations

### 1. Clone & Install

```bash
git clone https://github.com/daniellopez882/AI-powered-Sales-CRM-Agent.git
cd AI-powered-Sales-CRM-Agent
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Add your API keys to .env
```

```env
OPENAI_API_KEY=sk-...
APOLLO_API_KEY=...
HUBSPOT_ACCESS_TOKEN=...
SLACK_BOT_TOKEN=...
```

### 3. Launch

```bash
# Start the revenue API
python -m api.main

# Start the MCP tool server
python -m mcp.server
```

### 4. Use the Prompts in Your Own Stack

```python
from agents.prompts import build_agent_prompt, LEAD_ENRICHER_PROMPT, ALL_PROMPTS

# Inject any agent prompt — guardrails included automatically
prompt = build_agent_prompt(LEAD_ENRICHER_PROMPT)

# Or access all prompts by key
enricher_prompt = ALL_PROMPTS["lead_enricher"]
```

---

## ⚙️ The State Machine

Every piece of data flows through a single typed state — clean, predictable, inspectable.

```python
class CRMAgentState(TypedDict):
    messages: Annotated[list, add_messages]  # Full conversation history
    raw_lead: Optional[dict]                 # Input lead signal
    enriched_lead: Optional[dict]            # Post-enrichment profile
    email_draft: Optional[dict]              # Generated outreach
    sequence: Optional[dict]                 # Follow-up sequence
    deal_analysis: Optional[dict]            # Revenue analysis
    pipeline_report: Optional[dict]          # Weekly report payload
    competitor_battle_card: Optional[dict]   # Competitive intel
    next_agent: Optional[str]                # Routing signal
    requires_human: bool                     # Escalation flag
    confidence: float                        # Agent confidence score
```

---

## 🛡️ Guardrails & Compliance

SalesIQ is built enterprise-first. Safety and compliance are not afterthoughts — they are baked into every agent prompt via `GUARDRAILS_PROMPT`, injected automatically by `build_agent_prompt()`.

**Data Privacy**
- GDPR, CAN-SPAM, and CASL compliance flags built into every email sequence
- PII masked in all logs: `john@acme.com` → `j***@acme.com`

**Human-in-the-Loop Escalation** *(non-negotiable)*
- Deal value > **$50,000** → human reviews before any outreach
- C-Suite contact at a Fortune 500 → human approves the email
- Agent confidence < **0.65** → flagged for human verification
- Any prospect reply → automation pauses immediately

**API Rate Limit Enforcement**
- Apollo: 50 enrichments/hour · Gmail: 500 emails/day · LinkedIn: 20 connections/day
- Exponential backoff on all upstream API failures

---

## 📦 Tech Stack

| Layer | Technology |
| :--- | :--- |
| Orchestration | LangGraph StateGraph |
| Agents | CrewAI + LangChain |
| LLM | GPT-4 Turbo / Claude 3.5 Sonnet |
| Tool Protocol | Model Context Protocol (MCP) |
| API | FastAPI + Uvicorn |
| Integrations | Apollo · HubSpot · Gmail · Slack |

---

## 🗺️ Roadmap

- [ ] Supabase integration for deal persistence
- [ ] Real-time Slack alerts on deal stage changes
- [ ] Voice follow-up via ElevenLabs + Twilio
- [ ] Multi-tenant workspace support
- [ ] A/B email performance analytics dashboard

---

<div align="center">

**Built for the 1% of sales operators who refuse to lose deals to process.**

*Engineered by [Ismail Sajid](https://github.com/daniellopez882) — Agentic AI Engineer*

⭐ Star this repo if SalesIQ is the system you wish existed sooner.

</div>
