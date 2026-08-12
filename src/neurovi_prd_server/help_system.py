from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Mapping


HELP_SESSION_THREAD_PREFIX = "neurovi-help-"

COMMAND_GUIDANCE = {
    "/help": "opsional isi `topic` dengan prd, e2e, gap, inventory, version, repo, atau reconcile",
    "/prd list": "isi `query` dengan kata yang Anda ingat; `limit` boleh dibiarkan default",
    "/prd show": "isi `document` dengan DOC-ID atau nama dokumen; `section` hanya jika ingin bagian tertentu",
    "/e2e list": "isi `query` dengan nama proses; filter lain boleh dikosongkan",
    "/e2e show": "isi `e2e_code_or_name` dengan kode atau nama proses",
    "/gap list": "tidak memerlukan parameter",
    "/gap e2e": "isi `e2e_code_or_name` dengan kode atau nama proses",
    "/gap prd": "isi `document` dengan DOC-ID atau nama dokumen",
    "/inventory find-prd": "isi `query` dengan kode, judul, atau kata kunci dokumen",
    "/inventory scan-format": "isi `document` dengan DOC-ID dokumen",
    "/version list": "tidak memerlukan parameter",
    "/version compare": "isi `from_version` dan `to_version` dengan dua versi yang ingin dibandingkan",
    "/repo health": "tidak memerlukan parameter",
    "/repo validate": "tidak memerlukan parameter",
    "/repo commands": "tidak memerlukan parameter",
    "/reconcile start": "ketik sebagian nama proses pada `e2e_code_or_name`, lalu pilih hasil yang muncul",
    "/reconcile continue": "tidak memerlukan parameter; membuka sesi aktif terakhir milik Anda",
    "/reconcile answer": "fallback admin: isi `session_id` dan jawaban bebas pada `answer`",
    "/reconcile control": "fallback admin: isi `session_id`, lalu pilih SKIP, DEFER, atau UNKNOWN pada `action`",
    "/reconcile add-reference": "fallback admin: isi `session_id` dan lokasi referensi pada `reference`",
    "/reconcile decide": "fallback admin: isi `session_id` dan keputusan pada `decision`",
    "/reconcile status": "fallback admin: isi `session_id`",
    "/finish": "isi `session_id`, pilih `approval` BASELINE_APPROVAL, dan pilih `bump`; publikasi saat ini dapat ditolak sebagai belum tersedia",
}
KNOWN_SLASH_COMMANDS = frozenset(COMMAND_GUIDANCE)

CONTEXTUAL_HELP_SYSTEM_PROMPT = """You are the read-only help advisor for the
Neurovi PRD Discord bot. Answer in simple Indonesian for nontechnical hospital
staff. Return exactly one JSON object using the response contract below.

Safety and behavior:
- A normal chat message is only a question. Never claim that you ran a command,
  changed a document, resolved a gap, started a session, committed, or pushed.
- Recommend only slash commands from the catalog below. Never invent a command.
- First explain what the user can do now, then give the exact command and the
  minimum parameter they need to fill.
- If the requested result is not supported by the catalog, explicitly say that
  the bot cannot do it yet and that a developer enhancement is required. Do not
  pretend to resolve it. Give the closest practical workaround using only the
  available commands.
- If the request is ambiguous, help the user start with a safe discovery command
  instead of asking for technical IDs they are unlikely to know.
- Keep the answer under 1,500 characters and use short paragraphs or bullets.
- Put slash commands only in the `commands` array, never inside prose fields.
- The runtime supplies parameter instructions from its trusted catalog. Do not
  invent or return parameter names or command syntax.

Available command catalog:
- /prd list, /prd show: find or read immutable original PRDs.
- /e2e list, /e2e show: find or inspect E2E process inventory and source flows.
- /gap list, /gap e2e, /gap prd: scan diagnostic context gaps without changing documents.
- /inventory find-prd, /inventory scan-format: search coverage or inspect PRD heading format.
- /version list, /version compare: inspect global repository versions.
- /repo health, /repo validate, /repo commands: inspect service/repository health and capabilities.
- /reconcile start, /reconcile continue: start or resume the guided controlled review.
- /reconcile answer, /reconcile control, /reconcile add-reference,
  /reconcile decide, /reconcile status: administrative reconciliation fallbacks.
- /finish: request approved global publication; current runtime may report that
  publication is not implemented rather than commit or push.
- /help: show this command guidance.

Response contract:
{
  "summary": "one short sentence showing you understand the user's need",
  "next_step": "what the user can safely do now, without slash commands",
  "commands": ["one exact command from the catalog"],
  "requires_developer": false,
  "limitation": "required when requires_developer is true",
  "workaround": "nearest practical workaround, without slash commands"
}
"""


