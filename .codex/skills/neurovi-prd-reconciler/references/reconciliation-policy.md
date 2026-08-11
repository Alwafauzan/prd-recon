# Neurovi PRD Reconciliation Policy

## Purpose

Preserve the functional scope and meaning of original PRDs while making their E2E context, logical data flow, cases, conditions, gaps, defects, and user decisions traceable.

## Authority Order

Use this precedence order:

1. Facts stated in `source/original/`.
2. Explicit facts stated in another identified source document.
3. User decisions recorded with a decision identifier.
4. Mechanical discovery evidence.

Mechanical discovery evidence never becomes a fact without user confirmation.

## Hard Invariants

- Never edit `source/original/`.
- Never remove a source claim from the preserved baseline.
- Never add a requirement from general SIMRS knowledge.
- Never repair an ambiguity by guessing.
- Never expand scope because a related document was discovered.
- Never convert a technical recommendation into a PRD requirement.
- Never treat a renamed file as a changed requirement.
- Never hide an excluded candidate; retain the decision and reason.
- Never use Graphify as source truth.
- Never describe a candidate relationship as confirmed.
- Never create independent PRD or E2E release versions; use the approved global repository version.
- Never move or overwrite an existing global baseline tag.

## Allowed Enrichment

The reconciled PRD may become more complete only through:

- preserved facts moved into a consistent structure;
- explicit facts linked from identified documents;
- confirmed user decisions;
- provenance and traceability metadata;
- visible gap, ambiguity, conflict, and defect records;
- logical upstream/downstream context that does not expand scope.

## Evidence Labels

Use one of these labels for every reconciled item:

- `SOURCE_FACT`: explicit in the primary source document.
- `CROSS_SOURCE_FACT`: explicit in another identified source document.
- `USER_CONFIRMED`: introduced or resolved by a recorded user decision.
- `MECHANICAL_CANDIDATE`: discovered by filename, token, flow, or generated correlation.
- `GAP`: not defined by available sources.
- `AMBIGUOUS`: supports more than one interpretation.
- `CONFLICT`: contradicts another identified statement.
- `EXCLUDED`: reviewed and deliberately kept outside the relationship or scope.

Do not place `MECHANICAL_CANDIDATE`, `GAP`, `AMBIGUOUS`, or `CONFLICT` text inside the preserved baseline as if it were an approved requirement.

## Document Relationship Roles

- `PRIMARY_SCOPE`: document defines the work being performed.
- `UPSTREAM`: provides a trigger, prerequisite, or input.
- `DOWNSTREAM`: consumes an output or continues the flow.
- `INTEGRATION`: defines a shared handoff or boundary.
- `CONTEXT`: provides understanding but no work scope.
- `SHARED_CROSS_E2E`: participates in more than one E2E with a separately stated role.
- `EXCLUDED`: reviewed but intentionally not associated.

## Document Selection Statuses

- `PROPOSED_INCLUDE`
- `CONFIRMED_INCLUDE`
- `CONTEXT_ONLY`
- `TAKE_OFF`
- `DEFERRED`

Only `CONFIRMED_INCLUDE` and `CONTEXT_ONLY` may enter an approved E2E context package. `CONTEXT_ONLY` must not create implementation scope.

## Reconciliation Statuses

- `DISCOVERED`
- `SELECTED_FOR_REVIEW`
- `FORMAT_SCANNED`
- `DEFECT_IDENTIFIED`
- `AWAITING_USER_DECISION`
- `USER_CONFIRMED`
- `RECONCILED`
- `BASELINED`

## Defect Types

- `MISSING_INPUT`
- `MISSING_OUTPUT`
- `BROKEN_HANDOFF`
- `UNDEFINED_DATA_OWNER`
- `UNDEFINED_STATUS_TRANSITION`
- `MISSING_CASE_OR_CONDITION`
- `CONFLICTING_BUSINESS_RULE`
- `IDENTIFIER_MISMATCH`
- `ORPHAN_DATA_OUTPUT`
- `AMBIGUOUS_SCOPE`
- `CROSS_DOCUMENT_CONFLICT`
- `FORMAT_INCONSISTENCY`
- `UNTRACED_STATEMENT`

