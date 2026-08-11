from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


HELP_SESSION_THREAD_PREFIX = "neurovi-help-"


@dataclass(frozen=True)
class HelpTopic:
    key: str
    keywords: tuple[str, ...]
    content: str


OVERVIEW = """# Neurovi PRD Bot Help

Di server Discord, tag bot untuk memulai sesi bantuan baru. Bot membuat thread
secara otomatis dan memperlakukan pesan lanjutan di thread itu sebagai
pertanyaan bantuan, bukan perintah untuk membaca atau mengubah repository.
Direct message dilayani tanpa membuat thread.

Command utama:
- /prd list, /prd show - mencari dan menampilkan PRD original.
- /e2e list, /e2e show - melihat inventaris dan detail E2E.
- /gap list, /gap e2e, /gap prd - memindai gap konteks.
- /inventory find-prd, /inventory scan-format - mencari dokumen dan format.
- /version list, /version compare - melihat versi global repository.
- /repo health, /repo validate, /repo commands - status dan validasi.
- /reconcile ... - rekonsiliasi terkontrol melalui agent gateway.
- /finish - menutup sesi dan menerbitkan versi global yang disetujui.

Gunakan /help topic:<prd|e2e|gap|inventory|version|repo|reconcile>.
Anda juga dapat bertanya: "bagaimana melihat PRD original?" atau
"command apa untuk scan gap E2E?"."""


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

- /reconcile start e2e_code_or_name:<E2E>
- /reconcile answer session_id:<ID> answer:<jawaban>
- /reconcile control session_id:<ID> action:<SKIP|DEFER|UNKNOWN>
- /reconcile add-reference session_id:<ID> reference:<path atau referensi>
- /reconcile decide session_id:<ID> decision:<keputusan>
- /reconcile status session_id:<ID>
- /finish session_id:<ID> approval:BASELINE_APPROVAL bump:<patch|minor|major>

Command ini memerlukan agent gateway dan role yang diizinkan. Runtime interview
saat ini menahan /finish dengan status NOT_ATTEMPTED dan tidak membuat commit
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
        "Saya memperlakukan pesan ini sebagai pertanyaan bantuan, tetapi topiknya "
        "belum dikenali.\n\n" + OVERVIEW
    )


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
) -> bool:
    return is_direct_message or bot_mentioned or is_session_thread