@dataclass(frozen=True)
class HelpTopic:
    key: str
    keywords: tuple[str, ...]
    content: str


OVERVIEW = """# Bantuan Neurovi PRD

Tulis pertanyaan atau kebutuhan Anda dengan bahasa sehari-hari di channel.
Bot membuat thread bantuan secara otomatis, lalu mengarahkan Anda ke slash
command yang tepat. Pesan biasa hanya meminta panduan: bot tidak menjalankan
command dan tidak mengubah dokumen dari chat tersebut. Direct message dilayani
tanpa membuat thread.

Command utama:
- /prd list, /prd show - mencari dan menampilkan PRD original.
- /e2e list, /e2e show - melihat inventaris dan detail E2E.
- /gap list, /gap e2e, /gap prd - memindai gap konteks.
- /inventory find-prd, /inventory scan-format - mencari dokumen dan format.
- /version list, /version compare - melihat versi global repository.
- /repo health, /repo validate, /repo commands - status dan validasi.
- /reconcile ... - rekonsiliasi terkontrol melalui agent gateway.
- /finish - menutup sesi dan menerbitkan versi global yang disetujui.

Jika belum tahu harus mulai dari mana, jelaskan tujuan Anda, misalnya:
"Saya ingin melihat dokumen pendaftaran rawat jalan" atau
"Saya ingin memeriksa bagian proses yang belum jelas".

Gunakan /help topic:<prd|e2e|gap|inventory|version|repo|reconcile> untuk
melihat satu kelompok command."""


GETTING_STARTED = """# Mulai dari sini

Tidak perlu mengetahui kode dokumen atau kode E2E terlebih dahulu.

1. Jika ingin mencari dokumen, jalankan `/prd list` dan isi `query` dengan nama
   atau kata yang Anda ingat.
2. Jika ingin mencari proses, jalankan `/e2e list` dan isi `query` dengan nama
   proses.
3. Jika ingin mulai peninjauan terpandu, jalankan `/reconcile start`, ketik
   sebagian nama proses, lalu pilih hasil yang muncul.
4. Jika sebelumnya sudah mulai, jalankan `/reconcile continue`.

Pesan chat ini tidak menjalankan langkah tersebut. Pilih command di atas agar
bot dapat membaca atau memproses permintaan Anda secara aman."""


