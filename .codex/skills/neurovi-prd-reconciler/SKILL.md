---
name: neurovi-prd-reconciler
description: "Reconcile Neurovi SIMRS PRDs under explicit user control using one of two separate modes: main-flow gap closure or detailed business-case gap closure for an E2E code or name. Use when selecting an E2E process, automatically consuming its owner-domain PRD worklist, interviewing users about main-flow or detailed business-case gaps with skippable questions, correlating later answers to deferred gaps, recommending controlled gap-closure options, preserving source facts, tracing cross-document and cross-E2E context, detecting defects, or preparing user-approved reconciliation artifacts."
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
8. Reconciliation reads eligible PRDs through the verified canonical baseline in `reconciliation/canonical/`. Bootstrap version `v0.0.0` contains one canonical PRD per eligible unique source payload and one E2E context per active domain. Before use, require the manifest inventory checksum, `content_id`, original path, original SHA-256, generated SHA-256, payload length, and preserved payload bytes to match the eligible `.md` source beneath `source/original/PRD/PRD Generator (.md)/`; stop when any check fails.
9. Keep the matched eligible original PRD as the source-fact authority. Canonical v0 supplies the stable code, normalized wrapper, section map, provenance, and complete byte-identical source payload; it does not gain independent source authority or permit a semantic change. Later canonical versions may change meaning only through source-backed content or explicit user-confirmed decisions.
10. Exclude `PRD Generator (.md) - Copy`, `menu-flow`, `KONTEKS-SESI.md`, `Integrasi/Api Doc/APLICARES-KETERSEDIAAN KAMAR.md`, and `Pelayanan (.md)/ringkasan-merge-prd-rj.md` from the primary source set.
11. Treat every other file or repository, including PDF, DOCX, Mermaid, Graphify, unverified generated documents, and user-added references, as reasoning support only. It may guide discovery, relationship hypotheses, gap detection, and questions, but cannot establish source facts, change primary-source facts, or enter the preserved baseline without a separate explicit user decision.
10. Automatically close a gap only when an eligible source fact is explicit, its canonical payload is verified, no conflicting statement is identified, and applying it changes no meaning or scope. Record it as `RESOLVED_BY_SOURCE_FACT` with its source reference and no decision ID.
11. Stop at semantic approval gates that can change reconciled meaning. Owner-domain routing and owner-worklist membership are automatic inventory context, not user decisions and not confirmed source facts.
12. Consume `reconciliation/canonical/automatic-reconciliation.json` as the global deterministic scanner-candidate register. A row may be treated as closed only when it is `RESOLVED_BY_SOURCE_FACT`; `OPEN_SOURCE_EXPLICIT_GAP`, `OPEN_INSUFFICIENT_SOURCE_EVIDENCE`, `EXCLUDED_NON_ACTIVE_SOURCE_EVIDENCE`, and `HUMAN_DECISION_REQUIRED` remain open or excluded exactly as recorded. Never reinterpret an open row as an implicit requirement.

## Inspect the Inventory

Use the bundled read-only inspector instead of reconstructing inventory queries repeatedly:

```bash
python3 .codex/skills/neurovi-prd-reconciler/scripts/inspect_inventory.py --repo neurovi-prd list-e2e
python3 .codex/skills/neurovi-prd-reconciler/scripts/inspect_inventory.py --repo neurovi-prd show-e2e --e2e E2E-RJ
python3 .codex/skills/neurovi-prd-reconciler/scripts/inspect_inventory.py --repo neurovi-prd find-document --query "pendaftaran rawat jalan"
python3 .codex/skills/neurovi-prd-reconciler/scripts/inspect_inventory.py --repo neurovi-prd scan-format --document DOC-XXXXXXXXXXXXXXX
python3 .codex/skills/neurovi-prd-reconciler/scripts/version_diff.py --repo neurovi-prd list
python3 .codex/skills/neurovi-prd-reconciler/scripts/version_diff.py --repo neurovi-prd compare --from v0.0.1 --to v0.0.2
```

Change `--repo` only when the document repository is mounted elsewhere. Add
`--json` for machine-readable output.

## Choose One Reconciliation Mode

Select exactly one mode before opening a session. Never combine scanner findings, questions, audit state, or completion state across modes.

- **Main-flow reconciliation**: consume only the main-flow scan. Resolve trigger, primary sequence, handoff, output, status transition, cross-domain continuation, and conflicts that affect the main E2E flow. Exclude detailed validation, alternate-case, error, exception, and acceptance-criteria questions.
- **Detailed-process reconciliation**: consume only the business-case scan. Resolve scenarios, conditions, business rules, validation, errors, exceptions, and acceptance criteria. Exclude general E2E sequence or handoff questions unless a cited detailed case directly depends on that handoff.

