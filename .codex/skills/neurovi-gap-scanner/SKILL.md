---
name: neurovi-gap-scanner
description: "Run Neurovi PRD read-only diagnostics: a main-flow scanner for E2E continuity, a business-case scanner for detailed behavior, or document-health statistics per business flow and across the full eligible PRD repository. Use when users ask whether an E2E process is connected, whether business cases are sufficiently described, or for aggregate document coverage and review-candidate statistics before controlled reconciliation."
---

# Neurovi Gap Scanner

## Contract

Run this skill as one of two explicit read-only scanners. Never combine their
findings into one undifferentiated gap report.

1. Read the tools `AGENTS.md` and `neurovi-prd/AGENTS.md`, then obey both.
2. Read `references/gap-taxonomy.md` before interpreting results.
3. Never edit `source/original/`, inventory ownership, or reconciliation decisions.
4. Preserve source facts exactly.
5. Use only eligible original `.md` PRDs under
   `source/original/PRD/PRD Generator (.md)/` as primary scan sources.
6. Treat other formats, Graphify, Mermaid, and relation indexes as supporting
   reasoning only. They may help locate a handoff but cannot create a source fact.
7. Treat missing headings and incomplete mechanical evidence as candidates, not
   proven semantic defects.
8. Cite document IDs, paths, worklist steps, relation IDs, evidence references,
   headings, or marker lines for every finding.
9. Route user interviews and source-preserving resolution to
   `$neurovi-prd-reconciler`; do not resolve gaps in this skill.

## Choose One Scanner

### Scanner 1: Main Business Flow

Use when the question is whether one E2E process is connected from start to
finish. It checks:

- trigger and initial input;
- ordered owner-worklist stages;
- primary sequence and handoff;
- process output and status transition;
- source-explicit within-domain and cross-domain continuation;
- conflicts that change the meaning or order of the main flow.

It excludes alternate cases, detailed validation, error handling, and acceptance
criteria. A `REFERENCES` relation without explicit flow evidence is supporting
context and is not treated as a handoff.

```bash
python3 .codex/skills/neurovi-gap-scanner/scripts/scan_gaps.py \
  --repo neurovi-prd main-flow --e2e E2E-RI
```

### Scanner 2: Detailed Business Cases

Use when the question is whether detailed behavior is described. It checks:

- scope exclusions and case boundaries;
- alternate scenarios and conditions;
- business rules and validation behavior;
- errors and exceptions;
- acceptance criteria;
- explicit unresolved markers such as `TBD` or `belum didefinisikan`.

Run it for one PRD when the user names a document. Run it for one E2E to
aggregate the owner-domain PRD worklist and identify which PRDs require deeper
review. It excludes primary-flow continuity findings.

```bash
python3 .codex/skills/neurovi-gap-scanner/scripts/scan_gaps.py \
  --repo neurovi-prd business-cases --document DOC-4199BA40F7A28D80

python3 .codex/skills/neurovi-gap-scanner/scripts/scan_gaps.py \
  --repo neurovi-prd business-cases --e2e E2E-EMR
```

Pass `--json` before the scanner name for machine-readable output. Change
`--repo` only when the document repository is mounted elsewhere.

## Route the Request

- “Apakah alur Rawat Inap sudah tersambung?” -> main-flow scanner.
- “Apa handoff Rawat Jalan ke Rawat Inap yang belum jelas?” -> main-flow scanner.
- “Apakah kasus Tindakan & BHP sudah lengkap?” -> business-case document scanner.
- “PRD mana dalam EMR yang belum lengkap detail kasusnya?” -> business-case E2E scanner.
- If the user asks only to “scan gaps” without indicating intent, explain the two
  choices and ask whether they mean process continuity or detailed behavior.

## Document Health Statistics

Use the health aggregator when the user asks for statistics rather than a gap
interview. It runs both scanners over owner-domain PRDs but keeps their metrics
separate. It reports detected coverage, documents requiring review, unresolved
markers, source-explicit flow gaps, and per-flow totals. Never turn the combined
percentage into a semantic quality score.

```bash
python3 .codex/skills/neurovi-gap-scanner/scripts/document_health.py \
  --repo neurovi-prd flow

python3 .codex/skills/neurovi-gap-scanner/scripts/document_health.py \
  --repo neurovi-prd flow --e2e E2E-RJ

python3 .codex/skills/neurovi-gap-scanner/scripts/document_health.py \
  --repo neurovi-prd all
```

The aggregate is read-only. A missing context family remains a mechanical
review candidate, and the percentage describes detectable coverage only.

## Present Findings

For every scan:

1. Lead with the selected scanner and its scope.
2. State what the scanner intentionally excludes.
3. Separate source-explicit conflicts from mechanical candidates.
4. Use operational language before internal taxonomy codes.
5. Recommend the relevant next action: inspect a specific handoff for Scanner 1,
   or inspect a specific PRD/case family for Scanner 2.
6. If resolution is requested, invoke `$neurovi-prd-reconciler` with the selected
   E2E and only the scanner output matching the selected reconciliation mode.

Read `references/usage-guide.md` for examples. Scanner results never modify the
approved global Git version.
