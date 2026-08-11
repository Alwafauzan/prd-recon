# Server and Discord Deployment

## Architecture

The server package has two execution paths:

1. Read-only commands call the existing deterministic skill scripts using
   argument arrays, without a shell.
2. Reconciliation commands send a structured request to an agent gateway.
   They are disabled unless a gateway and Discord role allowlists are set.

The `neurovi-prd/` submodule remains the document source truth. Graphify is not
used as source truth, and the bot container mounts only that submodule at
`/repository` read-only. Skills, scripts, and server code remain in the parent
`neurovi-doc-reconciliator` repository.

## Install as a Python Package

Python 3.11 or newer is required.

```bash
python3 -m venv .venv
.venv/bin/pip install ".[discord]"
.venv/bin/neurovi-doc-reconciliator health --deep
```

List and execute capabilities locally:

```bash
.venv/bin/neurovi-doc-reconciliator capabilities
.venv/bin/neurovi-doc-reconciliator run e2e.list --param group=admisi-emr
.venv/bin/neurovi-doc-reconciliator run prd.show \
  --param document=DOC-4287D4C5CFF2D2E0 \
  --param "section=3. In Scope"
```

## Discord Application Setup

1. Create an application and bot in the Discord Developer Portal.
2. Enable the `applications.commands` and `bot` OAuth scopes.
3. Grant `Send Messages`, `Send Messages in Threads`, `Create Public Threads`,
   `Read Message History`, `Attach Files`, and `Use Application Commands`.
4. Copy `.env.example` to `.env`.
5. Set `DISCORD_TOKEN`.
6. Optionally set one or more guild IDs for immediate development sync.
7. Enable the Message Content privileged intent for natural-language help.
8. Set role IDs before enabling reconciliation or `/finish`.

In a server channel, the bot ignores ordinary messages. Mentioning the bot
creates a public thread attached to the triggering message and sends the help
answer there. Follow-up text in that bot-owned thread continues the session
without another tag. Direct messages are answered directly. A mention inside
an existing thread cannot create a nested thread, so the bot directs the user
to invoke it from the parent channel. Plain messages never execute tools or
mutate the repository.

## Run with Docker Compose

```bash
cp .env.example .env
docker compose build
docker compose up -d
docker compose logs -f discord-bot
```

The image contains the Python adapter, deterministic scripts, and repository
skills. The `neurovi-prd/` submodule is mounted at `/repository` read-only, so
document updates do not require rebuilding the tools image.

## Agent Gateway Contract

The bot sends an HTTP `POST` request:

```json
{
  "capability": "reconcile.start",
  "parameters": {
    "e2e": "E2E-ADM-01",
    "repository_root": "/repository"
  },
  "actor": {
    "discord_user_id": "123",
    "discord_user_name": "name",
    "discord_role_ids": ["456"],
    "guild_id": "789",
    "channel_id": "101"
  }
}
```

The gateway must return:

```json
{
  "message": "Question or result for the user",
  "status": "AWAITING_USER",
  "session_id": "REC-E2E-ADM-01-001"
}
```

The gateway is responsible for loading the applicable repository skill,
persisting the reconciliation audit trail, enforcing approval gates, and
returning stable session IDs. It must not trust the Discord request alone for
Git baseline creation.

### Finish and Publish Contract

`/finish` sends this terminal request to the gateway:

```json
{
  "capability": "reconcile.finish",
  "parameters": {
    "session_id": "REC-E2E-ADM-01-001",
    "approval": "BASELINE_APPROVAL",
    "version_bump": "patch",
    "publish": true,
    "repository_root": "/repository"
  },
  "actor": {
    "discord_user_id": "123",
    "discord_role_ids": ["456"]
  }
}
```

The bot requires a role in `NEUROVI_DISCORD_APPROVER_ROLE_IDS`. The writable
gateway worker must independently verify the actor, session, and approval. It
must then perform this transaction in order:

1. Lock the reconciliation session and repository publish operation.
2. Reject unapproved baseline content and every `UNEXPLAINED_CHANGE`.
3. Verify that the working tree contains only expected session and generated
   release changes; unrelated or unsafe changes block publication.
4. Calculate the next unused global semantic version from existing annotated
   tags and the requested `patch`, `minor`, or `major` bump.
5. Generate `reconciliation/releases/<version>/manifest.json` and `changes.md`.
6. Regenerate derived navigation, then run the tools-repository validator:
   `<tools-root>/scripts/build_structure.py validate --source source/original --target .`.
7. Create one release commit and an annotated tag that references the baseline
   decision ID. Never reuse, move, replace, or force-update a tag.
8. Push the branch commit and tag together with `git push --atomic` to the
   configured remote.
9. Mark the session finished only after the remote confirms the atomic push.

The success response must identify the exact published state:

```json
{
  "message": "Global baseline v0.0.2 published.",
  "status": "PUBLISHED",
  "session_id": "REC-E2E-ADM-01-001",
  "result": {
    "repository_version": "v0.0.2",
    "commit_sha": "<full-commit-sha>",
    "tag": "v0.0.2",
    "remote": "origin",
    "branch": "main",
    "push_status": "ATOMIC_PUSH_SUCCEEDED"
  }
}
```

If validation, commit, tag creation, or push fails, the gateway must not report
the session as finished. It must preserve an open or failed publish state for
retry and return a failure reason. The Discord bot remains read-only and never
receives Git credentials; the dedicated gateway worker owns the writable
checkout and remote credentials.

## Security Defaults

- Discord responses are ephemeral by default.
- Server-channel text requires a bot mention; follow-ups are scoped to the
  bot-created help thread.
- Natural-language text is help-only and cannot execute capabilities.
- The document submodule volume is read-only in the Discord bot.
- Reconciliation and approval role lists default to empty, which denies access.
- Bot tokens and gateway tokens stay in `.env`, never in Git.
- Commands use subprocess argument arrays and never invoke a shell.
- Large PRDs and reports are returned as Discord attachments.

## Update Procedure

```bash
git pull --ff-only
git submodule sync --recursive
git submodule update --init --recursive
python3 scripts/build_structure.py validate \
  --source neurovi-prd/source/original \
  --target neurovi-prd
docker compose build
docker compose up -d
```

Use the repository global version policy before creating release tags.
The Python package version is deployment metadata only; installing or building
the adapter never creates a document baseline or a Git version tag.
