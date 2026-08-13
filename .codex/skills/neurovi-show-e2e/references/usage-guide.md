# Neurovi Show E2E Usage Guide

## List All Domain Worklists

```text
Use $neurovi-show-e2e.
```

The default output lists every active E2E domain worklist and confirms total eligible files, unique PRDs, and unassigned PRDs.

## Filter the List

```text
Tampilkan domain pelayanan utama dengan $neurovi-show-e2e.
```

Filters narrow the existing inventory. They do not create domains or change owner assignments.

## Show One Domain

```text
Use $neurovi-show-e2e untuk E2E-RJ.
```

The detail view shows the ordered PRD worklist and indexed relationships. A PRD can appear as context for another domain through a relation while retaining one owner domain.

## Interpretation

- `DOMAIN_WORKLIST_PROPOSAL` is an active automatic review worklist, not a baselined semantic decision.
- `MECHANICAL_PROPOSAL` owner assignment is automatic routing metadata. It remains distinguishable from a user-requested placement change but does not require confirmation before flow checking.
- `SOURCE_EXPLICIT` relation evidence cites eligible PRD text.
- `REVIEW_REQUIRED` relations are mechanical discovery candidates.
- `CONFLICT_FOUND` remains open until a user decision resolves it.
- Mermaid, Graphify, PDF, DOCX, Copy folders, and other sources are reasoning support only.
