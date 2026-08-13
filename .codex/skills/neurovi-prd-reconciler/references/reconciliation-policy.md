# Neurovi PRD Reconciliation Policy

## Purpose

Preserve the functional scope and meaning of original PRDs while making their E2E context, logical data flow, cases, conditions, gaps, defects, and user decisions traceable.

## Authority Order

Use this precedence order:

1. Facts stated in an eligible `.md` PRD beneath `source/original/PRD/PRD Generator (.md)/`.
2. Explicit facts stated in another eligible `.md` PRD from that same primary-source folder.
3. User decisions recorded with a decision identifier.
4. Supporting reasoning and mechanical discovery evidence.

Supporting or mechanical evidence never becomes a source fact. It may guide
reasoning, discovery, relationship hypotheses, gap detection, and questions;
adding any resulting claim requires an explicit user decision.

## Canonical Baseline Consumption

Use `reconciliation/canonical/manifest.json`, its generated PRDs, and its E2E
contexts as the baseline consumed by reconciliation. Bootstrap version `v0.0.0`
is the initial canonical baseline and is accepted only
when all of the following match the eligible original Markdown PRD:

- active E2E inventory checksum;
- `document_id`, `content_id`, original path, and source SHA-256;
- generated canonical SHA-256, recorded payload offset, and payload length;
- every preserved payload byte and the exact generated file boundary.

Fail closed when the baseline is missing, stale, malformed, or modified. The
matched file under `source/original/PRD/PRD Generator (.md)/` remains the source
truth and source-fact authority. Canonical v0 contributes stable document code,
normalized wrapper, section navigation, provenance, and E2E navigation only; it
cannot add, remove, correct, or reinterpret a source claim. Later canonical
versions may change meaning only from eligible source facts or explicit
user-confirmed decisions.

## E2E Domain Worklist

Use `reconciliation/e2e-inventory/domain-worklist.json` as the only active E2E
inventory. Each eligible unique PRD has exactly one owner domain. Related PRDs
may provide within-domain or cross-domain context through indexed relations,
but the relation neither duplicates ownership nor expands the primary PRD
scope. Mermaid/process-path inventories and the former all-format source-folder
inventory are legacy and must not be consumed.

Owner-domain assignment is automatic routing for the flow-checking worklist.
It does not require a user decision and does not establish a source fact,
relationship fact, or approved requirement. Preserve its assignment basis,
confidence, and review metadata so inventory quality can be improved without
blocking reconciliation. When the user starts a domain, every eligible owner
PRD is available as `OWNER_WORKLIST` source context immediately.

## Hard Invariants

- Never edit `source/original/`.
- Never reconcile from a canonical baseline that has not been verified against the active inventory and immutable original payload.
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
- Never select or reconcile a source document unless its verified canonical baseline maps to an original PRD with the exact `.md` extension beneath `source/original/PRD/PRD Generator (.md)/`.
- Never select anything from `PRD Generator (.md) - Copy`, any other original-source folder, `menu-flow`, or the supporting Markdown artifacts `KONTEKS-SESI.md`, `Integrasi/Api Doc/APLICARES-KETERSEDIAAN KAMAR.md`, and `Pelayanan (.md)/ringkasan-merge-prd-rj.md`.
- Never promote Mermaid, PDF, DOCX, Graphify, generated/canonical documents, supporting Markdown artifacts, or user-added references into the reconciliation source-document set.
- Never use supporting reasoning as `SOURCE_FACT` or `CROSS_SOURCE_FACT`, or let it override facts preserved from an eligible primary PRD.

## Allowed Enrichment

The reconciled PRD may become more complete only through:

- preserved facts moved into a consistent structure;
- explicit facts linked from other eligible primary PRDs;
- confirmed user decisions;
- provenance and traceability metadata;
- visible gap, ambiguity, conflict, and defect records;
- logical upstream/downstream context that does not expand scope.

## Automatic Source-Fact Closure

A reconciliation gap may be closed without a human decision only when all of
the following are true:

- the fact is explicit in an eligible primary Markdown PRD;
- every involved PRD has a verified lossless canonical payload;
- the relation retains an exact source reference;
- the evidence is labeled `SOURCE_FACT` or `CROSS_SOURCE_FACT` and
  `SOURCE_EXPLICIT`;
- no conflict, ambiguity, alternate interpretation, scope choice, or new
  requirement is identified;