TOPICS = (
    HelpTopic(
        "prd",
        ("prd", "dokumen", "original", "asli", "section", "bagian"),
        """# Bantuan PRD

- /prd list [query] [limit]
  Menampilkan daftar dokumen original. Contoh query: pendaftaran rawat jalan.
- /prd show document:<DOC-ID atau nama> [section]
  Menampilkan konten original tanpa rekonsiliasi atau improvisasi.

Contoh:
/prd show document:DOC-4287D4C5CFF2D2E0 section:3. In Scope

Jika nama ambigu, bot mengembalikan pilihan DOC-ID dan tidak memilih otomatis.""",
    ),
    HelpTopic(
        "e2e",
        ("e2e", "alur", "flow", "proses", "domain", "node", "edge"),
        """# Bantuan E2E

- /e2e list [query] [group] [status] [limit]
  Menampilkan inventaris E2E dan status kandidatnya.
- /e2e show e2e_code_or_name:<kode atau nama>
  Menampilkan node, edge, source flow, dan membership eksplisit.

Contoh:
/e2e show e2e_code_or_name:E2E-ADM-01

Kandidat mekanis tetap dipisahkan dari membership yang sudah eksplisit.""",
    ),
    HelpTopic(
        "gap",
        ("gap", "scan", "scanner", "defect", "missing", "kurang", "konteks"),
        """# Bantuan Gap Scanner

- /gap list
  Menampilkan E2E yang masih memiliki gap candidate.
- /gap e2e e2e_code_or_name:<kode atau nama>
  Memindai gap lintas dokumen pada satu E2E.
- /gap prd document:<DOC-ID atau nama>
  Memindai gap internal dan struktur satu PRD.

Hasil scan adalah kandidat review, bukan keputusan atau perubahan dokumen.""",
    ),
    HelpTopic(
        "inventory",
        ("inventory", "inventaris", "cari", "find", "format", "coverage"),
        """# Bantuan Inventory

- /inventory find-prd query:<kode, judul, atau kata kunci>
  Mencari dokumen beserta status coverage E2E.
- /inventory scan-format document:<DOC-ID>
  Memeriksa keluarga heading tanpa mengubah source.

Gunakan /prd show setelah menemukan DOC-ID yang tepat.""",
    ),
    HelpTopic(
        "version",
        ("version", "versi", "tag", "diff", "compare", "perubahan"),
        """# Bantuan Versioning

- /version list
  Menampilkan tag versi global repository.
- /version compare from_version:<vX.Y.Z> to_version:<vX.Y.Z>
  Menampilkan dokumen yang berubah antarversi.

Versi berlaku untuk repository secara global, bukan per PRD atau per E2E.""",
    ),
    HelpTopic(
        "repo",
        ("repo", "repository", "health", "validate", "validasi", "command"),
        """# Bantuan Repository

- /repo health - memastikan repository dapat dibaca.
- /repo validate - memverifikasi source original terhadap manifest.
- /repo commands - menampilkan capability yang terpasang.
- /help [topic] - menampilkan petunjuk penggunaan.

Validasi tidak mengubah source/original/.""",
    ),
    HelpTopic(
        "reconcile",
        (
            "reconcile",
            "rekonsiliasi",
            "interview",
            "decision",
            "skip",
            "defer",
            "unknown",
            "baseline",
        ),
        """# Bantuan Rekonsiliasi

Untuk user operasional:

- Jalankan /reconcile start, ketik sebagian nama proses, lalu pilih dari daftar.
- Ikuti kartu panduan dan gunakan tombol yang tersedia.
- Gunakan /reconcile continue untuk membuka kembali sesi terakhir Anda.

Tidak perlu mengingat session ID atau kode keputusan.

Fallback administrator:

- /reconcile answer session_id:<ID> answer:<jawaban>
- /reconcile control session_id:<ID> action:<SKIP|DEFER|UNKNOWN>
- /reconcile add-reference session_id:<ID> reference:<path atau referensi>
- /reconcile decide session_id:<ID> decision:<keputusan>
- /reconcile status session_id:<ID>
- /finish session_id:<ID> approval:BASELINE_APPROVAL bump:<patch|minor|major>

Command ini memerlukan agent gateway dan role yang diizinkan. Runtime interview
saat ini menyediakan daftar proses, tombol pilihan, dan formulir jawaban. User
tidak perlu menyalin session ID atau mengetik kode keputusan; command answer,
control, dan decide tetap tersedia sebagai fallback administrator. `/finish`
saat ini ditahan dengan status NOT_ATTEMPTED dan tidak membuat commit
atau push. Publisher final nantinya harus memvalidasi perubahan, menentukan
versi berikutnya, membuat commit dan annotated tag, lalu melakukan atomic push.
Jika masih ada konten belum disetujui, validasi gagal, working tree tidak aman,
atau push gagal, proses harus ditolak tanpa menandai sesi selesai.""",
    ),
)


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.findall(r"[a-z0-9]+", value))


def answer_help(query: str | None = None) -> str:
    if not query or not query.strip():
        return OVERVIEW
    normalized = normalize(query)
    if any(
        phrase in normalized
        for phrase in (
            "mulai dari mana",
            "harus mulai",
            "cara mulai",
            "saya bingung",
            "tidak tahu mulai",
            "belum tahu",
        )
    ):
        return GETTING_STARTED
    for topic in TOPICS:
        if normalized == topic.key:
            return topic.content
    scored = []
    for topic in TOPICS:
        score = sum(1 for keyword in topic.keywords if normalize(keyword) in normalized)
        if score:
            scored.append((score, topic.key, topic.content))
    if scored:
        scored.sort(key=lambda item: (-item[0], item[1]))
        return scored[0][2]
    return (
        "Saya memahami ini sebagai permintaan bantuan, tetapi belum ada command "
        "yang dapat saya pastikan cocok. Pesan chat tidak akan menjalankan atau "
        "mengubah apa pun.\n\nGunakan `/help` untuk melihat kemampuan yang tersedia, "
        "atau jelaskan objek dan tujuan Anda, misalnya: \"cari PRD pendaftaran\", "
        "\"lihat alur rawat jalan\", atau \"periksa gap proses\". Jika kebutuhan "
        "Anda tidak memiliki command, bot akan menjelaskan workaround yang tersedia "
        "dan menyarankan enhancement kepada developer."
    )


