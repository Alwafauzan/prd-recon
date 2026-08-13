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
TERMINAL_RECONCILIATION_STATUSES = frozenset(
    {"START_FAILED", "STOPPED_BY_USER", "FINISHED", "PUBLISHED"}
)
PROCESS_STAGE_LABELS = {
    "ENTRY": "Awal proses",
    "WORKLIST": "Pelayanan utama",
    "ASSESSMENT": "Pemeriksaan",
    "EXECUTION": "Tindakan",
    "HANDOFF": "Lanjutan proses",
    "EXIT": "Akhir proses",
}


def load_e2e_options(repo_root: Path) -> tuple[tuple[str, str], ...]:
    path = repo_root / "reconciliation/e2e-inventory/domain-worklist.json"
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


def guided_process_summary(repo_root: Path, e2e_code: str) -> str:
    path = repo_root / "reconciliation/e2e-inventory/domain-worklist.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "Daftar proses belum dapat dibaca. Coba lagi nanti."
    domains = value.get("domains", []) if isinstance(value, Mapping) else []
    domain = next(
        (
            item
            for item in domains
            if isinstance(item, Mapping)
            and str(item.get("e2e_code", "")).casefold() == e2e_code.casefold()
        ),
        None,
    )
    if not isinstance(domain, Mapping):
        return "Proses yang dipilih tidak ditemukan."
    documents = domain.get("documents", [])
    if not isinstance(documents, list):
        documents = []
    lines = [
        f"# {domain.get('title', e2e_code)}",
        "",
        str(domain.get("purpose", "Daftar pemeriksaan alur proses.")),
        "",
        f"Dokumen utama dalam daftar pemeriksaan: {len(documents)}",
        "",
        "## Urutan pemeriksaan",
        "",
    ]
    for item in documents:
        if not isinstance(item, Mapping):
            continue
        stage = PROCESS_STAGE_LABELS.get(
            str(item.get("worklist_stage", "")).upper(), "Bagian proses"
        )
        lines.append(f"{item.get('worklist_order', '-')}. **{stage}** — {item.get('title', '')}")
    lines.extend(
        [
            "",
            "Semua dokumen pada daftar ini langsung dipakai untuk memeriksa alur. "
            "Hubungan dengan proses lain tetap dipakai sebagai konteks penunjang.",
        ]
    )
    return "\n".join(lines)


def guided_gap_summary(repo_root: Path, e2e_code: str) -> str:
    path = repo_root / "reconciliation/e2e-inventory/domain-worklist.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "Daftar proses belum dapat dibaca. Coba lagi nanti."
    domains = value.get("domains", []) if isinstance(value, Mapping) else []
    domain = next(
        (
            item
            for item in domains
            if isinstance(item, Mapping)
            and str(item.get("e2e_code", "")).casefold() == e2e_code.casefold()
        ),
        None,
    )
    if not isinstance(domain, Mapping):
        return "Proses yang dipilih tidak ditemukan."
    document_count = int(domain.get("document_count", 0) or 0)
    review_count = int(domain.get("review_required_count", 0) or 0)
    relation_count = int(domain.get("relation_count", 0) or 0)
    cross_count = int(domain.get("cross_domain_relation_count", 0) or 0)
    if review_count:
        review_text = (
            f"Ada {review_count} catatan yang perlu dilihat kembali dalam daftar ini."
        )
    else:
        review_text = (
            "Belum ada catatan kualitas inventaris yang ditandai khusus. Pemeriksaan "
            "akan langsung mencari gap alur atau keputusan bisnis yang belum jelas."
        )
    return "\n".join(
        [
            f"# Pemeriksaan awal: {domain.get('title', e2e_code)}",
            "",
            f"Bot menemukan {document_count} dokumen utama dan {relation_count} hubungan "
            f"dokumen, termasuk {cross_count} hubungan ke proses lain.",
            "",
            review_text,
            "",
            "Hasil ini hanya membantu menentukan bagian yang perlu ditinjau. Bot belum "
            "mengubah dokumen atau mengambil keputusan.",
            "",
            "Jika ingin membahasnya satu per satu, kembali ke `/mulai` lalu pilih "
            "**Perbaiki alur utama** atau **Perbaiki detail proses**.",
        ]
    )


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
        (r"source flow Mermaid", "worklist domain"),
        (r"source flow", "worklist domain"),
        (r"diagram alur", "worklist domain"),
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


def reconciliation_session_paths(repo_root: Path) -> tuple[Path, ...]:
    workspace_root = repo_root / "reconciliation/workspaces"
    if not workspace_root.is_dir():
        return ()
    legacy = workspace_root.glob("*/session.json")
    scoped = workspace_root.glob("*/sessions/*/session.json")
    return tuple(sorted((*legacy, *scoped)))


