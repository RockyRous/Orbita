# Core Flows

## Workspace layout

Orbita uses navigation, a root chat, and a resizable/collapsible execution tracker. Selecting an execution row focuses its details and available chat evidence; collapsing the tracker never removes chat access.

## First run

1. Orbita checks the local Codex installation and its supported contract.
2. If unavailable or incompatible, it explains the mismatch without inventing a workaround.
3. The user selects a local project.
4. Orbita opens an empty root-chat workspace with an empty tracker and a composer that shows runtime state.

## Start a root task

1. The user enters an instruction in the composer.
2. Orbita creates a supported Codex thread and turn.
3. The root task becomes `Open`; the user message is `Sending` until accepted.
4. Supported output streams into the ordered chat.
5. The root execution appears in the tracker only after source identity exists.
6. Starting another root task or switching project remains unavailable while the slot is occupied.

## Conduct the conversation

Orbita renders supported messages/events in source order. Tool calls, commands, results, file changes, plans, errors, approvals, and questions have readable representations. Unknown events remain generic cards with provenance. The user may inspect details, send a follow-up, or request interruption. A terminal outcome is shown only after authoritative evidence.

## Observe agent work

An execution row appears only when evidence proves an execution exists. A supported parent relation nests it; an unknown parent leaves it unlinked. Row data is limited to supported identity, role, assignment, status, activity, attention, and outcome. Selecting it opens details and jumps to associated chat evidence. Plan wording alone never creates a row.

## Observe product workflow

Plans, roles, and GitHub issues live in a separate workflow-context area. Explicit links may connect a role, plan item, work item, root task, or execution, and each link names its source. Similar titles and timestamps are never enough to invent a link.

## Handle attention and interruption

A supported approval/question raises `Action required` and focuses the event. An interruption first shows `Interrupt requested`; only source evidence may show `Interrupted`. The root task remains open and becomes `Review required`; the user can follow up or finish it.

## Connection, review, and reopening

Lost runtime connection raises `Connection problem`; current statuses degrade to unknown where unprovable. Orbita performs only bounded supported reconciliation, never starts a replacement task, removes duplicates, and retains missing intervals as gaps. A terminal outcome raises review attention. A finished task may reactivate through a follow-up; archive is reversible.
