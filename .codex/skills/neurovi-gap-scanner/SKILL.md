---
name: neurovi-gap-scanner
description: Scan Neurovi SIMRS E2E flows and PRDs for mechanical, explicit, and user-confirmed context gaps without modifying source documents. Use with no parameter to list E2E flows that still have gaps, with an E2E code or name to map related documents and cross-document context gaps, or with a document code or name to map internal PRD context and format gaps. Use when users ask to scan, inspect, inventory, prioritize, or explain incomplete flow, handoff, data context, cases, conditions, or document structure before controlled reconciliation.
---

# Neurovi Gap Scanner

## Contract

Run this skill as a read-only diagnostic scanner.

1. Read the tools `AGENTS.md` and `neurovi-prd/AGENTS.md`, then obey both.
2. Read `references/gap-taxonomy.md` before interpreting scan results.
3. Never edit `source/original/` or reconciliation decisions.
4. Preserve source facts exactly.
5. Treat missing headings, token matches, Mermaid mappings, and absent generated links as mechanical gap candidates, not proven semantic defects.
6. Distinguish source flow documents, explicit memberships, confirmed memberships, and mechanical candidates.
7. Cite document IDs, paths, flow nodes, edges, headings, or register rows for every finding.
8. Route gap resolution and user interviews to `$neurovi-prd-reconciler`; do not resolve gaps inside this skill.

## Run the Scanner

Use the bundled scanner:

```bash
# No parameter: list E2Es with remaining gap candidates or confirmed gaps.
python3 .codex/skills/neurovi-gap-scanner/scripts/scan_gaps.py --repo neurovi-prd

# E2E code or name: map documents and cross-document gaps.
python3 .codex/skills/neurovi-gap-scanner/scripts/scan_gaps.py --repo neurovi-prd --e2e E2E-ADM-01

# Document code or name: map internal document gaps.
python3 .codex/skills/neurovi-gap-scanner/scripts/scan_gaps.py --repo neurovi-prd --document DOC-XXXXXXXXXXXXXXX
python3 .codex/skills/neurovi-gap-scanner/scripts/scan_gaps.py --repo neurovi-prd --document "pendaftaran rawat jalan"
```

Pass `--json` for machine-readable output. Change `--repo` only when the
document repository is mounted elsewhere.

## Route the Request

### No Parameter

List only E2Es with at least one gap candidate, open confirmed defect, skipped question, or deferred question.

- Sort confirmed/open defects first, then mechanical gap count.
- Show E2E code, name, current boundary status, gap count, open defect count, and primary gap types.
- State that the list is a prioritization queue, not proof that each finding is a semantic defect.
- Ask the user to select an E2E code or name for deeper scanning.

### E2E Code or Name

Resolve exact code, exact title, then unambiguous partial match. Show choices when ambiguous.

Map:

- source flow and boundary status;
- source-explicit document memberships;
- user-confirmed include/context/take-off decisions when a workspace exists;
- mechanical document candidates without calling them members;
- nodes without document candidates;
- missing confirmed context traces between stages/documents;
- exact-content duplicates requiring source representation review;
- open defects and skipped/deferred interview questions;
- internal gap candidate counts for each related document.

Report cross-document gaps separately from document-internal gaps. Never infer that two documents hand off data merely because their titles share tokens.

### Document Code or Name

Resolve an exact document ID first, then exact title/path, then an unambiguous partial match. Show candidate documents when ambiguous.

Map:

- source identity and provenance;
- E2E relationships by evidence class;
- detected section families;
- context found under nonstandard headings;
- missing section/context candidates;
- explicit lexical gap markers such as `TBD` or `belum didefinisikan`;
- open confirmed defects or interview questions referring to the document.

Use these distinctions:

- `SECTION_PRESENT`: matching context appears under a detected heading.
- `CONTEXT_PRESENT_UNSTRUCTURED`: context terms exist, but no standard heading was detected.
- `CONTEXT_GAP_CANDIDATE`: neither a matching heading nor mechanical context marker was found.
- `EXPLICIT_GAP_MARKER_CANDIDATE`: source text contains an explicit unresolved marker.

Do not claim context is absent solely because a standard heading is absent.

## Present Findings

For every scan:

1. Lead with scope and evidence limitations.
2. Separate confirmed gaps from mechanical candidates.
3. Include evidence references and counts.
4. Recommend the next scan depth or reconciliation target.
5. When resolution is requested, invoke `$neurovi-prd-reconciler` with the selected E2E/document and the scanner findings.

Use `assets/gap-scan-report-template.md` when saving a scan report. Read `references/usage-guide.md` for invocation examples. Scanner results do not change the approved global Git version.