def load_active_reconciliation_sessions(
    repo_root: Path,
) -> tuple[tuple[str, int], ...]:
    sessions = []
    for path in reconciliation_session_paths(repo_root):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(value, Mapping):
            continue
        if value.get("status") in TERMINAL_RECONCILIATION_STATUSES:
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
    for path in reconciliation_session_paths(repo_root):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(value, dict) and value.get("session_id") == session_id:
            return value
    return None


def latest_reconciliation_session_for_user(
    repo_root: Path,
    discord_user_id: int,
    reconciliation_mode: str | None = None,
) -> str | None:
    candidates = []
    requested_mode = str(reconciliation_mode or "").upper()
    for path in reconciliation_session_paths(repo_root):
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
        session_mode = str(value.get("reconciliation_mode", "MAIN_FLOW")).upper()
        if requested_mode and session_mode != requested_mode:
            continue
        if value.get("status") in TERMINAL_RECONCILIATION_STATUSES:
            continue
        session_id = str(value.get("session_id", "")).strip()
        if session_id:
            candidates.append((str(value.get("updated_at", "")), session_id))
    return max(candidates)[1] if candidates else None


def reconciliation_resume_request(
    session: Mapping[str, Any] | None,
    reconciliation_mode: str,
) -> tuple[str, dict[str, Any]]:
    if not isinstance(session, Mapping):
        return "reconcile.status", {}
    current = session.get("current_question")
    status = str(session.get("status", "")).upper()
    if status in {"SELECTED_FOR_REVIEW", "IN_PROGRESS"} and not isinstance(
        current, Mapping
    ):
        capability = (
            "reconcile.main-flow.start"
            if reconciliation_mode == "MAIN_FLOW"
            else "reconcile.business-cases.start"
        )
        return capability, {"e2e": str(session.get("e2e_code", ""))}
    return "reconcile.status", {"session_id": str(session.get("session_id", ""))}


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
        (r"source flow Mermaid", "daftar pemeriksaan proses"),
        (r"source flow", "daftar pemeriksaan proses"),
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
    if normalized_type in {"CONFIRMATION", "OPEN_ANSWER"}:
        return normalized_type
    if question.strip().casefold().startswith("apakah"):
        return "CONFIRMATION"
    return "OPEN_ANSWER"


def agent_status_label(status: str | None) -> str:
    return {
        "AWAITING_USER": "Menunggu pilihan Anda",
        "IN_PROGRESS": "Sedang diproses",
        "READY_FOR_BASELINE_REVIEW": "Siap ditinjau",
        "BLOCKED": "Belum dapat dilanjutkan",
        "STOPPED_BY_USER": "Sesi telah diakhiri",
        "PUBLISHED": "Selesai diterbitkan",
    }.get(str(status or "").upper(), "Sedang diproses")


def processing_state_text(action: str) -> tuple[str, str]:
    return {
        "answer": (
            "Sedang menyimpan jawaban...",
            "Mohon tunggu. Bot sedang memahami jawaban dan menyiapkan langkah berikutnya.",
        ),
        "decision": (
            "Sedang menyimpan pilihan...",
            "Mohon tunggu. Pilihan belum dianggap tersimpan sampai proses selesai.",
        ),
        "control": (
            "Sedang melanjutkan pemeriksaan...",
            "Mohon tunggu. Bot sedang mencatat pilihan dan mencari pertanyaan berikutnya.",
        ),
        "stop": (
            "Sedang mengakhiri sesi...",
            "Mohon tunggu. Tombol akan hilang setelah sesi berhasil ditutup.",
        ),
        "start": (
            "Sedang menyiapkan pemeriksaan...",
            "Bot sedang membaca daftar proses dan menyiapkan pertanyaan pertama.",
        ),
        "continue": (
            "Sedang membuka sesi...",
            "Bot sedang memuat pertanyaan terakhir dan pilihan yang tersedia.",
        ),
    }.get(
        action,
        ("Sedang memproses...", "Mohon tunggu sampai proses selesai."),
    )


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


