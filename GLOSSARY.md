# Orbita

Orbita is a desktop workspace for conducting a Codex conversation and understanding the observable work performed through it.

## Language

**Root task**: A user-owned stream of work containing one root chat, its turns, and observable delegated executions until the user finishes it.
_Avoid_: session, root agent, job

**Root chat**: The complete conversational surface of a root task: user input, Codex output, supported tool activity, questions, and approvals.
_Avoid_: prompt box, compact input, evidence timeline

**Turn**: One user request and the resulting Codex activity within a root task.
_Avoid_: task, chat, session

**Agent execution**: An observed instance of an agent performing assigned work within a root task.
_Avoid_: plan item, work item, synthetic agent

**Delegation**: An observed assignment of work from one agent execution to another.
_Avoid_: inferred relationship, plan step

**Execution row**: The tracker representation of exactly one observable agent execution.
_Avoid_: task card, todo, plan item

**Agent role**: An explicitly provided function or responsibility associated with an agent execution.
_Avoid_: inferred persona, model name

**Plan item**: An item in an explicitly reported plan for a root task or turn.
_Avoid_: agent execution, work item

**Work item**: An externally tracked unit of product work, such as a GitHub issue, explicitly associated with a root task, plan item, or agent execution.
_Avoid_: agent execution, turn

**Workflow link**: An explicit association between a root task, agent execution, role, plan item, or work item.
_Avoid_: inferred relationship

**Execution status**: The source-backed condition of an agent execution.
_Avoid_: attention state, root-task lifecycle

**Attention state**: An independent indication that a root task needs user action, review, or awareness of a connection problem.
_Avoid_: execution status, notification

**Open**: The root-task lifecycle state that occupies the single active slot and can accept a turn or follow-up.
_Avoid_: running

**Finish**: The non-destructive transition that releases a root task's active slot while preserving its chat and workflow history.
_Avoid_: complete, archive, delete

**Archive**: The reversible transition that removes a finished root task from the primary workspace without deleting it.
_Avoid_: finish, delete

**Provenance**: The evidence that connects displayed information to an observed or explicitly provided source.
_Avoid_: assumption, unsupported inference

**Gap**: A known interval for which Orbita cannot recover complete source evidence.
_Avoid_: idle, no activity
