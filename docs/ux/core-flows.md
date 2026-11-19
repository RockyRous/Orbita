# Core Flows

## First run

1. Orbita checks for a local Codex installation and records its version and exposed contract.
2. If the installation is unsupported or unavailable, Orbita explains the mismatch without guessing at a workaround.
3. The user selects one local project.
4. Orbita shows an empty task workspace with a compact root-task input.

## Start a root task

1. The user enters an instruction and starts the task.
2. Orbita creates the supported Codex thread and turn through App Server.
3. The root task becomes open and occupies the active slot.
4. The workspace shows the root execution with its current evidence and provenance.
5. Project switching and starting another root task remain unavailable while this slot is occupied.

## Observe delegated work

1. Orbita receives App Server events.
2. An agent execution appears only when the event stream provides enough evidence to identify or correlate it.
3. A supported parent relationship places the execution beneath its parent.
4. If the relationship is unavailable, Orbita shows a neutral unlinked execution or delegation event rather than inventing a tree edge.
5. Opening a task card reveals a focused evidence timeline, available assignment or summary, last activity, outcome, and gaps.

## Handle attention

1. A supported approval or user question marks the root task as `Action required`.
2. The workspace keeps the affected execution visible and identifies the source of the request when supported.
3. The user responds through the public App Server contract.
4. The attention state clears only after the response is accepted or the request is otherwise resolved.
5. Runtime status remains independent from acknowledgement.

## Interrupt and recover

1. The user interrupts the current root turn.
2. Orbita sends the supported interrupt action and waits for source evidence of the outcome.
3. The root task remains open and becomes `Review required` when the interruption is confirmed.
4. The user may send a follow-up or finish the root task.

Orbita may reconnect and reconcile an existing task after a transport failure. It never starts a replacement task automatically.

## Review a successful result

1. A settled successful turn produces `Review required`.
2. When Automatic Finish is eligible and enabled, the root task becomes finished while review attention remains.
3. The user reviews the available outcome and agent evidence.
4. The user may acknowledge the review, reactivate the same root task with a follow-up, or archive the finished task.

When Automatic Finish is disabled, the task remains open until the user sends a follow-up or finishes it manually.

## Finish, reactivate, and archive

- **Finish:** releases the active slot without deleting the thread or evidence.
- **Reactivate:** a follow-up to a finished task reopens the same task and thread if the active slot is free.
- **Archive:** reversibly hides a finished task from the primary workspace.
- **Unarchive:** restores an archived task to the finished view; it does not start a turn.

## Close and reopen Orbita

1. If a root task is open, Orbita determines whether the proven runtime path can continue safely without the UI.
2. If it can, the UI closes without terminating the task.
3. If it cannot, Orbita warns the user before an action that would stop work.
4. On reopening, Orbita reconciles local projections with App Server history.
5. Duplicate events are removed, and missing intervals are shown as gaps.

The exact background and reconciliation mechanism is an M0 result, not a product assumption.
