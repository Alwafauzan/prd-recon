# Reconciliation Artifact Schema

## Active E2E Inventory

`reconciliation/e2e-inventory/domain-worklist.json` is the only active E2E
inventory. It contains exactly one owner-domain assignment per eligible unique
`content_id`, ordered domain worklists, source representations, and indexed
within-domain/cross-domain relations. Legacy Mermaid/process-path inventories
and the all-format source-folder inventory are not valid inputs.

Owner-domain PRDs from this inventory automatically form the source worklist;
they do not require workspace selection rows or user confirmation. A relation
does not expand primary scope and remains a proposal until supported by source
evidence or a user-confirmed decision.

## Canonical Bootstrap Baseline

`reconciliation/canonical/manifest.json` maps every eligible unique PRD to one
stable code and generated canonical Markdown wrapper, and maps every active
domain to one canonical E2E context. Version `v0.0.0` is the initial bootstrap
baseline ready for reconciliation consumption, but it is not a Git release tag.
Reconciliation consumes this layer only after verifying the active inventory
checksum, original provenance, original and generated checksums, payload offset,
payload length, and complete byte-identical payload.

The manifest also records
`automatic_source_fact_reconciliation_status`,
`automatically_reconciled_source_fact_count`, and
`human_decision_required_count`. Each E2E manifest row records its relevant
automatic and human-decision counts. Conflict relations must never contribute
to the automatic count.

`reconciliation/canonical/automatic-reconciliation.json` records the full
deterministic review of main-flow and business-case scanner candidates across
all eligible PRDs. Its Markdown companion is
`reconciliation/canonical/automatic-reconciliation.md`. A closed row must cite
an exact original path and line, use a verified canonical payload, preserve an
empty decision ID, and state `requirement_change=NONE`. Assumptions, revision
history, future-only text, unresolved markers, missing evidence, and conflicts
must not be counted as automatic closures.

The PRD wrapper and section map are navigation metadata. Only the verified
payload matched to its immutable original may support `SOURCE_FACT`. The E2E
context maps owner worklists and within/cross-domain relations; mechanical
relations remain candidates and do not expand PRD scope.

```text
reconciliation/canonical/
├── manifest.json
├── index.md
├── prds/
│   └── PRD-<DOMAIN>-<NNN>.md
└── e2e/
    └── E2E-<DOMAIN>.md
```

## Workspace Layout

```text
reconciliation/workspaces/<e2e-code>/
└── sessions/
    ├── main-flow/
    │   └── session.json and mode-scoped registers
    └── business-cases/
        └── session.json and mode-scoped registers
```

Each mode-scoped workspace contains:

```text
<mode-workspace>/
├── review-session.md
├── document-selection.csv
├── context-trace.csv
├── reference-register.csv
├── defect-register.csv
├── interview-register.csv
├── answer-correlation.csv
├── decision-register.csv
├── e2e-context.md
├── references/
│   └── <original-reference-file>
└── promoted/
    └── <document-code>-<normalized-title>.md
```

Bootstrap creates one active canonical copy of each document and E2E context.
Later approved reconciliation replaces those same active paths; do not create
parallel canonical copies:

```text
reconciliation/canonical/
├── prds/
│   └── <document-code>.md
└── e2e/
    └── <e2e-code>.md
```

Create small release artifacts only after the user confirms a repository baseline:

```text
reconciliation/releases/
├── index.md
└── v<major>.<minor>.<patch>/
    ├── manifest.json
    └── changes.md
```

Do not duplicate canonical documents inside baseline folders. Git stores historical content. Do not place working files in `source/original/`.

## Session Fields

`session.json` must include:

```json
{
  "session_id": "REC-...",
  "e2e_code": "E2E-...",
  "e2e_title": "...",
  "e2e_selection_status": "AUTO_WORKLIST",
  "reconciliation_mode": "MAIN_FLOW-or-BUSINESS_CASES",
  "reconciliation_mode_label": "Perbaikan alur utama-or-Perbaikan detail proses",
  "started_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "source_inventory_version": "...",
  "canonical_baseline_manifest_sha256": "...",
  "base_canonical_version": "v0.0.0-or-later",
  "base_global_version": "v0.0.1-or-UNRELEASED",
  "base_git_commit": "commit-or-UNCOMMITTED",
  "status": "SELECTED_FOR_REVIEW"
}
```

