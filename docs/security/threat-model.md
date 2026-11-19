# Threat Model

## Scope

This threat model covers the single-user, local Windows MVP: one project, one root task, a local Codex App Server, local projections, a bounded diagnostic buffer, and a desktop user interface. Remote access, multi-user operation, plugins, and additional harnesses are outside the MVP.

## Assets

- Source code and files in the selected project.
- Codex authentication state and runtime policy.
- Prompts, model output, tool arguments, command output, and approvals.
- Root-task and agent-execution history.
- Local project paths and user identity information.
- Release signing credentials and distributed application artifacts.

## Trust boundaries

1. **User to Orbita UI:** user intent enters through root input, approvals, interruption, follow-up, and lifecycle actions.
2. **Rendered content to privileged application code:** model output, Markdown, code, paths, tool results, and diagnostics are untrusted display content.
3. **UI to native/runtime boundary:** UI actions may reach process, filesystem, or App Server capabilities.
4. **Orbita to App Server:** bidirectional protocol messages can request privileged user decisions and carry sensitive content.
5. **App Server to selected project:** Codex may read and modify project files under its configured policy.
6. **Memory to local persistence:** projections and raw events move sensitive content onto disk.
7. **Local data to diagnostic export:** export can cross the user's trust boundary.
8. **Build system to distributed artifact:** dependencies and release infrastructure can affect every installation.

## Threats and required controls

### Fabricated or stale execution state

**Risk:** Orbita presents an execution as successful, waiting, or related to a parent without sufficient evidence.

**Controls:** source provenance, explicit unknown and gap states, deterministic replay, versioned mappings, and no completion inference from silence.

### Confused-deputy approvals

**Risk:** the user approves an action without understanding its source, project, command, path, tool, or consequences.

**Controls:** show all source context exposed by the contract, keep approval and execution status separate, avoid reusable approval policy outside Codex, and reject stale or already-resolved prompts.

### UI content injection

**Risk:** untrusted Markdown, HTML, links, ANSI sequences, file names, or tool output executes script or invokes privileged application actions.

**Controls:** safe rendering, restrictive content policy, no remote executable content, explicit link handling, and a narrow native-command allowlist. Framework-specific controls are selected after M0.

### Process and argument injection

**Risk:** a project path or user value is interpolated into a shell command.

**Controls:** structured process arguments, explicit working directories, no shell interpolation, and validation of the executable and runtime version.

### Filesystem escape

**Risk:** relative paths, symlinks, junctions, alternate path forms, or race conditions cause an Orbita-owned filesystem action to target data outside the intended project.

**Controls:** resolve and verify target identity at the operation boundary, treat Windows path forms explicitly, minimize Orbita-owned file actions, and leave Codex actions under Codex policy.

### Credential and content retention

**Risk:** raw events, diagnostics, or projections persist tokens, prompts, source, commands, or environment data longer than expected.

**Controls:** minimal normalized projection, pre-persistence redaction of known credential fields, bounded raw storage, sensitivity measurement, explicit clearing, local-only defaults, and a separate sanitation pass for export.

### Silent duplicate execution

**Risk:** recovery starts a replacement root task and repeats file or command side effects.

**Controls:** reconnect and reconcile existing identity; never silently replace or restart a root task; make any new execution an explicit user action.

### Silent task termination

**Risk:** closing the UI terminates active work without warning.

**Controls:** continue safely in the background only when M0 proves the lifecycle; otherwise warn before stopping work and show the recovered outcome or gap on return.

### Protocol drift

**Risk:** an App Server update changes fields or semantics and causes unsafe controls or false state.

**Controls:** version and capability checks, generated contracts, unknown-variant preservation, compatibility tests, and affected-feature degradation.

### Supply-chain compromise

**Risk:** a dependency, build workflow, update channel, or signing key delivers malicious application code.

**Controls:** locked dependencies, dependency review, third-party notices, reproducible checks, least-privilege CI, signed artifacts and updates, protected signing keys, and provenance or attestations where practical.

## Security invariants

- Orbita never auto-approves a Codex action.
- Orbita never displays hidden chain-of-thought.
- Orbita never silently starts a replacement task after failure.
- Orbita never uploads diagnostic or usage data by default.
- Orbita never treats local cache as authoritative execution history.
- Unknown protocol data cannot grant a privileged action.

## Deferred threats

Remote access, shared workspaces, third-party plugins, additional harnesses, and automatic updates require separate threat-model extensions before implementation.
