# Server and Discord Deployment

## Architecture

The deployment runs two isolated services:

1. `discord-bot` mounts the document repository read-only. Read commands call
   deterministic skill scripts, while reconciliation commands call the
   internal agent endpoint.
2. `reconciliation-agent` mounts the document repository writable, reads
   `NEUROVI_LLM_*` directly, loads the reconciliation skill and policies into
   the model context, and persists controlled interview/session artifacts.

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
openssl rand -hex 32
docker compose build
docker compose up -d
docker compose logs -f discord-bot reconciliation-agent
```

Put the generated value in `NEUROVI_AGENT_GATEWAY_TOKEN`. Compose uses
`http://reconciliation-agent:8080/invoke` as the internal gateway URL. The same
token is mapped to the bot and the agent; it is not the 9router token.

The image contains the Python adapters, deterministic scripts, and repository
skills. The `discord-bot` service mounts `neurovi-prd/` read-only. Only the
`reconciliation-agent` service receives a writable document mount, the
submodule Git metadata, optional host SSH agent socket, and LLM configuration.
Set `NEUROVI_AGENT_UID` and `NEUROVI_AGENT_GID` to the host owner of the
checkout so session artifacts can be written without running the container as
root. Initialize the submodule before starting Compose.

## Reconciliation Model Configuration

Configure the model profile in `.env`:

```env
NEUROVI_LLM_PROVIDER=9router
NEUROVI_LLM_BASE_URL=https://router.example/v1
NEUROVI_LLM_API_KEY=<gateway-only-secret>
NEUROVI_LLM_MODEL=<model-id>
NEUROVI_LLM_REASONING_EFFORT=high
NEUROVI_LLM_TIMEOUT_SECONDS=180
```

These variables belong to the reconciliation agent container. The agent reads
the provider endpoint, API key, model, and effort directly from its own
environment when starting. The Discord bot does not select a model and never
includes LLM configuration or API keys in gateway requests. The agent must
record the effective provider, model, and effort in the reconciliation audit
trail without recording the API key. For an OpenAI-compatible 9router endpoint,
set `NEUROVI_LLM_BASE_URL` to its API base ending in `/v1`; the runtime appends
`/chat/completions`. A full endpoint ending in `/chat/completions` or
`/responses` is also accepted.

Docker Compose reads `.env` for variable substitution, but the `discord-bot`
service maps only Discord and gateway variables. `NEUROVI_LLM_*` is mapped only
into `reconciliation-agent`, so the Discord process never receives the provider
API key.

At runtime, the model does not receive arbitrary filesystem or Git write
access. The server supplies repository evidence and selected PRD excerpts,
requires structured JSON output, and applies only whitelisted session/register
updates. Mechanical findings remain candidates, and model output cannot become
baseline content without an explicit `/reconcile decide` user decision.

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

The included agent service loads the applicable repository skill, persists the
reconciliation audit trail, independently checks Discord role IDs, and returns
stable session IDs. It ignores a client-supplied repository path and uses only
the repository configured inside the agent container.

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

The current container runtime implements the controlled LLM interview and
decision workspace, but deliberately blocks `reconcile.finish` before commit,
tag, or push. The atomic publisher remains locked until canonical artifact
generation, `UNEXPLAINED_CHANGE` enforcement, and release-manifest generation
are implemented. A blocked finish response reports `NOT_ATTEMPTED` and never
pretends publication succeeded.

## Security Defaults

- Discord responses are ephemeral by default.
- Server-channel text requires a bot mention; follow-ups are scoped to the
  bot-created help thread.
- Natural-language text is help-only and cannot execute capabilities.
- The document submodule volume is read-only in the Discord bot.
- Reconciliation and approval role lists default to empty, which denies access.
- Bot tokens and gateway tokens stay in `.env`, never in Git.
- LLM API keys remain gateway-side and are never included in Discord payloads
  or responses.
- The shared agent gateway token is separate from the LLM API key.
- The LLM can propose controlled actions but cannot directly write files or run
  Git commands.
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
