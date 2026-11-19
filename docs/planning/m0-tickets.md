# Draft M0 Ticket Breakdown

This is a review draft. Do not publish these tickets until the user approves their granularity and blocking edges.

## Proposed parent

**M0: Prove the Codex App Server foundation for an observable agent workspace**

The parent tracks the go/no-go gate described in [the protocol spike plan](../protocol/spike-plan.md). Child tickets are narrow, independently verifiable slices. Proposed labels refer to the repository's configured GitHub vocabulary. A blocked ticket does not receive a readiness label until every native blocking edge is closed.

## 1. Prove one pinned root-task round trip

**Blocked by:** None.

**What it delivers:** A reproducible probe that uses one pinned App Server contract to start a root task in a disposable project and observe its terminal result without terminal parsing.

**Acceptance criteria:**

- [ ] The runtime version, feature configuration, transport, generated contract, and output digest are recorded.
- [ ] A client initializes through a public App Server surface.
- [ ] One root thread and turn start successfully.
- [ ] Streaming evidence and an authoritative terminal outcome are captured in a sanitized fixture.
- [ ] A repeated clean run produces the same contract classification and an equivalent observable result.
- [ ] Unsupported or experimental surfaces are identified explicitly.

**Proposed labels:** `ready-for-agent`, `enhancement`, `documentation`

## 2. Prove follow-up and interruption on the same root task

**Blocked by:** Ticket 1.

**What it delivers:** A user can continue the same root task with a follow-up and interrupt an active turn, with both outcomes tied to the original thread.

**Acceptance criteria:**

- [ ] A follow-up creates a new turn under the same root-task identity.
- [ ] The follow-up result is distinguishable from the previous turn.
- [ ] An active turn can be interrupted through a supported action.
- [ ] The interrupted outcome is confirmed by source evidence rather than transport silence.
- [ ] Error, timeout, and late-event behavior are captured in fixtures and tests.

**Proposed labels:** `enhancement`

**Triage transition:** add `ready-for-agent` after Ticket 1 closes.

## 3. Prove an evidence-backed multi-agent hierarchy

**Blocked by:** Ticket 1.

**What it delivers:** A reproducible delegated-work scenario and a capability matrix that establishes which root and subagent task cards Orbita can truthfully show.

**Acceptance criteria:**

- [ ] The scenario causes multiple real subagent executions through supported configuration.
- [ ] Identity, parent relationship, assignment or source summary, activity, and outcome are evaluated separately.
- [ ] Each projected field is classified as direct, safely derived, unavailable, ambiguous, or version/feature dependent.
- [ ] Missing identity or relationship data produces a documented weaker fallback rather than a fabricated card or edge.
- [ ] Child failure and unavailable child detail are represented in sanitized fixtures.
- [ ] The scenario can be replayed in contract tests without a live model run.

**Proposed labels:** `enhancement`, `documentation`

**Triage transition:** add `ready-for-agent` after Ticket 1 closes.

## 4. Prove approval and attention round trips

**Blocked by:** Ticket 1.

**What it delivers:** Supported approvals and user questions appear as attributable attention, and user responses complete a verified protocol round trip.

**Acceptance criteria:**

- [ ] At least one approval request is captured with all source context exposed by the contract.
- [ ] Accept and one negative resolution are tested where supported.
- [ ] A supported user question is tested or documented as unavailable.
- [ ] Resolution, cancellation, expiration, and late events do not leave false `Action required` state.
- [ ] Attention acknowledgement does not change execution status.
- [ ] No action is auto-approved.

**Proposed labels:** `enhancement`

**Triage transition:** add `ready-for-agent` after Ticket 1 closes.

## 5. Prove deterministic continuity across restart

**Blocked by:** Tickets 2, 3, and 4.

**What it delivers:** The same root-task workspace can be reconstructed after client and runtime interruptions without duplicate task cards or invented completion.

**Acceptance criteria:**

- [ ] Client-only restart is tested during active work.
- [ ] Client and runtime restart are tested.
- [ ] A failure during delegated work is tested.
- [ ] Replayed and duplicate events produce an equivalent idempotent projection.
- [ ] Root identity, supported child relationships, outcomes, and attention reconcile correctly.
- [ ] Missing intervals are visible as gaps.
- [ ] Background continuation paths are classified as supported, unsafe, or unavailable.
- [ ] The test never starts a silent replacement root task.

**Proposed labels:** `enhancement`

**Triage transition:** add `ready-for-agent` after Tickets 2, 3, and 4 close.

## 6. Bound and sanitize local diagnostic data

**Blocked by:** Tickets 3, 4, and 5.

**What it delivers:** Measured local-data requirements and a tested sanitation pipeline preserve monitoring and recovery without silently retaining credentials or unbounded raw history.

**Acceptance criteria:**

- [ ] Representative event counts, rates, bursts, payload sizes, and per-task storage are measured.
- [ ] Recovery-critical and diagnostic-only event classes are distinguished.
- [ ] Synthetic tokens, passwords, paths, prompts, commands, and tool-output secrets exercise the pipeline.
- [ ] Known credential fields are removed before persistence.
- [ ] Normalized projection omits payload content it does not need.
- [ ] Export applies a second sanitation pass.
- [ ] Buffer overflow creates an explicit gap and does not corrupt the durable projection.
- [ ] Clearing local data removes both projection and raw diagnostic data.
- [ ] The ticket recommends measured retention bounds without implementing unrelated settings.

**Proposed labels:** `enhancement`, `documentation`

**Triage transition:** add `ready-for-agent` after Tickets 3, 4, and 5 close.

## 7. Decide the M0 product gate

**Blocked by:** Tickets 1 through 6.

**What it delivers:** A human-reviewable go/no-go decision that limits Orbita's MVP promises to capabilities demonstrated by the pinned runtime.

**Acceptance criteria:**

- [ ] Capability and recovery matrices contain evidence for every required MVP behavior.
- [ ] The minimum identity, work description, activity, outcome, and provenance threshold is evaluated explicitly.
- [ ] Supported, degraded, unavailable, and unsafe-to-infer behaviors are documented.
- [ ] Runtime ownership options are compared using measured lifecycle and recovery behavior.
- [ ] The decision identifies which product and architecture documents must change.
- [ ] A human approves go, re-scope, or stop before production UI work begins.

**Proposed labels:** `documentation`

**Triage transition:** add `ready-for-human` after Tickets 1 through 6 close.

## Dependency view

```text
1 Prove root round trip
├── 2 Prove follow-up and interruption ─┐
├── 3 Prove multi-agent hierarchy ─────┼── 5 Prove continuity ─┐
└── 4 Prove approval and attention ────┘                      ├── 6 Bound diagnostic data
                                                              └───────────────┐
1-6 ──────────────────────────────────────────────────────────────────────────┴── 7 Decide gate
```

Before publication, confirm that each ticket fits one fresh agent context and that no edge represents mere convenience rather than a genuine blocker.
