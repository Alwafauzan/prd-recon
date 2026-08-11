---
name: neurovi-show-e2e
description: Display the read-only Neurovi SIMRS end-to-end process inventory from repository E2E source-flow artifacts. Use when users ask to list all E2E flows, show available E2E codes or names, filter E2Es by macro group or status, inspect one E2E flow and its literal nodes or edges, or identify source-explicit process and document memberships without running a gap scan or reconciliation.
---

# Neurovi Show E2E

## Contract

Use this skill only to display the current E2E inventory.

1. Read the tools `AGENTS.md` and `neurovi-prd/AGENTS.md`, then obey both.
2. Treat `reconciliation/e2e-inventory/e2e-domain-inventory.json` as a rebuildable inventory derived from source flows and explicit user-controlled inputs.
3. Treat the referenced Mermaid files under `source/original/` as source evidence for flow nodes and edges.
4. Never use Graphify as source truth.
5. Preserve inventory statuses exactly. Do not rename `SOURCE_FLOW_CANDIDATE` as confirmed, approved, or baselined.
6. Keep source-explicit document memberships separate from mechanical document candidates.
7. Never infer a new E2E boundary, document membership, handoff, or process order while displaying the list.
8. Route gap analysis to `$neurovi-gap-scanner` and controlled changes to `$neurovi-prd-reconciler`.

## Run the Viewer

Use the bundled script from the tools repository root:

```bash
# List the complete E2E inventory.
python3 .codex/skills/neurovi-show-e2e/scripts/show_e2e.py --repo neurovi-prd

# Show one E2E by exact code, exact name, or unambiguous partial name.
python3 .codex/skills/neurovi-show-e2e/scripts/show_e2e.py --repo neurovi-prd --e2e E2E-ADM-01
python3 .codex/skills/neurovi-show-e2e/scripts/show_e2e.py --repo neurovi-prd --e2e "Registration Rajal"

# Filter the list.
python3 .codex/skills/neurovi-show-e2e/scripts/show_e2e.py --repo neurovi-prd --group admisi-emr
python3 .codex/skills/neurovi-show-e2e/scripts/show_e2e.py --repo neurovi-prd --status SOURCE_FLOW_WITH_EXPLICIT_PATH
python3 .codex/skills/neurovi-show-e2e/scripts/show_e2e.py --repo neurovi-prd --query rawat

# Machine-readable output.
python3 .codex/skills/neurovi-show-e2e/scripts/show_e2e.py --repo neurovi-prd --json
```

Change `--repo` only when the document repository is mounted elsewhere.

## Present the List

For each E2E, show:

- E2E code and title;
- macro group;
- exact inventory status;
- node and edge counts;
- source-explicit membership count;
- mechanical candidate-match count.

Lead with an evidence notice that the inventory contains candidate boundaries unless its exact status says otherwise. Group the default list by macro group.

## Present One E2E

Show source identity, status, nodes, literal edges, explicit process paths, and source-explicit document memberships. Label mechanical candidate counts as navigation candidates only; do not present them as included documents.

If a selector matches multiple E2Es, return all choices and wait for the user to select one.

Read `references/usage-guide.md` for examples and interpretation rules.
