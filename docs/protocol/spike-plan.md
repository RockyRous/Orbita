# M0 Protocol Spike Plan

## Objective

Determine whether a pinned Codex App Server can support Orbita's truthful task-centric workspace before selecting a production desktop architecture.

## Constraints

- Use only public supported or explicitly identified experimental App Server surfaces.
- Do not parse terminal presentation text or read private Codex storage.
- Do not invent payload fields, agent relationships, or completion rules.
- Keep experiments in a disposable Git repository with synthetic secrets and non-sensitive content.
- Record runtime version, feature configuration, transport, and contract digests for every fixture.

## Gate A: Contract pinning

1. Record the Codex CLI/App Server version and enabled features.
2. Generate the available schema and bindings from that binary.
3. Classify every surface used by the probe as stable, experimental, deprecated, or unavailable.
4. Establish a reproducible initialization path.

**Acceptance:** another clean run with the same pinned inputs can initialize and validate the same contract.

## Gate B: Root-task round trip

1. Start the App Server through a public runtime path.
2. Initialize a client in a disposable project.
3. Create a root thread and start a turn.
4. Capture streaming events and the authoritative terminal outcome.
5. Send a follow-up in the same thread.
6. Interrupt a separate turn and capture the confirmed outcome.

**Acceptance:** root launch, follow-up, interrupt, error, and outcome are demonstrated by request/response/event evidence without terminal parsing.

## Gate C: Agent observability

Run a scenario that causes Codex to delegate independent work to multiple subagents using only supported configuration.

For root and child executions, test:

- identity and correlation;
- parent relationship;
- assignment or source summary;
- first and last observed activity;
- active, waiting, successful, failed, interrupted, and unknown evidence;
- tool activity and result availability;
- several concurrent children;
- child failure and missing child details.

**Acceptance:** every projected field is classified as direct, safely derived, unavailable, ambiguous, or version/feature dependent and is backed by a sanitized fixture.

## Gate D: Attention and controls

Exercise:

- an approval request and valid response;
- a declined or cancelled approval where supported;
- a supported user question where available;
- interrupt during active work;
- late events and races around resolution;
- attribution of attention to a root or child execution.

**Acceptance:** each supported action has a complete round trip and a negative scenario. Unsupported distinctions are documented rather than simulated.

## Gate E: Continuity

Test three recoveries:

1. client restart while the runtime remains available;
2. client and runtime restart;
3. client or runtime failure during active agent work.

Measure:

- stable identities;
- replay and pagination behavior;
- parent relationship recovery;
- outcome and attention recovery;
- duplicate delivery;
- ordering limitations;
- live-only gaps;
- late events;
- pending approval replay or expiration;
- whether background continuation is safe through any public runtime path.

**Acceptance:** a cold restart produces a coherent projection without fabricated completion or duplicate task cards, and missing intervals are visible as gaps.

## Gate F: Deterministic projection

- Replay a fixture more than once and compare normalized projections.
- Deliver duplicate events and verify idempotency.
- Introduce an unknown variant and verify graceful degradation.
- Change a fixture version and exercise migration or safe rebuild behavior.
- Trace every status-bearing projection back to evidence.

**Acceptance:** equivalent input produces an equivalent projection, duplicates do not multiply state, and unknown variants do not break unrelated work.

## Gate G: Retention and sensitivity measurement

Measure representative scenarios for:

- event count and rate;
- burst behavior;
- payload-size distribution;
- storage per root task;
- content-heavy payload classes;
- recovery-critical versus diagnostic-only events;
- overflow behavior for a bounded buffer;
- prompts, source, paths, commands, environment-like data, and credential-bearing fields.

Seed synthetic tokens, passwords, private paths, and secrets in prompts and tool output. Verify pre-persistence redaction of known credential fields, minimal normalized storage, a second sanitation pass on export, explicit gap behavior after truncation, and complete local-data clearing.

**Acceptance:** retention, size, compression, and redaction recommendations are based on measurements. Seeded credentials are absent wherever the policy promises they are absent.

## Exit deliverables

- Pinned contract and digests.
- Reproducible probe.
- Sanitized fixtures.
- Typed adapter for the tested surface.
- Capability and recovery matrices.
- Projection replay tests.
- Retention and sensitivity report.
- Explicit supported, degraded, and unavailable product promises.
- A go/no-go recommendation against the minimum in [compatibility.md](compatibility.md).

Production framework, IPC, process topology, persistence engine, and exact execution-status mapping remain undecided until these deliverables are reviewed.
