---
name: neurovi-show-e2e
description: Display the read-only Neurovi SIMRS E2E domain worklist inventory built from eligible original Markdown PRDs. Use when users ask to list domains, show available E2E codes or names, filter worklists, inspect one domain's owned PRDs, or view indexed within-domain and cross-domain relationships without running a gap scan or reconciliation.
---

# Neurovi Show E2E

## Contract

Use this skill only to display the active E2E domain worklist inventory.

1. Read the tools `AGENTS.md` and `neurovi-prd/AGENTS.md`, then obey both.
2. Treat `reconciliation/e2e-inventory/domain-worklist.json` as the only active E2E inventory.
3. Treat each domain as a worklist for checking flow continuity, not as a source-folder classification or Mermaid boundary.
4. Every unique eligible PRD has one owner domain. Show cross-domain use through relation edges without duplicating ownership.
5. Preserve exact assignment, relation, conflict, and review statuses.
6. `MECHANICAL_PROPOSAL` and `REVIEW_REQUIRED` are routing and quality metadata, not user-approved facts and not approval gates for using the worklist.
7. Never infer a new owner, relationship, flow order, or scope while displaying the inventory.
8. Route gap analysis to `$neurovi-gap-scanner` and controlled changes to `$neurovi-prd-reconciler`.

## Run the Viewer

```bash
python3 .codex/skills/neurovi-show-e2e/scripts/show_e2e.py --repo neurovi-prd
python3 .codex/skills/neurovi-show-e2e/scripts/show_e2e.py --repo neurovi-prd --e2e E2E-RJ
python3 .codex/skills/neurovi-show-e2e/scripts/show_e2e.py --repo neurovi-prd --e2e "Rawat Inap"
python3 .codex/skills/neurovi-show-e2e/scripts/show_e2e.py --repo neurovi-prd --group pelayanan-utama
python3 .codex/skills/neurovi-show-e2e/scripts/show_e2e.py --repo neurovi-prd --query rawat
python3 .codex/skills/neurovi-show-e2e/scripts/show_e2e.py --repo neurovi-prd --json
```

## Present the List

For each domain, show its code, title, group, unique-PRD count, relation count, cross-domain relation count, and review-required count. Lead with the invariant that all unique PRDs have one owner domain.

## Present One Domain

Show the ordered PRD worklist, stage, flow-check fields requiring review, within-domain relations, cross-domain relations, evidence class, evidence reference, and conflict status. If a selector is ambiguous, show the choices and wait for the user.

Read `references/usage-guide.md` for examples and interpretation rules.
