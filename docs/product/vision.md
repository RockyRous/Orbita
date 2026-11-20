# Product Vision

## Problem

Codex is effective as an interactive terminal conversation, but a conversation alone becomes difficult to supervise when work involves tools, plans, approvals, product tickets, delegated agents, and parallel execution. The user needs a complete Codex conversation without returning to the terminal and a structured view of the related work.

## Target user

The first user is a Windows developer who conducts real project work through Codex and wants to supervise it from one desktop application. The MVP supports one local project and one active root task at a time; that task can contain every agent execution the supported Codex integration actually exposes.

## Product statement

Orbita is a local-first desktop client for Codex that combines a functionally complete root chat with a live, source-driven tracker of observable agent executions and their workflow context.

The root chat is the primary interaction surface. The tracker makes agent roles, assignments, statuses, delegation, plans, and explicitly linked product work visible beside the conversation. The user should complete supported Codex work in Orbita without returning to the terminal.

## Positioning

Orbita is an independent client built on supported Codex integration surfaces, not a runtime replacement or a visual clone. It differs from a generic chat client by exposing observable execution and product workflow as a structured view. It differs from a manual task manager by deriving execution rows from real agent activity.

## Product principles

1. **Conversation fidelity.** Every supported interaction required to conduct a Codex task has a usable root-chat representation.
2. **Workflow visibility.** Observable agents, roles, delegation, plans, linked work items, outcomes, and attention remain visible beside the conversation.
3. **Evidence before appearance.** Every execution, relationship, status, and outcome has provenance.
4. **Different facts stay different.** A plan item, GitHub issue, chat turn, and agent execution are related concepts, not interchangeable records.
5. **Unknown is valid.** Missing or ambiguous evidence is shown as unknown or as a gap.
6. **Runtime semantics stay in Codex.** Orbita controls only supported Codex behavior and never fabricates runtime state.
7. **Local data serves continuity.** Local projections improve the workspace without replacing Codex as execution authority.

## Functional parity

Functional 1:1 Codex chat means every interaction exposed by the supported Codex contract and needed for the terminal workflow has an equivalent usable path in Orbita. This includes, where supported: starting and resuming threads; ordered transcript; streamed output; tool activity and errors; plans; approvals and questions; follow-ups, interruption, and outcomes; and model, mode, or effort controls. It does not require copying terminal visuals or undocumented behavior.

## Non-goals

- A pixel-level clone or fork of an official Codex desktop application.
- A replacement Codex runtime, full terminal emulator, editor, or IDE.
- Manual or synthetic task cards, drag-and-drop Kanban, or inferred agent relationships.
- Turning plans or GitHub issues into agent executions.
- Direct subagent control without a supported contract, hidden reasoning reconstruction, arbitrary live-session attachment, or several simultaneous root tasks in the MVP.
- Full GitHub issue authoring/synchronization, remote/mobile/team features, multiple harnesses, or a plugin marketplace.
