# M0 delegation research: evidence-backed hierarchy on Codex 0.170.0

## Scope and status

This note supports [Orbita issue #4](https://github.com/RockyRous/Orbita/issues/4). It identifies the delegation evidence exposed by the exact local `codex-cli 0.170.0` contract and by first-party OpenAI source at the matching `rust-v0.170.0` tag. It does not claim that a live model produced any child execution. This research track did not start a model turn.

The distinction is important:

- **Confirmed fact** means the exact local stable-only generated contract, local help, or version-pinned first-party implementation directly establishes the shape or mapping.
- **Candidate** means the contract can represent the fact and the runtime source has a plausible delivery path, but issue #4 still needs a live sanitized fixture from the pinned configuration.
- **Unknown** means neither schema presence nor inspected source proves the behavior required by Orbita. Unknowns must remain gaps or weaker fallbacks.

The product terms in this note follow [GLOSSARY.md](../../GLOSSARY.md): an agent execution is an observed runtime execution, a task card represents exactly one observable agent execution, and provenance is required for every displayed claim.

## Pinned local snapshot and reproduction

The inspected runtime is the same Windows x64 installation recorded in [the root-round-trip research](m0-contract-research.md):

| Item | Value |
| --- | --- |
| CLI | `codex-cli 0.170.0` |
| Native executable SHA-256 | `8d06dc231dba649c7d48d3eecab239c452a1ac498c41dd6492a6f301b90a22ce` |
| Official release | [`rust-v0.170.0`](https://github.com/openai/codex/releases/tag/rust-v0.170.0) |
| Release commit | [`29eb79e9866b3262a777fdf8195c1b9e63684c91`](https://github.com/openai/codex/commit/29eb79e9866b3262a777fdf8195c1b9e63684c91) |
| App Server marker | `[experimental]` in local `codex app-server --help` |
| Contract profile used for claims below | generated without `--experimental` |

Reproduce the relevant local inspection without a model turn:

```powershell
codex --version
codex app-server --help
codex app-server generate-ts --help
codex features list | Select-String -Pattern 'multi_agent|agent_identity|runtime_agent|subagent|collaboration'

$probeRoot = Join-Path ([IO.Path]::GetTempPath()) ('orbita-m0-delegation-' + [guid]::NewGuid().ToString('N'))
codex app-server generate-ts --out (Join-Path $probeRoot 'ts-stable')
codex app-server generate-ts --experimental --out (Join-Path $probeRoot 'ts-experimental')
```

Relevant effective feature rows on the inspected machine were:

```text
collaboration_modes                      removed            true
multi_agent                              deprecated         true
multi_agent_v2                           stable             false
multi_agent_v2_dynamic_tools             under development  false
runtime_agent_instances                  under development  false
subagent_default_context_limits          under development  false
subagent_thread_environments             under development  false
use_agent_identity                       under development  false
```

The first-party feature registry agrees that legacy `multi_agent` is deprecated/default-on, while `multi_agent_v2` is stable/default-off; the related dynamic-tools and subagent-environment features are under development/default-off ([feature registry, lines 1651-1685](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/features/src/lib.rs#L1651-L1685)). Enabling `multi_agent_v2` selects V2 ahead of legacy behavior ([configuration selection, lines 1729-1755](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/core/src/config/mod.rs#L1729-L1755)). Feature stage does not upgrade the top-level App Server command from its local `[experimental]` marker.

The contract snapshot above was generated with no delegation override; its `multi_agent_v2` row was therefore `stable false`. A stable-only type proves only that this binary exports the type without the generator's experimental filter. It does **not** prove that either legacy or V2 delegation is effective for a live connection. Any run that enables `multi_agent_v2` must record that override and regenerate or re-digest its contract before its observations can be compared with this note.

The following stable-only generated files were byte-identical to their committed counterparts at `rust-v0.170.0`:

| Generated file | SHA-256 |
| --- | --- |
| `SubAgentSource.ts` | `6fa78b756bd916c4254a9c84655dbbcc45654790f7a9890f6809c4fbf8e45ecb` |
| `v2/Thread.ts` | `a6a528b2d88115ff3fe8db1c32ced5a90a1af3ec3fa0cfe39106931d6cccebd6` |
| `v2/ThreadItem.ts` | `55b1c9faf87ac8827c690566df253a7de5b5f3df5a2391f3b3696162e24b3380` |
| `v2/CollabAgentStatus.ts` | `0ec81079c0ca4737c448fc415250fc9c93d1385e7aafbc468226cf9ecabe8630` |
| `v2/ItemCompletedNotification.ts` | `bc22cba12c9b96529356b1f90cc3871ebd6b2850cd6647a6881a49a5033ba6c6` |

`ThreadItem` and all inspected collaboration/activity enums were identical between stable-only and `--experimental` generation. `Thread` as a whole differed because the experimental profile adds unrelated fields such as environments and attachment metadata; the delegation fields listed below remain in stable-only output. “Stable-only” means retained by this binary's filter, not a promise about other versions.

## Confirmed contract facts

### Child identity and lineage

The stable-only `Thread` type provides:

- `id`: the thread identity;
- `sessionId`: a session-tree grouping identity;
- `parentThreadId`: documented as set only when the thread is a subagent;
- `source`: which can be a `subAgent` source;
- optional `agentNickname` and `agentRole` labels.

The version-pinned source defines `parentThreadId` without an experimental marker and keeps `agentNickname` and `agentRole` in the same public `Thread` object ([thread data, lines 202-285](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/app-server-protocol/src/protocol/v2/thread_data.rs#L202-L285)). `SubAgentSource.thread_spawn` contains `parent_thread_id`, `depth`, optional `agent_path`, nickname, and role ([source lineage, lines 3287-3305](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/protocol/src/protocol.rs#L3287-L3305)); its implementation exposes a parent only for the thread-spawn variant ([lines 3397-3449](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/protocol/src/protocol.rs#L3397-L3449)).

These fields can directly identify a child thread and a stated parent. They do not by themselves prove that the App Server client will receive the child `Thread` live in the scenario, nor that every non-root internal thread should become an Orbita task card. `sessionId` groups a tree but is not a parent edge. `forkedFromId`, `rootTurnId`, `agentPath`, nickname, and role must not be substituted for `parentThreadId`.

### Spawn correlation and assignment

Stable-only `ThreadItem` includes `collabAgentToolCall` with:

- a unique item `id`;
- `tool`, including `spawnAgent`;
- tool-call `status`;
- `senderThreadId` and `receiverThreadIds`;
- optional `prompt`, requested model, and requested reasoning effort; and
- `agentsStates`, a map keyed by target thread ID.

For a spawn operation, the contract explicitly says the receiver is the newly spawned agent and the prompt is the text sent with the tool call when available ([item contract, lines 457-478](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/app-server-protocol/src/protocol/v2/item.rs#L457-L478)). The event mapper creates an in-progress spawn item with the prompt, then a completed item with the new receiver thread ID and its initial agent state ([event mapping, lines 79-136](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/app-server-protocol/src/protocol/event_mapping.rs#L79-L136)).

Therefore, an observed completed `spawnAgent` item with one receiver provides direct evidence of:

- the sender execution identity;
- the child thread identity;
- a spawn relation from sender to receiver; and
- the assignment text only when `prompt` is non-null.

The spawn tool-call status `completed` means the spawn call produced a receiver; it is not the child's terminal outcome. A failed spawn with no receiver is a delegation attempt or diagnostic event, not an agent execution and not a child task card.

`Thread.preview` is documented only as “usually the first user message.” It is not an authoritative assignment. `agentRole`, nickname, and path are labels, not assignment text. If both spawn `prompt` and child user input are unavailable, the task card's assignment/summary is unavailable; Orbita must not summarize model prose heuristically.

### Activity, status, and outcome evidence

Stable-only `ThreadItem` also includes `subAgentActivity` with `agentThreadId`, `agentPath`, optional resolved model/effort, and one of `started`, `interacted`, `interrupted`, or `completed` ([item contract, lines 480-490](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/app-server-protocol/src/protocol/v2/item.rs#L480-L490), [activity enum, lines 1350-1367](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/app-server-protocol/src/protocol/v2/item.rs#L1350-L1367)). The mapper emits these as completed item notifications correlated to the containing `threadId` and `turnId` ([event mapping, lines 187-202](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/app-server-protocol/src/protocol/event_mapping.rs#L187-L202)).

Collaboration target states are `pendingInit`, `running`, `interrupted`, `completed`, `errored`, `shutdown`, or `notFound`; completed and errored states may carry a message ([state mapping, lines 1371-1423](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/app-server-protocol/src/protocol/v2/item.rs#L1371-L1423)). Collaboration tool calls separately have `inProgress`, `completed`, `failed`, or `interrupted` status ([lines 1313-1346](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/app-server-protocol/src/protocol/v2/item.rs#L1313-L1346)). These two status domains must not be conflated.

The following mappings are contract-safe only when the cited value is actually observed for the target child:

| Evidence | Safe statement | Unsafe statement |
| --- | --- | --- |
| `agentsStates[child].pendingInit` | Last observed target state is pending initialization | Child is actively executing |
| `agentsStates[child].running` | Last observed target state is running | Child will complete or is making progress |
| `agentsStates[child].completed` | Last observed target state is completed; optional source message is available | Every child turn succeeded, or result is durable/recoverable |
| `agentsStates[child].errored` | Last observed target state is errored; source message may exist | Spawn tool failure proves a child execution failed |
| `agentsStates[child].interrupted` | Last observed target state is interrupted | The root task is interrupted |
| `agentsStates[child].shutdown` or `notFound` | Target became unavailable in that observation | Successful, failed, or deleted execution |
| `subAgentActivity.started/interacted` | Direct activity occurred for that child | Execution status is active now |
| `subAgentActivity.completed` | A completion activity was reported | Successful outcome without a terminal state |
| `collabAgentToolCall.status == failed` | The collaboration tool call failed | An identified child execution failed |
| child `turn/completed.turn.status` | Direct outcome for that observed child turn | Outcome for unobserved turns or the whole root task |

`item/started` and `item/completed` include the item plus the containing thread and turn IDs ([item notifications, lines 1427-1454](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/app-server-protocol/src/protocol/v2/item.rs#L1427-L1454), [lines 1524-1540](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/app-server-protocol/src/protocol/v2/item.rs#L1524-L1540)). This permits event-level provenance and safely derived first/last-observed activity ordinals. It does not turn absence of later events into an idle or terminal state.

## Candidate live-delivery path

First-party implementation has a path for newly created threads: it collects initialized connections and asks the processor to attach a listener for the new thread ([App Server runtime, lines 1349-1367](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/app-server/src/lib.rs#L1349-L1367)). Listener setup has explicit V2-child handling and installs subscribers on created threads ([thread lifecycle, lines 189-241](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/app-server/src/request_processors/thread_lifecycle.rs#L189-L241), [lines 330-480](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/app-server/src/request_processors/thread_lifecycle.rs#L330-L480)).

This makes the following reasonable candidates for the pinned live probe, not confirmed capabilities:

1. the root connection receives the child `thread/started` and subsequent child turn/item notifications;
2. the completed spawn item, child `Thread.parentThreadId`, and subagent source all agree on the same parent-child edge;
3. child `turn/completed` provides the authoritative child-turn outcome;
4. a later wait or interaction item updates `agentsStates` to the child's terminal agent state; and
5. multiple child listeners remain distinguishable under concurrent activity.

Issue #4 must capture each candidate. Schema availability and listener source are insufficient because live subscription timing, event ordering, omissions, late events, and recovery completeness are still unmeasured.

## Known unknowns and blockers

- No live fixture yet proves that child `thread/started`, child turns, spawn items, and subagent activities are all delivered to one App Server client in this configuration.
- No source inspected here promises a total ordering among the parent spawn item, child thread notification, child turn events, subagent activity, and root completion. Correlate identities; never infer relationships from adjacency.
- `agentsStates` is documented as the last known state in that item. Its freshness, replay behavior, and durability after restart are unknown.
- `subAgentActivity.completed` does not carry success/failure. It cannot be an outcome by itself.
- `Thread.status.type == "idle"` is runtime thread state, not successful execution evidence. `systemError` is not automatically the error of a specific child turn.
- A source message on `completed` or `errored` may be useful result/error content, but completeness, sanitization needs, and recovery are version/configuration dependent.
- Optional prompt, nickname, role, path, model, effort, message, and child detail may be null or absent. Missing detail is not evidence that no child existed.
- The contract can represent `agentsStates[child].errored`, but the inspected public sources do not provide a deterministic, least-privilege way to force a real child execution into `errored`. A nonzero shell command can be recovered by the model; an invalid spawn that creates no receiver is not a failed child execution. This is a blocker for issue #4's required real child-failure fixture until the builder obtains a safe source-backed trigger or captures a genuine failure.
- `interrupted` is a distinct, testable negative outcome candidate; it does not satisfy a requirement specifically demanding failure/`errored`.
- Recovery and pagination of child details are outside this live-observability research and remain Gate E work.

## Least-privilege disposable delegation scenario

This is a handoff design, not an executed result. It minimizes permissions and makes any observed child identity and assignment easy to validate.

### Environment and feature profile

1. Use the exact pinned executable and an isolated probe home/config.
2. Create a new disposable Git repository containing only:

   ```text
   alpha.txt  -> ORBITA_CHILD_ALPHA
   beta.txt   -> ORBITA_CHILD_BETA
   ```

3. Start App Server over stdio with an explicit V2/legacy split:

   ```powershell
   codex app-server --listen stdio:// --enable multi_agent_v2 --disable multi_agent --strict-config
   ```

4. Record the effective feature list using the same overrides. Keep `multi_agent_v2_dynamic_tools`, `subagent_thread_environments`, `subagent_default_context_limits`, `runtime_agent_instances`, and `use_agent_identity` disabled. Do not opt into experimental App Server fields: initialize with `capabilities.experimentalApi: false`.
5. Start one ephemeral root thread with the absolute disposable-repository `cwd`, `sandbox: "read-only"`, `approvalPolicy: "never"`, a recorded model/provider, and no plugins, MCP requirements, web search, secrets, or network-dependent task.

V2 defaults to four concurrent threads per session, and its effective child limit subtracts the root ([configuration defaults, lines 274-282](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/core/src/config/mod.rs#L274-L282), [effective limit, lines 1758-1769](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/core/src/config/mod.rs#L1758-L1769)). Root plus two children fits that source-defined default, but the run must record the effective value rather than assume it.

### Synthetic root instruction

Use one fixed prompt whose content can be allowlisted in fixtures:

```text
Use the available collaboration spawn-agent tool to create exactly two independent child agents before waiting for either one.

Child alpha: read only alpha.txt in the current project and return exactly ORBITA_CHILD_ALPHA. Do not modify files and do not use network access.
Child beta: read only beta.txt in the current project and return exactly ORBITA_CHILD_BETA. Do not modify files and do not use network access.

Do not read either file in the root execution. Wait for both children. Then return a two-key JSON object containing their exact results. Do not spawn more agents and do not modify files.
```

The prompt asks the model to use a public runtime tool; Orbita does not synthesize a delegation call. Two children must be observed from source evidence or the run fails. If the model ignores the delegation instruction, record an unsuccessful capability run; do not fabricate children, rewrite the transcript, or retry without a recorded attempt number and bound.

### Negative scenarios

- **Unavailable detail:** derive an offline fixture variant by removing optional prompt/detail evidence from an approved sanitized live fixture while retaining the child identity event. Expected projection: identified child with assignment/result detail unavailable. This tests fallback only; it is not new live capability evidence.
- **Interrupted child candidate:** in a separate fixed prompt, ask the root to spawn a long-enough read-only child and use the available interrupt-agent tool before waiting. Accept only an actually observed `interrupted` target state or child turn status. This is model-mediated and must be bounded; it proves interruption, not failure.
- **Errored child:** no deterministic safe trigger is confirmed. Do not simulate `errored` in a live fixture, treat spawn failure as child failure, or use destructive/environmental sabotage. An offline hand-authored `errored` fixture may test projection code, but issue #4 cannot cite it as proof that the pinned runtime emitted a real failed child.

## Exact capability matrix

Each matrix cell must use exactly one classification from [compatibility.md](compatibility.md): `directly observed`, `safely derived`, `unavailable`, `ambiguous`, or `version/feature dependent`.

Record one row for each `(runId, executionAlias, field)` with these columns:

| Column | Meaning |
| --- | --- |
| `runId` | Sanitized run identifier tied to the run manifest |
| `executionAlias` | Causally allocated alias such as `<ROOT_1>`, `<CHILD_1>` |
| `field` | One exact field name from the list below |
| `observedValue` | Sanitized value, or `null` when unavailable |
| `classification` | One of the five required classifications |
| `evidenceRefs` | Non-empty ordered transcript ordinals for direct/derived claims |
| `derivation` | Empty for direct evidence; explicit deterministic rule for derived evidence |
| `contractProfile` | `stable-only` or separately recorded experimental profile |
| `runtimeIdentity` | CLI version plus executable digest reference |
| `featureProfile` | Effective feature-manifest digest and explicit overrides |
| `firstObservedOrdinal` | First supporting event ordinal, if any |
| `lastObservedOrdinal` | Last supporting event ordinal, if any |
| `conflict` | `false`, or a description of contradictory source evidence |
| `gap` | `false`, or a description of missing expected evidence |

Required `field` rows for the root and every observed child are:

```text
execution.identity
execution.kind
execution.parentIdentity
execution.spawnCorrelation
execution.sourceKind
execution.assignment
execution.sourceSummary
execution.firstActivity
execution.lastActivity
execution.currentStatus
execution.terminalOutcome
execution.resultAvailability
execution.resultSummary
execution.failureDetail
execution.model
execution.reasoningEffort
execution.provenanceCompleteness
```

The run-level matrix must additionally contain:

```text
delegation.realChildCount
delegation.distinctChildIdentities
delegation.multipleChildrenConcurrent
delegation.allParentEdgesSupported
delegation.allDisplayedAssignmentsSupported
delegation.childFailureObserved
delegation.unavailableDetailFallbackVerified
delegation.unknownVariantToleranceVerified
delegation.replayDeterministic
```

Suggested derivations are intentionally narrow:

- `execution.kind = child` is safely derived when a direct child thread ID appears in a `spawnAgent.receiverThreadIds`, direct `Thread.parentThreadId`, or direct `source.subAgent.thread_spawn`; record which rule fired.
- `execution.parentIdentity` is direct when a source field names the parent. If spawn sender and `parentThreadId` agree, retain both evidence references; agreement is not a new identity.
- `firstActivity` and `lastActivity` are safely derived as the minimum/maximum transcript ordinal among directly correlated events. They describe observation, not actual runtime start/end.
- A display status can be safely derived only from an explicitly reviewed mapping of a direct target state or child turn status. Missing events yield `unavailable`, not idle.
- A terminal child outcome should prefer an observed matching child `turn/completed`. A terminal `agentsStates` value is direct last-known agent state but must be labeled with that scope. Conflicts are `ambiguous` and block a definitive card outcome.
- Assignment is direct only from non-null spawn `prompt` or an independently observed source-provided child instruction proven to belong to that child. Generated summaries are not allowed.

## Acceptance rules for issue #4

The positive live run passes the hierarchy portion only if all of the following hold:

1. two distinct non-root thread identities are directly observed;
2. each identity has direct spawn or thread lineage to the root, and conflicting edges are absent;
3. each displayed child has a direct assignment or is deliberately rendered with assignment unavailable;
4. each child has at least one directly correlated activity event;
5. every shown status/outcome has an evidence reference and reviewed mapping;
6. root and child evidence remain distinct under interleaving;
7. missing optional detail produces a weaker card/event, never a fabricated value or edge; and
8. a sanitized fixture replays to the same normalized matrix without a model run.

Full issue acceptance additionally requires a genuine child failure and an unavailable-child-detail fixture. The positive scenario, an interrupted scenario, or an offline synthetic `errored` fixture alone does not satisfy genuine child failure. If no safe real failure can be produced, record `delegation.childFailureObserved = false`, classify it `unavailable`, and keep the issue open or re-scope it explicitly.

## Projection and fallback rules

- Create a child task card only after a unique child execution identity is observed. A spawn attempt without a receiver is a timeline event on the sender, not a child card.
- Add a tree edge only from direct parent evidence. If a child identity exists without a supported edge, render a neutral unlinked execution as required by the UX flow.
- If two direct sources disagree on parent or identity, preserve both evidence records, classify the relationship ambiguous, and render no edge.
- Do not make a card from plan text, a guessed agent count, `sessionId` grouping, file paths, adjacency, nickname, role, or model-generated narration.
- Treat tool-call status, target-agent status, child-turn outcome, and root-turn outcome as separate fields.
- Preserve `shutdown`, `notFound`, missing detail, late events, and unknown variants without collapsing them into success or failure.
- Do not allow a child outcome to finish the root task. Automatic Finish still requires the independently proven settled-root conditions in product truth.

## Safe probe handoff

The builder should:

1. reuse the pinned initialize/thread/turn harness from issue #2, adding only the explicit feature overrides and fixed delegation prompt above;
2. generate and validate against the stable-only contract from the same executable before launch;
3. capture stdout JSONL and stderr separately with monotonic ordinals; accept event interleaving and correlate only by direct IDs;
4. stop successfully only after the root terminal event and all already-identified children have a source-backed terminal or explicit unknown state after bounded reconciliation;
5. retain spawn, child-thread, child-turn, subagent-activity, and wait/interruption evidence even when redundant, because disagreements are diagnostic;
6. sanitize before persistence: alias thread/turn/item IDs by first causal definition, replace absolute paths, allowlist the two prompts and sentinels, remove reasoning and unrelated content, redact credentials/environment values, and run a second forbidden-pattern scan;
7. commit only sanitized fixtures plus the run/contract/feature manifests; never publish the isolated home, raw transcript, model reasoning, or private paths;
8. create offline replay variants for missing optional detail and unknown variants without presenting those variants as live runtime evidence; and
9. report the genuine-child-failure blocker rather than weakening `errored` into spawn failure, command failure, interruption, disappearance, or silence.

## First-party sources

- [OpenAI Codex 0.170.0 release](https://github.com/openai/codex/releases/tag/rust-v0.170.0)
- [Generated TypeScript contract at 0.170.0](https://github.com/openai/codex/tree/rust-v0.170.0/codex-rs/app-server-protocol/schema/typescript)
- [App Server protocol item definitions](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/app-server-protocol/src/protocol/v2/item.rs)
- [App Server event-to-item mapping](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/app-server-protocol/src/protocol/event_mapping.rs)
- [App Server thread data contract](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/app-server-protocol/src/protocol/v2/thread_data.rs)
- [Core subagent source and lineage](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/protocol/src/protocol.rs)
- [Feature stages and defaults](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/features/src/lib.rs)
- [Multi-agent runtime configuration selection](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/core/src/config/mod.rs)
- [App Server new-thread listener lifecycle](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/app-server/src/request_processors/thread_lifecycle.rs)
