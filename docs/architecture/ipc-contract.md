# Desktop IPC and Projection Contract

This is the product boundary for the first Tauri shell. It deliberately contains no guessed App Server payloads.

## Frontend commands

| Command | Input | Result |
| --- | --- | --- |
| `inspect_runtime` | none | runtime compatibility state |
| `select_project` | explicit user intent | selected project or cancellation |
| `start_root_task` | approved project identity, instruction | accepted root-task identity |
| `send_follow_up` | root-task identity, instruction | accepted/rejected command result |
| `interrupt_turn` | root-task identity, active turn identity | accepted/rejected command result |
| `get_projection` | root-task identity | complete projection snapshot |
| `stop_runtime` | explicit user intent | lifecycle-valid result |

Inputs are serializable typed records, validated in Rust. No command accepts raw shell text, an arbitrary executable path, a frontend-chosen status, or raw protocol JSON.

## Projection channel

The backend emits an ordered envelope:

```text
{ sequence, rootTaskId, update | gap | snapshotRequired }
```

The frontend applies strictly increasing sequence numbers. A missing sequence requests a snapshot; it never guesses the skipped state. A projection exposes only runtime state, task/turn/activity/execution/workflow-link records, gaps, supported actions, and typed errors.

## Control rule

A control is enabled only after a proven pinned protocol round trip, Rust lifecycle validation, positive and negative automated coverage, and UI handling for pending, rejected, failed, and terminal states.