Each mode has its own session ID, workspace, current question, registers, audit events, stop/resume state, and result. A user may have both modes active for the same E2E. Do not ask the user to remember session IDs.

## Reconciliation Workflow

### 1. Resolve the E2E

Accept an E2E domain code or name from the user. Resolve it against `reconciliation/e2e-inventory/domain-worklist.json`.

- Use an exact code match first, then an exact case-insensitive title match.
- Show possible matches and ask the user when the name is ambiguous.
- Never create an E2E merely because the user gave an example.
- Treat the resolved domain as the automatic flow-checking worklist selected by the user. Do not ask the user to confirm the domain boundary or the owner-domain placement of its PRDs.
- Preserve the inventory's assignment evidence and confidence as routing metadata. Automatic routing does not convert a mechanical assignment into a source fact or an approved requirement.

### 2. Build the Automatic Worklist Context

Collect documents from these evidence classes without merging their status:

1. Eligible `.md` PRDs owned by the selected domain worklist.
2. Eligible `.md` PRDs connected through indexed within-domain or cross-domain relations.
3. Previously user-confirmed relationship, conflict, and gap decisions.
4. Eligible `.md` PRD relation candidates marked for reasoning review.
5. User-added references as supporting evidence only.

Load every eligible owner-domain PRD automatically as `OWNER_WORKLIST` with `PRIMARY_SCOPE` routing context. Consume its verified canonical wrapper, stable code, section map, provenance, and complete byte-identical source payload. Use the canonical E2E context as the domain worklist and relationship map, while retaining mechanical relations as candidates. Present its `document_id`, code, title, source path, owner domain, duplicate information, assignment evidence, and relation evidence when useful. Never describe automatic membership or a mechanical relation as user-confirmed.
Never load a Mermaid document, a supporting Markdown artifact, a file outside the exact primary-source folder, a non-`.md` file, an unverified generated file, or a user-added reference as owner-worklist source content.

### 3. Identify Questions That Need a User Decision

Do not ask whether an owner-domain PRD is primary, supporting, unrelated, or deferred. Do not ask the user to confirm the selected domain.

Ask only when cited evidence exposes a functional or semantic issue that the sources cannot settle, such as:

- a conflicting business rule or source statement;
- a broken or undefined handoff between named documents or process stages;
- missing input, output, owner, identifier, status transition, case, or condition that affects flow continuity;
- an ambiguous scope decision that could change reconciled meaning;
- an exact-content duplicate whose source representation must be chosen before promotion.

Each question must name the affected document titles or handoff, state the cited issue in plain Indonesian, explain why an answer is needed, and avoid asking for inventory classification. Allow the user to add a new reference when it may supply missing context.

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

Scan only the defect families permitted by the selected reconciliation mode. Use relevant owner and related PRDs for source context, but consume only the matching scanner output. Create a defect only when evidence can be cited.

Detect missing input/output, broken handoff, undefined data owner, undefined status transition, missing case or condition, conflicting rule, identifier mismatch, orphan output, ambiguous scope, and cross-document conflict.

For every defect, record source evidence, affected documents and E2Es, and impact. Resolve it automatically only through the strict source-fact gate above. Otherwise record a neutral decision question and leave it open.

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
2. Rescan its title, headings, explicit statements, format, candidate E2Es, and cross-document relationships for reasoning support; do not label its statements as source facts.
3. Re-run the affected E2E worklist and defect scan.
4. Recommend another domain when explicit flow position, data handoff, actors, or scope boundaries fit better.
5. Explain supporting and contradicting evidence.
6. Warn when the selected domain has no logical stage or data relationship, conflicts with confirmed scope, or requires scope improvisation.
7. Accept a relevant user decision as final and record it. If the user overrides a warning, preserve the override and rationale as a decision.

### 10. Apply Decisions and Baseline

Apply only decisions marked `USER_CONFIRMED`.

- Trace every changed statement, relationship, name, or code to an eligible primary PRD or `decision_id`.
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

Report the selected E2E, automatic owner-worklist documents, related context documents, rename proposals, format changes, defects, decisions required, cross-E2E relations, proposed global Git version, documents changed from the previous version, and validation result.

## Usage Reference

Read `references/usage-guide.md` when the user asks how to invoke or operate the skill. Use `references/artifact-schema.md` for fields and folder layout. Use `references/git-versioning-policy.md` for global version and tag rules. Do not treat illustrative examples in the guide as repository facts.
