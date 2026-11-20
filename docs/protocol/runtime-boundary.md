# Runtime Boundary for the Desktop MVP

This document describes what the future Tauri/Rust core may claim for the currently qualified `codex-cli 0.171.0` Windows x64 profile. It is not a general compatibility promise.

## Confirmed root path

The 0.171.0 fixtures directly observed initialization over JSONL/stdio, root launch, same-thread follow-up, interruption, and matching authoritative terminal `turn/completed` outcome. The core must pin the native executable/version/digest and generated contract before enabling these commands. Historical 0.170.0 fixtures remain immutable evidence for their own profile.

## Launch and shutdown

Rust starts the exact `codex app-server` executable using structured executable, argument, and working-directory APIs. `stdout` is protocol JSONL; `stderr` is bounded diagnostics only. The core gates commands on successful initialization and owns coordinated stdin close/process shutdown.

Process EOF, exit, malformed JSON, timeout, or missing activity is a disconnect/degraded gap—not a terminal result. Closing a window with active work warns the user until background continuation is separately proven.

## Capability table

| Capability | Current claim | Desktop behavior |
| --- | --- | --- |
| Root launch | directly observed for pin | eligible for live slice after supervisor tests |
| Same-thread follow-up | directly observed for pin | eligible after lifecycle/UI tests |
| Interrupt | directly observed for pin | eligible after race tests |
| Terminal outcome | directly observed for pin | only matching `turn/completed` settles UI |
| Child hierarchy, role, assignment | ambiguous/unavailable | no hierarchy claim; show only direct evidence |
| Approval/action response | unavailable | no enabled approval control |
| Recovery/background continuation | unavailable | explicit gap/warning; no silent restart |

## Adapter rules

The adapter validates incoming and outgoing messages against generated, versioned contracts. Request IDs, thread IDs, and turn IDs are correlated explicitly. Unknown variants are bounded diagnostic evidence and degrade only their affected projection. Raw event shapes never become the React state contract.
