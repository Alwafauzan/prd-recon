---
name: neurovi-prd-reconciler
description: Reconcile Neurovi SIMRS PRDs under explicit user control using an E2E code or name. Use when selecting an E2E process, interviewing users about flow gaps with skippable questions, correlating later answers to deferred gaps, recommending controlled gap-closure options, promoting or consistently renaming original PRDs, validating include or take-off decisions, adding reference documents, normalizing inconsistent PRD formats without changing source facts or scope, tracing cross-document and cross-E2E context, detecting defects, recommending a more relevant domain, warning about illogical placement, or creating a user-approved global Git baseline for all documents.
---

# Neurovi PRD Reconciler

## Operating Contract

Treat this skill as a controlled reconciliation workflow, not a PRD authoring workflow.

1. Read the tools `AGENTS.md` and `neurovi-prd/AGENTS.md`, then obey both.
2. Read `references/reconciliation-policy.md`, `references/artifact-schema.md`, and `references/git-versioning-policy.md` completely before changing reconciliation artifacts or Git baselines.
3. Never edit `source/original/`.
4. Preserve every source fact, case, condition, rule, and scope boundary exactly in meaning.
5. Never add, remove, correct, or improvise a requirement without an explicit user decision.
6. Keep technical implementation details in downstream division artifacts unless they already exist in the source PRD.
7. Treat Mermaid flows, token matches, Graphify links, and generated correlations as discovery evidence only.
8. Stop at each approval gate and ask the user to decide. Do not silently promote a candidate to confirmed status.

## Inspect the Inventory

Use the bundled read-only inspector instead of reconstructing inventory queries repeatedly:

```bash
python3 .codex/skills/neurovi-prd-reconciler/scripts/inspect_inventory.py --repo neurovi-prd list-e2e
python3 .codex/skills/neurovi-prd-reconciler/scripts/inspect_inventory.py --repo neurovi-prd show-e2e --e2e E2E-ADM-01
python3 .codex/skills/neurovi-prd-reconciler/scripts/inspect_inventory.py --repo neurovi-prd find-document --query "pendaftaran rawat jalan"
python3 .codex/skills/neurovi-prd-reconciler/scripts/inspect_inventory.py --repo neurovi-prd scan-format --document DOC-XXXXXXXXXXXXXXX
python3 .codex/skills/neurovi-prd-reconciler/scripts/version_diff.py --repo neurovi-prd list
python3 .codex/skills/neurovi-prd-reconciler/scripts/version_diff.py --repo neurovi-prd compare --from v0.0.1 --to v0.0.2
```

Change `--repo` only when the document repository is mounted elsewhere. Add
`--json` for machine-readable output.

## Reconciliation Workflow

### 1. Resolve the E2E

Accept an E2E code or name from the user. Resolve it against `reconciliation/e2e-inventory/e2e-domain-inventory.json`.

- Use an exact code match first, then an exact case-insensitive title match.
- Show possible matches and ask the user when the name is ambiguous.
- Never create an E2E merely because the user gave an example.
- Label source-flow E2Es as candidates until the user confirms their boundary.

### 2. Build the Document Review Queue

Collect documents from these evidence classes without merging their status:

1. Source flow document.
2. Explicit source-path membership.
3. Previously user-confirmed membership.
4. Mechanical candidates.
5. User-added references.

Present each document with its `document_id`, title, source path, content duplicate information, evidence, proposed relationship, and current approval status. Never describe a mechanical candidate as being inside the E2E.

### 3. Run the User Selection Gate

Ask the user to decide each proposed document as one of:

- `CONFIRMED_INCLUDE`
- `CONTEXT_ONLY`
- `TAKE_OFF`
- `DEFERRED`

Record `TAKE_OFF` as an auditable exclusion; do not delete the source or erase its discovery evidence. Allow the user to add a new reference at this gate.

### 4. Promote Without Mutating the Original

Interpret promotion as creating a derived working copy, never moving or editing the original.

- Preserve the original `document_id`, path, title, checksum, and source headings in provenance.
- Propose a normalized filename and optional document code only for the derived document.
- Use `PRD-<DOMAIN>-<CAPABILITY>-<NNN>` only as a proposal; require user confirmation before assigning it.
- Limit rename changes to filename, canonical heading, and document code. Do not change scope or meaning.
- Keep exact-content duplicates visible and ask which source representation should be promoted.

Use `assets/reconciled-prd-template.md` for the promoted document and `assets/review-session-template.md` for the approval session.

### 5. Reconcile the Format

Normalize structure while preserving content.

- Move or quote source-backed content into consistent sections with trace references.
- Keep source wording when paraphrasing could alter meaning.
- Mark an absent section as `NOT_DEFINED_IN_SOURCE`; never fill it by inference.
- Keep conflicts, gaps, and proposed resolutions outside the preserved baseline.
- Enumerate cases and conditions only when supported by a source or confirmed decision.
- Describe data flow logically. Do not invent tables, endpoints, payloads, components, or test implementation.

