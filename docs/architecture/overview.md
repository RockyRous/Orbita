# Architecture Overview

## Boundary and topology

Codex owns model interaction, conversation state, tools, sandbox, approvals, orchestration, and authoritative execution history. Orbita owns the desktop user experience, supported commands, normalized projection, workflow links, and bounded diagnostics.

```text
React/TypeScript desktop UI
  ├─ Root chat
  ├─ Execution tracker
  └─ Workflow context
             │ typed Tauri commands + ordered projection channel
Rust application core
  ├─ runtime/version gate
  ├─ App Server process supervisor
  ├─ versioned protocol adapter
  ├─ normalized projection and provenance
  └─ redaction and bounded diagnostics
             │ newline-delimited JSON over child stdio
Codex App Server → selected local project under Codex policy
```

The React webview does not start processes, read the project, or own raw App Server semantics. Rust owns executable validation, structured arguments/cwd, stdin/stdout/stderr handling, initialization, correlation, validation, terminal classification, redaction, queues, and shutdown.

## Production shell

Orbita uses **Tauri 2** with **React, TypeScript, and Vite** for its Windows-first desktop shell. The detailed decision and least-privilege rules are [ADR 0003](../adr/0003-tauri-desktop-client.md). The fixture browser/Tkinter observer is not part of this topology.

## Projection boundary

Frontend state consists of product types such as runtime state, root-task/turn/activity projections, gaps, supported actions, and command results. Raw App Server requests and notifications remain behind a generated, versioned Rust adapter. An ordered channel carries sequence-numbered updates; a sequence gap triggers a snapshot request, never an invented intermediate state.

## Compatibility and evidence

The exact runtime remains pinned and capability-gated. Matching `turn/completed` is the only terminal source for a turn. EOF, process exit, timeouts, silence, item completion, and narration are never completion evidence. Unknown variants degrade only their affected projection and produce diagnostic/gap evidence.

## Workflow context

Plans, roles, and GitHub work items are explicit, provenance-carrying records separate from executions. A workflow link does not create an execution row, and an execution outcome does not mutate an issue.

## Deferred decisions

Persistence engine, signing/update channel, background service, production recovery topology, status mapping beyond evidence, and support beyond the pinned runtime require separate evidence and decisions.
