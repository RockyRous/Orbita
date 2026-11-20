# M0 go/no-go assessment

## Decision status

**Current recommendation: no-go for the full task-centric agent workspace.** This is an evidence assessment for GitHub issue #8, not a product decision, issue closure, or approval to build production UI. A human must choose go, re-scope, or stop after the remaining live evidence is reviewed.

The assessment is pinned to `codex-cli 0.170.0`, the native executable digest `8d06dc231dba649c7d48d3eecab239c452a1ac498c41dd6492a6f301b90a22ce`, and stable-only generated bindings. App Server and its generators remain CLI-marked experimental. See [M0 contract research](../protocol/m0-contract-research.md).

## Evidence inventory

| Capability | Current evidence | Assessment |
| --- | --- | --- |
| Root task, terminal outcome | Hardened, reviewed fixtures `live-turn-1.json` and `live-turn-2.json`; semantic digest `491637aea23170f7c5e2ea44c420299c38e8d3090b852be592e3c3d220e682d3`. | Directly observed for this pin. |
| Follow-up and interrupt | Reviewed `live-controls.json` and normalized artifact prove same-root follow-up and correlated interruption. | Directly observed for this pin. |
| Delegation schema/projection | Stable contract research plus offline normalizer and failure diagnostics; live attempts did not establish complete two-child hierarchy. | Ambiguous/unavailable for required hierarchy fields. |
| Approval/attention | Contract research and offline normalization exist; no approved live request/response evidence. | Unavailable. |
| Continuity/recovery | Candidate stable read/history surfaces and offline replay/gap work exist; a bounded reconnect probe returned no source root identity and preserved an explicit gap. | Unavailable for recovery; safe gap fallback observed. |
| Retention/diagnostics | Offline sanitization and bounded-buffer preparation exist; representative live measurements remain incomplete. | Not a product retention decision. |

Exact implementation/evidence commits currently include:

- `9370179` — hardened root-task evidence;
- `a12bd17` — proven root-task capabilities;
- `fcdc332` — offline continuity and diagnostics probes;
- `9f63cd5` — M0 continuity recovery research;
- `b0e4180` — delegation observability boundary;
- `fc179df` — unavailable command-approval path.

Those commits document a pinned experiment, not a supported-version guarantee. The compatibility matrix remains authoritative: [compatibility.md](../protocol/compatibility.md).

## Blocking evidence gaps

### Hierarchy

MVP needs observable delegated work with an identity, direct parent relation, source assignment or explicit unavailable fallback, activity, outcome, and provenance. The current delegation runner/normalizer fails closed rather than inventing cards, but it has not yet produced an approved fixture proving two real child executions and every required field. Child failure remains an explicit blocker. See [delegation research](../protocol/m0-delegation-research.md).

### Approval and attention

No live fixture establishes a supported approval/user-question request, human resolution, negative outcome, late resolution, or reconnect treatment. Orbita cannot honestly expose actionable approval controls until that round trip is observed. See [approval research](../protocol/m0-approval-research.md).

### Recovery

No client-only restart, client-and-runtime restart, or active-work failure has proven source identity recovery, pagination, de-duplication, parent-edge recovery, or an explicit gap. `thread/read` and history-list methods are candidates, not proof. See [continuity research](../protocol/m0-continuity-research.md).

## Conditional re-scope that is currently defensible

If the human elects re-scope, the MVP may be limited to a **single local root-task observer** for the exact pinned runtime:

- start one root task; show its source-backed turn lifecycle and terminal outcome;
- support a same-thread follow-up and a correlated interrupt where the existing pin evidence applies;
- retain a bounded, sanitized local diagnostic/projection record; and
- show disconnects, unknown protocol variants, and unrecoverable intervals as explicit gaps.

This is not a multi-agent task tracker and must retain a visible compatibility/pin limitation. It must not silently replace a lost root task.

## Prohibited claims until evidence closes the gaps

- visible or complete subagent hierarchy, delegation count, parent edges, assignments, activity, results, failure, or recovery;
- actionable approvals, user questions, automatic approval, expiry, or reconnect replay;
- durable restart/reconnect recovery, historical completeness, pagination correctness, background continuation, or no-duplicate guarantees;
- support for another Codex version, feature profile, model/provider, transport, platform, or experimental surface; and
- terminal success inferred from EOF, timeout, silence, item completion, local cache, or model narration.

## Human decision required

Full go requires the live evidence demanded by [the spike plan](../protocol/spike-plan.md): hierarchy, approvals, continuity, deterministic replay, and data measurements. Until then, choose either:

1. **Re-scope** to the narrow root-task observer above; or
2. **Continue M0** with the three blocker slices before production UI work.

No issue is closed by this document.
