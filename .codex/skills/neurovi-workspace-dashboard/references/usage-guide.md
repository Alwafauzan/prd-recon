# Workspace Dashboard — Usage Guide

The dashboard turns the recorded reconciliation workspaces into static,
self-contained HTML pages (no JavaScript, no network access needed). Open the
files in any browser.

## Workflow

1. Run reconciliation sessions with `neurovi-prd-reconciler` as usual; every
   decision, defect, and session status change is recorded in
   `reconciliation/workspaces/<e2e>/sessions/<mode>/`.
2. Regenerate the dashboard:

   ```bash
   python3 .codex/skills/neurovi-workspace-dashboard/scripts/workspace_dashboard.py --repo neurovi-prd
   ```

   Re-running overwrites the HTML completely — there is no merge step and no
   stale state.
3. Open `output/index.html` for the whole worklist, then follow a card into
   `output/workspace-<E2E>.html` for per-E2E detail.
4. Commit the regenerated `output/*.html` together with the change that
   triggered it, so the pushed dashboard always matches the pushed workspace
   state.

## Reading the Pages

### Overview (`index.html`)

- Global KPIs: E2E count, sessions recorded, decisions recorded, defects still
  OPEN, scanner candidates still OPEN vs total.
- One card per E2E: session status per mode (`RECONCILED`/`BASELINED` = done;
  anything else is still in progress), decision count, open defects, open
  scanner candidates. Cards without a detail page mean no session has been
  recorded for that E2E yet.

### Detail (`workspace-<E2E>.html`)

One block per reconciliation mode session:

- **KPI cards** — decisions (with `USER_CONFIRMED` count), interview questions
  answered, defects still OPEN, scanner candidates still OPEN for that mode.
- **Konflik Versi A vs Versi B** — tally of decisions whose chosen option
  explicitly follows one representation version. Decisions with
  version-neutral wording are not counted here; the bar is an adoption
  indicator, not a complete classification.
- **Register Keputusan** — every recorded decision, grouped by the canonical
  PRD code its `affected_documents` resolve to, with type badges
  (`CONFLICT`, `GAP_RES`, `GAP_CLOSURE`) and raw status.
- **Defect Register** — one card per defect. Open defects keep an amber accent
  and stay visible until a recorded disposition closes them; closed cards show
  the closing decision ID.
- **Kandidat Scanner** — funnel of the scanner register for that E2E/mode:
  total, closed from literal source facts, excluded as non-active evidence,
  routed to human decision, and anything still open. Scanner candidates are
  review candidates only — this funnel is never proof of requirement changes.
- **Timeline Sesi** — session start, decision recording timestamps, and the
  final status transition (all UTC, from the registers themselves).
- **Kesiapan Baseline** — the Baseline Readiness checklist extracted verbatim
  from `review-session.md`; unchecked items are the remaining gates before a
  baseline can be approved.

## Notes and Limits

- The dashboard reports recorded facts only. If a register row is missing, the
  page says so plainly instead of implying progress.
- The only non-deterministic element is the generation timestamp in the
  footer; everything else is derived from repository content.
- If the submodule is not checked out, point `--repo` at a sibling checkout,
  e.g. `--repo ../neurovi-prd`.
