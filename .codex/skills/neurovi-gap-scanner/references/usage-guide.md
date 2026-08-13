# Neurovi Two-Scanner Usage Guide

## Main Business Flow

```text
Use $neurovi-gap-scanner untuk memeriksa alur utama Rawat Inap.
```

Run:

```bash
python3 .codex/skills/neurovi-gap-scanner/scripts/scan_gaps.py \
  --repo neurovi-prd main-flow --e2e E2E-RI
```

Expected emphasis:

- ordered owner-domain PRDs;
- trigger, sequence, handoff, output, and status checks;
- source-explicit flow relations only;
- cross-domain continuations such as Rawat Jalan -> SPRI/Transfer Internal ->
  Rawat Inap;
- explicit conflicts affecting order or mandatory behavior.

Detailed scenario families do not appear in this report.

## Detailed Cases for One PRD

```text
Use $neurovi-gap-scanner untuk detail kasus PRD Tindakan & BHP.
```

Run:

```bash
python3 .codex/skills/neurovi-gap-scanner/scripts/scan_gaps.py \
  --repo neurovi-prd business-cases --document DOC-4199BA40F7A28D80
```

Expected emphasis:

- alternate flows;
- failures and exceptions;
- cases and conditions;
- business rules;
- validation behavior;
- acceptance criteria;
- explicit unresolved markers.

Main-flow handoffs do not appear in this report.

## Detailed Cases for One E2E

```text
Use $neurovi-gap-scanner untuk detail kasus domain EMR.
```

Run:

```bash
python3 .codex/skills/neurovi-gap-scanner/scripts/scan_gaps.py \
  --repo neurovi-prd business-cases --e2e E2E-EMR
```

The result aggregates only owner-worklist PRDs and shows which documents need a
separate document-level review. It does not duplicate PRD ownership into related
domains.

## JSON Output

Place `--json` before the scanner subcommand:

```bash
python3 .codex/skills/neurovi-gap-scanner/scripts/scan_gaps.py \
  --repo neurovi-prd --json main-flow --e2e E2E-RI
```

## Document Health Statistics

Show one selected flow with document-level rows:

```bash
python3 .codex/skills/neurovi-gap-scanner/scripts/document_health.py \
  --repo neurovi-prd flow --e2e E2E-RJ
```

Show all flows or the overall repository summary:

```bash
python3 .codex/skills/neurovi-gap-scanner/scripts/document_health.py \
  --repo neurovi-prd flow

python3 .codex/skills/neurovi-gap-scanner/scripts/document_health.py \
  --repo neurovi-prd all
```

Health output reports main-flow coverage and detailed-case coverage separately.
The combined percentage is navigation support only, not a final document quality
score and not evidence that a requirement is correct.

## Interpretation

- Missing headings do not prove missing facts.
- Owner-domain assignment is automatic routing metadata.
- Mechanical `REFERENCES` relations do not prove a handoff.
- Source-explicit flow relations may identify a real dependency or conflict.
- Other source formats remain reasoning support only.
- The two outputs may both inform reconciliation, but they must remain separate
  evidence blocks so a missing detailed case is not reported as a broken E2E flow.
