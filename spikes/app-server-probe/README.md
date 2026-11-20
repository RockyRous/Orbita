# Orbita M0 App Server probe

This is a **throwaway M0 experiment**, not Orbita's production stack. It uses
Python to exercise only the public Codex App Server process boundary over
newline-delimited JSON on stdio.

The historical default profile is pinned to `codex-cli 0.170.0`. It fails
closed for another reported version. A separate `0.171.0` compatibility
profile is recorded in `fixtures/*-0.171.0.json` and
`docs/protocol/compatibility-profile-0.171.0.md`; it is selected only with
`ORBITA_PINNED_CODEX_VERSION='codex-cli 0.171.0'` and an explicit
`--contract-fixture`. No profile silently substitutes for another version.

## Current evidence status

`fixtures/live-turn.json` predates the environment isolation, strict no-tools
allowlist, generated-schema validation, complete runtime pinning, and fixture
pair remediation. It is retained only as **obsolete historical evidence** and
must not be used to close Issue #2.

The current reviewed evidence is `fixtures/live-turn-1.json` and
`fixtures/live-turn-2.json`. Both are fresh hardened runs: every required
surface was schema-valid and classified, no server request or tool activity was
observed, the matching terminal event was `turn/completed` with
`status: "completed"`, and the final agent text was `ORBITA_M0_OK`. Their
semantic projections share SHA-256
`491637aea23170f7c5e2ea44c420299c38e8d3090b852be592e3c3d220e682d3`.

`fixtures/live-controls.json` is the reviewed pinned evidence for the next
control slice. It proves a completed root turn, a completed follow-up turn in
the same thread, and an interrupted third turn after a correlated public
`turn/interrupt` request/response. Its normalized projection is
`fixtures/live-controls-normalized.json`. It records no tool or server-request
activity; the lack of a late event is an observation, not a requirement for
future runtimes.

The offline harness now validates the following intended live boundary:

The live slice:

1. generates stable and experimental schemas into disposable directories;
2. records canonical schema-manifest and combined-bundle SHA-256 digests;
3. starts `codex app-server --listen stdio://` with an isolated disposable
   `CODEX_HOME` and Git repository;
4. sends stable `initialize`, receives the correlated response, and sends
   `initialized`; and
5. proves that connection remains usable with stable `thread/start` and a
   non-empty source thread ID; and
6. only with explicit `--confirm-live-model`, starts one correlated turn and
   waits for its matching authoritative `turn/completed`.

Before persistence, the probe replaces the private Codex home, disposable
project path, server user agent, and source thread ID with typed placeholders.
It does not parse terminal output or read private Codex storage.

The opt-in live slice creates an ephemeral thread in a disposable Git project
with `approvalPolicy: "never"` and `sandbox: "read-only"`, then sends exactly:

```text
Reply with exactly: ORBITA_M0_OK. Do not use tools.
```

It uses the normally authenticated App Server startup without inspecting or
copying authentication storage. A single deadline bounds the handshake, thread,
turn, streaming, and terminal wait. EOF, timeout, an error response, a
non-matching terminal event, or any terminal status other than `completed`
fails closed.

The control slice is separately opt-in and consumes model quota:

```powershell
python -B spikes/app-server-probe/probe.py live-controls --confirm-live-model --timeout-seconds 120 --late-observation-seconds 2 --capture-output <sanitized-capture-path> --output <normalized-evidence-path>
```

It runs the root sentinel, a same-thread follow-up sentinel, then a distinct
long no-tools turn which it interrupts only after its matching `turn/started`.
It requires both the correlated interrupt response and a matching
`turn/completed` with `status: "interrupted"`.

## Issue #5 human-gated command approval runner

`approval_live_runner.py` is a separate, explicitly opt-in experiment for one
ordinary command approval. It is not run by the offline suite. It creates an
isolated disposable Git project and `CODEX_HOME`, uses `approvalPolicy:
"on-request"` with reviewer `user`, read-only sandboxing, and disabled network
access. The prompt permits only `echo ORBITA_APPROVAL_ACCEPTED`; any other
server request, policy/session decision, command, non-empty reason, network
context, or mismatched source correlation fails closed.

Run it only when a human is present to read the sanitized context and type the
one-shot decision after it is displayed:

```powershell
python -B spikes/app-server-probe/approval_live_runner.py --confirm-live-approval --output <sanitized-result-path>
```

The prompt accepts exactly `accept` or `decline`; Enter aborts. The runner does
not auto-approve, does not persist raw protocol lines, and stores only a
sanitized result at the explicit output path. It requires the same request ID,
thread ID, turn ID, and item context for the approval; a matching
`serverRequest/resolved`; and a correlated terminal turn event. An accepted
run additionally requires the fixed sentinel and `completed` terminal status.
No run result is a compatibility claim until reviewed.

The generated schema tree is deliberately not checked in: version 0.170.0 emits
808 JSON files. The fixture retains the exact commands, file counts, full-tree
canonical manifest digests, combined-bundle digests, and surface
classifications needed to regenerate and compare the contract without adding a
multi-megabyte snapshot.

## Requirements

- Python 3.12
- `jsonschema==4.26.0` from `requirements.txt`. This dependency is required to
  validate the generated Draft 7 contract's nested `$ref`, `oneOf`, and `anyOf`
  constructs reliably; the Python standard library has no JSON Schema validator.
- Git on `PATH`
- `codex-cli 0.170.0` on `PATH`

## Exact commands

From the repository root:

```powershell
python -B spikes/app-server-probe/probe.py capture-contract --output spikes/app-server-probe/fixtures/contract.json
python -B spikes/app-server-probe/probe.py initialize --output spikes/app-server-probe/fixtures/initialize.json
python -B -m unittest discover -s spikes/app-server-probe/tests -v
Get-FileHash -Algorithm SHA256 spikes/app-server-probe/fixtures/contract.json,spikes/app-server-probe/fixtures/initialize.json,spikes/app-server-probe/fixtures/live-turn-1.json,spikes/app-server-probe/fixtures/live-turn-2.json
```

The live command remains explicit opt-in and consumes model quota:

```powershell
python -B spikes/app-server-probe/probe.py live-turn --confirm-live-model --timeout-seconds 120 --output <review-path>
```

Each command overwrites only the explicitly supplied output file. Fixture
changes require human review; regeneration is evidence, not automatic approval.

## Surface classification for this pin

| Surface | Generated profile | Remediated live result |
| --- | --- | --- |
| `initialize` | stable | directly observed in both hardened runs |
| `initialized` | stable | directly observed in both hardened runs |
| `thread/start` | stable | directly observed in both hardened runs |
| `turn/start` | stable | directly observed in both hardened runs |
| `turn/started` | stable | directly observed in both hardened runs |
| `item/agentMessage/delta` | stable | directly observed in both hardened runs |
| `item/completed` | stable | directly observed in both hardened runs |
| `turn/completed` | stable | directly observed in both hardened runs |

Experimental schema generation is recorded separately and
`capabilities.experimentalApi` is explicitly `false` in the live exchange.
