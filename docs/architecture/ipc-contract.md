# Desktop IPC and Projection Contract

This is the product boundary for the first Tauri shell. It deliberately contains no guessed App Server payloads.

## Frontend commands

| Command | Input | Result |
| --- | --- | --- |
| `inspect_runtime` | none | runtime compatibility state |
| `select_project` | explicit user intent | selected project or cancellation |
| `start_root_task` | approved project identity, instruction | accepted root-task identity |
| `send_follow_up` | root-task identity, instruction | accepted/rejected command result |
| `request_interrupt` | none; Rust uses the active turn it owns | request submitted/rejected |
| `get_projection` | root-task identity | complete projection snapshot |
| `stop_runtime` | explicit user intent | lifecycle-valid result |

Inputs are serializable typed records, validated in Rust. No command accepts raw shell text, an arbitrary executable path, a frontend-chosen status, or raw protocol JSON.

## Projection channel

The backend emits an ordered envelope:

```text
{ sequence, rootTaskId, update | gap | snapshotRequired }
```

The frontend applies strictly increasing sequence numbers. A missing sequence requests a snapshot; it never guesses the skipped state. A projection exposes only runtime state, task/turn/activity/execution/workflow-link records, gaps, supported actions, and typed errors.

### First live root-turn slice

`start_root_task` accepts a Tauri `Channel` named `updates`. Rust, not React,
correlates the App Server JSONL with the accepted thread and turn and sends
strictly ordered normalized envelopes: `turnAccepted`, `turnStarted`,
`assistantDelta`, `assistantMessage`, and `turnCompleted`. The terminal invoke
result remains a summary for callers that need it; it is not the source of
live rendering. The child stdout reader applies bounded backpressure instead
of dropping protocol lines.

### Interrupt request

While a root turn is active, `request_interrupt` sends the qualified stable
`turn/interrupt` request with identities retained by Rust. The UI can state
only that the request was submitted. It must wait for the matching authoritative
`turn/completed` projection before rendering an interrupted terminal outcome.

## Control rule

A control is enabled only after a proven pinned protocol round trip, Rust lifecycle validation, positive and negative automated coverage, and UI handling for pending, rejected, failed, and terminal states.