def is_allowed_bot_context(
    *,
    channel_id: int | None,
    parent_channel_id: int | None,
    channel_name: str | None,
    owner_id: int | None,
    bot_user_id: int,
    allowed_channel_ids: frozenset[int],
) -> bool:
    return is_allowed_help_message_context(
        channel_id=channel_id,
        parent_channel_id=parent_channel_id,
        is_session_thread=is_help_session_thread(
            channel_name=channel_name,
            owner_id=owner_id,
            bot_user_id=bot_user_id,
        ),
        allowed_channel_ids=allowed_channel_ids,
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
        if bot.user is None or not is_allowed_bot_context(
            channel_id=interaction.channel_id,
            parent_channel_id=getattr(interaction.channel, "parent_id", None),
            channel_name=getattr(interaction.channel, "name", None),
            owner_id=getattr(interaction.channel, "owner_id", None),
            bot_user_id=bot.user.id,
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

    async def ensure_session_owner(interaction, session_id: str) -> bool:
        session = load_reconciliation_session(settings.repo_root, session_id)
        started_by = session.get("started_by", {}) if isinstance(session, Mapping) else {}
        owner_id = (
            str(started_by.get("discord_user_id", ""))
            if isinstance(started_by, Mapping)
            else ""
        )
        if owner_id == str(interaction.user.id):
            return True
        message = "Sesi ini sedang digunakan oleh pengguna lain."
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
        if question_kind == "CONFIRMATION" and question:
            description = "Saya menemukan keputusan bisnis yang perlu Anda pastikan."
        elif question:
            description = "Saya memerlukan jawaban singkat untuk melanjutkan peninjauan."
        else:
            description = plain_language_agent_message(response.message)
        embed = discord.Embed(
            title=(
                f"{session.get('reconciliation_mode_label', 'Peninjauan dokumen')}: "
                f"{session.get('e2e_title', '')}"
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
            if session_id
            and str(response.status or "").upper()
            not in TERMINAL_RECONCILIATION_STATUSES
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

    def processing_embed(session_id: str, action: str):
        title, description = processing_state_text(action)
        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.gold(),
        )
        embed.add_field(
            name="Status tombol",
            value="Semua tombol dinonaktifkan sementara untuk mencegah klik ganda.",
            inline=False,
        )
        embed.set_footer(text=f"Referensi sesi: {session_id}")
        return embed

    def disabled_reconciliation_view(session_id: str, owner_id: int):
        view = ReconciliationView(session_id, owner_id)
        for item in view.children:
            item.disabled = True
        return view

    async def show_processing_state(
        interaction,
        session_id: str,
        owner_id: int,
        action: str,
    ) -> None:
        await interaction.response.edit_message(
            embed=processing_embed(session_id, action),
            view=disabled_reconciliation_view(session_id, owner_id),
        )

    async def restore_reconciliation_message(
        interaction,
        session_id: str,
        owner_id: int,
        error: Exception,
    ) -> None:
        session = load_reconciliation_session(settings.repo_root, session_id)
        current = (
            session.get("current_question")
            if isinstance(session, Mapping)
            else None
        )
        answer_was_recorded = not isinstance(current, Mapping)
        failure_message = (
            "Jawaban atau pilihan Anda sudah tercatat, tetapi langkah berikutnya "
            "belum siap. Buka `/mulai`, lalu pilih tombol lanjut untuk mencoba lagi."
            if answer_was_recorded
            else "Jawaban atau pilihan Anda belum tercatat. Silakan coba lagi."
        )
        response = AgentResponse(
            message=(
                failure_message + " " + plain_language_gateway_error(error)
            ),
            status=str(session.get("status", "AWAITING_USER"))
            if isinstance(session, Mapping)
            else "AWAITING_USER",
            session_id=session_id,
        )
        await update_reconciliation_message(interaction, response, owner_id, edit=True)
        await interaction.followup.send(
            failure_message,
            ephemeral=True,
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
            if bot.user is None or not is_allowed_bot_context(
                channel_id=interaction.channel_id,
                parent_channel_id=getattr(interaction.channel, "parent_id", None),
                channel_name=getattr(interaction.channel, "name", None),
                owner_id=getattr(interaction.channel, "owner_id", None),
                bot_user_id=bot.user.id,
                allowed_channel_ids=settings.discord_allowed_channel_ids,
            ):
                return
            if interaction.user.id != self.owner_id:
                await interaction.response.send_message(
                    "Sesi ini sedang digunakan oleh pengguna lain.", ephemeral=True
                )
                return
            if not await ensure_session_owner(interaction, self.session_id):
                return
            if not await ensure_reconcile_access(interaction):
                return
            await show_processing_state(
                interaction, self.session_id, self.owner_id, "answer"
            )
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
                await restore_reconciliation_message(
                    interaction, self.session_id, self.owner_id, error
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
            if kind == "CONFIRMATION":
                self.add_item(
                    ReconciliationActionButton(
                        session_id,
                        "Ya, sudah sesuai",
                        "CONFIRM",
                        discord.ButtonStyle.success,
                    )
                )
                self.add_item(AnswerButton(session_id))
                self.add_item(
                    ReconciliationActionButton(
                        session_id,
                        "Belum sesuai",
                        "Tidak, cakupan proses ini belum sesuai.",
                        discord.ButtonStyle.danger,
                    )
                )
                self.add_item(
                    ReconciliationControlButton(
                        session_id,
                        "Jawab nanti",
                        "DEFER",
                        discord.ButtonStyle.secondary,
                    )
                )
                self.add_item(
                    ReconciliationControlButton(
                        session_id,
                        "Saya belum tahu",
                        "UNKNOWN",
                        discord.ButtonStyle.secondary,
                    )
                )
            elif question:
                self.add_item(AnswerButton(session_id))
                self.add_item(
                    ReconciliationControlButton(
                        session_id,
                        "Lewati pertanyaan",
                        "SKIP",
                        discord.ButtonStyle.secondary,
                    )
                )
                self.add_item(
                    ReconciliationControlButton(
                        session_id,
                        "Jawab nanti",
                        "DEFER",
                        discord.ButtonStyle.secondary,
                    )
                )
                self.add_item(
                    ReconciliationControlButton(
                        session_id,
                        "Saya belum tahu",
                        "UNKNOWN",
                        discord.ButtonStyle.secondary,
                    )
                )
            self.add_item(StopSessionButton(session_id))

        async def interaction_check(self, interaction) -> bool:
            if bot.user is None or not is_allowed_bot_context(
                channel_id=interaction.channel_id,
                parent_channel_id=getattr(interaction.channel, "parent_id", None),
                channel_name=getattr(interaction.channel, "name", None),
                owner_id=getattr(interaction.channel, "owner_id", None),
                bot_user_id=bot.user.id,
                allowed_channel_ids=settings.discord_allowed_channel_ids,
            ):
                return False
            if interaction.user.id == self.owner_id:
                return await ensure_session_owner(interaction, self.session_id)
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
            await show_processing_state(
                interaction, view.session_id, view.owner_id, "decision"
            )
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
                await restore_reconciliation_message(
                    interaction, view.session_id, view.owner_id, error
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
            await show_processing_state(
                interaction, view.session_id, view.owner_id, "control"
            )
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
                await restore_reconciliation_message(
                    interaction, view.session_id, view.owner_id, error
                )

    class AnswerButton(discord.ui.Button):
        def __init__(self, session_id: str) -> None:
            super().__init__(
                label="Tulis jawaban",
                style=discord.ButtonStyle.primary,
                custom_id=f"neurovi:{session_id}:answer:custom",
            )

        async def callback(self, interaction) -> None:
            view = self.view
            if isinstance(view, ReconciliationView):
                await interaction.response.send_modal(
                    AnswerModal(view.session_id, view.owner_id)
                )

    class StopSessionButton(discord.ui.Button):
        def __init__(self, session_id: str) -> None:
            super().__init__(
                label="Akhiri sesi",
                style=discord.ButtonStyle.danger,
                custom_id=f"neurovi:{session_id}:stop:confirm",
            )

        async def callback(self, interaction) -> None:
            view = self.view
            if not isinstance(view, ReconciliationView):
                return
            await interaction.response.send_message(
                "Akhiri sesi sekarang? Semua jawaban tetap tersimpan, tetapi "
                "pertanyaan yang belum selesai tidak akan dianggap terjawab.",
                view=ConfirmStopSessionView(
                    view.session_id, view.owner_id, interaction.message
                ),
                ephemeral=True,
            )

    class ConfirmStopSessionView(discord.ui.View):
        def __init__(self, session_id: str, owner_id: int, source_message) -> None:
            super().__init__(timeout=120)
            self.session_id = session_id
            self.owner_id = owner_id
            self.source_message = source_message

        async def interaction_check(self, interaction) -> bool:
            if interaction.user.id == self.owner_id:
                return await ensure_session_owner(interaction, self.session_id)
            await interaction.response.send_message(
                "Sesi ini sedang digunakan oleh pengguna lain.", ephemeral=True
            )
            return False

        @discord.ui.button(label="Ya, akhiri sesi", style=discord.ButtonStyle.danger)
        async def confirm(self, interaction, button) -> None:
            del button
            if not await ensure_reconcile_access(interaction):
                return
            await interaction.response.edit_message(
                content=processing_state_text("stop")[1],
                view=None,
            )
            if self.source_message is not None:
                await self.source_message.edit(
                    embed=processing_embed(self.session_id, "stop"),
                    view=disabled_reconciliation_view(
                        self.session_id, self.owner_id
                    ),
                )
            try:
                response = await invoke_agent(
                    interaction,
                    "reconcile.stop",
                    {"session_id": self.session_id},
                )
                embed = discord.Embed(
                    title="Sesi telah diakhiri",
                    description=plain_language_agent_message(response.message),
                    color=discord.Color.dark_grey(),
                )
                embed.add_field(
                    name="Yang tersimpan",
                    value=(
                        "Jawaban dan pilihan sebelumnya tetap tercatat. Pertanyaan "
                        "yang belum selesai tetap terbuka dan tidak dianggap disetujui."
                    ),
                    inline=False,
                )
                embed.set_footer(text=f"Referensi sesi: {self.session_id}")
                if self.source_message is not None:
                    await self.source_message.edit(embed=embed, view=None)
                await interaction.edit_original_response(
                    content="Sesi telah diakhiri.", view=None
                )
            except AgentGatewayError as error:
                if self.source_message is not None:
                    session = load_reconciliation_session(
                        settings.repo_root, self.session_id
                    )
                    response = AgentResponse(
                        message="Sesi belum dapat diakhiri.",
                        status=str(session.get("status", "AWAITING_USER"))
                        if isinstance(session, Mapping)
                        else "AWAITING_USER",
                        session_id=self.session_id,
                    )
                    current = session.get("current_question") if isinstance(session, Mapping) else None
                    question = str(current.get("question", "")) if isinstance(current, Mapping) else ""
                    embed = discord.Embed(
                        title=(
                            f"Tinjau proses: {session.get('e2e_title', '')}"
                            if isinstance(session, Mapping)
                            else "Rekonsiliasi dokumen"
                        ),
                        description="Sesi belum diakhiri. Anda dapat mencoba lagi.",
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
                    embed.set_footer(text=f"Referensi sesi: {self.session_id}")
                    await self.source_message.edit(
                        embed=embed,
                        view=ReconciliationView(self.session_id, self.owner_id),
                    )
                await interaction.followup.send(
                    "Sesi belum dapat diakhiri. " + plain_language_gateway_error(error),
                    ephemeral=True,
                )

        @discord.ui.button(label="Batal", style=discord.ButtonStyle.secondary)
        async def cancel(self, interaction, button) -> None:
            del button
            await interaction.response.edit_message(
                content="Sesi tetap dilanjutkan.", view=None
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
            user = interaction.client.user
            if user is None:
                return False
            channel = interaction.channel
            return is_allowed_bot_context(
                channel_id=interaction.channel_id,
                parent_channel_id=getattr(channel, "parent_id", None),
                channel_name=getattr(channel, "name", None),
                owner_id=getattr(channel, "owner_id", None),
                bot_user_id=user.id,
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

    async def run_local_from_component(
        interaction,
        capability: str,
        params: Mapping[str, str] | None = None,
        filename: str = "result.md",
    ) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            result = await asyncio.to_thread(runner.execute, capability, params or {})
            await send_text(interaction, result.output, filename)
        except CapabilityError as error:
            await interaction.followup.send(
                "Permintaan belum dapat diproses. " + str(error), ephemeral=True
            )

    class ProcessSelect(discord.ui.Select):
        def __init__(self, mode: str) -> None:
            self.mode = mode
            action = {
                "reconcile_main_flow": "Pilih proses untuk memperbaiki alur utama",
                "reconcile_business_cases": "Pilih proses untuk memperbaiki detail proses",
                "show": "Pilih proses yang ingin dilihat",
                "main_flow": "Pilih proses untuk diperiksa alurnya",
                "business_cases": "Pilih proses untuk diperiksa detail kasusnya",
                "document_health": "Pilih proses untuk melihat kesehatan dokumennya",
            }[mode]
            options = [
                discord.SelectOption(label=title[:100], value=code, description=code)
                for code, title in e2e_options
            ]
            super().__init__(
                placeholder=action,
                min_values=1,
                max_values=1,
                options=options,
                custom_id=f"neurovi:process:{mode}",
            )

        async def callback(self, interaction) -> None:
            view = self.view
            if not isinstance(view, ProcessSelectView):
                return
            code = self.values[0]
            if self.mode in {"reconcile_main_flow", "reconcile_business_cases"}:
                if not await ensure_reconcile_access(interaction):
                    return
                title, description = processing_state_text("start")
                await interaction.response.edit_message(
                    content=f"**{title}**\n{description}", view=None
                )
                try:
                    capability = (
                        "reconcile.main-flow.start"
                        if self.mode == "reconcile_main_flow"
                        else "reconcile.business-cases.start"
                    )
                    response = await invoke_agent(
                        interaction, capability, {"e2e": code}
                    )
                    await update_reconciliation_message(
                        interaction, response, interaction.user.id, edit=False
                    )
                except AgentGatewayError as error:
                    await interaction.edit_original_response(
                        content=(
                            "Pemeriksaan belum dapat dimulai. "
                            + plain_language_gateway_error(error)
                        ),
                        view=ProcessSelectView(self.mode, interaction.user.id),
                    )
                return
            await interaction.response.edit_message(
                content="**Sedang menyiapkan hasil...**\nMohon tunggu.", view=None
            )
            if self.mode == "show":
                output = guided_process_summary(settings.repo_root, code)
                await send_text(interaction, output, "alur-proses.md")
                return
            capability, filename = {
                "main_flow": ("gap.main-flow", "pemeriksaan-alur-utama.md"),
                "business_cases": (
                    "gap.business-cases-e2e",
                    "pemeriksaan-detail-kasus.md",
                ),
                "document_health": (
                    "health.documents-flow",
                    "kesehatan-dokumen-flow.md",
                ),
            }[self.mode]
            try:
                result = await asyncio.to_thread(
                    runner.execute, capability, {"e2e": code}
                )
                await send_text(interaction, result.output, filename)
            except CapabilityError as error:
                await interaction.followup.send(
                    "Pemeriksaan belum dapat diselesaikan. " + str(error),
                    ephemeral=True,
                )

    class ProcessSelectView(discord.ui.View):
        def __init__(self, mode: str, owner_id: int) -> None:
            super().__init__(timeout=900)
            self.owner_id = owner_id
            if e2e_options:
                self.add_item(ProcessSelect(mode))

        async def interaction_check(self, interaction) -> bool:
            if interaction.user.id == self.owner_id:
                return True
            await interaction.response.send_message(
                "Menu ini sedang digunakan oleh pengguna lain. Jalankan `/mulai` "
                "untuk membuka menu Anda sendiri.",
                ephemeral=True,
            )
            return False

    class SearchPrdModal(discord.ui.Modal, title="Cari dokumen"):
        query = discord.ui.TextInput(
            label="Nama atau kata yang Anda ingat",
            placeholder="Contoh: pendaftaran rawat jalan",
            max_length=200,
        )

        async def on_submit(self, interaction) -> None:
            await run_local_from_component(
                interaction,
                "prd.list",
                {"query": str(self.query), "limit": "20"},
                "hasil-pencarian-dokumen.md",
            )

    class StartMenuView(discord.ui.View):
        def __init__(self, owner_id: int) -> None:
            super().__init__(timeout=900)
            self.owner_id = owner_id

        async def interaction_check(self, interaction) -> bool:
            if interaction.user.id == self.owner_id:
                return True
            await interaction.response.send_message(
                "Menu ini sedang digunakan oleh pengguna lain. Jalankan `/mulai` "
                "untuk membuka menu Anda sendiri.",
                ephemeral=True,
            )
            return False

        @discord.ui.button(
            label="Perbaiki alur utama",
            emoji="🧭",
            style=discord.ButtonStyle.success,
        )
        async def reconcile_main_flow(self, interaction, button) -> None:
            del button
            if not e2e_options:
                await interaction.response.send_message(
                    "Daftar proses belum tersedia. Hubungi administrator.", ephemeral=True
                )
                return
            await interaction.response.send_message(
                "Pilih proses. Bot hanya akan membahas urutan utama, perpindahan "
                "antarbagian, hasil, status, dan kelanjutan proses.",
                view=ProcessSelectView("reconcile_main_flow", interaction.user.id),
                ephemeral=True,
            )

        @discord.ui.button(
            label="Perbaiki detail proses",
            emoji="🔎",
            style=discord.ButtonStyle.success,
        )
        async def reconcile_business_cases(self, interaction, button) -> None:
            del button
            if not e2e_options:
                await interaction.response.send_message(
                    "Daftar proses belum tersedia. Hubungi administrator.", ephemeral=True
                )
                return
            await interaction.response.send_message(
                "Pilih proses. Bot hanya akan membahas skenario, kondisi, aturan, "
                "validasi, error, pengecualian, dan kriteria penerimaan.",
                view=ProcessSelectView("reconcile_business_cases", interaction.user.id),
                ephemeral=True,
            )

        async def continue_mode(self, interaction, reconciliation_mode: str) -> None:
            session_id = latest_reconciliation_session_for_user(
                settings.repo_root, interaction.user.id, reconciliation_mode
            )
            if not session_id:
                label = (
                    "alur utama"
                    if reconciliation_mode == "MAIN_FLOW"
                    else "detail proses"
                )
                await interaction.response.send_message(
                    f"Belum ada sesi {label} yang aktif.", ephemeral=True
                )
                return
            if not await ensure_reconcile_access(interaction):
                return
            title, description = processing_state_text("continue")
            await interaction.response.edit_message(
                content=f"**{title}**\n{description}", view=None
            )
            try:
                session = load_reconciliation_session(
                    settings.repo_root, session_id
                )
                capability, parameters = reconciliation_resume_request(
                    session, reconciliation_mode
                )
                if capability == "reconcile.status" and not parameters:
                    parameters = {"session_id": session_id}
                response = await invoke_agent(
                    interaction, capability, parameters
                )
                await update_reconciliation_message(
                    interaction, response, interaction.user.id, edit=False
                )
            except AgentGatewayError as error:
                await interaction.edit_original_response(
                    content=(
                        "Sesi belum dapat dibuka. "
                        + plain_language_gateway_error(error)
                    ),
                    view=StartMenuView(interaction.user.id),
                )

        @discord.ui.button(
            label="Lanjut alur utama",
            emoji="↩️",
            style=discord.ButtonStyle.primary,
        )
        async def continue_main_flow(self, interaction, button) -> None:
            del button
            await self.continue_mode(interaction, "MAIN_FLOW")

        @discord.ui.button(
            label="Lanjut detail proses",
            emoji="↩️",
            style=discord.ButtonStyle.primary,
        )
        async def continue_business_cases(self, interaction, button) -> None:
            del button
            await self.continue_mode(interaction, "BUSINESS_CASES")

        @discord.ui.button(
            label="Lihat alur proses",
            emoji="🗺️",
            style=discord.ButtonStyle.primary,
        )
        async def show_process(self, interaction, button) -> None:
            del button
            await interaction.response.send_message(
                "Pilih proses yang ingin dilihat.",
                view=ProcessSelectView("show", interaction.user.id),
                ephemeral=True,
            )

        @discord.ui.button(
            label="Cari dokumen",
            emoji="🔎",
            style=discord.ButtonStyle.secondary,
        )
        async def search_document(self, interaction, button) -> None:
            del button
            await interaction.response.send_modal(SearchPrdModal())

        @discord.ui.button(
            label="Periksa alur utama",
            emoji="🧭",
            style=discord.ButtonStyle.secondary,
        )
        async def scan_main_flow(self, interaction, button) -> None:
            del button
            await interaction.response.send_message(
                "Pilih proses. Bot akan memeriksa apakah alur dari awal sampai akhir "
                "tersambung tanpa mengubah dokumen.",
                view=ProcessSelectView("main_flow", interaction.user.id),
                ephemeral=True,
            )

        @discord.ui.button(
            label="Periksa detail kasus",
            emoji="🔍",
            style=discord.ButtonStyle.secondary,
        )
        async def scan_business_cases(self, interaction, button) -> None:
            del button
            await interaction.response.send_message(
                "Pilih proses. Bot akan memeriksa skenario, aturan, validasi, dan "
                "pengecualian pada PRD di dalam proses tersebut.",
                view=ProcessSelectView("business_cases", interaction.user.id),
                ephemeral=True,
            )

        @discord.ui.button(
            label="Kesehatan per flow",
            emoji="📊",
            style=discord.ButtonStyle.secondary,
        )
        async def document_health_flow(self, interaction, button) -> None:
            del button
            await interaction.response.send_message(
                "Pilih proses. Bot akan menampilkan statistik kelengkapan alur dan "
                "detail proses tanpa mengubah dokumen.",
                view=ProcessSelectView("document_health", interaction.user.id),
                ephemeral=True,
            )

        @discord.ui.button(
            label="Kesehatan keseluruhan",
            emoji="📈",
            style=discord.ButtonStyle.secondary,
        )
        async def document_health_all(self, interaction, button) -> None:
            del button
            await run_local_from_component(
                interaction,
                "health.documents-all",
                filename="kesehatan-dokumen-keseluruhan.md",
            )

    operator_permissions = discord.Permissions(manage_guild=True)
    prd = app_commands.Group(
        name="prd",
        description="Original PRD commands",
        default_permissions=operator_permissions,
    )
    e2e = app_commands.Group(
        name="e2e",
        description="E2E inventory commands",
        default_permissions=operator_permissions,
    )
    gap = app_commands.Group(
        name="gap",
        description="Gap scanner commands",
        default_permissions=operator_permissions,
    )
    document_health = app_commands.Group(
        name="document-health",
        description="Document health statistics",
        default_permissions=operator_permissions,
    )
    inventory = app_commands.Group(
        name="inventory",
        description="Document inventory commands",
        default_permissions=operator_permissions,
    )
    version = app_commands.Group(
        name="version",
        description="Global version commands",
        default_permissions=operator_permissions,
    )
    repo = app_commands.Group(
        name="repo",
        description="Repository commands",
        default_permissions=operator_permissions,
    )
    reconcile = app_commands.Group(
        name="reconcile",
        description="Controlled reconciliation commands",
        default_permissions=operator_permissions,
    )

    @bot.tree.command(name="mulai", description="Buka menu utama Neurovi")
    async def start_menu(interaction):
        embed = discord.Embed(
            title="Apa yang ingin Anda lakukan?",
            description=(
                "Pilih tombol berikut. Bot akan meminta pilihan berikutnya satu per "
                "satu; Anda tidak perlu mengingat kode proses, kode dokumen, atau ID sesi."
            ),
            color=discord.Color.teal(),
        )
        embed.add_field(
            name="Untuk peninjauan dokumen",
            value=(
                "Pilih **Perbaiki alur utama**, **Perbaiki detail proses**, "
                "atau **Lanjutkan sesi**."
            ),
            inline=False,
        )
        embed.add_field(
            name="Hanya ingin melihat informasi",
            value=(
                "Pilih **Lihat alur proses**, **Cari dokumen**, **Periksa alur utama**, "
                "**Periksa detail kasus**, atau **Kesehatan dokumen**."
            ),
            inline=False,
        )
        await interaction.response.send_message(
            embed=embed,
            view=StartMenuView(interaction.user.id),
            ephemeral=settings.discord_ephemeral,
        )

    @bot.tree.command(name="help", description="Show command usage help")
    async def slash_help(interaction, topic: str | None = None):
        await interaction.response.send_message(
            answer_help(topic), ephemeral=settings.discord_ephemeral
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

    @e2e.command(name="show", description="Display one E2E domain worklist")
    async def e2e_show(interaction, e2e_code_or_name: str):
        await run_local(
            interaction,
            "e2e.show",
            {"e2e": e2e_code_or_name},
            "e2e-detail.md",
        )

    @gap.command(name="alur", description="Periksa kesinambungan alur utama")
    @app_commands.describe(
        e2e_code_or_name="Ketik nama proses, lalu pilih dari daftar"
    )
    async def gap_main_flow(interaction, e2e_code_or_name: str):
        await run_local(
            interaction,
            "gap.main-flow",
            {"e2e": e2e_code_or_name},
            "pemeriksaan-alur-utama.md",
        )

    @gap_main_flow.autocomplete("e2e_code_or_name")
    async def gap_main_flow_autocomplete(interaction, current: str):
        del interaction
        return [
            app_commands.Choice(name=f"{title} ({code})"[:100], value=code)
            for code, title in match_e2e_options(e2e_options, current)
        ]

    @gap.command(name="kasus", description="Periksa detail kasus bisnis")
    @app_commands.describe(
        e2e_code_or_name="Ketik nama proses, lalu pilih dari daftar"
    )
    async def gap_business_cases(interaction, e2e_code_or_name: str):
        await run_local(
            interaction,
            "gap.business-cases-e2e",
            {"e2e": e2e_code_or_name},
            "pemeriksaan-detail-kasus.md",
        )

    @gap_business_cases.autocomplete("e2e_code_or_name")
    async def gap_business_cases_autocomplete(interaction, current: str):
        del interaction
        return [
            app_commands.Choice(name=f"{title} ({code})"[:100], value=code)
            for code, title in match_e2e_options(e2e_options, current)
        ]

    @document_health.command(
        name="flow", description="Tampilkan kesehatan dokumen per flow bisnis"
    )
    @app_commands.describe(
        e2e_code_or_name="Opsional: pilih satu flow atau kosongkan untuk semua flow"
    )
    async def document_health_flow(
        interaction, e2e_code_or_name: str | None = None
    ):
        params = {"e2e": e2e_code_or_name} if e2e_code_or_name else {}
        await run_local(
            interaction,
            "health.documents-flow",
            params,
            "kesehatan-dokumen-per-flow.md",
        )

    @document_health_flow.autocomplete("e2e_code_or_name")
    async def document_health_flow_autocomplete(interaction, current: str):
        del interaction
        return [
            app_commands.Choice(name=f"{title} ({code})"[:100], value=code)
            for code, title in match_e2e_options(e2e_options, current)
        ]

    @document_health.command(
        name="all", description="Tampilkan kesehatan seluruh dokumen"
    )
    async def document_health_all(interaction):
        await run_local(
            interaction,
            "health.documents-all",
            filename="kesehatan-dokumen-keseluruhan.md",
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

    @reconcile.command(name="alur", description="Perbaiki gap alur utama")
    @app_commands.describe(
        e2e_code_or_name="Ketik nama proses, lalu pilih dari daftar"
    )
    async def reconcile_main_flow(interaction, e2e_code_or_name: str):
        await run_agent(
            interaction, "reconcile.main-flow.start", {"e2e": e2e_code_or_name}
        )

    @reconcile_main_flow.autocomplete("e2e_code_or_name")
    async def reconcile_main_flow_autocomplete(interaction, current: str):
        del interaction
        return [
            app_commands.Choice(name=f"{title} ({code})"[:100], value=code)
            for code, title in match_e2e_options(e2e_options, current)
        ]

    @reconcile.command(name="detail", description="Perbaiki gap detail proses")
    @app_commands.describe(
        e2e_code_or_name="Ketik nama proses, lalu pilih dari daftar"
    )
    async def reconcile_business_cases(interaction, e2e_code_or_name: str):
        await run_agent(
            interaction, "reconcile.business-cases.start", {"e2e": e2e_code_or_name}
        )

    @reconcile_business_cases.autocomplete("e2e_code_or_name")
    async def reconcile_business_cases_autocomplete(interaction, current: str):
        del interaction
        return [
            app_commands.Choice(name=f"{title} ({code})"[:100], value=code)
            for code, title in match_e2e_options(e2e_options, current)
        ]

    for group in (
        prd,
        e2e,
        gap,
        document_health,
        inventory,
        version,
        repo,
        reconcile,
    ):
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
