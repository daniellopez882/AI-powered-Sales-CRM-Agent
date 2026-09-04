# ADR-001 — Orchestration framework

- **Status:** Accepted, with a known overlap to resolve
- **Date:** 2026-09-03

## Problem

The system runs several specialised agents. Something has to decide which agent
handles a request, pass state between them, survive a process restart mid-session,
and fail in a way that can be debugged.

## Alternatives considered

**A single prompt with tool calls.** Simplest, and adequate for two or three
tools. Rejected: routing, retry and partial failure all end up implicit inside
one model call, so there is nothing to unit test. A wrong route and a wrong
answer look identical from outside.

**CrewAI alone.** Good ergonomics for multi-step role-playing agents, which is
what the enricher and analyser actually are. Rejected as the top-level
orchestrator: control flow is delegated to the framework, so "why did it pick
that agent" is hard to answer, and there is no first-class checkpoint story.

**LangGraph alone.** Explicit `StateGraph`, named nodes, conditional edges,
built-in checkpointing. Routing becomes a plain Python function that can be
tested without a model.

**LangGraph for orchestration, CrewAI inside workers.** What exists today.

## Decision

LangGraph owns the top-level graph. `route_from_orchestrator` is an ordinary
function returning a node name, so routing is testable in isolation. Each node
is a named wrapper that catches exceptions, appends to `state["errors"]` and
sets `requires_human`, rather than letting a failure propagate and abort the run.

Four workers (`lead_enricher`, `email_personalizer`, `deal_analyzer`,
`competitor_intel`) still use CrewAI internally for their multi-step reasoning.

## Consequences

Good:

- Routing is deterministic and unit-testable without an LLM.
- A single agent failing degrades to a human-escalation result instead of a 500.
- Checkpointing comes from the framework rather than hand-rolled session code.

Bad:

- **Two agent frameworks in one dependency tree.** LangGraph and CrewAI overlap
  substantially, roughly doubling the surface for version conflicts, and CrewAI
  pulls a large transitive tree. This is historical, not deliberate design.
- Contributors must understand both models.

## Open item

Collapse the overlap. Either drop CrewAI and express the workers as LangGraph
subgraphs, or keep CrewAI and thin the top-level graph. The first is preferred:
the workers' multi-step behaviour is expressible as subgraphs, and dropping
CrewAI would substantially shrink the install. Not yet done because the worker
prompts are tuned against CrewAI's task/agent abstractions and rewriting them
without an evaluation harness would be changing behaviour blind — which is why
[the eval harness](../../README.md#evaluation) is roadmap item 1.
