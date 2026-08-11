# Neurovi Show E2E Usage Guide

## List All E2Es

```text
Use $neurovi-show-e2e.
```

The default output lists every E2E domain in the generated inventory and groups entries by macro group.

## Filter the List

```text
Gunakan $neurovi-show-e2e untuk macro group pelayanan-utama.
```

```text
Tampilkan E2E yang sudah memiliki explicit process path.
```

Filters only narrow the existing inventory. They do not create new domains or approve boundaries.

## Show One E2E

```text
Use $neurovi-show-e2e untuk E2E-ADM-01.
```

The detail view shows:

- source Mermaid identity;
- exact candidate status;
- literal node and edge sequence;
- linked explicit process paths, when present;
- source-explicit document memberships, when present;
- mechanical document-candidate count as navigation evidence only.

## Ambiguous Names

```text
Tampilkan E2E order.
```

If several titles contain the selector, list their codes and titles instead of selecting one silently.

## Continue to Other Workflows

For gap analysis:

```text
Scan gap E2E-ADM-01 dengan $neurovi-gap-scanner.
```

For controlled reconciliation:

```text
Mulai rekonsiliasi E2E-ADM-01 dengan $neurovi-prd-reconciler.
```

## Interpretation

- `SOURCE_FLOW_CANDIDATE` means a source flow exists but its E2E boundary still requires manual review.
- `SOURCE_FLOW_WITH_EXPLICIT_PATH` means the source flow is linked to at least one source-explicit process path; it does not automatically baseline the whole E2E domain.
- Source-explicit memberships come from the declared process inventory.
- Mechanical candidate matches are search/navigation results, not approved memberships.
- Graphify remains a rebuildable navigation layer.
