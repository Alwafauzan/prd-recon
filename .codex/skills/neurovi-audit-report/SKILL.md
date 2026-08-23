---
name: neurovi-audit-report
description: "Generate a read-only audit report of the Neurovi PRD repository: domain groups, E2E domains, owned PRDs, scanner gap candidates with their status, and every fix already applied (automatic source-fact closures, user-confirmed decisions, logged defects, session and release history). Produces a plain-language summary for non-technical readers (PM/PO) plus full technical detail for the auditor. Use when a PO, PM, or auditor asks for a full per-group per-flow report of gaps and what has been resolved."
---

# Neurovi Audit Report

## Contract

1. Read the tools `AGENTS.md` and `neurovi-prd/AGENTS.md`, then obey both.
2. This skill is strictly read-only. Never edit `source/original/`, the E2E
   inventory, canonical artifacts, session registers, or Git state.
3. Report recorded facts only. Scanner candidates remain mechanical review
   candidates; never present them as proven semantic defects or approved
   requirements.
4. Separate the two fix classes and never merge them:
   - `RESOLVED_BY_SOURCE_FACT`: closed automatically from an explicit eligible
     source fact, with an empty decision ID.
   - `USER_CONFIRMED` decisions and `RESOLVED_BY_DECISION` defects: closed
     through a recorded human decision inside a reconciliation session.
5. An empty or missing session workspace means no human reconciliation has been
   recorded. State that plainly; do not imply progress from scanner output.
6. Release history comes only from `reconciliation/releases/` and annotated
   global tags. Working commits are `UNRELEASED`.
7. The report may cross-reference an open scanner candidate against confirmed
   decisions recorded on the *same document* to flag it as "possibly already
   addressed, needs verification." This is a document-level heuristic, not a
   literal 1:1 match — the scanner register's `resolution_decision_id` field is
   never populated by this skill (that would require the skill to write to
   canonical data, which contract #2 forbids). Always label the cross-reference
   as indicative, never as proof a specific gap is closed.
8. A session `status` of `AWAITING_USER_DECISION` or `SELECTED_FOR_REVIEW`
   means the session is not finished, even if every individual decision inside
   it is `USER_CONFIRMED`. Only `RECONCILED`/`BASELINED` counts as done. Report
   this distinction plainly — do not let a fully-decided-but-unclosed session
   read as "not started" (undercounts progress) or as "finished" (overstates
   it).

## Run the Report

```bash
python3 .codex/skills/neurovi-audit-report/scripts/audit_report.py --repo neurovi-prd
python3 .codex/skills/neurovi-audit-report/scripts/audit_report.py --repo neurovi-prd --e2e E2E-RJ
python3 .codex/skills/neurovi-audit-report/scripts/audit_report.py --repo neurovi-prd --group pelayanan-utama
python3 .codex/skills/neurovi-audit-report/scripts/audit_report.py --repo neurovi-prd --summary-only
python3 .codex/skills/neurovi-audit-report/scripts/audit_report.py --repo neurovi-prd --output audit-report.md
```

Add `--json` for machine-readable output. Change `--repo` only when the
document repository is mounted elsewhere.

## Data Sources

- `reconciliation/e2e-inventory/domain-worklist.json`: domain groups, E2E
  domains, and the owned PRD worklist with stages.
- `reconciliation/canonical/manifest.json`: canonical document codes and
  baseline status. Also used to resolve every known source `document_id`
  (primary and alternate representations) back to its canonical
  `document_code`, for decision-to-gap document matching.
- `reconciliation/canonical/automatic-reconciliation.json`: deterministic
  scanner-candidate register with per-item status and literal evidence.
- `reconciliation/workspaces/<e2e>/sessions/<mode>/`: reconciliation sessions,
  decision registers, and defect registers, when they exist. The legacy flat
  layout `reconciliation/workspaces/<e2e>/session.json` is also read.
- `reconciliation/releases/`: approved global releases, when they exist.

## Present Findings

The script (`audit_report.py`) renders both layers itself — do not hand-write
either one:

1. **Ringkasan untuk PM**: plain-language, no status-code jargon, one block per
   E2E — documents covered, decisions made, defects deliberately left open
   (with reason), and gap candidates split into "possibly already addressed by
   a decision on the same document, verify" vs "no decision recorded at all."
   Session status is translated to plain words, with an explicit note when a
   session is fully decided but not yet closed.
2. **Technical detail**: global summary, release history, then per-group and
   per-E2E sections with open gaps, source-fact fixes, excluded evidence,
   confirmed decisions, and logged defects in separate tables, each with raw
   status codes and literal evidence references.
3. End with what is still missing for a baseline-ready state (open gaps with no
   decision on their document at all, sessions not started or not closed,
   decisions not recorded).

Read `references/usage-guide.md` for the auditor workflow and step-by-step
inspection procedure.
