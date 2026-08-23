# Panduan Auditor — Alur Kerja dan Langkah Pemeriksaan

Panduan ini menjelaskan cara mengaudit status rekonsiliasi PRD Neurovi secara
read-only: kelompok domain, alur E2E, PRD, gap, dan fix yang sudah dilakukan.
Auditor tidak mengubah dokumen, artefak, maupun Git.

## 0. Prasyarat

- Struktur folder berdampingan:
  ```text
  prd-recon/
  ├── neurovi-doc-reconciliator/   ← jalankan semua command dari sini
  └── neurovi-prd/
  ```
- Python terpasang (`python --version`).
- Repo dokumen dapat dibaca:
  ```powershell
  Test-Path ..\neurovi-prd\reconciliation\e2e-inventory\domain-worklist.json
  ```
  Hasil harus `True`. Jika `False`, hentikan dan minta operator memeriksa
  checkout repository.

## 1. Alur kerja auditor (gambaran besar)

```text
Verifikasi lingkungan
  → jalankan report lengkap
  → baca ringkasan global (baseline, gap, fix, sesi, rilis)
  → telusuri per kelompok → per E2E → per PRD
  → verifikasi bukti fix ke dokumen sumber
  → periksa sesi, keputusan, dan riwayat rilis
  → jalankan validasi integritas repository
  → simpan/bagikan report
```

## 2. Langkah 1 — Jalankan report lengkap

```powershell
python .codex/skills/neurovi-audit-report/scripts/audit_report.py --repo ..\neurovi-prd --output audit-report.md
```

Tanpa `--output`, report tampil di layar. Report selalu read-only; aman
dijalankan berulang kali.

## 3. Langkah 2 — Baca ringkasan global

Report punya dua lapis, keduanya dibuat otomatis oleh script:

1. **Ringkasan untuk PM** (paling atas): bahasa awam, tanpa kode status
   teknis. Satu blok per E2E: dokumen yang dicakup, jumlah keputusan resmi,
   defect yang sengaja dibiarkan terbuka (dengan alasan), dan gap yang
   dipecah menjadi "kemungkinan sudah dibahas lewat keputusan pada dokumen
   yang sama — perlu verifikasi" vs "belum ada keputusan sama sekali". Cocok
   dikirim langsung ke PM/PO non-teknis.
2. **Ringkasan Global (teknis)** dan detail per kelompok/E2E di bawahnya:
   kode status mentah, ID, dan bukti kutipan literal — untuk auditor/PO
   teknis dan arsip pekerjaan sendiri.

Bagian teknis menjawab pertanyaan auditor dalam urutan:

| Baris report | Pertanyaan auditor |
|---|---|
| Baseline canonical | Versi baseline saat ini dan status rilisnya |
| Kelompok / E2E / PRD unik | Cakupan inventaris |
| Kandidat gap / terbuka / tertutup / dikecualikan | Posisi gap keseluruhan |
| Sesi / keputusan USER_CONFIRMED / rilis | Apakah rekonsiliasi manusia sudah berjalan |

Tanda penting:

- `Belum ada sesi rekonsiliasi manusia yang tercatat` berarti seluruh fix
  berasal dari penutupan otomatis source fact, bukan keputusan PO.
- `release_status: UNRELEASED` berarti belum ada baseline resmi; semua
  perubahan masih working state.
- Kolom **"Terkait keputusan?"** pada tabel Gap terbuka adalah indikasi
  berbasis dokumen yang sama, bukan bukti gap itu pasti tertutup — field
  `resolution_decision_id` di register scanner memang tidak pernah diisi
  otomatis (skill ini read-only dan tidak menulis ke data canonical). Selalu
  verifikasi manual ke dokumen sebelum mengklaim gap tersebut selesai.
- Sesi berstatus `AWAITING_USER_DECISION` atau `SELECTED_FOR_REVIEW` berarti
  sesi itu belum ditutup resmi, walau semua keputusan di dalamnya sudah
  `USER_CONFIRMED`. Report akan menandai ini secara eksplisit di Ringkasan
  untuk PM — jangan baca sebagai "belum dikerjakan" maupun "sudah selesai".

## 4. Langkah 3 — Telusuri per kelompok dan alur

Gunakan filter agar fokus:

```powershell
# Satu kelompok
python .codex/skills/neurovi-audit-report/scripts/audit_report.py --repo ..\neurovi-prd --group pelayanan-utama

# Satu alur (E2E)
python .codex/skills/neurovi-audit-report/scripts/audit_report.py --repo ..\neurovi-prd --e2e E2E-RJ

# Ringkasan tanpa tabel detail gap
python .codex/skills/neurovi-audit-report/scripts/audit_report.py --repo ..\neurovi-prd --summary-only
```

Untuk setiap E2E, periksa berurutan:

1. tabel PRD (kode canonical, judul, stage) — apakah worklist masuk akal;
2. tabel **Gap terbuka** — berapa banyak, jenis apa, mode apa, dan apakah
   kolom "Terkait keputusan?" menunjuk ke keputusan yang perlu diverifikasi;
3. tabel **Sudah diperbaiki dari source fact** — fix apa yang sudah terjadi;
4. tabel **Dikecualikan dari cakupan aktif** — bukti non-aktif yang sengaja
   diabaikan (asumsi, riwayat, rencana masa depan), beserta alasannya;
5. tabel **Keputusan terkonfirmasi** — keputusan PO/SME yang tercatat, beserta
   dokumen yang terdampak;
