# Neurovi PRD Reconciler Usage Guide

## Invoking the Skill

When repository-local skills are discoverable, invoke:

```text
Use $neurovi-prd-reconciler untuk rekonsiliasi E2E-ADM-01.
```

When the root-level skill is not automatically discovered, invoke it by path:

```text
Baca dan gunakan .codex/skills/neurovi-prd-reconciler/SKILL.md untuk rekonsiliasi E2E yang saya pilih.
```

## Typical Workflow

### Select an E2E

```text
Gunakan $neurovi-prd-reconciler. Tampilkan kandidat E2E yang berhubungan dengan pendaftaran rawat jalan, tetapi jangan tetapkan pilihan sebelum saya konfirmasi.
```

The skill resolves the code or name and asks the user to confirm ambiguous matches.

### Review Documents

```text
Tampilkan source flow, explicit membership, kandidat mekanis, dan reference tambahan secara terpisah. Saya akan memilih include, context only, take off, atau deferred.
```

Candidates remain candidates until the user decides.

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
Scan dokumen yang sudah saya include. Tampilkan defect alur dan data yang memerlukan keputusan saya. Jangan usulkan requirement baru sebagai fakta.
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

- `include`: confirm the document as part of the E2E scope or context.
- `context only`: retain context without adding work scope.
- `take off`: exclude from the E2E while keeping the audit record.
- `deferred`: postpone the decision.
- `approve rename`: approve only the derived filename/title/code change.
- `approve decision`: allow the recorded decision to affect the baseline.
- `accept as is`: retain a known gap or defect without changing the PRD.
- `skip`: continue the interview while preserving the unanswered question.
- `confirm correlation`: allow a later answer to resolve a specific earlier question or gap.
- `keep gap open`: retain the gap because available evidence is insufficient.

## Reading the Output

- `SOURCE_FACT` is safe baseline evidence.
- `CROSS_SOURCE_FACT` requires a visible source reference.
- `USER_CONFIRMED` requires a decision ID.
- `MECHANICAL_CANDIDATE` is a search result, not membership.
- `GAP`, `AMBIGUOUS`, and `CONFLICT` require review.
- `TAKE_OFF` means excluded by decision, not deleted.

## Important Note

All codes, names, and processes in usage examples are illustrative invocation patterns. They do not establish repository truth or approve an E2E boundary.
