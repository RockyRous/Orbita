# M0 approval and attention research

## Purpose and scope

This note records the research and test design for [Issue #5](https://github.com/RockyRous/Orbita/issues/5). It asks one bounded question: which public Codex App Server requests can require a human response, and what evidence is sufficient to project them as attributable attention without inventing protocol behavior?

The findings are pinned to the locally installed `codex-cli 0.170.0`, its generated stable and experimental JSON Schemas, and the matching first-party source tag. App Server is still an experimental integration surface; a method appearing in stable schema generation does not make the whole App Server API stable or prove that a configured runtime will emit that method.

This work does not select a production framework, storage engine, status model, or UI. It follows [ADR 0001](../adr/0001-app-server-boundary.md), the source hierarchy in [compatibility.md](compatibility.md), Gate D of the [spike plan](spike-plan.md), and the pre-persistence rules in [diagnostics-and-data.md](../security/diagnostics-and-data.md).

## Evidence base

Independent contract evidence, in descending order of relevance to this pin:

1. `codex-cli 0.170.0`, `codex app-server --help`, and JSON Schemas generated locally both with and without `--experimental`.
2. The pinned first-party [server-request registry](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/app-server-protocol/src/protocol/common.rs), [v2 item types](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/app-server-protocol/src/protocol/v2/item.rs), [MCP elicitation types](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/app-server-protocol/src/protocol/v2/mcp.rs), [permission types](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/app-server-protocol/src/protocol/v2/permissions.rs), and [resolved-notification type](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/app-server-protocol/src/protocol/v2/notification.rs).
3. The pinned first-party [`request_user_input` round-trip test](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/app-server/tests/suite/v2/request_user_input.rs) and [turn-interrupt test](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/app-server/tests/suite/v2/turn_interrupt.rs). These are implementation evidence, not a substitute for Orbita observing its own runtime.
4. OpenAI's [App Server integration instructions](https://developers.openai.com/siwc/token-sharing-open-source/codex-app-server), which define newline-delimited stdio, initialization, thread/turn correlation, and `turn/completed` as the authoritative terminal signal.

Generated schema is a validation oracle, not a fixture generator. Expected values below are small literals derived independently from the sources. A fixture copied from implementation output and then asserted against itself is not a contract test.

## Confirmed public request surfaces

The 0.170.0 stable-generated `ServerRequest` union contains five current v2 request methods relevant to human attention. The same registry also contains two explicitly deprecated v1 methods for turns started through legacy APIs. Issue #5 must use `thread/start` and `turn/start`, so the deprecated `applyPatchApproval` and `execCommandApproval` methods are classified but are not test targets.

Here, **confirmed** means that the exact local executable exposes and types the JSON-RPC request and response surface. It does **not** mean that Orbita has observed a selected runtime emit it, that every model/configuration enables it, or that it is a supported product promise. In particular, the generated `ToolRequestUserInput*` types label themselves `EXPERIMENTAL` even though the method appears in the non-`--experimental` bundle. The separate `--experimental` bundle adds fields such as command `availableDecisions` and the MCP `openai/userVerification` elicitation mode; neither is part of the initial slice or a fallback payload.

| Method | Required source context in the generated contract | Response contract | Initial Issue #5 disposition |
| --- | --- | --- | --- |
| `item/commandExecution/requestApproval` | JSON-RPC request ID; `threadId`, `turnId`, `itemId`, `startedAtMs`; action `kind`; optional `approvalId`, command, cwd, reason, environment and policy context | `decision`; literal `accept`, `decline`, and `cancel` are supported. `decline` denies the command and continues the turn; `cancel` denies and immediately interrupts it. Session and policy-amendment decisions also exist. | Primary approval seam. Initially test only `kind: command` and the literal one-shot decisions. |
| `item/fileChange/requestApproval` | JSON-RPC request ID; `threadId`, `turnId`, `itemId`, `startedAtMs`; optional reason and `grantRoot` | `decision`: `accept`, `acceptForSession`, `decline`, or `cancel` | Valid secondary approval surface, but not required for the first slice. `grantRoot` is marked unstable/unclear and must not underpin a claim. |
| `item/tool/requestUserInput` | JSON-RPC request ID; `threadId`, `turnId`, `itemId`; `questions`; `isBlocking`; deprecated optional `autoResolutionMs` | `answers`, keyed by question ID, each containing an answer-string array | Candidate user-question seam. The method survives stable schema generation, but its source and payload descriptions explicitly say experimental. Availability remains runtime/configuration dependent until observed. |
| `mcpServer/elicitation/request` | JSON-RPC request ID; `threadId`; nullable `turnId`; `serverName`; mode-specific form or URL context | `action`: `accept`, `decline`, or `cancel`; accepted form content is mode-specific, while decline/cancel content may be null | Separate MCP elicitation seam. Useful for later coverage, not interchangeable with a command approval or tool question. |
| `item/permissions/requestApproval` | JSON-RPC request ID; `threadId`, `turnId`, `itemId`, `startedAtMs`, cwd, requested permissions; optional environment and reason | A granted permission profile plus `turn` or `session` scope; no accept/decline/cancel discriminator | Classify and preserve, but do not invent a denial payload. Defer a negative-path claim until first-party evidence or a pinned observation establishes it. |

The command and file-change parameter types carry the context needed for direct thread/turn/item attribution. `approvalId`, when present, disambiguates multiple callbacks associated with one command item; the JSON-RPC request ID still identifies the response envelope. MCP elicitation is different: `turnId` may legitimately be null because turn association is App Server correlation rather than the MCP request's protocol identity, and the pinned source says no MCP tool-item association is currently exposed.

The current command type also contains special `humanCommand` behavior guarded by the experimental `requiredHumanApproval` initialize capability. That is not the ordinary command-approval path and is outside the first Issue #5 slice.

## Confirmed resolution and terminal facts

`serverRequest/resolved` is a public server notification with exactly `threadId` and the original JSON-RPC `requestId`. It confirms that the matching server request is no longer pending. It contains no decision, cancellation reason, expiry reason, item ID, turn status, or execution result; none may be inferred from it.

The pinned `request_user_input` test demonstrates a response followed by `serverRequest/resolved` for the same request and thread before `turn/completed`. The pinned interrupt test demonstrates that interrupting a turn with a pending command approval resolves that exact request and then completes the turn with status `interrupted`. These establish useful expected examples, but Orbita must still accept safe interleaving and must not assert a global total event order beyond causally necessary relationships.

Attention and execution remain independent facts:

- receiving a supported pending request creates actionable attention;
- acknowledging or viewing attention does not respond to the request and does not change execution status;
- sending a response does not itself prove execution success;
- `serverRequest/resolved` closes only the matching pending request and does not determine the response decision or turn status; and
- only the correlated public turn lifecycle determines whether execution later completed, failed, or was interrupted.

No request may be auto-approved. The initial experiment must use a user reviewer and a policy that can ask for approval; it must not select session-wide acceptance, persistent policy amendments, guardian/automatic review, or any configuration that silently responds on the user's behalf.

## Unknowns that require pinned observation

The local contract does not establish the following. They must remain `unknown`, `unavailable`, or version-dependent until a sanitized run proves them:

- which safe prompt and runtime configuration deterministically causes the selected model to request an ordinary command approval;
- exact ordering between item notifications, the server request, its JSON-RPC response, `serverRequest/resolved`, and later turn events in all paths;
- the App Server error or ignore behavior for duplicate, malformed, mismatched, expired, or late responses;
- whether pending server requests are replayed after process restart or connection replacement, and how their age is communicated;
- any server-defined expiry interval or an expiry/cancellation reason carried outside the currently generated contract;
- whether `item/tool/requestUserInput` is emitted for the selected model, mode, and feature configuration;
- the runtime meaning of non-blocking questions. `autoResolutionMs` is deprecated; `isBlocking` is authoritative in the type, but App Server does not define a portable client countdown in the public payload;
- how a negative response should be represented for `item/permissions/requestApproval`;
- child-agent attribution for requests that lack a directly observed mapping from their source thread/item to an Orbita Agent Execution; and
- whether a particular MCP elicitation mode is enabled without experimental capability negotiation.

These unknowns are not permission to guess payloads or lifecycle states.

## Attribution and attention rules

For every supported request, preserve the JSON-RPC request ID, method, source thread, and every source identifier exposed by that method. Attribute only from observed correlations:

1. A command, file, permission, or tool-question request maps directly to its observed `threadId`, `turnId`, and `itemId`.
2. It maps to an Agent Execution only when an independently observed thread/item relationship proves that execution owns the source. Never infer ownership from arrival order, current selection, or the most recently active card.
3. An MCP elicitation with a non-null `turnId` may be attributed to that observed turn. With null `turnId`, show root/thread-level attention and the MCP server name; do not manufacture a turn or agent attribution.
4. A resolution clears only the pending record whose request ID and thread both match. A late resolution for another request or thread must not clear current attention.
5. Multiple pending requests remain independently actionable. A response or resolution for one cannot acknowledge or resolve the others.

All contract-exposed source context that is safe to render must be available to the user before a decision. Sensitive fields are sanitized for fixtures and diagnostics, but the product must not collapse a command, cwd, reason, requested permission, question, option, MCP server, or mode into an unattributed generic prompt.

## Safe synthetic scenario

The first live approval experiment, when separately authorized, should run only in a disposable Git repository with an isolated probe home, bounded deadlines, no MCP servers, no reusable credentials in the project, and no network need. Its sole intended command prints the fixed sentinel `ORBITA_APPROVAL_ACCEPTED` and performs no write. The model instruction should request exactly that command, require an approval checkpoint, forbid all other tools/actions, and forbid file or network access.

The scenario is successful only if the runtime emits a schema-valid ordinary `item/commandExecution/requestApproval` whose complete available source context is captured before any response. The harness pauses for an explicit test-operator choice. It then responds with the exact pinned response shape for `accept`, observes the matching `serverRequest/resolved`, observes the fixed sentinel through public command/turn evidence, and waits for the correlated terminal turn outcome.

Repeat from a fresh disposable environment with the literal `decline` decision. The independent expected behavior is that the selected command does not produce the sentinel and the request resolves; the contract says the agent may continue the turn, so the test must not require immediate terminal interruption. A later separate `cancel` slice may require an interrupted terminal outcome, but only after the accept/decline tracer bullets pass.

If the model does not request approval, issues another tool call, proposes a different command, requests network/file access, or the runtime cannot satisfy the safety constraints, abort the run and record the capability as unproven. Do not send a synthetic response to a request that was not received, and do not weaken the sandbox merely to force a pass.

The user-question scenario is fixture-first. Use a non-secret, single-choice question with fixed benign labels and no free-form personal data. A live question round trip is optional until the selected runtime/configuration is shown to emit `item/tool/requestUserInput`; otherwise the explicit unavailable result below satisfies the Issue #5 research handoff without claiming support.

## Approved test seams

### Seam 1: public App Server process boundary

Launch the pinned executable over newline-delimited stdio and observe only public JSON-RPC envelopes, server requests, responses, notifications, process termination, and bounded deadlines. Validate each relevant message against the exact generated schema profile recorded by the run.

This seam catches method availability, public payload shape, request/response correlation, resolution, and terminal behavior. It does not inspect private Codex storage, internal queues, terminal UI, or implementation helpers.

Minimal red-green slices, implemented one at a time:

1. **A1 — accept one harmless command.** Require the exact method literal, non-empty required source identifiers, a matching JSON-RPC response ID, a matching `serverRequest/resolved`, the fixed sentinel, and an authoritative terminal outcome. Do not assert generated ID formats, timestamps, incidental notifications, human-readable error text, or a total event order.
2. **A2 — decline the same command.** Require no sentinel, a matching resolution, and no false actionable attention afterward. Do not assert that decline interrupts the turn; the pinned contract says it continues.
3. **A3 — cancel after A1/A2 are proven.** Require matching resolution and a correlated terminal `interrupted` outcome. Do not derive interruption from the resolution notification alone.
4. **A4 — question round trip or explicit unavailability.** If the runtime emits `item/tool/requestUserInput`, validate every question and answer against the pin, respond by matching question ID, require matching resolution, and prove that acknowledgement alone sent no answer. Otherwise emit the bounded unavailable result defined below.
5. **A5 — late and mismatched events fail closed.** A resolution for the wrong request/thread, a duplicate response, a response after observed resolution, or disconnect before resolution may produce a documented error or remain unknown, but can never approve an action, clear unrelated attention, or create a successful turn outcome.

### Seam 2: deterministic normalized attention fixtures

Feed a finite, hand-reviewed sanitized transcript plus its run manifest into the public normalization/projection boundary. This suite is offline and never launches a model or App Server. It catches unsafe fixture production, wrong attribution, request-ID collisions, false clearing, and implementation-coupled status assertions; it does not prove that the live runtime emits a fixture.

Hand-author the smallest fixture pairs needed for:

- pending command approval with all required source context;
- accepted, declined, and cancelled resolutions, each preserving the response evidence separately from terminal turn evidence;
- a tool question with one benign answer and a matching resolution;
- a null-turn MCP elicitation attributed only to its thread;
- two simultaneous requests where resolving one leaves the other actionable;
- a late resolution for an old request that cannot clear a newer request; and
- disconnect/expiry with no protocol proof, projected as non-actionable unknown/stale evidence rather than a response-capable prompt.

Expected normalized values are reviewed literals: method classification, deterministic source aliases, response kind where directly observed, `pending` versus `resolved` request evidence, attention required/not required, attribution confidence, and separately observed terminal status. Tests must not assert helper calls, internal class names, storage rows, UI strings, or a production status enum.

## Fixture sanitation and repeatability

Sanitize before writing any fixture. Unsanitized protocol content may exist only in memory or a disposable capture directory that is removed after normalization.

1. Validate against the recorded stable or experimental generated schema before projection. Unknown or invalid payloads fail closed into a bounded sanitized diagnostic; they never become actionable approval UI.
2. Replace request, thread, turn, item, approval, elicitation, and environment IDs with deterministic typed aliases assigned by first causal definition. Preserve referential equality across request, response, and resolution.
3. Retain only the fixed synthetic command, sentinel, benign question/option literals, and decision/action enums needed by the test. Redact other command text, reasons, tool arguments, file-change content, permission paths, MCP messages, schemas, metadata, and response content.
4. Replace cwd, repository, home, username, and temporary paths with typed placeholders. Remove tokens, cookies, authorization data, environment values, URL query/fragment data, and credential-shaped strings by case-insensitive policy.
5. Never persist answers for `isSecret: true`. Secret-question coverage, if later required, records only that a secret field existed and was not retained. The first fixture uses `isSecret: false`.
6. Preserve transcript order, but omit or alias wall-clock values, durations, request IDs, and other volatility from the semantic projection. Canonically serialize UTF-8 JSON with sorted object keys, preserved array order, no insignificant whitespace, and one trailing newline.
7. Scan sanitized keys and string values for seeded secrets and private paths. Fixture emission fails if any forbidden value remains.

Each full fixture has a content SHA-256. A fixture pair representing equivalent runs also has a semantic digest over only:

```text
runtime/version + executable and generated-contract identities
feature profile + transport
request method and stable/experimental classification
source-correlation facts and required evidence kinds
observed response kind + matching resolution fact
separate terminal method/status and fixed sentinel-present fact
attention-required and attribution-confidence facts
```

The expected semantic projection and digest are independently reviewed test data. Different raw IDs, timestamps, disposable paths, and harmless extra notifications must not change the semantic digest. Different decisions, request methods, attribution, resolution, or terminal outcomes must change it.

## Expiry, disconnect, and late-event policy

The 0.170.0 generated resolution notification has no expiry signal. Therefore Orbita must not label a request expired merely because a local timer elapsed. A local UI timeout may stop presenting a response control, but its evidence classification remains `unknown/stale` until a public response, matching resolution, terminal event, or documented reconnect replay proves more.

On disconnect with an unresolved request, disable response actions and remove false `Action required`; surface connection/reconciliation attention instead. Re-enable the original action only if the current runtime replays a schema-valid request that can be proven to be the same pending request. Never resend an approval response speculatively after reconnect.

A matching late `serverRequest/resolved` is idempotent closure evidence. It cannot change execution status or clear another request. A late server request associated with an already terminal turn is retained as sanitized contradictory evidence and is not actionable until a documented runtime rule proves otherwise.

## Explicit unavailable fallback

Use this result when a pinned live slice cannot establish a capability:

```json
{
  "capability": "approval-or-user-question",
  "availability": "unavailable-or-unproven",
  "runtime": "codex-cli 0.170.0",
  "reasonCode": "request-not-observed-or-contract-ambiguous",
  "actionableAttention": false,
  "responseEnabled": false,
  "supportClaim": false
}
```

The concrete capability and reason code may be narrowed to a reviewed literal such as `tool-user-input` and `experimental-method-not-observed`; do not copy free-form implementation errors into expected values. This fallback is preferable to fabricating an approval payload, treating silence as acceptance, or leaving a stale action enabled.

## Deliberately not tested or claimed

This Issue #5 design does not claim support for:

- deprecated v1 `applyPatchApproval` or `execCommandApproval`;
- `humanCommand`, automatic/guardian review, session acceptance, persistent exec/network policy amendments, or strict auto-review;
- permission-request denial/cancellation until its public response contract is established;
- every MCP elicitation mode, device verification, URL navigation, secret input, or third-party MCP server;
- reconnect replay, durable recovery, expiry timing, child-agent routing, or offline/background completion;
- production projection/storage/status models, UI layout, notifications, exports, or retention policy; or
- compatibility with any executable, schema digest, model, provider, feature profile, transport, or operating system other than the recorded run.

Passing fixture tests alone proves projection logic only. Passing one live path proves only that path for its recorded pin. It does not change the repository's current no-supported-version compatibility statement.

## Builder handoff

After implementation exists, the builder should expose one explicit-opt-in live process command and one pure offline normalization command. Implement A1, then its matching fixture; A2, then its matching fixture; continue one vertical slice at a time. Keep live tests separate from mandatory offline tests.

Before Issue #5 can close:

1. regenerate stable and experimental schemas from the exact executable and record their digests and classifications;
2. run the accept and negative live slices from fresh disposable environments with a human response gate and no automatic reviewer;
3. test a supported tool question or record the explicit unavailable result;
4. prove request/thread/item attribution from public evidence and keep attention acknowledgement independent from execution status;
5. replay sanitized fixture pairs in fresh processes and compare reviewed semantic digests;
6. scan all fixtures and diagnostics for forbidden content;
7. record any ordering, expiry, disconnect, duplicate, or late-response behavior as observation scoped to the exact pin, not as a universal contract; and
8. require human review for every fixture or expected-value change. Never overwrite an approved fixture automatically.
