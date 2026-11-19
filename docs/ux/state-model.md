# State Model

Orbita keeps lifecycle, execution, and attention separate. Combining them would make states such as "the turn succeeded but the user has not reviewed it" impossible to express truthfully.

## Root-task lifecycle

| State | Occupies active slot | Accepts follow-up | Visible in primary workspace |
| --- | --- | --- | --- |
| `Open` | Yes | Yes | Yes |
| `Finished` | No | Yes, by reactivation | Yes |
| `Archived` | No | After unarchive | No |

Lifecycle is Orbita organizational state. It does not overwrite Codex execution outcomes.

### Lifecycle transitions

```text
new root task -> Open
Open --manual Finish--> Finished
Open --eligible Automatic Finish--> Finished
Finished --follow-up, active slot free--> Open
Finished --Archive--> Archived
Archived --Unarchive--> Finished
```

Interrupt affects the current turn, not the lifecycle. Destructive deletion is outside the MVP.

## Turn outcome

A turn outcome is accepted only from authoritative protocol evidence. The exact protocol mapping is determined by M0.

Product-level outcome categories are:

- successful;
- failed;
- interrupted or cancelled;
- unknown.

No timeout, lack of events, or disappearing indicator is sufficient evidence of success.

## Agent-execution status

Execution status is source-driven. The UI may use semantic categories such as observed, active, waiting, successful, failed, interrupted, disconnected, and unknown only when the pinned protocol provides enough evidence for each mapping.

M0 owns the canonical mapping table. Unsupported distinctions collapse to a weaker truthful category, usually `unknown`.

## Attention state

| State | Trigger | Clear condition |
| --- | --- | --- |
| `Action required` | Supported approval or user question | The request is resolved. |
| `Review required` | A terminal turn outcome has not been reviewed | The user acknowledges the result or starts a follow-up. |
| `Connection problem` | Disconnect, degradation, or unresolved recovery gap | Reconciliation succeeds or the problem is explicitly resolved. |
| `No attention` | No outstanding attention evidence | A new attention trigger occurs. |

Attention acknowledgement never changes execution status.

## Automatic Finish eligibility

Automatic Finish is enabled by default and is configurable. It is eligible only when all of the following are proven:

1. The root turn has an authoritative settled successful outcome.
2. No approval or supported question is pending.
3. No child execution is observably active or waiting.
4. No connection or recovery gap is unresolved.
5. Reconciliation is complete.

Any uncertainty makes Automatic Finish ineligible. When it runs, lifecycle changes to `Finished`, the active slot is released, and `Review required` remains. It never archives, deletes, summarizes, or starts work.

## Provenance and gaps

Every status-bearing projection records the evidence needed to explain it. Derived fields identify their derivation rule. When evidence cannot be recovered, the model records a gap rather than interpreting the absence as inactivity or completion.