A defect must cite evidence and ask a neutral question. A defect must not contain an assumed resolution.

## Interview Policy

- Allow the user to skip, defer, or answer `UNKNOWN` for every reconciliation question.
- Do not block unrelated questions because an earlier question was skipped.
- Preserve the skipped question, affected defect, and reason when supplied.
- Treat a later answer as a possible correlation, not an automatic answer to earlier questions.
- Cite the exact answer and explain why it may apply to each target gap.
- Require user confirmation before marking a correlated gap resolved.
- Allow the user to reject or narrow a proposed correlation without changing the original answer.
- Do not repeatedly ask a skipped question unless new evidence exists, the user requests it, or baseline readiness requires an explicit disposition.

Use these interview statuses:

- `PENDING`
- `ANSWERED`
- `SKIPPED_BY_USER`
- `DEFERRED`
- `UNKNOWN`
- `CANDIDATE_FROM_RELATED_ANSWER`
- `CONFIRMED_RESOLVED`
- `ACCEPTED_OPEN`

## Gap Closure Recommendations

Recommendations help the user decide; they do not establish requirements.

Each recommendation must include:

- the cited gap or broken handoff;
- two or three options when evidence supports meaningful alternatives;
- the `KEEP_GAP_OPEN` option when evidence is insufficient;
- flow continuity impact;
- logical data integrity impact;
- primary-scope impact;
- supporting and contradicting evidence;
- tradeoffs and unresolved uncertainty;
- one clearly labeled `PROPOSED_RESOLUTION` with rationale.

Do not recommend technical implementation details that belong to Designer, Developer, or QA. Do not present a best-practice assumption as a source fact. A selected option requires a decision ID before changing the baseline.

## Rename Policy

Renaming is for consistent navigation only.

- Preserve the original filename and title in provenance.
- Rename only a derived promoted document.
- Propose, then request user approval.
- Prefer a stable document code plus a clear functional title.
- Do not use a rename to merge distinct scopes.
- Do not split a source PRD without a user decision.
- Do not merge source PRDs without a user decision.

Suggested code pattern:

```text
PRD-<DOMAIN>-<CAPABILITY>-<NNN>
```

The pattern is optional. The user controls the final code and title.

## Domain Recommendation Rules

Evaluate domain relevance using cited evidence:

1. Explicit placement in a source process or flow.
2. Confirmed stage input/output relationship.
3. Shared business trigger, actor, entity, or lifecycle.
4. Confirmed upstream/downstream dependency.
5. Filename or token similarity.

Treat items 1-2 as strong evidence, 3-4 as contextual evidence, and item 5 as weak discovery evidence.

Warn the user when:

- no stage can explain the document's role;
- no input/output or business dependency connects it;
- placement contradicts an approved primary scope;
- inclusion requires new requirements or technical improvisation;
- the recommendation relies only on title similarity.

The user makes the final decision. Record an accepted warning as `USER_OVERRIDE` with the rationale; do not keep arguing after the user provides a sufficiently relevant reason.

## Technical Boundary

The PRD baseline describes functional behavior, logical data movement, cases, conditions, and business constraints. Do not introduce database design, API shape, UI component design, code architecture, or test implementation unless stated by the source or approved as a PRD decision.

Designer, developer, and QA outputs are separate derived artifacts. They consume the same approved E2E context and must trace back to the PRD baseline.

## Version Authority

Use the annotated global Git tag and its commit as the version authority for all reconciled documents. Use document codes, source content IDs, and checksums for document identity and change detection, not independent release numbers.

Creating a global baseline requires an explicit `BASELINE_APPROVAL` decision. Draft commits, mechanical inventory regeneration, scans, and unresolved review sessions do not establish a released version.
