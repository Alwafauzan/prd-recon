# Neurovi Gap Scanner Taxonomy

## Evidence Classes

- `USER_CONFIRMED_GAP`: recorded in a reconciliation defect or interview register.
- `SOURCE_EXPLICIT_GAP`: the source explicitly states an unresolved item.
- `MECHANICAL_GAP_CANDIDATE`: inferred only from missing structure, mappings, traces, or literal markers.

Only the first two may be described as known gaps. Mechanical findings require review.

## E2E Gap Types

- `UNCONFIRMED_E2E_BOUNDARY`: the E2E still comes from an unapproved source-flow candidate.
- `NO_EXPLICIT_DOCUMENT_MEMBERSHIP`: no source-explicit document membership is attached.
- `NO_CONFIRMED_DOCUMENT_SELECTION`: no user-confirmed include/context selection exists.
- `FLOW_NODE_WITHOUT_DOCUMENT_CANDIDATE`: a source flow node has no mechanical document candidate.
- `MECHANICAL_CANDIDATES_UNREVIEWED`: document candidates exist but have not been reviewed.
- `NO_CONFIRMED_CONTEXT_TRACE`: no confirmed stage/document handoff trace exists.
- `DUPLICATE_CONTENT_REVIEW_REQUIRED`: multiple related document IDs share one content ID.
- `OPEN_RECONCILIATION_DEFECT`: an open confirmed defect exists.
- `SKIPPED_OR_DEFERRED_QUESTION`: an interview question remains unresolved.

## Cross-Document Gap Types

- `BROKEN_OR_UNTRACED_HANDOFF`
- `UNMAPPED_HANDOFF_ENDPOINT`: one side of a source-flow edge has no document candidate.
- `UNCONFIRMED_DOCUMENT_HANDOFF`: both sides have document candidates but no approved context trace.
- `UNDEFINED_INPUT_OUTPUT`
- `UNDEFINED_DATA_OWNER`
- `IDENTIFIER_OR_STATUS_NOT_TRACED`
- `RELATIONSHIP_UNCONFIRMED`
- `CONFLICTING_CONTEXT_CANDIDATE`
- `SOURCE_REPRESENTATION_AMBIGUOUS`

Report these only as confirmed when a register or explicit source supports them. Otherwise use `MECHANICAL_GAP_CANDIDATE`.

## Document Context Families

- `PURPOSE_BACKGROUND`
- `SCOPE`
- `OUT_OF_SCOPE`
- `ACTORS_STAKEHOLDERS`
- `TRIGGER_PRECONDITIONS`
- `MAIN_FLOW`
- `ALTERNATE_FLOW`
- `ERROR_EXCEPTION`
- `CASES_CONDITIONS`
- `BUSINESS_RULES`
- `LOGICAL_DATA_FLOW`
- `STATUS_LIFECYCLE`
- `DEPENDENCIES_INTEGRATION`
- `ACCEPTANCE_CRITERIA`

A missing family is a structure/context candidate. The original PRD may express the information in prose or a nonstandard section.

## Severity

- `HIGH`: confirmed defect, explicit unresolved marker affecting flow/data, or unconfirmed primary process boundary.
- `MEDIUM`: missing confirmed handoff, membership, cases, conditions, data, or status context.
- `LOW`: format inconsistency, naming inconsistency, or unreviewed weak correlation.

Severity is for review prioritization only. It does not authorize a change.

## Resolution Boundary

The scanner identifies and maps. `$neurovi-prd-reconciler` interviews the user, correlates answers, recommends gap-closure options, records decisions, and changes derived baselines after approval.
