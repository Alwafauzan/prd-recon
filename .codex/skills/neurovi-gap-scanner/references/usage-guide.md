# Neurovi Gap Scanner Usage Guide

## Scan All E2Es

```text
Use $neurovi-gap-scanner.
```

With no parameter, the skill lists E2E flows that still have gap candidates or confirmed open gaps.

## Scan One E2E

```text
Use $neurovi-gap-scanner untuk E2E-ADM-01.
```

The skill maps source flow, related documents by evidence class, cross-document gap candidates, document-internal gap counts, open defects, and unresolved interview questions.

## Scan One Document

```text
Use $neurovi-gap-scanner untuk DOC-A7F31FC64110BDA0.
```

or:

```text
Use $neurovi-gap-scanner untuk dokumen Pendaftaran Rawat Jalan.
```

If a title matches several documents, the skill lists choices instead of selecting one silently.

## Continue to Reconciliation

```text
Gunakan hasil scan ini sebagai input $neurovi-prd-reconciler. Interview saya untuk menentukan gap mana yang perlu ditutup.
```

The scanner never applies a recommendation or changes the baseline.

## Important Interpretation

- Missing heading does not prove missing context.
- Token similarity does not prove document membership.
- Mermaid structure does not establish an approved E2E boundary.
- A gap candidate becomes confirmed only through explicit source evidence or user decision.
