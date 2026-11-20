# Desktop MVP Plan

This is the implementation contract for GitHub issue #13. Work is complete only when it satisfies its acceptance criteria and cites source evidence.

## Delivery slices

1. **Documentation and contracts:** ADR, architecture, product/UX state model, protocol runtime note, IPC/projection type contract, and third-party research inventory.
2. **Secure shell:** Tauri 2 + React/TypeScript/Vite scaffold; one least-privilege window capability; strict CSP; typed command/channel skeleton.
3. **Runtime core:** Codex discovery/pin gate; supervised App Server child; initialize/JSONL handling; fixture replay and unknown-variant isolation.
4. **Live root chat:** project selection, start thread/turn, ordered stream, safe event rendering, root row, terminal outcome.
5. **Proven controls:** same-thread follow-up, interruption races, close/disconnect behavior.
6. **Tracker and workflow:** source-backed execution rows and direct relationships; explicit plan/role/issue context; no synthetic cards.
7. **Reliability and release:** bounded redacted diagnostics, clear/export, reconciliation only when proven, Windows packaging smoke.

## Required ticket gates

Each slice is a separate GitHub issue. A ticket is not `ready-for-agent` until it identifies its protocol evidence, security boundary, tests, and dependencies. Unknown protocol capability blocks only the related UI claim; it does not justify a demo substitute.

## Reference policy

Happier, bb, and CodexUI may inform interaction research only. No source, asset, dependency, generated binding, design token, or copy is reused without exact upstream URL/commit, license review, security review, attribution plan, and an explicit issue.
