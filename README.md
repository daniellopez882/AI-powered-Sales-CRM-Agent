# 🚀 SalesIQ: The Autonomous Revenue Engine

[![CI/CD](https://github.com/daniellopez882/AI-powered-Sales-CRM-Agent/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/daniellopez882/AI-powered-Sales-CRM-Agent/actions/workflows/ci-cd.yml)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](Dockerfile)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**SalesIQ** is a production-grade, agentic AI sales operations system built for high-growth B2B companies. It transforms raw lead signals into qualified pipeline through a coordinated crew of specialized AI agents.

Built with **LangGraph + CrewAI + FastAPI**, SalesIQ isn't just a chatbot — it's an autonomous sales floor that enriches leads, personalizes outreach, and analyzes deal intelligence at scale.

---

## 💎 Enterprise-Grade Features

*   **🕵️ Orchestrated Intelligence**: A central **SalesOrchestrator** (LangGraph) coordinates specialized agents for enrichment, personalization, and analysis.
*   **🛡️ Production Security**: Integrated `X-API-Key` authentication, rate limiting (`slowapi`), and universal PII masking in structured logs.
*   **🏎️ Performance Scaling**: Redis-backed enrichment caching reduces latency and API costs by up to 80%.
*   **🔄 Persistent Sessions**: SQLite/Postgres checkpointing allows complex multi-turn sales workflows to survive server restarts.
*   **⚖️ Compliance First**: Full audit logging system for B2B data handling transparency.
*   **📦 Cloud Native**: Fully Dockerized with multi-stage builds and `docker-compose` orchestration.

---

## 🏗️ The Agentic Architecture

SalesIQ uses a "Supervisor-Worker" pattern implemented via LangGraph:

1.  **LeadEnricher**: Deep B2B intelligence via Apollo.io integration.
2.  **EmailPersonalizer**: Generates hyper-personalized, context-aware outreach copy.
3.  **DealAnalyzer**: Analyzes HubSpot deal history to predict win probability.
4.  **FollowUpScheduler**: Manages behavioral-based follow-up sequences.
5.  **CompetitorIntel**: Real-time battle card generation from market news.

---

## 🚀 Quick Start

### 1. Clone & Set Up
```bash
git clone https://github.com/daniellopez882/AI-powered-Sales-CRM-Agent.git
cd AI-powered-Sales-CRM-Agent
cp .env.example .env
```

### 2. Run with Docker (Recommended)
```bash
docker-compose up -d
```
The API will be live at `http://localhost:8000/docs`.

### 3. Local Development
```bash
pip install -r requirements.txt
python -m api.main
```

---

## 🛠️ Tech Stack

- **Orchestration**: LangGraph, CrewAI, LangChain
- **Core**: Python 3.11, FastAPI
- **Integrations**: Apollo.io, HubSpot, Slack, Gmail
- **Data & Auth**: Redis (Cache), SQLite (State), Pydantic v2
- **Observability**: Structlog, Sentry, LangSmith

---

## 🔒 Security & Compliance

SalesIQ is designed for mature organizations:
- **PII Protection**: Automatic regex-based masking of emails and phone numbers in all logs.
- **Audit Trails**: Every agent decision is recorded with a unique `session_id`.
- **Rate Protection**: Sliding window rate limiting prevents API abuse and token-cost spikes.

---

## 🤝 Contribution

We welcome PRs for new integration providers (Salesforce, Apollo, Outreach) and agent specialized frameworks.

---
*Created by the SalesIQ Agentic AI Team. Built for the future of B2B Revenue.*
