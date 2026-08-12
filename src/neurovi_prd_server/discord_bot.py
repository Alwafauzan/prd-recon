from __future__ import annotations

import asyncio
import io
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Mapping

from neurovi_prd_server.agent_gateway import (
    AgentGateway,
    AgentGatewayError,
    AgentResponse,
)
from neurovi_prd_server.capabilities import CapabilityError, CapabilityRunner
from neurovi_prd_server.config import ConfigurationError, Settings
from neurovi_prd_server.help_system import (
    answer_help,
    build_help_thread_name,
    is_help_context,
    is_plain_help_request,
    is_help_session_thread,
    strip_bot_mention,
)


LOGGER = logging.getLogger("neurovi_prd_server.discord")


def load_e2e_options(repo_root: Path) -> tuple[tuple[str, str], ...]:
    path = repo_root / "reconciliation/e2e-inventory/e2e-domain-inventory.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ()
    domains = value.get("domains", []) if isinstance(value, Mapping) else []
    options = []
    for item in domains:
        if not isinstance(item, Mapping):
            continue
        code = str(item.get("e2e_code", "")).strip()
        title = str(item.get("title", "")).strip()
        if code and title:
            options.append((code, title))
    return tuple(sorted(options, key=lambda item: (item[1].casefold(), item[0])))


def match_e2e_options(
    options: tuple[tuple[str, str], ...], query: str, limit: int = 25
) -> tuple[tuple[str, str], ...]:
    normalized = query.strip().casefold()
    if not normalized:
        return options[:limit]
    ranked = []
    for code, title in options:
        code_value = code.casefold()
        title_value = title.casefold()
        if normalized not in code_value and normalized not in title_value:
            continue
        rank = 0 if code_value.startswith(normalized) else 1
        if title_value.startswith(normalized):
            rank = 0
        ranked.append((rank, title_value, code, title))
    ranked.sort()
    return tuple((code, title) for _, _, code, title in ranked[:limit])