New identifiers include the mode marker, for example `REC-E2E-RJ-MF-001` and
`REC-E2E-RJ-BC-001`. Read historical `REC-E2E-...-001` sessions as legacy
main-flow sessions. Each mode owns its current question, registers, audit, and
stop/resume state.

The session runtime may additionally use `STOPPED_BY_USER` as a terminal
working-session status. When present, record `stopped_at` and `stopped_by`, keep
the current unanswered question intact, and append a
`SESSION_STOPPED_BY_USER` audit event. This status closes the interactive
session only; it is not `RECONCILED`, `BASELINED`, or `PUBLISHED` and must not
create Git release artifacts.

## Global Release Manifest

Use this structure for `reconciliation/releases/vX.Y.Z/manifest.json`:

```json
{
  "schema_version": 1,
  "repository_version": "v0.0.2",
  "previous_repository_version": "v0.0.1",
  "change_class": "PATCH",
  "baseline_decision_id": "DEC-GLOBAL-001",
  "created_at": "ISO-8601",
  "changed_documents": [
    {
      "document_code": "PRD-...",
      "old_path": "reconciliation/canonical/prds/old-name.md",
      "new_path": "reconciliation/canonical/prds/new-name.md",
      "change_type": "RENAMED",
      "changed_sections": ["Document Control"],
      "change_summary": "Approved normalized title and filename",
      "scope_impact": "NONE",
      "e2e_codes": ["E2E-..."],
      "source_references": ["DOC-...#heading"],
      "decision_ids": ["DEC-..."]
    }
  ],
  "documents": [
    {
      "document_code": "PRD-...",
      "path": "reconciliation/canonical/prds/PRD-....md",
      "sha256": "...",
      "source_document_ids": ["DOC-..."]
    }
  ],
  "e2e_contexts": [
    {
      "e2e_code": "E2E-...",
      "path": "reconciliation/canonical/e2e/E2E-....md",
      "sha256": "..."
    }
  ],
  "decision_ids": ["DEC-..."]
}
```

The manifest records changed documents and the complete active canonical inventory. Unchanged files remain in `documents` or `e2e_contexts` with their checksums, but appear in `changed_documents` only when they differ from the previous tag.

Do not store the current release commit SHA in this manifest. Resolve it from the annotated tag after release.

## Document Selection Fields

`document-selection.csv` is not an owner-worklist checklist. Do not create a
row merely because an eligible PRD belongs to the selected owner domain.
Automatic membership is represented by the active inventory and exposed at
runtime as `worklist_status=OWNER_WORKLIST`.

Use selection rows only for historical compatibility or an exceptional,
explicit user decision about a related document, source representation, or
promotion. They are not required before owner PRDs can be read or scanned.

Use these CSV columns:

```text
selection_id,e2e_code,document_id,original_title,original_path,content_id,proposed_document_code,proposed_title,relationship_role,evidence_type,evidence_reference,selection_status,decision_id,notes
```

Do not overwrite candidate evidence after a take-off decision.
Create selection rows only for eligible original `.md` PRDs beneath
`source/original/PRD/PRD Generator (.md)/`. Do not create rows for the Copy
folder, other original-source folders, `menu-flow`, the three declared
supporting Markdown artifacts, Mermaid, PDF, DOCX, Graphify,
generated/canonical files, or user-added references.

## Context Trace Fields

Use these CSV columns:

```text
trace_id,e2e_code,stage_code,from_document_id,to_document_id,relationship_role,input_or_trigger,output_or_result,logical_entity,identifier,status_or_condition,evidence_type,evidence_reference,approval_status,decision_id,notes
```

Leave unknown values empty and create a defect. Do not infer values to make the row complete.

## User-Added Reference Fields

Use these CSV columns:

```text
reference_id,session_id,original_filename,original_path,stored_path,sha256,supplied_by,added_at,proposed_e2e_codes,format_scan_status,relationship_scan_status,decision_id,notes
```

- If the document already exists in the repository, record its path without duplicating it.
- If the user uploads an external document, preserve it under the session `references/` directory.
- Re-run format, relationship, domain-placement, and defect scans after registration.
- Treat registered references as supporting evidence only. They cannot be
  selected, promoted, or assigned a canonical document code as reconciliation
  source documents.
