# Neurovi Document Reconciliator

Repository tools untuk inventarisasi, scanning gap, rekonsiliasi PRD terkontrol,
versioning global dokumen, serta adapter Discord. Source truth dokumen berada di
repository `neurovi-prd`, yang dipasang sebagai Git submodule pada
`./neurovi-prd`.

## Struktur

- `.codex/skills/`: skill rekonsiliasi, scanner, dan penampil dokumen.
- `scripts/`: generator dan validator deterministik repository dokumen.
- `src/`: package command service dan Discord adapter.
- `tests/`: test capability, help, dan konfigurasi.
- `neurovi-prd/`: submodule repository dokumen PRD.

## Setup

```bash
git clone --recurse-submodules <tools-repository-url>
python3 -m venv .venv
.venv/bin/pip install ".[discord]"
.venv/bin/neurovi-doc-reconciliator health --deep
```

Validasi source document repository:

```bash
python3 scripts/build_structure.py validate \
  --source neurovi-prd/source/original \
  --target neurovi-prd
```

Deployment menjalankan `discord-bot` read-only dan `reconciliation-agent`
writable sebagai dua container terpisah. Agent membaca konfigurasi 9router
langsung dari `NEUROVI_LLM_*`; Discord hanya menerima URL dan shared gateway
token. Setup lengkap dijelaskan di `docs/server-deployment.md`.

Di Discord, rekonsiliasi menggunakan alur terpandu: user memilih nama proses
dari autocomplete, lalu menjawab melalui tombol atau formulir singkat. Session
ID dan kode keputusan internal tetap tersedia untuk audit tetapi tidak perlu
diketik oleh user operasional.

Pertanyaan biasa di channel yang diizinkan otomatis dibuatkan thread bantuan
tanpa perlu tag bot. Pesan, mention, DM, dan slash command di luar channel yang
diizinkan tidak diproses; hanya thread bantuan yang dibuat bot dari channel
tersebut yang tetap menerima pesan lanjutan.
Jawaban mengarahkan user ke slash command yang tersedia dan tidak pernah
menjalankan tool atau mengubah dokumen dari chat biasa. Jika kebutuhannya belum
didukung, bot menyebutkan perlunya enhancement developer serta memberi
workaround dengan command yang ada.
