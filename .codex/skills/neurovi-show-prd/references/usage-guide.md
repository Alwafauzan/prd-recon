# Neurovi Show PRD Usage Guide

## List Original Documents

```text
Use $neurovi-show-prd.
```

The no-parameter mode lists repository records backed by `source/original/`. This is navigation, not a canonical or reconciled PRD list.

## Show by Document Code

```text
Use $neurovi-show-prd untuk DOC-4287D4C5CFF2D2E0.
```

The result includes provenance metadata and literal content. Text formats are read directly from the original file. Binary formats use the generated literal extraction and retain a link to the original binary.

## Show by Name or Path

```text
Tampilkan PRD original Pendaftaran Rawat Jalan dengan $neurovi-show-prd.
```

```text
Tampilkan source/original/PRD/Pendaftaran & Triase/PRD_Pendaftaran_Rawat_Jalan.docx.
```

Exact matches take priority. When several originals match, return their document codes, titles, and source paths and ask the user to select one.

## Show One Section

```text
Tampilkan bagian In Scope dari DOC-4287D4C5CFF2D2E0 menggunakan $neurovi-show-prd.
```

Section output uses detected source headings. Do not construct a semantic section when no heading boundary exists.

## Large Documents

If the literal document does not fit in one response:

1. state that the output will be split without summarization;
2. preserve original order and text;
3. label each chunk with stable part numbers;
4. continue from the exact prior boundary when requested.

## Source Integrity

- A checksum mismatch means the catalog or extraction may be stale; stop instead of displaying stale generated content.
- `documents/<DOC-ID>/content.md` is a literal extraction artifact, not a rewritten PRD.
- `reconciliation/`, `processes/`, `graph/`, and Graphify are context/navigation layers, not original PRD content.
