# Orbita

Orbita presents observable Codex work as a structured workspace without replacing the Codex runtime.

## Language

**Root task**:
A user-level unit of work that can contain multiple follow-ups and agent executions until the user finishes it.
_Avoid_: Session, root agent, job

**Turn**:
One request-and-result cycle within a root task.
_Avoid_: Task, session

**Agent execution**:
An observed instance of an agent performing assigned work within a root task.
_Avoid_: Task, worker, synthetic agent

**Task card**:
The workspace representation of exactly one observable agent execution.
_Avoid_: Todo, inferred task

**Execution status**:
The source-backed condition of an agent execution.
_Avoid_: Attention state, task lifecycle

**Attention state**:
The independent indication that a root task needs user action, review, or awareness of a connection problem.
_Avoid_: Execution status, notification

**Open**:
The root-task lifecycle state that occupies the single active slot and can accept a turn or follow-up.
_Avoid_: Running

**Finish**:
The non-destructive transition that releases a root task's active slot while preserving its history.
_Avoid_: Complete, archive, delete

**Archive**:
The reversible transition that removes a finished root task from the primary workspace without deleting it.
_Avoid_: Finish, delete

**Provenance**:
The evidence that connects a displayed claim to an observed source.
_Avoid_: Assumption, inference without evidence

**Gap**:
A known interval for which Orbita cannot recover complete source evidence.
_Avoid_: Idle, no activity
