# Discord Command Catalog

All read-only commands run deterministic repository scripts. Reconciliation
commands call the configured agent gateway and never edit `source/original/`.

## Help

| Discord command | Purpose |
|---|---|
| `/help` | Show the command overview |
| `/help topic:prd` | Show help for one tool group |
| Question in an allowed channel | Create a help thread automatically |
| Message in a bot-created help thread | Continue the help session without another tag |
| Direct message | Interpret the message as a help question without a thread |

Supported help topics: `prd`, `e2e`, `gap`, `inventory`, `version`,
`repo`, and `reconcile`. A question in a channel listed by
`NEUROVI_DISCORD_ALLOWED_CHANNEL_IDS` does not require a bot mention. The bot
creates a public thread and uses the configured gateway model
only as a read-only command advisor. It explains what the user can do now,
recommends exact commands from this catalog, and provides command-based
workarounds. If no current command can satisfy the request, it states that a
developer enhancement is required instead of pretending the problem was
resolved. Plain messages never execute a repository capability; users must use
a slash command for execution.

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
| `/gap list` | `gap.list` | Read |
| `/gap e2e` | `gap.e2e` | Read |
| `/gap prd` | `gap.prd` | Read |

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
| `/reconcile start` | `reconcile.start` | Reconcile |
| `/reconcile continue` | `reconcile.status` | Reconcile |
| `/reconcile answer` | `reconcile.answer` | Reconcile |
| `/reconcile control` | `reconcile.control` | Reconcile |
| `/reconcile add-reference` | `reconcile.add-reference` | Reconcile |
| `/reconcile decide` | `reconcile.decide` | Reconcile |
| `/reconcile status` | `reconcile.status` | Reconcile |
| `/finish` | `reconcile.finish` | Approver |

`/reconcile start` provides process-name autocomplete. The agent response is
shown as a short guided card with buttons for confirmation, document role,
skip/defer/unknown controls, and a modal for free-form answers. The bot retains
the session ID, so ordinary users do not need to copy it or type internal
decision codes. `/reconcile continue` restores the latest active session for
the current user. The explicit `answer`, `control`, and `decide` commands remain
available as administrative fallbacks.

`/reconcile control` accepts only `SKIP`, `DEFER`, or `UNKNOWN`.
`/finish` requires `session_id`, explicit `approval:BASELINE_APPROVAL`, and a
global `bump` of `patch`, `minor`, or `major`. The current interview runtime
blocks this command with `NOT_ATTEMPTED`; it does not commit or push yet. The
target publisher may stop the reconciliation only after validation, commit,
annotated tag creation, and atomic push all succeed. The gateway must keep the
session open or failed when publishing cannot finish.