### 6. Trace E2E and Cross-Document Context

Build `e2e-context.md` from confirmed relationships using `assets/e2e-context-template.md`.

- Link upstream and downstream stages without absorbing their work into the primary PRD scope.
- Record logical input, output, identifier, status, owner, handoff, and consuming document when explicit.
- Allow one document to relate to multiple E2Es with separate relationship roles.
- Distinguish `PRIMARY_SCOPE`, `UPSTREAM`, `DOWNSTREAM`, `INTEGRATION`, `CONTEXT`, and `SHARED_CROSS_E2E`.
- Never use cross-E2E context to expand a document's primary scope.

### 7. Scan for Defects and Gaps

Scan all confirmed documents and their handoffs. Create a defect only when evidence can be cited.

Detect missing input/output, broken handoff, undefined data owner, undefined status transition, missing case or condition, conflicting rule, identifier mismatch, orphan output, ambiguous scope, and cross-document conflict.

For every defect, record source evidence, affected documents and E2Es, impact, and a neutral decision question. Do not resolve it automatically.

### 8. Run a Skippable Reconciliation Interview

Use `assets/interview-session-template.md` to interview the user about open gaps and broken flow handoffs.

- Ask one focused question at a time and explain why the answer matters.
- Always allow `SKIP`, `DEFER`, or `UNKNOWN`; never force an answer to continue the interview.
- Preserve skipped questions with status `SKIPPED_BY_USER` and continue to other answerable questions.
- When a later answer may address a skipped question or another gap, create `CANDIDATE_FROM_RELATED_ANSWER` with the source answer, target gaps, correlation basis, and confidence explanation.
- Show the correlation to the user and ask for confirmation. Never convert it to a requirement or close a defect automatically.
- Allow one answer to correlate to multiple questions or defects, but record every target link separately.
- Revisit skipped questions only when new evidence exists, at the user's request, or during baseline readiness review.

For each unresolved flow gap, present controlled resolution options:

1. Describe the current broken or undefined handoff using cited evidence.
2. Provide two or three functional resolution options when sufficient context exists.
3. Explain flow continuity, logical data integrity, scope impact, supporting evidence, tradeoffs, and remaining uncertainty for each option.
4. Recommend one option with a concise reason, labeled `PROPOSED_RESOLUTION`.
5. Include `KEEP_GAP_OPEN` when available evidence is insufficient.
6. Ask the user to confirm, modify, reject, defer, or skip the recommendation.

Do not introduce API, database, UI, code, or testing implementation in a gap-closure recommendation unless the source already defines it. A recommendation becomes baseline content only through a `USER_CONFIRMED` decision.

### 9. Handle New References and Domain Recommendations

When the user adds a document:

1. Preserve an uploaded file under the session `references/` directory, or record its existing repository path; do not place it in `source/original/`.
2. Rescan its title, headings, source facts, format, candidate E2Es, and cross-document relationships.
3. Re-run the affected E2E review queue and defect scan.
4. Recommend another domain when explicit flow position, data handoff, actors, or scope boundaries fit better.
5. Explain supporting and contradicting evidence.
6. Warn when the selected domain has no logical stage or data relationship, conflicts with confirmed scope, or requires scope improvisation.
7. Accept a relevant user decision as final and record it. If the user overrides a warning, preserve the override and rationale as a decision.

### 10. Apply Decisions and Baseline

Apply only decisions marked `USER_CONFIRMED`.

- Trace every changed statement, relationship, name, or code to a source or `decision_id`.
- Keep unresolved defects visible.
- Keep skipped questions visible unless the user confirms a later-answer correlation or explicitly accepts the gap as open.
- Do not mark an E2E or PRD `BASELINED` while unapproved content is mixed into the preserved baseline.
- Generate role context from the same approved E2E package; do not add role-specific technical decisions to the PRD baseline.
- Update global manual E2E registers only from confirmed decisions, preserve unrelated rows, then regenerate derived inventory outputs.
- Use one global Git version for the complete repository. Do not assign independent semantic versions to PRDs or E2Es.
- Propose a global version bump and annotated tag only after all included changes receive `BASELINE_APPROVAL`.
- Generate a release manifest and `changes.md` that identify every changed document and the source-backed or decision-backed reason for each change.
- Use Git diff for mechanical file changes and decision registers for semantic change descriptions. Never invent a semantic summary from the diff alone.
- Never create, move, replace, or force-update a baseline tag without explicit user approval.

After regeneration, run:

```bash
python3 scripts/build_structure.py validate --source neurovi-prd/source/original --target neurovi-prd
```

Report the selected E2E, included and excluded documents, rename proposals, format changes, defects, decisions required, cross-E2E relations, proposed global Git version, documents changed from the previous version, and validation result.

## Usage Reference

Read `references/usage-guide.md` when the user asks how to invoke or operate the skill. Use `references/artifact-schema.md` for fields and folder layout. Use `references/git-versioning-policy.md` for global version and tag rules. Do not treat illustrative examples in the guide as repository facts.