def plain_language_agent_message(message: str) -> str:
    cleaned = message.strip()
    initial = re.search(
        r"(?P<code>E2E-[A-Z0-9-]+)\s+[—-]\s+[“\"](?P<title>[^”\"]+)[”\"].*?"
        r"(?P<count>\d+)\s+kandidat dokumen mekanis",
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if initial:
        return (
            f"Bot menemukan alur **{initial.group('title')}** dan "
            f"{initial.group('count')} dokumen yang mungkin terkait. Sebelum "
            "melanjutkan, pastikan ini memang proses yang ingin Anda bahas. "
            "Dokumen tersebut belum dianggap disetujui."
        )
    replacements = (
        (r"source flow Mermaid", "diagram alur"),
        (r"source flow", "diagram alur"),
        (r"kandidat dokumen mekanis", "dokumen yang mungkin terkait"),
        (r"kandidat mekanis", "kemungkinan terkait"),
        (r"secara mekanis", "berdasarkan kemiripan kata"),
        (r"boundary", "cakupan proses"),
        (r"baseline", "versi yang disetujui"),
        (r"scope", "cakupan"),
    )
    for pattern, replacement in replacements:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(
        r"\s*Jawab\s+`?CONFIRM`?.*?(?:SKIP|DEFER|UNKNOWN).*?(?:\.|$)",
        "",
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return cleaned.strip()


def plain_language_gateway_error(error: Exception) -> str:
    message = str(error).strip()
    message = re.sub(
        r"^Agent gateway (?:rejected request \(\d+\)|request failed):\s*",
        "",
        message,
        flags=re.IGNORECASE,
    )
    message = re.sub(r"^ERROR:\s*", "", message, flags=re.IGNORECASE)
    no_match = re.search(r"No E2E matches:\s*(.+)", message, flags=re.IGNORECASE)
    if no_match:
        return (
            f"Proses **{no_match.group(1)}** tidak ditemukan. Ketik sebagian nama "
            "proses lalu pilih salah satu hasil yang muncul."
        )
    if "Session not found" in message:
        return "Sesi tersebut sudah tidak tersedia. Mulai sesi baru dari daftar proses."
    return plain_language_agent_message(message) or "Terjadi kendala sementara. Coba lagi."


def load_active_reconciliation_sessions(
    repo_root: Path,
) -> tuple[tuple[str, int], ...]:
    workspace_root = repo_root / "reconciliation/workspaces"
    sessions = []
    for path in workspace_root.glob("*/session.json"):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(value, Mapping):
            continue
        if value.get("status") in {"FINISHED", "PUBLISHED"}:
            continue
        session_id = str(value.get("session_id", "")).strip()
        started_by = value.get("started_by", {})
        user_id = started_by.get("discord_user_id") if isinstance(started_by, Mapping) else None
        try:
            owner_id = int(str(user_id))
        except (TypeError, ValueError):
            continue
        if session_id:
            sessions.append((session_id, owner_id))
    return tuple(sorted(sessions))


def load_reconciliation_session(
    repo_root: Path, session_id: str
) -> dict[str, Any] | None:
    workspace_root = repo_root / "reconciliation/workspaces"
    for path in workspace_root.glob("*/session.json"):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(value, dict) and value.get("session_id") == session_id:
            return value
    return None


def latest_reconciliation_session_for_user(
    repo_root: Path, discord_user_id: int
) -> str | None:
    candidates = []
    workspace_root = repo_root / "reconciliation/workspaces"
    for path in workspace_root.glob("*/session.json"):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(value, Mapping):
            continue
        started_by = value.get("started_by", {})
        owner = started_by.get("discord_user_id") if isinstance(started_by, Mapping) else None
        if str(owner) != str(discord_user_id):
            continue
        if value.get("status") in {"FINISHED", "PUBLISHED"}:
            continue
        session_id = str(value.get("session_id", "")).strip()
        if session_id:
            candidates.append((str(value.get("updated_at", "")), session_id))
    return max(candidates)[1] if candidates else None


def plain_language_question(question: str) -> str:
    cleaned = question.strip()
    document = re.search(
        r"DOC-[A-Z0-9]+\s+[—-]\s+[“\"](?P<title>[^”\"]+)[”\"]",
        cleaned,
    )
    if document and "CONFIRMED_INCLUDE" in cleaned:
        return f"Bagaimana dokumen **{document.group('title')}** digunakan dalam proses ini?"
    replacements = (
        (r"CONFIRMED_INCLUDE", "dokumen utama"),
        (r"CONTEXT_ONLY", "dokumen pendukung"),
        (r"TAKE_OFF", "tidak terkait"),
        (r"DEFERRED", "ditunda"),
        (r"PRIMARY_SCOPE", "cakupan utama"),
        (r"boundary", "cakupan proses"),
        (r"source flow Mermaid", "diagram alur"),
        (r"source flow", "diagram alur"),
    )
    for pattern, replacement in replacements:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*Jawab\s+.*$", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def reconciliation_question_kind(
    question: str,
    question_type: str | None = None,
    document_ids: str | None = None,
) -> str:
    normalized_type = str(question_type or "").upper()
    if normalized_type in {"CONFIRMATION", "DOCUMENT_SELECTION", "OPEN_ANSWER"}:
        return normalized_type
    if "CONFIRMED_INCLUDE" in question and "CONTEXT_ONLY" in question:
        return "DOCUMENT_SELECTION"
    if document_ids and "dokumen" in question.casefold():
        return "DOCUMENT_SELECTION"
    if question.strip().casefold().startswith("apakah"):
        return "CONFIRMATION"
    return "OPEN_ANSWER"


def agent_status_label(status: str | None) -> str:
    return {
        "AWAITING_USER": "Menunggu pilihan Anda",
        "IN_PROGRESS": "Sedang diproses",
        "READY_FOR_BASELINE_REVIEW": "Siap ditinjau",
        "BLOCKED": "Belum dapat dilanjutkan",
        "PUBLISHED": "Selesai diterbitkan",
    }.get(str(status or "").upper(), "Sedang diproses")


def is_allowed_discord_context(
    *,
    channel_id: int | None,
    allowed_channel_ids: frozenset[int],
) -> bool:
    return bool(allowed_channel_ids and channel_id in allowed_channel_ids)


def is_allowed_help_message_context(
    *,
    channel_id: int | None,
    parent_channel_id: int | None,
    is_session_thread: bool,
    allowed_channel_ids: frozenset[int],
) -> bool:
    return is_allowed_discord_context(
        channel_id=channel_id,
        allowed_channel_ids=allowed_channel_ids,
    ) or bool(
        is_session_thread
        and parent_channel_id in allowed_channel_ids
    )


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
    e2e_options = load_e2e_options(settings.repo_root)

    async def invoke_agent(
        interaction,
        capability: str,
        parameters: Mapping[str, Any],
    ) -> AgentResponse:
        if gateway is None:
            raise AgentGatewayError("Agent rekonsiliasi belum dikonfigurasi.")
        payload = dict(parameters)
        payload["repository_root"] = str(settings.repo_root)
        return await asyncio.to_thread(
            gateway.invoke,
            capability,
            payload,
            actor_payload(interaction),
        )

    async def ensure_reconcile_access(interaction) -> bool:
        if not is_allowed_discord_context(
            channel_id=interaction.channel_id,
            allowed_channel_ids=settings.discord_allowed_channel_ids,
        ):
            return False
        if not has_role(interaction, settings.discord_reconcile_role_ids):
            message = "Anda belum memiliki izin untuk menjalankan rekonsiliasi."
        elif gateway is None:
            message = "Layanan rekonsiliasi belum tersedia. Hubungi administrator."
        else:
            return True
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
        return False

    async def update_reconciliation_message(
        interaction,
        response: AgentResponse,
        owner_id: int,
        *,
        edit: bool,
    ) -> None:
        session_id = response.session_id
        session = (
            load_reconciliation_session(settings.repo_root, session_id)
            if session_id
            else None
        )
        current = session.get("current_question") if isinstance(session, Mapping) else None
        question = str(current.get("question", "")) if isinstance(current, Mapping) else ""
        why_needed = str(current.get("why_needed", "")) if isinstance(current, Mapping) else ""
        question_kind = reconciliation_question_kind(
            question,
            str(current.get("question_type", "")) if isinstance(current, Mapping) else "",
            str(current.get("document_ids", "")) if isinstance(current, Mapping) else "",
        )
        if question_kind == "DOCUMENT_SELECTION":
            description = (
                "Langkah sebelumnya sudah tersimpan. Sekarang tentukan apakah "
                "dokumen berikut menjadi dokumen utama, hanya pendukung, atau "
                "tidak terkait dengan proses ini."
            )
        elif question_kind == "CONFIRMATION" and question:
            description = "Sebelum melanjutkan, saya perlu memastikan satu hal."
        elif question:
            description = "Saya memerlukan jawaban singkat untuk melanjutkan peninjauan."
        else:
            description = plain_language_agent_message(response.message)
        embed = discord.Embed(
            title=(
                f"Tinjau proses: {session.get('e2e_title', '')}"
                if isinstance(session, Mapping)
                else "Rekonsiliasi dokumen"
            ),
            description=description,
            color=discord.Color.blurple(),
        )
        embed.add_field(
            name="Status",
            value=agent_status_label(response.status),
            inline=False,
        )
        if question:
            embed.add_field(
                name="Pilihan berikutnya",
                value=plain_language_question(question),
                inline=False,
            )
        if why_needed:
            embed.add_field(
                name="Mengapa ini ditanyakan",
                value=plain_language_agent_message(why_needed)[:500],
                inline=False,
            )
        if session_id:
            embed.set_footer(text=f"Referensi sesi: {session_id}")
        view = (
            ReconciliationView(session_id, owner_id)
            if session_id and response.status == "AWAITING_USER"
            else None
        )
        if edit:
            await interaction.edit_original_response(embed=embed, view=view)
        else:
            await interaction.followup.send(
                embed=embed,
                view=view,
                ephemeral=settings.discord_ephemeral,
            )

    class AnswerModal(discord.ui.Modal, title="Jawab pertanyaan"):
        answer = discord.ui.TextInput(
            label="Jawaban Anda",
            placeholder="Tulis dengan bahasa sehari-hari...",
            style=discord.TextStyle.paragraph,
            max_length=2000,
        )

        def __init__(self, session_id: str, owner_id: int) -> None:
            super().__init__()
            self.session_id = session_id
            self.owner_id = owner_id

        async def on_submit(self, interaction) -> None:
            if not is_allowed_discord_context(
                channel_id=interaction.channel_id,
                allowed_channel_ids=settings.discord_allowed_channel_ids,
            ):
                return
            if interaction.user.id != self.owner_id:
                await interaction.response.send_message(
                    "Sesi ini sedang digunakan oleh pengguna lain.", ephemeral=True
                )
                return
            if not await ensure_reconcile_access(interaction):
                return
            await interaction.response.defer()
            try:
                response = await invoke_agent(
                    interaction,
                    "reconcile.answer",
                    {"session_id": self.session_id, "answer": str(self.answer)},
                )
                await update_reconciliation_message(
                    interaction, response, self.owner_id, edit=True
                )
            except AgentGatewayError as error:
                await interaction.followup.send(
                    "Jawaban belum tersimpan. " + plain_language_gateway_error(error),
                    ephemeral=True,
                )

    class ReconciliationView(discord.ui.View):
        def __init__(self, session_id: str, owner_id: int) -> None:
            super().__init__(timeout=None)
            self.session_id = session_id
            self.owner_id = owner_id
            session = load_reconciliation_session(settings.repo_root, session_id)
            current = session.get("current_question") if isinstance(session, Mapping) else None
            question = str(current.get("question", "")) if isinstance(current, Mapping) else ""
            kind = reconciliation_question_kind(
                question,
                str(current.get("question_type", "")) if isinstance(current, Mapping) else "",
                str(current.get("document_ids", "")) if isinstance(current, Mapping) else "",
            )
            if kind == "DOCUMENT_SELECTION":
                self.add_item(
                    ReconciliationActionButton(
                        session_id,
                        "Dokumen utama",
                        "CONFIRMED_INCLUDE",
                        discord.ButtonStyle.success,
                    )
                )
                self.add_item(
                    ReconciliationActionButton(
                        session_id,
                        "Pendukung",
                        "CONTEXT_ONLY",
                        discord.ButtonStyle.primary,
                    )
                )
                self.add_item(
                    ReconciliationActionButton(
                        session_id,
                        "Tidak terkait",
                        "TAKE_OFF",
                        discord.ButtonStyle.danger,
                    )
                )
                self.add_item(
                    ReconciliationControlButton(
                        session_id, "Lewati", "SKIP", discord.ButtonStyle.secondary
                    )
                )
                self.add_item(
                    ReconciliationControlButton(
                        session_id, "Tunda", "DEFER", discord.ButtonStyle.secondary
                    )
                )
                self.add_item(
                    ReconciliationControlButton(
                        session_id,
                        "Tidak tahu",
                        "UNKNOWN",
                        discord.ButtonStyle.secondary,
                    )
                )
            elif kind == "CONFIRMATION":
                self.add_item(
                    ReconciliationActionButton(
                        session_id,
                        "Ya, lanjutkan",
                        "CONFIRM",
                        discord.ButtonStyle.success,
                    )
                )
                self.add_item(AnswerButton(session_id))
                self.add_item(
                    ReconciliationActionButton(
                        session_id,
                        "Tidak sesuai",
                        "Tidak, cakupan proses ini belum sesuai.",
                        discord.ButtonStyle.danger,
                    )
                )
                self.add_item(
                    ReconciliationControlButton(
                        session_id, "Tunda", "DEFER", discord.ButtonStyle.secondary
                    )
                )
                self.add_item(
                    ReconciliationControlButton(
                        session_id,
                        "Tidak tahu",
                        "UNKNOWN",
                        discord.ButtonStyle.secondary,
                    )
                )
            else:
                self.add_item(AnswerButton(session_id))
                self.add_item(
                    ReconciliationControlButton(
                        session_id, "Lewati", "SKIP", discord.ButtonStyle.secondary
                    )
                )
                self.add_item(
                    ReconciliationControlButton(
                        session_id, "Tunda", "DEFER", discord.ButtonStyle.secondary
                    )
                )
                self.add_item(
                    ReconciliationControlButton(
                        session_id,
                        "Tidak tahu",
                        "UNKNOWN",
                        discord.ButtonStyle.secondary,
                    )
                )

        async def interaction_check(self, interaction) -> bool:
            if not is_allowed_discord_context(
                channel_id=interaction.channel_id,
                allowed_channel_ids=settings.discord_allowed_channel_ids,
            ):
                return False
            if interaction.user.id == self.owner_id:
                return True
            await interaction.response.send_message(
                "Sesi ini sedang digunakan oleh pengguna lain.", ephemeral=True
            )
            return False

    class ReconciliationActionButton(discord.ui.Button):
        def __init__(
            self, session_id: str, label: str, answer: str, style
        ) -> None:
            super().__init__(
                label=label,
                style=style,
                custom_id=f"neurovi:{session_id}:decision:{answer}",
            )
            self.answer = answer

        async def callback(self, interaction) -> None:
            view = self.view
            if not isinstance(view, ReconciliationView):
                return
            if not await ensure_reconcile_access(interaction):
                return
            await interaction.response.defer()
            try:
                response = await invoke_agent(
                    interaction,
                    "reconcile.decide",
                    {"session_id": view.session_id, "decision": self.answer},
                )
                await update_reconciliation_message(
                    interaction, response, view.owner_id, edit=True
                )
            except AgentGatewayError as error:
                await interaction.followup.send(
                    "Pilihan belum tersimpan. " + plain_language_gateway_error(error),
                    ephemeral=True,
                )

    class ReconciliationControlButton(discord.ui.Button):
        def __init__(
            self, session_id: str, label: str, action: str, style
        ) -> None:
            super().__init__(
                label=label,
                style=style,
                custom_id=f"neurovi:{session_id}:control:{action}",
            )
            self.action = action

        async def callback(self, interaction) -> None:
            view = self.view
            if not isinstance(view, ReconciliationView):
                return
            if not await ensure_reconcile_access(interaction):
                return
            await interaction.response.defer()
            try:
                response = await invoke_agent(
                    interaction,
                    "reconcile.control",
                    {"session_id": view.session_id, "action": self.action},
                )
                await update_reconciliation_message(
                    interaction, response, view.owner_id, edit=True
                )
            except AgentGatewayError as error:
                await interaction.followup.send(
                    "Pilihan belum tersimpan. " + plain_language_gateway_error(error),
                    ephemeral=True,
                )

    class AnswerButton(discord.ui.Button):
        def __init__(self, session_id: str) -> None:
            super().__init__(
                label="Jawab sendiri",
                style=discord.ButtonStyle.primary,
                custom_id=f"neurovi:{session_id}:answer:custom",
            )

        async def callback(self, interaction) -> None:
            view = self.view
            if isinstance(view, ReconciliationView):
                await interaction.response.send_modal(
                    AnswerModal(view.session_id, view.owner_id)
                )

    class NeuroviBot(commands.Bot):
        async def setup_hook(self) -> None:
            for session_id, owner_id in load_active_reconciliation_sessions(
                settings.repo_root
            ):
                self.add_view(ReconciliationView(session_id, owner_id))
            if settings.discord_guild_ids:
                for guild_id in settings.discord_guild_ids:
                    guild = discord.Object(id=guild_id)
                    self.tree.copy_global_to(guild=guild)
                    await self.tree.sync(guild=guild)
                    LOGGER.info("Synced commands to guild %s", guild_id)
            else:
                await self.tree.sync()
                LOGGER.info("Synced global commands")

    class ScopedCommandTree(app_commands.CommandTree):
        async def interaction_check(self, interaction) -> bool:
            return is_allowed_discord_context(
                channel_id=interaction.channel_id,
                allowed_channel_ids=settings.discord_allowed_channel_ids,
            )

    intents = discord.Intents.default()
    intents.message_content = settings.discord_text_help_enabled
    bot = NeuroviBot(
        command_prefix="!",
        intents=intents,
        help_command=None,
        tree_cls=ScopedCommandTree,
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

    def message_actor_payload(message) -> dict[str, Any]:
        roles = getattr(message.author, "roles", [])
        return {
            "discord_user_id": str(message.author.id),
            "discord_user_name": str(message.author),
            "discord_role_ids": [str(role.id) for role in roles],
            "guild_id": str(message.guild.id) if message.guild else None,
            "channel_id": str(message.channel.id),
        }

    async def contextual_help(message, query: str) -> str:
        if not query.strip() or gateway is None:
            return answer_help(query)
        try:
            response = await asyncio.to_thread(
                gateway.invoke,
                "help.answer",
                {"query": query},
                message_actor_payload(message),
            )
            return response.message
        except AgentGatewayError as error:
            LOGGER.warning("Contextual help advisor unavailable: %s", error)
            return answer_help(query)

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
                "Anda belum memiliki izin untuk menggunakan fitur ini.", ephemeral=True
            )
            return
        if gateway is None:
            await interaction.response.send_message(
                "Layanan rekonsiliasi belum tersedia. Hubungi administrator.",
                ephemeral=True,
            )
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            response = await invoke_agent(
                interaction,
                capability,
                parameters,
            )
            await update_reconciliation_message(
                interaction,
                response,
                interaction.user.id,
                edit=False,
            )
        except AgentGatewayError as error:
            await interaction.followup.send(
                plain_language_gateway_error(error), ephemeral=True
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

    @reconcile.command(name="start", description="Mulai peninjauan satu proses")
    @app_commands.describe(
        e2e_code_or_name="Ketik nama proses, lalu pilih dari daftar"
    )
    async def reconcile_start(interaction, e2e_code_or_name: str):
        await run_agent(
            interaction, "reconcile.start", {"e2e": e2e_code_or_name}
        )

    @reconcile_start.autocomplete("e2e_code_or_name")
    async def reconcile_start_autocomplete(interaction, current: str):
        del interaction
        return [
            app_commands.Choice(name=f"{title} ({code})"[:100], value=code)
            for code, title in match_e2e_options(e2e_options, current)
        ]

    @reconcile.command(name="continue", description="Lanjutkan sesi terakhir Anda")
    async def reconcile_continue(interaction):
        session_id = latest_reconciliation_session_for_user(
            settings.repo_root, interaction.user.id
        )
        if not session_id:
            await interaction.response.send_message(
                "Anda belum memiliki sesi aktif. Gunakan `/reconcile start` terlebih dahulu.",
                ephemeral=True,
            )
            return
        await run_agent(
            interaction, "reconcile.status", {"session_id": session_id}
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
        if not is_plain_help_request(message.content or ""):
            return
        bot_mentioned = bot.user in message.mentions
        session_thread = is_help_session_thread(
            channel_name=getattr(message.channel, "name", None),
            owner_id=getattr(message.channel, "owner_id", None),
            bot_user_id=bot.user.id,
        )
        if not is_allowed_help_message_context(
            channel_id=getattr(message.channel, "id", None),
            parent_channel_id=getattr(message.channel, "parent_id", None),
            is_session_thread=session_thread,
            allowed_channel_ids=settings.discord_allowed_channel_ids,
        ):
            return
        if not is_help_context(
            is_direct_message=message.guild is None,
            bot_mentioned=bot_mentioned,
            is_session_thread=session_thread,
            is_guild_channel=(
                message.guild is not None
                and not isinstance(message.channel, discord.Thread)
                and message.channel.id in settings.discord_allowed_channel_ids
            ),
            is_thread=isinstance(message.channel, discord.Thread),
        ):
            return
        query = strip_bot_mention(message.content or "", bot.user.id)

        if message.guild is None or session_thread:
            await message.reply(
                await contextual_help(message, query), mention_author=False
            )
            return

        try:
            thread = await message.create_thread(
                name=build_help_thread_name(str(message.author), message.id),
                auto_archive_duration=1440,
                reason="Neurovi automatic help session",
            )
            await thread.send(await contextual_help(message, query))
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
