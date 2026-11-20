# M0 continuity research: public recovery surfaces on Codex 0.170.0

## Scope and evidence status

This note supports Orbita issue #6. It is contract and source research only: no model turn, reconnect, restart, or history query was run. Claims are pinned to the local `codex-cli 0.170.0` snapshot recorded in [m0-contract-research.md](m0-contract-research.md): stable-only generated bindings (`--experimental` omitted), Windows x64 executable SHA-256 `8d06dc231dba649c7d48d3eecab239c452a1ac498c41dd6492a6f301b90a22ce`, and OpenAI's [`rust-v0.170.0`](https://github.com/openai/codex/releases/tag/rust-v0.170.0) source tag.

“Present in the stable-only generated contract” is not a recovery promise. App Server itself remains CLI-marked experimental. Per [compatibility.md](compatibility.md), recovery is untested until a sanitized fixture proves it.

## Confirmed contract facts

The local stable-only contract generation used for M0 includes public request/response types for these candidate read surfaces:

| Surface | What the pinned protocol directly establishes | Recovery conclusion |
| --- | --- | --- |
| `initialize` then `initialized` | Each new connection performs the normal handshake. | A restarted client must initialize again; this does not prove it can resume prior subscriptions. |
| `thread/read` | Takes a thread ID and returns `Thread`. | A caller can request a named thread, subject to a live proof of persistence and semantics. |
| `thread/list` | Exposes a thread-list request/response. | Candidate discovery surface; list completeness, scope, ordering, and cursor behavior are unproven. |
| `thread/loaded/list` | Exposes a loaded-thread list. | Candidate process/session observation surface; not evidence of durable history. |
| `thread/turns/list` | Exposes a turn-history list. | Candidate recovery source for turns; pagination and completeness require a live fixture. |
| `thread/items/list` | Exposes an item-history list. | Candidate recovery source for items; it is not proof of replay, ordering, or redaction safety. |
| `thread/resume` | Resumes a specified thread or path and returns a thread response. | It is an execution/lifecycle operation, not a safe read-only reconnect primitive. Do not invoke it during recovery research without a separately approved scenario. |

The protocol registrations make the read candidates explicit: `thread/list` is a non-serialized request; `thread/read` is serialized by its `threadId`; `thread/turns/list` and `thread/items/list` are annotated as concurrent reads of append-only rollout storage ([common.rs, lines 3640-3648 and 3794-3858](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/app-server-protocol/src/protocol/common.rs#L3640-L3858)). `thread/resume` is separately registered as a lifecycle operation ([lines 3182-3206](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/app-server-protocol/src/protocol/common.rs#L3182-L3206)).

The generated-contract exporter removes experimental variants when generation omits `--experimental`; any later experimental history surface must have a separate digest and result ([export filtering](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/app-server-protocol/src/export.rs#L108-L150)). `thread/items/read` and `thread/search*` are explicitly experimental in the pinned source and are not part of this baseline.

## Candidate recovery model

The only justified candidate sequence is:

1. Persist a normalized local projection with source aliases, evidence ordinals, runtime/contract/feature manifests, and explicit gaps — not a claim that the cache is authoritative.
2. After a client-only reconnect, start a fresh public App Server connection and handshake.
3. Read the known root by `thread/read`; use `thread/turns/list` and `thread/items/list` only after schema-validating their responses against the same generated stable-only contract.
4. Compare source identities and terminal evidence to the pre-disconnect projection. Deduplicate only by source identity plus evidence semantics, never event adjacency or text.
5. If the source does not return a previously observed identity/event, retain an explicit gap. Do not mark it idle, finished, deleted, or restarted.

This is a candidate, not confirmed reconnect behavior: no inspected source guarantees that a new connection receives missed notifications, that list results are complete, or that a process restart preserves the same history.

## Unknowns and blockers

- Whether `thread/read`, list calls, and their histories survive client restart, App Server restart, or a crashed active turn.
- Pagination shape, cursor semantics, maximum page size, snapshot consistency, duplicate delivery, ordering, and treatment of late events.
- Whether a list/read includes child threads, their parent edges, terminal outcomes, approvals, or pending attention with the same fidelity as live delivery.
- Whether `thread/loaded/list` means loaded by this process, this connection, or durable storage.
- Whether `thread/resume` reconnects observation, mutates execution state, or can create a replacement execution. It must remain out of the recovery probe.
- Background continuation, server ownership, authentication/session continuity, and recovery after process restart.

## Least-privilege live recovery scenario

This is a proposed future experiment, not executed work.

1. Pin the executable, stable-only contract digest, effective feature list, and exact `CODEX_HOME`; use a disposable Git repo with synthetic files only.
2. Start one root thread with `approvalPolicy: "never"` and `sandbox: "read-only"`; use a bounded no-tool prompt and capture a sanitized pre-disconnect baseline.
3. While the root turn is active, disconnect the client transport only. Do not issue `thread/resume`, a new turn, tools, approvals, or filesystem writes.
4. Start a new client connection, repeat `initialize`/`initialized`, then issue only schema-validated `thread/read` for the recorded root ID plus bounded `thread/turns/list` and `thread/items/list` requests.
5. Capture request/response/notification order with monotonic ordinals. Prove or reject identity continuity, source outcome recovery, duplicate handling, and a visible gap for anything absent.
6. Repeat separately with client-and-runtime restart and with runtime failure during active work. A missing response, EOF, timeout, or changed ID is a failed/unknown recovery observation, never success.

Persist only sanitized fixtures: causal aliases for IDs; method names, stable classifications, pagination metadata only if contract-exposed, and evidence ordinals. Remove prompts, reasoning, source, paths, command/tool payloads, credentials, and raw diagnostics before commit. This follows [Diagnostics and Local Data](../security/diagnostics-and-data.md).

## Acceptance matrix for issue #6

| Question | Passing evidence | Otherwise |
| --- | --- | --- |
| Client-only reconnect | Same root source ID is directly returned after a fresh handshake. | Show a reconciliation gap. |
| History recovery | Schema-valid turn/item pages correlate to pre-disconnect source IDs without duplication. | Mark unavailable/ambiguous; do not reconstruct. |
| Pagination | Bounded iteration proves cursor termination, no duplicate IDs, and recorded ordering limitations. | Do not claim full history. |
| Runtime restart | New runtime returns supported history with source-backed identity/outcome equivalence. | No background-continuation promise. |
| Active-turn failure | A terminal event or an explicit unrecoverable gap is observed. | Never infer terminal status from transport closure. |

## Primary sources

- [OpenAI Codex 0.170.0 release](https://github.com/openai/codex/releases/tag/rust-v0.170.0)
- [Pinned App Server request registrations](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/app-server-protocol/src/protocol/common.rs)
- [Pinned contract exporter](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/app-server-protocol/src/export.rs)
- [Pinned App Server README](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/app-server/README.md)
