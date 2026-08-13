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

## Lossless Canonical Bootstrap v0

Bootstrap every eligible original Markdown PRD into one generated format and a
stable `PRD-<DOMAIN>-<NNN>` code without changing the original payload:

```bash
python3 scripts/bootstrap_prd_baseline.py build --repo neurovi-prd
python3 scripts/bootstrap_prd_baseline.py validate --repo neurovi-prd
```

Generated files live under `neurovi-prd/reconciliation/canonical/` as canonical
bootstrap version `v0.0.0`. The `prds/` directory contains 209 source-preserving
canonical PRDs, while `e2e/` contains one worklist and relationship context for
each active domain. Version 0 is ready for reconciliation consumption but is not
an approved Git release or tag.

The reconciliation agent consumes these canonical files as its working PRD and
E2E representation. Before a session starts, it verifies the baseline against the active E2E
inventory and immutable original using document/content identity, provenance,
checksums, payload length, and complete byte-identical payload comparison. Any
mismatch blocks the session; the matched original remains the source-fact
authority. Formatting metadata never replaces, truncates, or rewrites original
content.

Relasi E2E yang dinyatakan eksplisit oleh PRD eligible, lolos verifikasi
canonical, dan tidak memiliki konflik ditutup otomatis sebagai
`RESOLVED_BY_SOURCE_FACT`. Relasi yang mengandung konflik atau pilihan makna
tetap `HUMAN_DECISION_REQUIRED`; agent wajib meminta keputusan user dan tidak
boleh memilih salah satu fakta sendiri. Penutupan otomatis hanya memperkaya
jejak konteks E2E dan tidak menerbitkan release, commit, tag, atau push.

Hasil scan penuh seluruh PRD tersimpan di
`neurovi-prd/reconciliation/canonical/automatic-reconciliation.json` dan
laporan manusianya di `automatic-reconciliation.md`. Register ini menutup
kandidat hanya dari kutipan literal aktif; asumsi, riwayat revisi, future phase,
penanda unresolved, bukti tidak cukup, dan konflik tetap terbuka atau dikecualikan.

Deployment menjalankan `discord-bot` read-only dan `reconciliation-agent`
writable sebagai dua container terpisah. Agent membaca konfigurasi 9router
langsung dari `NEUROVI_LLM_*`; Discord hanya menerima URL dan shared gateway
token. Setup lengkap dijelaskan di `docs/server-deployment.md`.

Di Discord, user operasional cukup menjalankan `/mulai`. Rekonsiliasi dibagi menjadi **Perbaiki alur utama** dan **Perbaiki detail proses**. Keduanya memiliki sesi, pertanyaan, audit, stop, dan resume terpisah sehingga gap urutan/handoff tidak bercampur dengan skenario, aturan, validasi, error, atau pengecualian. Menu tombol juga mengarahkan user untuk melihat alur proses, mencari
dokumen, atau memeriksa bagian yang belum jelas. Nama proses dipilih dari daftar,
lalu pertanyaan dijawab melalui tombol atau formulir singkat. Tombol **Akhiri
sesi** tersedia pada kartu aktif agar user dapat berhenti kapan saja tanpa
menerbitkan versi, commit, atau push. Session ID dan kode keputusan internal
tetap tersedia untuk audit tetapi tidak perlu diketik oleh user.

Statistik kesehatan dokumen tersedia melalui **Kesehatan per flow** dan
**Kesehatan keseluruhan** pada `/mulai`, atau command operator
`/document-health flow` dan `/document-health all`. Statistik memisahkan cakupan
alur utama dari detail proses dan hanya menunjukkan konteks yang terdeteksi,
bukan nilai mutu final atau bukti bahwa requirement sudah benar.

Saat tombol dipilih, kartu menampilkan state proses yang spesifik seperti
**Sedang menyimpan jawaban** atau **Sedang mengakhiri sesi**. Seluruh tombol
dinonaktifkan sementara untuk mencegah klik ganda. Jika proses gagal, tombol
aktif kembali. Bot membedakan pilihan yang belum tersimpan dari jawaban yang
sudah tercatat tetapi gagal menyiapkan langkah berikutnya.

User biasa hanya perlu melihat `/mulai` dan `/help`. Grup command teknis tetap
tersedia bagi operator Discord dengan permission **Manage Server** untuk
diagnostik dan kompatibilitas operasional.

Sumber utama yang boleh dipilih dan direkonsiliasi hanya PRD asli berekstensi
exact `.md` di `neurovi-prd/source/original/PRD/PRD Generator (.md)/`.
Folder `PRD Generator (.md) - Copy`, folder original lain, `menu-flow`, dan tiga
artefak Markdown pendukung (`KONTEKS-SESI.md`, dokumen API APLICARES, serta
`ringkasan-merge-prd-rj.md`) tidak termasuk. Mermaid, PDF, DOCX, Graphify,
dokumen generated/canonical, referensi tambahan, dan seluruh sumber lain hanya
boleh menunjang reasoning/discovery; semuanya tidak dapat menjadi fakta sumber
utama, dipilih, atau menggantikan fakta dari PRD utama.

Inventaris E2E aktif berada di
`neurovi-prd/reconciliation/e2e-inventory/domain-worklist.json`. Inventaris ini
memetakan setiap PRD unik ke tepat satu owner domain sebagai worklist
pemeriksaan flow, sementara pemakaian dokumen lintas domain dicatat melalui
indeks relasi. Inventaris Mermaid/process-path dan inventaris klasifikasi semua
format file sudah dihapus agar tidak menjadi sumber kebenaran kedua.

Pertanyaan biasa di channel yang diizinkan otomatis dibuatkan thread bantuan
tanpa perlu tag bot. Pesan, mention, DM, dan slash command di luar channel yang
diizinkan tidak diproses; hanya thread bantuan yang dibuat bot dari channel
tersebut yang tetap menerima pesan lanjutan, autocomplete, dan slash command.
Jawaban mengarahkan user ke slash command yang tersedia dan tidak pernah
menjalankan tool atau mengubah dokumen dari chat biasa. Jika kebutuhannya belum
didukung, bot menyebutkan perlunya enhancement developer serta memberi
workaround dengan command yang ada.
