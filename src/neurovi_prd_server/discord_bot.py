from __future__ import annotations

import asyncio
import io
import logging
import sys
from typing import Any, Mapping

from neurovi_prd_server.agent_gateway import AgentGateway, AgentGatewayError
from neurovi_prd_server.capabilities import CapabilityError, CapabilityRunner
from neurovi_prd_server.config import ConfigurationError, Settings
from neurovi_prd_server.help_system import (
    answer_help,
    build_help_thread_name,
    is_help_context,
    is_help_session_thread,
    strip_bot_mention,
)


LOGGER = logging.getLogger("neurovi_prd_server.discord")


def build_bot(settings: Settings):
    try:
        import discord
        from discord import app_commands
        from discord.ext import commands
    except ImportError as error:
        raise ConfigurationError(
            "Discord support is not installed. Run: pip install '.[discord]'"
        ) from error

    runner = CapabilityRunner(
        settings.repo_root,
        settings.tools_root,
        timeout_seconds=settings.command_timeout_seconds,
    )
    gateway = (
        AgentGateway(
            settings.agent_gateway_url,
            settings.agent_gateway_token,
            settings.agent_gateway_timeout_seconds,
        )
        if settings.agent_gateway_url
        else None
    )

    class NeuroviBot(commands.Bot):
        async def setup_hook(self) -> None:
            if settings.discord_guild_ids:
                for guild_id in settings.discord_guild_ids:
                    guild = discord.Object(id=guild_id)
                    self.tree.copy_global_to(guild=guild)
                    await self.tree.sync(guild=guild)
                    LOGGER.info("Synced commands to guild %s", guild_id)
            else:
                await self.tree.sync()
                LOGGER.info("Synced global commands")

    intents = discord.Intents.default()
    intents.message_content = settings.discord_text_help_enabled
    bot = NeuroviBot(
        command_prefix="!",
        intents=intents,
        help_command=None,
    )

    async def send_text(
        interaction,
        text: str,
        filename: str = "result.md",
        summary: str = "Hasil command terlampir.",
    ) -> None:
        cleaned = text.strip() or "No output."
        if len(cleaned) <= 1800:
            await interaction.followup.send(
                cleaned, ephemeral=settings.discord_ephemeral
            )
            return
        attachment = discord.File(
            io.BytesIO(cleaned.encode("utf-8")), filename=filename
        )
        await interaction.followup.send(
            summary,
            file=attachment,
            ephemeral=settings.discord_ephemeral,
        )

    async def run_local(
        interaction,
        capability: str,
        params: Mapping[str, str] | None = None,
        filename: str = "result.md",
    ) -> None:
        await interaction.response.defer(
            ephemeral=settings.discord_ephemeral, thinking=True
        )
        try:
            result = await asyncio.to_thread(runner.execute, capability, params or {})
            await send_text(interaction, result.output, filename)
        except CapabilityError as error:
            await interaction.followup.send(
                f"Command gagal: {error}", ephemeral=True
            )

    def actor_payload(interaction) -> dict[str, Any]:
        roles = getattr(interaction.user, "roles", [])
        return {
            "discord_user_id": str(interaction.user.id),
            "discord_user_name": str(interaction.user),
            "discord_role_ids": [str(role.id) for role in roles],
            "guild_id": str(interaction.guild_id) if interaction.guild_id else None,
            "channel_id": str(interaction.channel_id)
            if interaction.channel_id
            else None,
        }

    def has_role(interaction, allowed: frozenset[int]) -> bool:
        if not allowed:
            return False
        roles = getattr(interaction.user, "roles", [])
        return bool({role.id for role in roles} & allowed)

    async def run_agent(
        interaction,
        capability: str,
        parameters: Mapping[str, Any],
        approval: bool = False,
    ) -> None:
        allowed = (
            settings.discord_approver_role_ids
            if approval
            else settings.discord_reconcile_role_ids
        )
        if not has_role(interaction, allowed):
            await interaction.response.send_message(
                "Command ini dinonaktifkan untuk role Anda.", ephemeral=True
            )
            return
        if gateway is None:
            await interaction.response.send_message(
                "Agent gateway belum dikonfigurasi; command rekonsiliasi tetap terkunci.",
                ephemeral=True,
            )
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        payload = dict(parameters)
        payload["repository_root"] = str(settings.repo_root)
        try:
            response = await asyncio.to_thread(
                gateway.invoke,
                capability,
                payload,
                actor_payload(interaction),
            )
            prefix = []
            if response.session_id:
                prefix.append(f"Session: {response.session_id}")
            if response.status:
                prefix.append(f"Status: {response.status}")
            result = response.raw.get("result") if response.raw else None
            if isinstance(result, Mapping):
                for key, label in (
                    ("repository_version", "Version"),
                    ("commit_sha", "Commit"),
                    ("tag", "Tag"),
                    ("remote", "Remote"),
                    ("branch", "Branch"),
                    ("push_status", "Push"),
                ):
                    value = result.get(key)
                    if value is not None:
                        prefix.append(f"{label}: {value}")
            message = "\n".join(prefix + [response.message])
            await send_text(
                interaction,
                message,
                filename=f"{capability.replace('.', '-')}.md",
                summary="Respons agent terlampir.",
            )
        except AgentGatewayError as error:
            await interaction.followup.send(
                f"Agent gateway gagal: {error}", ephemeral=True
            )

    prd = app_commands.Group(name="prd", description="Original PRD commands")
    e2e = app_commands.Group(name="e2e", description="E2E inventory commands")
    gap = app_commands.Group(name="gap", description="Gap scanner commands")
    inventory = app_commands.Group(
        name="inventory", description="Document inventory commands"
    )
    version = app_commands.Group(name="version", description="Global version commands")
    repo = app_commands.Group(name="repo", description="Repository commands")
    reconcile = app_commands.Group(
        name="reconcile", description="Controlled reconciliation commands"
    )

    @bot.tree.command(name="help", description="Show command usage help")
    async def slash_help(interaction, topic: str | None = None):
        await interaction.response.send_message(
            answer_help(topic), ephemeral=settings.discord_ephemeral
        )

    @bot.tree.command(
        name="finish",
        description="Finish reconciliation and publish an approved global version",
    )
    @app_commands.choices(
        bump=[
            app_commands.Choice(name="Patch", value="patch"),
            app_commands.Choice(name="Minor", value="minor"),
            app_commands.Choice(name="Major", value="major"),
        ],
        approval=[
            app_commands.Choice(
                name="BASELINE_APPROVAL", value="BASELINE_APPROVAL"
            )
        ],
    )
    async def finish(
        interaction,
        session_id: str,
        approval: str,
        bump: str = "patch",
    ):
        if approval != "BASELINE_APPROVAL":
            await interaction.response.send_message(
                "Finish memerlukan approval BASELINE_APPROVAL.", ephemeral=True
            )
            return
        await run_agent(
            interaction,
            "reconcile.finish",
            {
                "session_id": session_id,
                "approval": approval,
                "version_bump": bump,
                "publish": True,
            },
            approval=True,
        )

    @prd.command(name="list", description="List original PRD records")
    async def prd_list(interaction, query: str | None = None, limit: int = 50):
        params = {"limit": str(limit)}
        if query:
            params["query"] = query
        await run_local(interaction, "prd.list", params, "prd-list.md")

    @prd.command(name="show", description="Display an immutable original PRD")
    async def prd_show(
        interaction, document: str, section: str | None = None
    ):
        params = {"document": document}
        if section:
            params["section"] = section
        await run_local(interaction, "prd.show", params, "original-prd.md")

    @e2e.command(name="list", description="List E2E inventory candidates")
    async def e2e_list(
        interaction,
        query: str | None = None,
        group: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ):
        params = {"limit": str(limit)}
        for key, value in (("query", query), ("group", group), ("status", status)):
            if value:
                params[key] = value
        await run_local(interaction, "e2e.list", params, "e2e-list.md")

    @e2e.command(name="show", description="Display one E2E source flow")
    async def e2e_show(interaction, e2e_code_or_name: str):
        await run_local(
            interaction,
            "e2e.show",
            {"e2e": e2e_code_or_name},
            "e2e-detail.md",
        )

    @gap.command(name="list", description="List E2Es with gap candidates")
    async def gap_list(interaction):
        await run_local(interaction, "gap.list", filename="gap-list.md")

    @gap.command(name="e2e", description="Scan gaps across one E2E")
    async def gap_e2e(interaction, e2e_code_or_name: str):
        await run_local(
            interaction,
            "gap.e2e",
            {"e2e": e2e_code_or_name},
            "e2e-gap-scan.md",
        )

    @gap.command(name="prd", description="Scan internal gaps in one PRD")
    async def gap_prd(interaction, document: str):
        await run_local(
            interaction,
            "gap.prd",
            {"document": document},
            "prd-gap-scan.md",
        )

    @inventory.command(name="find-prd", description="Find PRDs and E2E coverage")
    async def inventory_find_prd(interaction, query: str):
        await run_local(
            interaction,
            "inventory.find-prd",
            {"query": query},
            "document-search.md",
        )

    @inventory.command(name="scan-format", description="Scan PRD heading families")
    async def inventory_scan_format(interaction, document: str):
        await run_local(
            interaction,
            "inventory.scan-format",
            {"document": document},
            "format-scan.json",
        )

    @version.command(name="list", description="List global repository versions")
    async def version_list(interaction):
        await run_local(interaction, "version.list", filename="versions.md")

    @version.command(name="compare", description="Compare two global versions")
    async def version_compare(
        interaction, from_version: str, to_version: str
    ):
        await run_local(
            interaction,
            "version.compare",
            {"from": from_version, "to": to_version},
            "version-diff.md",
        )

    @repo.command(name="health", description="Check repository availability")
    async def repo_health(interaction):
        await interaction.response.send_message(
            f"Healthy: {settings.repo_root}", ephemeral=settings.discord_ephemeral
        )

    @repo.command(name="validate", description="Validate source preservation")
    async def repo_validate(interaction):
        await run_local(
            interaction, "repo.validate", filename="validation-report.json"
        )

    @repo.command(name="commands", description="List installed capabilities")
    async def repo_commands(interaction):
        await interaction.response.send_message(
            answer_help(), ephemeral=settings.discord_ephemeral
        )

    @reconcile.command(name="start", description="Start a controlled E2E session")
    async def reconcile_start(interaction, e2e_code_or_name: str):
        await run_agent(
            interaction, "reconcile.start", {"e2e": e2e_code_or_name}
        )

    @reconcile.command(name="answer", description="Answer one interview question")
    async def reconcile_answer(interaction, session_id: str, answer: str):
        await run_agent(
            interaction,
            "reconcile.answer",
            {"session_id": session_id, "answer": answer},
        )

    @reconcile.command(name="control", description="Skip, defer, or mark unknown")
    async def reconcile_control(interaction, session_id: str, action: str):
        normalized = action.strip().upper()
        if normalized not in {"SKIP", "DEFER", "UNKNOWN"}:
            await interaction.response.send_message(
                "Action harus SKIP, DEFER, atau UNKNOWN.", ephemeral=True
            )
            return
        await run_agent(
            interaction,
            "reconcile.control",
            {"session_id": session_id, "action": normalized},
        )

    @reconcile.command(name="add-reference", description="Add a session reference")
    async def reconcile_add_reference(
        interaction, session_id: str, reference: str
    ):
        await run_agent(
            interaction,
            "reconcile.add-reference",
            {"session_id": session_id, "reference": reference},
        )

    @reconcile.command(name="decide", description="Record a manual user decision")
    async def reconcile_decide(interaction, session_id: str, decision: str):
        await run_agent(
            interaction,
            "reconcile.decide",
            {"session_id": session_id, "decision": decision},
        )

    @reconcile.command(name="status", description="Show reconciliation status")
    async def reconcile_status(interaction, session_id: str):
        await run_agent(
            interaction, "reconcile.status", {"session_id": session_id}
        )

    for group in (prd, e2e, gap, inventory, version, repo, reconcile):
        bot.tree.add_command(group)

    @bot.event
    async def on_ready() -> None:
        LOGGER.info("Discord bot connected as %s", bot.user)

    @bot.event
    async def on_message(message) -> None:
        if message.author.bot:
            return
        if not settings.discord_text_help_enabled or bot.user is None:
            return
        bot_mentioned = bot.user in message.mentions
        session_thread = is_help_session_thread(
            channel_name=getattr(message.channel, "name", None),
            owner_id=getattr(message.channel, "owner_id", None),
            bot_user_id=bot.user.id,
        )
        if not is_help_context(
            is_direct_message=message.guild is None,
            bot_mentioned=bot_mentioned,
            is_session_thread=session_thread,
        ):
            return
        query = strip_bot_mention(message.content or "", bot.user.id)

        if message.guild is None or session_thread:
            await message.reply(answer_help(query), mention_author=False)
            return

        if isinstance(message.channel, discord.Thread):
            await message.reply(
                "Thread tidak dapat memiliki nested thread. Tag bot dari channel "
                "induk untuk memulai sesi Neurovi baru.",
                mention_author=False,
            )
            return

        try:
            thread = await message.create_thread(
                name=build_help_thread_name(str(message.author), message.id),
                auto_archive_duration=1440,
                reason="Neurovi help session requested by mention",
            )
            await thread.send(answer_help(query))
        except (discord.Forbidden, discord.HTTPException) as error:
            LOGGER.warning("Unable to create Discord help thread: %s", error)
            await message.reply(
                "Bot tidak dapat membuat thread sesi. Pastikan permission "
                "Create Public Threads dan Send Messages in Threads aktif.",
                mention_author=False,
            )

    return bot


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    try:
        settings = Settings.from_env()
        settings.require_discord()
        bot = build_bot(settings)
        bot.run(settings.discord_token, log_handler=None)
        return 0
    except ConfigurationError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
