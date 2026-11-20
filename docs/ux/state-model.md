# State Model

Orbita keeps lifecycle, turn outcome, execution status, connection state, attention, and workflow association separate. This permits truthful combinations such as: a successful root turn, an active child, pending review, and an open GitHub issue.

## Root-task lifecycle

| State | Active slot | Follow-up | Primary workspace |
| --- | --- | --- | --- |
| `Open` | yes | yes | yes |
| `Finished` | no | reactivates when slot is free | yes |
| `Archived` | no | after unarchive | no |

Lifecycle is Orbita organization, never a replacement for Codex outcomes, execution state, or external issue state. `Interrupt` affects a turn, not lifecycle.

## Turn and chat state

A local message moves `Draft → Sending → Accepted` or `Send failed`; only accepted input is authoritative conversation. A terminal outcome is only `Successful`, `Failed`, `Interrupted`, `Cancelled` when distinguishable, or `Unknown`—never inferred from silence, EOF, timeout, or animation. Streamed events may be in progress, settled, degraded, or unknown-but-preserved.

## Agent execution

The compatibility matrix maps supported evidence to `Observed`, `Active`, `Waiting`, `Successful`, `Failed`, `Interrupted`, `Disconnected`, or `Unknown`. Status never comes only from plan text, issue state, agent prose, a sibling, or absent events.

An execution can have a supported parent, be root, or have an unknown parent. Unknown parentage prevents an edge, not the row. Delegation requires supported relation and assignment evidence.

## Workflow associations

Roles, plan items, and work items are independent records. Their association is `Linked` only with explicit evidence, `Unresolved` when a reference cannot resolve, and `Unavailable` when no source supplies it. Completion of an execution never changes an external work item.

## Connection and attention

Connection is `Connected`, `Reconnecting`, `Degraded`, or `Disconnected`; it constrains claims but does not decide outcomes. Attention is `Action required`, `Review required`, `Connection problem`, or `No attention`. Clearing one trigger never clears unrelated state.

## Automatic Finish, provenance, and gaps

Automatic Finish requires a settled successful root outcome, no pending supported question/approval, no observably active child, no unresolved gap, and completed reconciliation. It changes only lifecycle to `Finished` and retains review attention. Every status-bearing projection records its evidence; missing evidence creates a gap rather than implied inactivity or success.
