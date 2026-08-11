---
name: neurovi-show-prd
description: Display immutable original Neurovi PRDs and their literal source content by document code, title, filename, or source path. Use when users ask to show, open, read, quote, inspect, or locate an original PRD; request a specific original section; verify source identity or checksum; or distinguish original source content from reconciled, canonical, E2E, or Graphify-derived context.
---

# Neurovi Show PRD

## Contract

Use this skill only to locate and display original repository documents.

1. Read the tools `AGENTS.md` and `neurovi-prd/AGENTS.md`, then obey both.
2. Never edit `source/original/`.
3. Treat `source/original/` as source truth and `catalog/document-index.json` as a rebuildable lookup index.
4. Display textual originals directly from `source/original/`. For binary originals, display `documents/<DOC-ID>/content.md` only as a literal extraction and always identify it as extracted content.
5. Never substitute reconciled PRDs, E2E context, Graphify pages, summaries, or inferred correlations for original content.
6. Never correct, complete, normalize, translate, summarize, or reinterpret source claims while presenting them.
7. If a document or section selector is ambiguous, show the candidates and wait for the user to choose. Never select silently.
8. If output is too large, preserve exact text and present it in numbered chunks or ask for a section. Never silently shorten it into a summary.

## Run the Viewer

Use the bundled script from the tools repository root. Pass the document
submodule explicitly:

```bash
# No document parameter: list original document records.
python3 .codex/skills/neurovi-show-prd/scripts/show_prd.py --repo neurovi-prd

# Resolve by exact document code, title, filename, or source path.
python3 .codex/skills/neurovi-show-prd/scripts/show_prd.py --repo neurovi-prd --document DOC-4287D4C5CFF2D2E0
python3 .codex/skills/neurovi-show-prd/scripts/show_prd.py --repo neurovi-prd --document "Pendaftaran Rawat Jalan"

# Display one literal section when detected headings are available.
python3 .codex/skills/neurovi-show-prd/scripts/show_prd.py --repo neurovi-prd --document DOC-4287D4C5CFF2D2E0 --section "3. In Scope"

# Machine-readable output.
python3 .codex/skills/neurovi-show-prd/scripts/show_prd.py --repo neurovi-prd --document DOC-4287D4C5CFF2D2E0 --json
```

Use `--query <text>` and `--limit <number>` to narrow the no-parameter inventory.
Change `--repo` only when the document repository is mounted elsewhere.

## Resolve Requests

Resolve a document in this order:

1. exact `DOC-*` code;
2. exact source path, filename, stem, or catalog title;
3. unambiguous partial title/path match.

Resolve a section by exact detected heading first, then an unambiguous partial heading. If headings were not detected, say so and offer the full literal extraction rather than inventing section boundaries.

## Present Content

Before the literal content, show:

- document ID and catalog title;
- immutable original source path;
- source format and SHA-256;
- whether the content is direct original text or a binary-document extraction;
- selected heading when section filtering is used.

Keep the literal content visually separate from any operational note. If the user also asks for analysis, place analysis after the source quotation and label it as analysis, never as original content.

Read `references/usage-guide.md` for invocation and ambiguity examples.
