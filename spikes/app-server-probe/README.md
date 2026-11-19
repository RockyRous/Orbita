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
   non-empty source thread ID.

Before persistence, the probe replaces the private Codex home, disposable
project path, server user agent, and source thread ID with typed placeholders.
It does not parse terminal output or read private Codex storage.

`turn/start` is present in the stable generated contract, but this probe does
not execute it. A root turn would invoke a live model, consume quota, and have
network-dependent behavior. Therefore streaming evidence, `turn/completed`,
terminal status, and final model text remain **not observed** in this safe run.

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
python -B -m unittest discover -s spikes/app-server-probe/tests -v
Get-FileHash -Algorithm SHA256 spikes/app-server-probe/fixtures/contract.json,spikes/app-server-probe/fixtures/initialize.json
```

`capture-contract` and `initialize` overwrite only the explicitly supplied
output file. Fixture changes require human review; regeneration is evidence, not
automatic approval.

## Surface classification for this pin

| Surface | Generated profile | Live result |
| --- | --- | --- |
| `initialize` | stable | directly observed |
| `initialized` | stable | directly observed |
| `thread/start` | stable | directly observed |
| `turn/start` | stable | not executed (live model/quota boundary) |

Experimental schema generation is recorded separately and
`capabilities.experimentalApi` is explicitly `false` in the live exchange.
