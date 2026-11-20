# MVP Scope

## Product boundary

**Current implementation re-scope:** M1 is a root-task observer for the pinned
runtime, following the M0 assessment. It includes root launch, source-backed
turn activity/outcome, same-thread follow-up, interrupt, and explicit gaps. It
does not include a subagent hierarchy, actionable approvals, or recovery claims
until the corresponding M0 evidence exists. See [ADR 0002](../adr/0002-root-task-observer.md).

The MVP serves one local user on Windows 11. The user selects one local project and can have one open root task at a time. That root task may contain any number of subagent executions actually exposed by Codex.

The product proceeds only after the M0 protocol spike satisfies the go/no-go criteria in [the spike plan](../protocol/spike-plan.md).

## Included behavior

- Detect a compatible local Codex installation and report incompatibility clearly.
- Select one local project.
- Start one root task from Orbita.
- Send a compact initial instruction and follow-ups to the root task.
- Present observable root and subagent executions as a source-driven hierarchy.
- Show task cards with only supported identity, assignment or summary, relationship, execution status, last activity, outcome, and provenance.
- Show a focused evidence timeline for an execution.
- Surface approvals and supported user questions as attention.
- Let the user respond to approvals, interrupt the current root turn, and send a follow-up to the root task.
- Recover a coherent task workspace after restart, within the evidence the App Server can restore.
- Mark missing history and ambiguous states explicitly.
- Finish and archive root tasks without deleting their history.

Capabilities such as parent-child relationships, detailed subagent history, granular statuses, and recovery depth are included only to the extent that M0 proves them.

## Root-task lifecycle

A root task is bound to one Codex thread and may contain multiple turns.

| Lifecycle state | Meaning |
| --- | --- |
| `Open` | Occupies the single active slot and may run a turn or accept a follow-up. |
| `Finished` | Releases the active slot while preserving the thread and history. |
| `Archived` | Reversibly hides a finished task from the primary workspace. |

Turn completion does not erase the distinction between execution outcome and user review. A finished task can still require review.

`Interrupt` stops the current turn but does not finish the root task. A manual **Finish task** action releases the active slot. Archive is available only for a finished task and is reversible. Destructive deletion is outside the MVP.

Sending a follow-up to a finished task reactivates the same root task and thread when the active slot is free. An archived task must first be unarchived.

## Automatic Finish

Automatic Finish is enabled by default and can be disabled.

It may run only after an authoritative settled successful turn outcome when:

- no approval or supported user question is pending;
- no child execution is observably active or waiting;
- no connection or recovery gap is unresolved;
- reconciliation has completed; and
- the outcome is neither ambiguous nor unknown.

If any condition is unproven, the root task remains open. Automatic Finish never runs for failed, interrupted, cancelled, disconnected, or unknown outcomes.

Automatic Finish releases the active slot and preserves `Review required`. It does not archive, delete, summarize, start another task, or rewrite the source outcome.

No product-level countdown is required. M0 determines which protocol evidence represents a settled successful outcome.

## Attention model

Attention is independent from execution status.

| Attention state | Meaning |
| --- | --- |
| `Action required` | A supported approval or user question is pending. |
| `Review required` | A turn succeeded, failed, or was interrupted and its outcome has not been reviewed. |
| `Connection problem` | The task is disconnected or degraded and reconciliation is incomplete. |
| `No attention` | No user action or review is currently required. |

Acknowledging attention changes only Orbita's attention state. It never changes an agent execution status or source outcome.

## Project and window behavior

- The active project cannot be switched while a root task is open. The user must finish it or explicitly interrupt and finish it first.
- Closing the UI must not silently stop active work.
- If M0 proves a safe background runtime path, work continues and reconciles when Orbita returns.
- Otherwise Orbita warns the user before stopping active work.
- Orbita may reconnect to and reconcile an existing root task, but it never silently starts a replacement task after a runtime failure.

## Quality requirements

- Active event streaming must not make core controls unresponsive.
- In-memory and persisted event data must remain bounded.
- Unknown protocol variants must degrade the affected projection without taking down unrelated work.
- Partial failures are visible and retries are bounded.
- Project paths with spaces and supported Windows path forms work without shell interpolation.
- Keyboard navigation reaches the root input, task hierarchy, task details, attention, and supported actions.
- Execution and attention states are distinguishable without relying on color alone.
- Code, command, error, and diagnostic output remains readable and safely rendered.
- No telemetry or diagnostic upload is enabled by default.
- Performance thresholds are set from M0 event-volume measurements and later UI profiling, not inherited as arbitrary targets.

## Out of scope

- Multiple simultaneous root tasks or projects.
- Arbitrary live-session attachment.
- Manual or editable task cards.
- A full transcript-oriented chat experience.
- Direct subagent messaging or control without a public API.
- A built-in editor, terminal, Git workflow, or graph editor.
- Remote access, mobile, multi-user collaboration, telemetry, and automatic updates.
- Plugin, MCP, skill, model, or runtime-profile management.

## MVP success criteria

The MVP succeeds when the first user can:

1. Launch a real root task from Orbita.
2. Understand which observable agents are working and how they relate without reading a complete chat transcript.
3. See every supported event that requires attention.
4. Handle an approval, interrupt a turn, and send a root-task follow-up.
5. Restart Orbita and recover a coherent task workspace without duplicate or fabricated state.
6. Distinguish source-backed information from unavailable, ambiguous, or missing information.
7. Finish and archive a root task without losing its history.
