# ADR 0003: Use Tauri 2 with React and TypeScript for the desktop client

- Status: Accepted
- Date: 2026-11-20

## Context

The Tkinter and browser observer were fixture-backed protocol demonstrations, not a Codex client. The confirmed product requires a Windows desktop application with a functional root chat and an evidence-driven tracker. The pinned experiment directly observed root launch, same-thread follow-up, interruption, and authoritative terminal outcome; hierarchy, approvals, recovery, and background continuation remain evidence-gated.

## Decision

Use Tauri 2 as the Windows desktop shell, React + TypeScript + Vite for the UI, and a Rust application core as the sole privileged boundary to a local `codex app-server` child over stdio.

Rust owns runtime discovery, exact-version/capability validation, structured process spawning, JSONL parsing, request correlation, protocol adaptation, projection, redaction, bounded diagnostics, and lifecycle handling. React receives only typed product projections via narrow Tauri commands and an ordered update channel.

## Security constraints

- No general shell/process, filesystem wildcard, remote origin, CDN, telemetry, or automatic upload permission is granted to the webview.
- Tauri capabilities are limited to the `main` window and explicitly enumerated commands.
- Rendered model/tool output is untrusted: no HTML injection, arbitrary command execution, or implicit external-link opening.
- The app starts Codex with executable/argument/cwd APIs, never shell interpolation.
- Credentials and raw transcripts do not enter frontend storage; redaction precedes persistence/export.

## Protocol constraints

Only matching authoritative `turn/completed` settles a turn. EOF, silence, timeouts, process exit, and item completion do not. A control is enabled only after a pinned round trip, a lifecycle-valid Rust command, positive and negative fixtures/tests, and UI handling for pending/error/terminal evidence. Fixture/demo mode is excluded from the production path.

## Consequences

This provides a production-oriented desktop path while retaining Codex as authority. It adds Rust/MSVC/WebView2/Node toolchain cost and two typed boundaries (App Server↔Rust and Rust↔TypeScript). It does not decide persistence, signing, auto-update, background continuation, hierarchy, approvals, recovery, or support for other Codex versions.

## Rejected alternatives

- Continuing Tkinter: inadequate for a rich streamed chat and dense tracker, and it was never agreed product direction.
- Browser-only observer: not the requested desktop application.
- Forking Happier, bb, or CodexUI: these are research references only; their code/assets/dependencies require a separate license and security review before any reuse.
