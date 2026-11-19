# Product Vision

## Problem

Codex work is primarily experienced as a linear conversation. When a root task delegates work, the user has to reconstruct who is working, how executions relate, what needs attention, and what actually finished from a stream of messages and tool activity. That makes parallel agent work difficult to supervise without losing context.

## Target user

The first user is the project owner: a Windows developer who wants to launch a Codex root task locally and understand its observable agent work as structured activity rather than as a chat transcript.

## Product statement

Orbita is a local-first visual control plane for Codex. The user launches a root task in Orbita, and Orbita presents observable root and subagent executions as a source-driven hierarchy with task cards, activity, outcomes, and attention states.

The task workspace is the primary surface. Root input and follow-ups are compact controls within that workspace, not a full-screen chat product.

## Positioning

Orbita is a workflow-specific client built on the public Codex App Server integration surface. It complements the Codex runtime instead of copying or replacing it. Its distinguishing job is to turn observable agent execution into a truthful task workspace.

## Product principles

1. **Evidence before appearance.** Every execution, relationship, status, and outcome shown to the user has provenance.
2. **Unknown is a valid result.** Missing or ambiguous evidence is displayed as unknown or as a gap, never filled with a plausible reconstruction.
3. **Task-centric, not chat-centric.** The workspace optimizes for supervision, review, and attention.
4. **Runtime semantics stay in Codex.** Orbita does not schedule agents, maintain agent memory, or synthesize delegation calls.
5. **User actions map to supported contracts.** Approvals, interruption, and follow-up use public App Server behavior.
6. **Local data serves continuity.** Local projections support recovery and diagnostics without replacing App Server as the execution source of truth.

## Non-goals

- A general-purpose chat client.
- A code editor, terminal, or IDE.
- A manual task manager or drag-and-drop Kanban.
- A custom agent orchestrator, scheduler, or task graph executor.
- Attaching to an arbitrary already-running CLI or desktop session in the MVP.
- Turning an agent's internal plan into synthetic task cards.
- Direct control of a subagent without a public supported API.
- Reconstructing hidden reasoning or chain-of-thought.
- A complete clone or fork of the official Codex desktop application.
- Supporting multiple agent harnesses, remote machines, mobile clients, or team collaboration in the MVP.
- MCP, skills, plugin, or model-management surfaces in the MVP.
