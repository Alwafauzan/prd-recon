from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Mapping


HELP_SESSION_THREAD_PREFIX = "neurovi-help-"

COMMAND_GUIDANCE = {
    "/mulai": "tidak memerlukan isian; pilih kebutuhan Anda lewat tombol",
    "/help": "opsional isi `topic` dengan prd, e2e, gap, health, inventory, version, repo, atau reconcile",
    "/prd list": "isi `query` dengan kata yang Anda ingat; `limit` boleh dibiarkan default",
    "/prd show": "isi `document` dengan DOC-ID atau nama dokumen; `section` hanya jika ingin bagian tertentu",
    "/e2e list": "isi `query` dengan nama proses; filter lain boleh dikosongkan",
    "/e2e show": "isi `e2e_code_or_name` dengan kode atau nama proses",
    "/gap alur": "ketik sebagian nama proses pada `e2e_code_or_name`, lalu pilih hasil yang muncul",
    "/gap kasus": "ketik sebagian nama proses pada `e2e_code_or_name`, lalu pilih hasil yang muncul",
    "/document-health flow": "opsional pilih satu flow; kosongkan untuk tabel semua flow",
    "/document-health all": "tidak memerlukan parameter",
    "/inventory find-prd": "isi `query` dengan kode, judul, atau kata kunci dokumen",
    "/inventory scan-format": "isi `document` dengan DOC-ID dokumen",
    "/version list": "tidak memerlukan parameter",
    "/version compare": "isi `from_version` dan `to_version` dengan dua versi yang ingin dibandingkan",
    "/repo health": "tidak memerlukan parameter",
    "/repo validate": "tidak memerlukan parameter",
    "/repo commands": "tidak memerlukan parameter",
    "/reconcile alur": "ketik sebagian nama proses untuk memperbaiki gap alur utama",
    "/reconcile detail": "ketik sebagian nama proses untuk memperbaiki gap detail proses",
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
- /mulai: open the primary guided menu for nontechnical users.
- /prd list, /prd show: find or read immutable original PRDs.
- /e2e list, /e2e show: find or inspect E2E domain worklists and relationships.
- /gap alur: scan continuity of one E2E main business flow without changing documents.
- /gap kasus: scan detailed scenarios, rules, validation, and exceptions in one E2E.
- /document-health flow, /document-health all: show read-only document health statistics per flow or for the entire repository.
- /inventory find-prd, /inventory scan-format: search coverage or inspect PRD heading format.
- /version list, /version compare: inspect global repository versions.
- /repo health, /repo validate, /repo commands: inspect service/repository health and capabilities.
- /reconcile alur, /reconcile detail: start the selected guided reconciliation mode.
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

Untuk mulai, jalankan `/mulai`, lalu pilih tombol sesuai kebutuhan:

- **Perbaiki alur utama** untuk menutup gap urutan dan perpindahan proses.
- **Perbaiki detail proses** untuk menutup gap skenario, aturan, dan validasi.
- **Lanjut alur utama** atau **Lanjut detail proses** untuk membuka sesi aktif.
- **Lihat alur proses** atau **Cari dokumen** untuk kebutuhan baca saja.
- **Periksa alur utama** untuk mengecek kesinambungan proses dari awal sampai akhir.
- **Periksa detail kasus** untuk mengecek skenario, aturan, validasi, dan pengecualian.
- **Kesehatan per flow** atau **Kesehatan keseluruhan** untuk melihat statistik dokumen.

Saat pemeriksaan berlangsung, semua jawaban menggunakan tombol atau formulir.
Tombol **Akhiri sesi** selalu tersedia dan tidak menerbitkan, commit, atau push
dokumen.

Jika belum tahu harus mulai dari mana, jelaskan tujuan Anda, misalnya:
"Saya ingin melihat dokumen pendaftaran rawat jalan" atau
"Saya ingin memeriksa bagian proses yang belum jelas".

Gunakan /help topic:<prd|e2e|gap|health|inventory|version|repo|reconcile> untuk
melihat satu kelompok command."""


GETTING_STARTED = """# Mulai dari sini

Tidak perlu mengetahui kode dokumen atau kode E2E terlebih dahulu.

1. Jalankan `/mulai`.
2. Pilih kebutuhan Anda melalui tombol.
3. Jika diminta memilih proses, pilih namanya dari daftar.
4. Saat pemeriksaan berlangsung, jawab dengan tombol atau formulir singkat.
5. Pilih jenis rekonsiliasi yang sesuai; kedua jenis memiliki sesi terpisah.
6. Pilih **Akhiri sesi** kapan saja jika ingin berhenti. Jawaban tetap tersimpan
   dan pertanyaan yang belum selesai tetap terbuka.

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
  Menampilkan worklist domain E2E dan jumlah PRD uniknya.
- /e2e show e2e_code_or_name:<kode atau nama>
  Menampilkan urutan PRD, pemeriksaan flow, dan relasi lintas domain.

Contoh:
/e2e show e2e_code_or_name:E2E-RJ

Assignment dan relasi mekanis tetap dipisahkan dari keputusan pengguna.""",
    ),
    HelpTopic(
        "gap",
        ("gap", "scan", "scanner", "defect", "missing", "kurang", "konteks"),
        """# Bantuan Pemeriksaan PRD

Ada dua pemeriksaan yang terpisah:

- /gap alur e2e_code_or_name:<kode atau nama>
  Memeriksa pemicu, urutan proses, perpindahan antar-PRD, hasil, perubahan status,
  dan kelanjutan ke domain lain.
- /gap kasus e2e_code_or_name:<kode atau nama>
  Memeriksa skenario alternatif, kondisi, aturan bisnis, validasi, error,
  pengecualian, dan kriteria penerimaan pada PRD dalam proses tersebut.

Pilih **alur** jika ingin mengetahui apakah proses tersambung dari awal sampai
akhir. Pilih **kasus** jika alur sudah diketahui dan Anda ingin memeriksa detail
perilakunya. Kedua hasil hanya kandidat review dan tidak mengubah dokumen.""",
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
        "health",
        ("health", "kesehatan", "statistik", "kelengkapan", "coverage"),
        """# Bantuan Kesehatan Dokumen

- /document-health flow [e2e_code_or_name]
  Menampilkan statistik setiap flow. Pilih satu flow jika ingin melihat daftar
  PRD dan area yang perlu ditinjau.
- /document-health all
  Menampilkan ringkasan seluruh repository dan flow prioritas.

Angka menunjukkan konteks yang terdeteksi oleh scanner, bukan nilai mutu final
atau bukti bahwa isi PRD sudah benar. Command ini tidak mengubah dokumen.""",
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

- Jalankan `/mulai`, lalu pilih **Perbaiki alur utama** atau **Perbaiki detail proses**.
- Pilih nama proses dari daftar; tidak perlu mengetahui kode proses.
- Ikuti kartu panduan dan gunakan tombol atau formulir yang tersedia.
- Pilih **Akhiri sesi** kapan saja jika ingin berhenti.

Kedua proses tidak bercampur. Alur utama hanya membahas pemicu, urutan,
perpindahan, hasil, status, dan kelanjutan proses. Detail proses hanya membahas
skenario, kondisi, aturan, validasi, error, pengecualian, dan kriteria penerimaan.

Jawaban yang sudah diberikan tetap tersimpan. Pertanyaan yang belum selesai tidak
dianggap terjawab atau disetujui. Mengakhiri sesi tidak menerbitkan versi, tidak
membuat commit, dan tidak melakukan push. Publikasi baseline adalah proses
approver terpisah dan belum tersedia melalui command user Discord.""",
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
