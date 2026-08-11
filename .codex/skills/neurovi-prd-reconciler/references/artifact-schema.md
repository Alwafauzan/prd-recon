# Reconciliation Artifact Schema

## Workspace Layout

Create a workspace only after the user selects an E2E:

```text
reconciliation/workspaces/<e2e-code>/
├── session.json
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

Store only one active canonical copy of each approved document and E2E context:

```text
reconciliation/canonical/
├── prds/
│   └── <document-code>-<normalized-title>.md
└── e2e/
    └── <e2e-code>-<normalized-title>.md
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
  "e2e_selection_status": "USER_CONFIRMED",
  "started_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "source_inventory_version": "...",
  "base_global_version": "v0.0.1-or-UNRELEASED",
  "base_git_commit": "commit-or-UNCOMMITTED",
  "status": "SELECTED_FOR_REVIEW"
}
```

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

Use these CSV columns:

```text
selection_id,e2e_code,document_id,original_title,original_path,content_id,proposed_document_code,proposed_title,relationship_role,evidence_type,evidence_reference,selection_status,decision_id,notes
```

Do not overwrite candidate evidence after a take-off decision.

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
- Do not assign a canonical document code until the user confirms promotion.

## Defect Register Fields

Use these CSV columns:

```text
defect_id,e2e_code,document_ids,defect_type,summary,evidence_references,affected_flow_or_data,impact,decision_question,status,resolution_decision_id,notes
```

Valid status values:

```text
OPEN,AWAITING_USER_DECISION,RESOLVED_BY_DECISION,ACCEPTED_AS_IS,NOT_A_DEFECT
```

## Decision Register Fields

Use these CSV columns:

```text
decision_id,e2e_code,decision_type,question,options,user_decision,rationale,affected_documents,affected_traces,requested_at,decided_at,status
```

Valid decision types include:

```text
E2E_SELECTION,DOCUMENT_INCLUDE,DOCUMENT_TAKE_OFF,DOCUMENT_ROLE,DOCUMENT_RENAME,DOCUMENT_CODE,DOMAIN_PLACEMENT,RELATION_CONFIRMATION,INTERVIEW_ANSWER,ANSWER_CORRELATION,GAP_CLOSURE,GAP_RESOLUTION,CONFLICT_RESOLUTION,BASELINE_APPROVAL,USER_OVERRIDE
```

Only a row with `status=USER_CONFIRMED` may change a baseline.

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

- original document ID;
- original content ID or checksum;
- original title and path;
- promotion decision ID;
- rename/code decision ID when applicable;
- every cross-source document used;
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
