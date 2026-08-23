---
name: neurovi-workspace-dashboard
description: "Generate a self-contained HTML dashboard of the Neurovi PRD reconciliation workspaces: one overview page across all E2E domains plus one detail page per E2E (session KPIs, decision register grouped by document, defect cards, scanner-candidate funnel, session timeline, and baseline-readiness checklist). Re-running regenerates and overwrites the HTML, so the dashboard always reflects the latest recorded workspace state. Use when a PO, PM, or auditor asks for a readable visual summary of reconciliation progress, overall or per E2E."
---

# Neurovi Workspace Dashboard

## Contract

1. Read the tools `AGENTS.md` and `neurovi-prd/AGENTS.md`, then obey both.
2. This skill is strictly read-only toward the document repository. It never
   edits `source/original/`, the E2E inventory, canonical artifacts, session
   registers, or Git state. The only files it writes are the generated HTML
   pages in the skill's own `output/` folder (or the `--out` directory).
3. Report recorded facts only. Scanner candidates remain mechanical review
   candidates; never present them as proven defects or approved requirements.
4. A session only counts as done when its status is `RECONCILED` or
   `BASELINED`. `AWAITING_USER_DECISION` / `SELECTED_FOR_REVIEW` /
   `STOPPED_BY_USER` sessions are shown with their raw status, never as
   finished.
5. An E2E without a workspace session is shown as "belum ada sesi rekonsiliasi
   tercatat". Scanner output alone is never presented as reconciliation
   progress.
6. Every run rewrites the output HTML completely (deterministic content plus a
   generation timestamp in the footer). Do not hand-edit the generated files —
   fix the script or the template instead, then regenerate.
7. The generated HTML is committed inside this skill's `output/` directory so
   the dashboard travels with the tools repository. Regenerate and commit the
   refreshed pages together with the change that triggered them.

## Run the Dashboard

```bash
python3 .codex/skills/neurovi-workspace-dashboard/scripts/workspace_dashboard.py --repo neurovi-prd
python3 .codex/skills/neurovi-workspace-dashboard/scripts/workspace_dashboard.py --repo neurovi-prd --e2e E2E-RJ
python3 .codex/skills/neurovi-workspace-dashboard/scripts/workspace_dashboard.py --repo neurovi-prd --out path/to/output
```

Change `--repo` only when the document repository is mounted elsewhere (for
example `--repo ../neurovi-prd` when both repositories sit side by side and the
submodule is not checked out). `--e2e` limits detail-page rendering to one E2E;
the overview `index.html` is always regenerated for the whole worklist.

## Data Sources

- `reconciliation/workspaces/<e2e>/sessions/<mode>/`: `session.json`,
  `decision-register.csv`, `interview-register.csv`, `defect-register.csv`, and
  `review-session.md` (the Baseline Readiness checklist is extracted from it).
  The legacy flat layout `reconciliation/workspaces/<e2e>/session.json` is also
  read.
- `reconciliation/canonical/automatic-reconciliation.json`: scanner candidate
  counts per E2E and per reconciliation mode.
- `reconciliation/canonical/manifest.json`: resolves a decision's
  `affected_documents` source document IDs back to canonical PRD codes for
  grouping.
- `reconciliation/e2e-inventory/domain-worklist.json`: E2E titles, purposes,
  and domain groups for page headers and the overview cards.

## Output

- `output/index.html`: overview — global KPIs plus one card per E2E in the
  worklist (session status per mode, decision count, open defects, open
  scanner candidates). Cards for E2Es with a detail page link to it.
- `output/workspace-<E2E>.html`: detail page per E2E — one block per session
  mode with KPI cards, Versi A/B adoption bar (counts only decisions whose
  chosen option explicitly names a version), the decision register grouped by
  canonical document, defect cards (open ones stay visually distinct), the
  scanner-candidate funnel for that mode, the session timeline, and the
  baseline-readiness checklist.

Read `references/usage-guide.md` for the reviewer workflow and how to
interpret each section.
