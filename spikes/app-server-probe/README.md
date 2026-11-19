# Orbita M0 App Server probe

This is a **throwaway M0 experiment**, not Orbita's production stack. It uses
Python's standard library to exercise only the public Codex App Server process
boundary over newline-delimited JSON on stdio.

The probe is pinned to `codex-cli 0.170.0`. It fails closed for another reported
version. The checked-in fixtures were produced with the launcher digest shown
in `fixtures/contract.json`; a different launcher is not silently accepted as
equivalent. The native executable digest is recorded separately in
`docs/protocol/m0-contract-research.md`.

## Proven boundary

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

The generated schema tree is deliberately not checked in: version 0.170.0 emits
808 JSON files. The fixture retains the exact commands, file counts, full-tree
canonical manifest digests, combined-bundle digests, and surface
classifications needed to regenerate and compare the contract without adding a
multi-megabyte snapshot.

## Requirements

- Python 3.12 (standard library only)
- Git on `PATH`
- `codex-cli 0.170.0` on `PATH`

## Exact commands

From the repository root:

```powershell
python -B spikes/app-server-probe/probe.py capture-contract --output spikes/app-server-probe/fixtures/contract.json
python -B spikes/app-server-probe/probe.py initialize --output spikes/app-server-probe/fixtures/initialize.json
python -B spikes/app-server-probe/probe.py live-turn --confirm-live-model --timeout-seconds 120 --output spikes/app-server-probe/fixtures/live-turn.json
python -B spikes/app-server-probe/probe.py live-turn --confirm-live-model --timeout-seconds 120 --output $env:TEMP/orbita-live-turn-run2.json
python -B -m unittest discover -s spikes/app-server-probe/tests -v
Get-FileHash -Algorithm SHA256 spikes/app-server-probe/fixtures/contract.json,spikes/app-server-probe/fixtures/initialize.json,spikes/app-server-probe/fixtures/live-turn.json
```

`live-turn` consumes model quota, which is why the confirmation flag is
mandatory. Each command overwrites only the explicitly supplied output file.
Fixture changes require human review; regeneration is evidence, not automatic
approval.

## Observed live evidence

Two clean-process runs succeeded on the pinned runtime. Each run consumed one
minimal model turn. Both independently observed:

- a source thread and turn identity;
- matching `turn/started` and `item/agentMessage/delta` evidence;
- matching `turn/completed` with status `completed`; and
- final agent text exactly `ORBITA_M0_OK`.

The raw runs legitimately differed in generated IDs and event ordinals. Their
deterministic repeatability projections were equal, with SHA-256:

```text
1657805055ed8d6db9e54cde54e3a58de1fbdfc82e103aea2b22844c45a32860
```

The reviewed sanitized `fixtures/live-turn.json` content SHA-256 is:

```text
dc8ca6b0375ea234cf224e3580fc98f3799e7bbac42d09b71eb437a9109527fd
```

## Surface classification for this pin

| Surface | Generated profile | Live result |
| --- | --- | --- |
| `initialize` | stable | directly observed |
| `initialized` | stable | directly observed |
| `thread/start` | stable | directly observed |
| `turn/start` | stable | directly observed, explicit opt-in only |
| `item/agentMessage/delta` | stable | directly observed |
| `turn/completed` | stable | directly observed with `completed` status |

Experimental schema generation is recorded separately and
`capabilities.experimentalApi` is explicitly `false` in the live exchange.
