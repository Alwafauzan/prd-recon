# Discord Command Catalog

All read-only commands run deterministic repository scripts. Reconciliation
commands call the configured agent gateway and never edit `source/original/`.

## Help

| Discord command | Purpose |
|---|---|
| `/mulai` | Open the guided primary menu for nontechnical users |
| `/help` | Show the command overview |
| `/help topic:prd` | Show help for one tool group |
| Question in an allowed channel | Create a help thread automatically |
| Message in a bot-created help thread | Continue the help session without another tag |
| Direct message | Interpret the message as a help question without a thread |

Supported help topics: `prd`, `e2e`, `gap`, `health`, `inventory`, `version`,
`repo`, and `reconcile`. A question in a channel listed by
`NEUROVI_DISCORD_ALLOWED_CHANNEL_IDS` does not require a bot mention. The bot
creates a public thread and uses the configured gateway model
only as a read-only command advisor. It explains what the user can do now,
recommends exact commands from this catalog, and provides command-based
workarounds. If no current command can satisfy the request, it states that a
developer enhancement is required instead of pretending the problem was
resolved. Plain messages never execute a repository capability; users must use
a slash command for execution.

For ordinary users, `/mulai` is the only command they need to remember. It
provides separate buttons for main-flow reconciliation, detailed-process reconciliation, and mode-specific resume, plus viewing a process,
finding a document, and checking unclear flow areas. Process selection uses a
dropdown and does not require an E2E code.

The technical command groups in the sections below default to Discord members
with **Manage Server** permission. This keeps the ordinary slash-command picker
focused on `/mulai` and `/help` while preserving deterministic operator tools.

## Original PRD

| Discord command | Capability | Access |
|---|---|---|
| `/prd list` | `prd.list` | Read |
| `/prd show` | `prd.show` | Read |

## E2E Inventory

| Discord command | Capability | Access |
|---|---|---|
| `/e2e list` | `e2e.list` | Read |
| `/e2e show` | `e2e.show` | Read |

## Gap Scanner

| Discord command | Capability | Access |
|---|---|---|
| `/gap alur` | `gap.main-flow` | Read |
| `/gap kasus` | `gap.business-cases-e2e` | Read |

## Document Health

| Discord command | Capability | Access |
|---|---|---|
| `/document-health flow` | `health.documents-flow` | Read |
| `/document-health all` | `health.documents-all` | Read |

`/document-health flow` accepts an optional process name. Without a selection it
shows all flows; with a selection it shows document-level rows for that flow.
`/document-health all` shows repository totals and the flows with the most
review candidates. Percentages describe mechanically detectable coverage only,
not semantic correctness or an approved quality score.

## Inventory and Versioning

| Discord command | Capability | Access |
|---|---|---|
| `/inventory find-prd` | `inventory.find-prd` | Read |
| `/inventory scan-format` | `inventory.scan-format` | Read |
| `/version list` | `version.list` | Read |
| `/version compare` | `version.compare` | Read |
| `/repo health` | local health check | Read |
| `/repo validate` | `repo.validate` | Read |
| `/repo commands` | capability catalog | Read |

## Controlled Reconciliation

These commands require `NEUROVI_AGENT_GATEWAY_URL` and a matching Discord role.

| Discord command | Gateway capability | Required role set |
|---|---|---|
| `/reconcile alur` | `reconcile.main-flow.start` | Reconcile |
| `/reconcile detail` | `reconcile.business-cases.start` | Reconcile |
| Guided card buttons and form | `reconcile.answer`, `reconcile.control`, `reconcile.decide` | Reconcile |
| `Akhiri sesi` button | `reconcile.stop` | Reconcile |

`/reconcile alur` and `/reconcile detail` provide process-name autocomplete. Main-flow reconciliation consumes only `main_flow_scan`; detailed-process reconciliation consumes only `business_case_scan`. Each mode has an independent session and can be resumed from `/mulai`. The agent response is
shown as a short guided card. Owner-domain PRDs are loaded automatically; the
bot asks only about cited functional gaps, conflicts, or undefined handoffs.
Cards provide answer/confirmation controls, skip/defer/unknown controls, and a
modal for free-form answers. The bot retains the session ID, so ordinary users
do not need to copy it or type internal decision codes.

Every active card includes **Akhiri sesi**. After a confirmation prompt, this
sets the working session to `STOPPED_BY_USER`, preserves earlier answers and the
current unanswered question, and removes the card controls. It never approves a
baseline or creates a commit, tag, or push. Repository publication remains a
separate approver workflow and is not exposed as an ordinary Discord command.

While an AI-backed action is running, the same card displays a specific state
such as **Sedang menyimpan jawaban**, **Sedang menyimpan pilihan**, or **Sedang
mengakhiri sesi**. All controls are disabled until the request finishes. On
failure, the previous controls are restored and the bot explicitly states that
the attempted answer or choice was not saved. If the agent received and stored
the answer but failed while preparing the next question, the bot says that the
answer is already recorded and directs the user to the matching **Lanjut**
button.
