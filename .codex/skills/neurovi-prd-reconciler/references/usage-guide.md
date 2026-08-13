# Neurovi PRD Reconciler Usage Guide

## Invoking the Skill

When repository-local skills are discoverable, invoke:

```text
Use $neurovi-prd-reconciler untuk rekonsiliasi E2E-RJ.
```

When the root-level skill is not automatically discovered, invoke it by path:

```text
Baca dan gunakan .codex/skills/neurovi-prd-reconciler/SKILL.md untuk rekonsiliasi E2E yang saya pilih.
```

## Choose the Reconciliation Process

Always choose one process; do not run a combined interview.

```text
Rekonsiliasi alur utama Rawat Jalan. Bahas hanya trigger, urutan utama,
handoff, output, status, dan kelanjutan lintas domain.
```

```text
Rekonsiliasi detail proses Rawat Jalan. Bahas hanya skenario, kondisi, aturan,
validasi, error, pengecualian, dan acceptance criteria.
```

In Discord, choose **Perbaiki alur utama** or **Perbaiki detail proses**.
Use **Lanjut alur utama** or **Lanjut detail proses** to resume the matching
session. Both processes may exist for the same E2E without overwriting each other.

## Typical Workflow

### Select an E2E

```text
Gunakan $neurovi-prd-reconciler untuk Rawat Jalan. Pakai semua PRD owner-domain sebagai worklist otomatis dan mulai dari gap alur yang benar-benar membutuhkan keputusan bisnis.
```

The skill resolves the code or name and asks the user to confirm ambiguous matches.

### Review Documents

```text
Tampilkan owner-domain PRD, relasi lintas domain, kandidat relasi mekanis, dan reference tambahan secara terpisah. Jangan meminta konfirmasi domain atau klasifikasi setiap owner PRD.
```

Owner PRDs are loaded automatically. Mechanical relations remain reasoning
candidates until source evidence or a semantic user decision supports them.
The runtime reads each owner PRD from the verified lossless canonical baseline
and stops if that canonical document is stale or no longer complete and
byte-identical to the original payload. Canonical E2E supplies the worklist and
relationship map without converting mechanical relations into facts.

### Promote and Normalize a PRD

```text
Promote dokumen yang saya setujui sebagai working copy. Usulkan nama dan document code yang seragam, tetapi jangan rename sebelum saya setujui. Jangan mengubah source original.
```

Promotion creates a derived file with full provenance.

### Add a New Reference

```text
Tambahkan dokumen pada <path> sebagai reference untuk sesi ini. Scan ulang format, hubungan E2E, gap, dan kemungkinan domain yang lebih sesuai.
```

The skill must explain why another domain may be stronger and warn about illogical placement. The user makes the final decision.

### Review Defects

```text
Scan semua PRD owner-domain. Tampilkan hanya defect alur dan data yang memerlukan keputusan saya. Jangan usulkan requirement baru sebagai fakta.
```

Each defect includes evidence and a neutral decision question.

### Run a Skippable Interview

```text
Interview saya untuk menutup gap alur satu per satu. Saya boleh menjawab, skip, defer, atau unknown. Jangan hentikan interview jika saya melewati pertanyaan.
```

When a later answer may also answer a skipped question, the skill presents the correlation and asks the user to confirm it.

### Request Gap Closure Recommendations

```text
Untuk setiap gap flow, tampilkan dua atau tiga opsi penyelesaian, dampak flow dan integritas datanya, lalu rekomendasikan satu opsi. Jangan masukkan rekomendasi ke baseline sebelum saya konfirmasi.
```

`KEEP_GAP_OPEN` remains available when evidence is insufficient. Recommendations remain proposals and must not include improvised technical implementation.

### Apply Decisions

```text
Terapkan hanya keputusan dengan status USER_CONFIRMED. Biarkan gap lain tetap terbuka.
```

### Stop a Working Session

In Discord, use the **Akhiri sesi** button on the active reconciliation card.
Confirm the stop action when prompted. Previous answers remain in the audit,
the current unanswered question remains open, and no baseline, commit, tag, or
push is created. Start the same E2E again later to create a new working session.

### Baseline

```text
Tampilkan baseline readiness dan usulkan versi Git global, misalnya v0.0.2. Sertakan dokumen yang berubah dan perubahan terhadap v0.0.1. Jangan commit atau membuat tag jika ada perubahan tanpa source reference, decision ID, atau BASELINE_APPROVAL.
```

All Designer, Developer, and QA context packages must use the same approved global repository tag. Individual PRDs and E2Es do not receive separate release versions.

Compare two released versions with:

```bash
python3 .codex/skills/neurovi-prd-reconciler/scripts/version_diff.py --repo neurovi-prd compare --from v0.0.1 --to v0.0.2
```

## User Decision Vocabulary

- `approve rename`: approve only the derived filename/title/code change.
- `approve decision`: allow the recorded decision to affect the baseline.
- `accept as is`: retain a known gap or defect without changing the PRD.
- `skip`: continue the interview while preserving the unanswered question.
- `deferred`: postpone a functional or semantic decision.
- `confirm correlation`: allow a later answer to resolve a specific earlier question or gap.
- `keep gap open`: retain the gap because available evidence is insufficient.

## Reading the Output

- `SOURCE_FACT` is safe baseline evidence.
- `CROSS_SOURCE_FACT` requires a visible reference to another eligible `.md`
  PRD beneath `source/original/PRD/PRD Generator (.md)/`.
- Other files may support reasoning and discovery but cannot be labeled
  `SOURCE_FACT` or `CROSS_SOURCE_FACT`.
- `USER_CONFIRMED` requires a decision ID.
- `MECHANICAL_CANDIDATE` is a relation/search proposal, not a confirmed relationship.
- `GAP`, `AMBIGUOUS`, and `CONFLICT` require review.
- Historical `TAKE_OFF` means excluded by an older decision, not deleted; the
  normal owner-worklist flow no longer asks for this classification.

## Important Note

All codes, names, and processes in usage examples are illustrative invocation patterns. They do not approve a domain assignment or relationship.
