# Diagnostics and Local Data

## Goals

Local data supports continuity, truthful monitoring, protocol diagnosis, and user-controlled export. It must not become a second execution authority or an unbounded hidden transcript archive.

## Data classes

### Durable normalized projection

Stores only the information needed to reconstruct the task workspace:

- root-task lifecycle and attention;
- source identities and relationship evidence;
- supported assignment or summary;
- execution status and outcome evidence;
- last observed activity;
- provenance and gap markers;
- runtime and projection schema versions.

The projection is a cache of observed facts. Reconciliation may correct it when App Server history provides stronger evidence.

### Bounded raw-event buffer

Retains a limited local window of protocol data for:

- unknown variants;
- projection debugging;
- compatibility regressions;
- recovery analysis;
- sanitized fixture production.

Raw data does not authorize UI state that the normalized mapping cannot justify. Buffer truncation creates an explicit gap.

### Diagnostic export

Export is an explicit user action. It includes version and capability context, selected sanitized events, gap information, and relevant application diagnostics. It does not silently include credentials or the entire project.

## Redaction stages

1. **Before persistence:** remove or replace known token, credential, and authentication fields before raw data reaches disk.
2. **During normalization:** omit payload content not required for the task workspace.
3. **During export:** run a stricter content-aware sanitation pass and present the export scope to the user.

Prompts, source code, paths, commands, and tool output remain sensitive even when known credential fields have been removed.

## Retention policy

No arbitrary TTL or size limit is canonical before M0. The first policy must be derived from measured event rates, payload sizes, recovery needs, diagnostic value, and sensitivity.

The resulting policy must remain:

- bounded by size, time, or both;
- local by default;
- partitionable enough to clear a root task or all Orbita data;
- explicit when truncation creates a recovery or diagnostic gap;
- resilient to buffer loss or corruption without losing the durable normalized projection.

## Continuity requirements

- Replaying the same source evidence is idempotent.
- A restart does not duplicate task cards or outcomes.
- Local lifecycle and attention remain distinct from source execution status.
- An unrecoverable interval is a gap, not an idle or successful period.
- A finished or archived task preserves its recoverable history.
- Reactivation uses the same root-task identity and thread when supported.

## User controls

The MVP must provide:

- a clear-data action;
- an explicit sanitized diagnostic export;
- visibility into unsupported or truncated history;
- an Automatic Finish setting;
- no default telemetry or automatic upload.

Fine-grained retention controls are added only if M0 evidence or real use demonstrates a need.

## M0 measurements

The [protocol spike](../protocol/spike-plan.md) must determine:

- representative and burst event volume;
- storage per root task;
- recovery-critical event classes;
- diagnostic-only event classes;
- content-heavy and credential-bearing fields;
- redaction effectiveness;
- truncation behavior;
- whether compression or operating-system-backed protection is warranted.