- the change records traceable E2E context only and does not rewrite a preserved
  PRD payload.

Record the result as `RESOLVED_BY_SOURCE_FACT`, leave the decision ID empty, and
do not ask the user to confirm it. Any failed condition routes the issue to
`HUMAN_DECISION_REQUIRED`. A source conflict can never be closed automatically.

## Evidence Labels

Use one of these labels for every reconciled item:

- `SOURCE_FACT`: explicit in the primary source document.
- `CROSS_SOURCE_FACT`: explicit in another eligible primary PRD from the exact allowed folder.
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

## Worklist and Relationship Statuses

Use `OWNER_WORKLIST` for automatic owner-domain source context. It is neither
an approval status nor a semantic decision. Do not create a decision or ask the
user to include, exclude, or classify each owner PRD.

The following legacy selection statuses may remain in historical workspaces or
be used for exceptional user-directed relationship or promotion decisions:

- `PROPOSED_INCLUDE`
- `CONFIRMED_INCLUDE`
- `CONTEXT_ONLY`
- `TAKE_OFF`
- `DEFERRED`

These statuses are not prerequisites for owner PRDs to be scanned. Any document
used as a primary reconciliation source remains subject to source eligibility:
it must have a verified lossless canonical baseline whose payload matches an
original `.md` PRD beneath `source/original/PRD/PRD Generator (.md)/`, and it
must not be one of the excluded supporting artifacts. Other sources can be cited
only as reasoning or discovery support and cannot establish baseline facts.

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

A defect must cite evidence. It may be closed as `RESOLVED_BY_SOURCE_FACT` only
under the automatic source-fact gate; otherwise it must ask a neutral question
and must not contain an assumed resolution.

## Interview Policy

- Open exactly one reconciliation mode per session: `MAIN_FLOW` or `BUSINESS_CASES`.
- A main-flow session consumes only main-flow scanner evidence and may address
  trigger, primary sequence, handoff, output, status transition, cross-domain
  continuation, or a conflict that changes the main flow.
- A business-cases session consumes only business-case scanner evidence and may
  address scenarios, conditions, business rules, validation, errors,
  exceptions, or acceptance criteria.
- Do not place both scanner outputs in one model request. Do not carry a current
  question, answer queue, completion state, or audit event from one mode into
  the other mode.
- Allow both modes to be active for the same E2E with independent stop and
  resume controls.
- Never ask the user to confirm a domain boundary, owner-domain placement, or
  whether an owner-worklist PRD is main/supporting/unrelated.
- Ask only about cited functional gaps, conflicts, undefined handoffs, missing
  business context, or other semantic choices that source facts cannot settle.
- Name the affected documents or handoff and explain the concrete consequence
  in plain Indonesian before asking for a decision.
- Allow the user to skip, defer, or answer `UNKNOWN` for every reconciliation question.
- Allow the user to stop the working session at any point without approving a
  baseline, answering the current question, or discarding prior audit history.
- Preserve the active unanswered question when a session is stopped. Stopping
  a session must not convert it to `ANSWERED`, `SKIPPED_BY_USER`, `DEFERRED`,
  `UNKNOWN`, or `USER_CONFIRMED`.
- Treat stopping a working session and publishing a repository baseline as
  separate operations. A stopped session must not create a release, commit,
  tag, or push.
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

Domain recommendations are inventory-maintenance advice, not a normal
reconciliation interview gate. Do not ask the user to validate the current
owner assignment while checking a flow. If the user explicitly requests an
owner-domain change, record the accepted change as `USER_OVERRIDE` with its
rationale; do not keep arguing after the user provides a sufficiently relevant
reason.

## Technical Boundary

The PRD baseline describes functional behavior, logical data movement, cases, conditions, and business constraints. Do not introduce database design, API shape, UI component design, code architecture, or test implementation unless stated by the source or approved as a PRD decision.

Designer, developer, and QA outputs are separate derived artifacts. They consume the same approved E2E context and must trace back to the PRD baseline.

## Version Authority

Use the annotated global Git tag and its commit as the version authority for all reconciled documents. Use document codes, source content IDs, and checksums for document identity and change detection, not independent release numbers.

Creating a global baseline requires an explicit `BASELINE_APPROVAL` decision. Draft commits, mechanical inventory regeneration, scans, and unresolved review sessions do not establish a released version.
