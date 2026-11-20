# MVP Scope

## Product boundary

The MVP is a Windows-first desktop application for one local user. The user selects one local project and may have one open root task at a time. It contains one functionally complete Codex chat and any agent executions actually observable through the supported integration.

The fixture-backed Tkinter observer is protocol-spike output, not product UI. Individual capabilities remain gated by reproducible protocol evidence. Unsupported data is unavailable, unknown, or a gap; it is never reconstructed from assumptions.

## Primary workspace

The workspace has three coordinated regions:

1. **Navigation:** current project, active root task, finished/archived history, task status and attention.
2. **Root chat:** complete ordered Codex conversation; streamed output; supported tools, commands, plans, questions, approvals, errors, composer, follow-ups, interruption, and runtime controls.
3. **Execution tracker:** resizable/collapsible table with one row per observable agent execution and links to chat evidence and workflow context.

## Included behavior

### Functional Codex chat

- Detect a compatible local Codex installation, select a project, and start one root task from Orbita.
- Show the available transcript in source order and stream assistant output without blocking controls.
- Render supported tool calls, command activity, results, file changes, plans, errors, approvals, and questions.
- Preserve an unknown event as a safe generic event instead of dropping it.
- Send initial instructions and follow-ups; interrupt the current root turn.
- Show terminal outcomes, disconnects, reconciliation, and recovery truthfully where supported.
- Expose model, mode, effort, queueing, and resume only where the pinned contract supports them.

### Execution tracker

- Create a row only for an observable agent execution.
- Show the root and supported subagent executions; nest only on a supported parent relationship.
- Show an unlinked execution when it is observed but its parent is unknown.
- Display only source-backed identity, role, assignment, status, last activity, duration, attention, and outcome.
- Navigate from a row to available chat evidence. The tracker is read-only; it is not a manual board.

### Workflow context

Orbita makes our process visible without claiming it is runtime state. It may show explicitly reported plans, assigned roles, GitHub issues, and associations to root tasks or executions. Each association carries provenance: a Codex event, an explicit user association, an app record, or an authorized external lookup.

A plan item or GitHub issue remains a **work item**, not an **agent execution**. The MVP may display and open an explicit issue reference; authoring, triage, and synchronization stay out of scope.

### Attention, lifecycle, and continuity

- Supported approvals and user questions become `Action required`; terminal outcomes become `Review required`; gaps become `Connection problem`.
- Root follow-up and interruption are supported only after a proven round trip. Direct subagent control is excluded until proven.
- A root task is `Open`, `Finished`, or `Archived`. Interrupt affects a turn, not lifecycle. Finish and Archive preserve history; delete is excluded.
- Automatic Finish is on by default but runs only after a settled successful source outcome, no pending approval/question, no observably active child, no unresolved gap, and completed reconciliation. Uncertainty keeps the task open.
- Local normalized projections support reopening; reconciliation never starts a replacement task and missing intervals remain gaps.

## Quality requirements

- Chat streaming and tracker updates keep the composer responsive.
- Long transcripts and execution tables remain navigable; states are distinguishable without color alone.
- Project paths with spaces work without shell interpolation.
- Rendered output is untrusted and cannot execute privileged UI actions.
- Persistence is bounded, local by default, redacted before storage/export, and user-clearable.
- No telemetry or diagnostic upload is enabled by default.

## Out of scope

- Multiple active root tasks/projects; arbitrary live-session attachment; manual rows or Kanban.
- Treating plans or issues as execution rows; full GitHub issue management.
- Direct subagent messaging/control without a public contract.
- Editor, full terminal, Git workflow, remote/mobile/team features, multiple harnesses, or marketplace.

## MVP success criteria

The user can select a project; launch a real task; conduct the supported Codex conversation without the terminal; see available activity/outcomes; understand observable agents, roles, assignments, and status; see linked plan/issue context distinctly; navigate between a row and its evidence; use proven follow-up/interrupt/approval controls; and reopen without fabricated or duplicate state.