- Use registered references only to support reasoning, discovery, gap detection,
  and user questions. They cannot establish source facts or override an eligible
  primary PRD.

## Defect Register Fields

Use these CSV columns:

```text
defect_id,e2e_code,document_ids,defect_type,summary,evidence_references,affected_flow_or_data,impact,decision_question,status,resolution_decision_id,notes
```

Valid status values:

```text
OPEN,AWAITING_USER_DECISION,RESOLVED_BY_SOURCE_FACT,RESOLVED_BY_DECISION,ACCEPTED_AS_IS,NOT_A_DEFECT
```

`RESOLVED_BY_SOURCE_FACT` requires eligible source-explicit evidence, verified
canonical payloads, `NO_CONFLICT_IDENTIFIED`, an exact evidence reference, and
an empty `resolution_decision_id`. It closes only the traced gap; it never
authorizes a semantic rewrite or repository release.

## Decision Register Fields

Use these CSV columns:

```text
decision_id,e2e_code,decision_type,question,options,user_decision,rationale,affected_documents,affected_traces,requested_at,decided_at,status
```

Valid decision types include:

```text
E2E_SELECTION,DOCUMENT_INCLUDE,DOCUMENT_TAKE_OFF,DOCUMENT_ROLE,DOCUMENT_RENAME,DOCUMENT_CODE,DOMAIN_PLACEMENT,RELATION_CONFIRMATION,INTERVIEW_ANSWER,ANSWER_CORRELATION,GAP_CLOSURE,GAP_RESOLUTION,CONFLICT_RESOLUTION,BASELINE_APPROVAL,USER_OVERRIDE
```

`E2E_SELECTION`, `DOCUMENT_INCLUDE`, `DOCUMENT_TAKE_OFF`, `DOCUMENT_ROLE`, and
`DOMAIN_PLACEMENT` may exist in historical artifacts, but the normal guided
flow must not generate them for automatic domain or owner-worklist routing.

Only a row with `status=USER_CONFIRMED` may introduce a semantic choice. A
deterministic `RESOLVED_BY_SOURCE_FACT` trace may enrich canonical E2E context
without a decision row when it passes the automatic source-fact gate.

## Interview Register Fields

Use these CSV columns:

```text
question_id,e2e_code,defect_ids,document_ids,flow_or_handoff,question,why_needed,asked_at,status,user_answer,answered_at,answer_evidence,notes
```

Valid statuses:

```text
PENDING,ANSWERED,SKIPPED_BY_USER,DEFERRED,UNKNOWN,CANDIDATE_FROM_RELATED_ANSWER,CONFIRMED_RESOLVED,ACCEPTED_OPEN
```

Keep skipped questions in the register. Do not replace the original row when a later answer may apply.

## Answer Correlation Fields

Use these CSV columns:

```text
correlation_id,source_question_id,source_answer_reference,target_question_id,target_defect_ids,correlation_basis,supporting_evidence,contradicting_evidence,proposed_resolution_options,recommended_option,recommendation_reason,scope_impact,data_integrity_impact,user_confirmation,status,decision_id,notes
```

Valid statuses:

```text
CANDIDATE,AWAITING_USER_CONFIRMATION,CONFIRMED,REJECTED,DEFERRED
```

Create one row per target question so a single answer can be accepted for one gap and rejected for another.

## Provenance Block

Every promoted PRD must record:

- canonical document code, path, version, and generated checksum;
- original document ID;
- original content ID or checksum;
- original title and path;
- promotion decision ID;
- rename/code decision ID when applicable;
- every other eligible primary PRD used for `CROSS_SOURCE_FACT`;
- every non-primary source consulted for supporting reasoning, clearly labeled as non-authoritative;
- global repository version such as `v0.0.2` or `UNRELEASED`;
- baseline Git commit or `UNCOMMITTED`;
- baseline status.

## Identifier Rules

Use stable, non-recycled identifiers:

```text
REC-<E2E>-<NNN>   reconciliation session
SEL-<E2E>-<NNN>   document selection
TRC-<E2E>-<NNN>   context trace
DEF-<E2E>-<NNN>   defect
DEC-<E2E>-<NNN>   user decision
```

Do not renumber existing identifiers after they have been referenced.