def _plain_help_field(value: Any, *, required: bool = False) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    shell_command = re.search(
        r"(?:^|[\s:])(?:bash|chmod|chown|cp|curl|docker|git|make|mv|npm|pip|"
        r"python|rm|sh|sudo|systemctl|wget)(?=\s+(?:--?\w|[^,.!?]+(?:\s|$)))",
        cleaned,
        flags=re.IGNORECASE,
    )
    forbidden = re.search(r"[`@&|$<>]", cleaned) or shell_command
    if (required and not cleaned) or len(cleaned) > 700 or "/" in cleaned or forbidden:
        return None
    return cleaned


def _normalize_model_command(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip().casefold()
    if isinstance(value, Mapping):
        command = value.get("command")
        if isinstance(command, str):
            return command.strip().casefold()
    return None


def render_contextual_help(value: Mapping[str, Any]) -> str | None:
    summary = _plain_help_field(value.get("summary"), required=True)
    next_step = _plain_help_field(value.get("next_step"), required=True)
    workaround = _plain_help_field(value.get("workaround"))
    limitation = _plain_help_field(value.get("limitation"))
    requires_developer = value.get("requires_developer")
    commands = value.get("commands")
    if summary is None or next_step is None or not isinstance(commands, list):
        return None
    if not isinstance(requires_developer, bool) or len(commands) > 3:
        return None

    command_lines = []
    for item in commands:
        command = _normalize_model_command(item)
        if command not in KNOWN_SLASH_COMMANDS:
            return None
        command_lines.append(f"- `{command}` — {COMMAND_GUIDANCE[command]}")

    sections = [summary, f"**Yang dapat dilakukan sekarang**\n{next_step}"]
    if command_lines:
        sections.append("**Gunakan command**\n" + "\n".join(command_lines))
    if requires_developer:
        if not limitation or not workaround:
            return None
        sections.append(
            "**Batas kemampuan saat ini**\n"
            + limitation
            + " Kebutuhan ini memerlukan enhancement oleh developer; bot tidak "
            "akan berpura-pura sudah menyelesaikannya."
        )
        sections.append(f"**Workaround**\n{workaround}")
    elif workaround:
        sections.append(f"**Langkah alternatif**\n{workaround}")
    sections.append(
        "Pesan bantuan ini hanya memberi panduan. Belum ada command yang "
        "dijalankan dan tidak ada dokumen yang diubah."
    )
    rendered = "\n\n".join(sections)
    return rendered if len(rendered) <= 1900 else None


def is_plain_help_request(content: str) -> bool:
    cleaned = content.strip()
    if not cleaned:
        return False
    # Prefix commands are not part of the natural-language help path.
    return not cleaned.startswith("!")


def strip_bot_mention(content: str, bot_user_id: int) -> str:
    pattern = rf"<@!?{bot_user_id}>"
    return re.sub(pattern, "", content).strip()


def build_help_thread_name(author_name: str, message_id: int) -> str:
    author_slug = normalize(author_name).replace(" ", "-") or "user"
    suffix = str(message_id)[-8:]
    return f"{HELP_SESSION_THREAD_PREFIX}{author_slug}-{suffix}"[:100]


def is_help_session_thread(
    *, channel_name: str | None, owner_id: int | None, bot_user_id: int
) -> bool:
    return bool(
        channel_name
        and channel_name.startswith(HELP_SESSION_THREAD_PREFIX)
        and owner_id == bot_user_id
    )


def is_help_context(
    *,
    is_direct_message: bool,
    bot_mentioned: bool,
    is_session_thread: bool,
    is_guild_channel: bool = False,
    is_thread: bool = False,
) -> bool:
    if is_thread and not is_session_thread:
        return False
    return is_direct_message or bot_mentioned or is_session_thread or is_guild_channel