6. tabel **Defect tercatat dari sesi manusia** — defect yang pernah ditinjau
   manusia; kalau statusnya masih `OPEN`, baca catatannya — sering kali ini
   keputusan sadar untuk membiarkan gap terbuka (`DEFERRED`/`KEEP_GAP_OPEN`),
   bukan sesuatu yang terlewat.

## 5. Langkah 4 — Verifikasi bukti fix ke dokumen sumber

Setiap baris fix memiliki bukti berupa `path:baris`, misalnya
`PRD/PRD Generator (.md)/Pelayanan (.md)/[FIX] prd-antrian-apm.md:15`.

Verifikasi dengan menampilkan dokumen aslinya (read-only):

```powershell
# Cari dokumen
python .codex/skills/neurovi-show-prd/scripts/show_prd.py --repo ..\neurovi-prd --query "antrian apm"

# Tampilkan isi berdasarkan document ID hasil pencarian
python .codex/skills/neurovi-show-prd/scripts/show_prd.py --repo ..\neurovi-prd --document DOC-XXXXXXXXXXXXXXX
```

Cocokkan bahwa pernyataan pada baris yang dikutip memang menjawab kandidat
gap tersebut. Fix yang sah selalu `RESOLVED_BY_SOURCE_FACT` dengan bukti
literal, atau keputusan dengan `decision_id` berstatus `USER_CONFIRMED`.

## 6. Langkah 5 — Periksa sesi, keputusan, dan rilis

- **Sesi**: report membaca `reconciliation/workspaces/<e2e>/sessions/*/`.
  Klaim "rekonsiliasi selesai" hanya valid jika ada sesi berstatus
  `RECONCILED`, bukan `SELECTED_FOR_REVIEW` atau `STOPPED_BY_USER`.
- **Keputusan**: setiap perubahan makna wajib punya baris `USER_CONFIRMED`
  di decision register sesi. Tanpa itu, perubahan tidak sah.
- **Rilis**: riwayat resmi hanya dari `reconciliation/releases/` dan tag Git
  global. Working commit bukan rilis.

## 7. Langkah 6 — Validasi integritas repository

Jalankan dua validasi read-only berikut dan catat hasilnya di catatan audit:

```powershell
# A. Preservasi sumber dan konsistensi inventaris
python scripts/build_structure.py validate --source ..\neurovi-prd\source\original --target ..\neurovi-prd

# B. Integritas baseline bootstrap v0.0.0
python scripts/bootstrap_prd_baseline.py validate --repo ..\neurovi-prd
```

Keduanya harus menghasilkan `"valid": true`. Kegagalan pada validasi A
(file sumber hilang/berubah) adalah temuan audit yang harus dilaporkan ke
operator. Kegagalan pada validasi B setelah canonical berubah secara sah
dapat diharapkan — konfirmasikan ke operator.

## 8. Langkah 7 — Simpan dan bagikan

- Simpan report dengan `--output audit-report.md` dan sertakan tanggal audit.
- Untuk integrasi tooling, gunakan `--json`.
- Laporkan temuan dalam format: cakupan yang diperiksa, gap terbuka, fix
  terverifikasi, fix yang gagal verifikasi, dan tindakan lanjutan.

## 9. Cara membaca status

| Status | Arti |
|---|---|
| `RESOLVED_BY_SOURCE_FACT` | Gap tertutup otomatis dari fakta sumber eksplisit; decision ID kosong |
| `OPEN_SOURCE_EXPLICIT_GAP` | Sumber sendiri menyatakan belum didefinisikan (TBD dsb.) |
| `OPEN_INSUFFICIENT_SOURCE_EVIDENCE` | Bukti sumber tidak cukup; butuh keputusan manusia |
| `HUMAN_DECISION_REQUIRED` | Konflik/ambiguitas sumber; wajib keputusan PO/SME |
| `EXCLUDED_NON_ACTIVE_SOURCE_EVIDENCE` | Bukti non-aktif (asumsi, riwayat, rencana masa depan); sengaja tidak dipakai |
| `USER_CONFIRMED` (decision) | Keputusan manusia yang sah untuk perubahan makna |

## 10. Red flag untuk auditor

- Klaim "selesai" tanpa folder sesi di `reconciliation/workspaces/`.
- Gap berstatus terbuka tetapi dianggap selesai tanpa decision record.
- Fix tanpa bukti `path:baris` yang dapat dibuka di dokumen sumber.
- Perubahan di `source/original/` — tidak boleh pernah terjadi.
- Tag/rilis dibuat tanpa keputusan `BASELINE_APPROVAL`.
- Sesi dengan seluruh keputusan `USER_CONFIRMED` tapi `session.json.status`
  masih `AWAITING_USER_DECISION`/`SELECTED_FOR_REVIEW` — pekerjaan manusia
  sudah selesai tapi belum ditutup resmi menjadi `RECONCILED`. Laporkan ini
  sebagai catatan tindak lanjut, jangan diam-diam dianggap sudah `RECONCILED`.
- Baris gap terbuka yang kolom "Terkait keputusan?"-nya kosong padahal E2E itu
  punya banyak keputusan tercatat — berarti dokumen itu memang belum pernah
  dibahas keputusan apa pun, bukan cuma belum diverifikasi.

## 11. Masalah umum

| Gejala | Tindakan |
|---|---|
| `ERROR: repository not found` | Periksa posisi PowerShell dan nilai `--repo` |
| `ERROR: E2E not found in inventory` | Periksa kode E2E dengan `show_e2e.py` |
| `ERROR: canonical manifest not found` | Minta operator memeriksa baseline bootstrap |
| Karakter aneh di layar Windows | Jalankan dengan `python -X utf8 ...` |
