#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    from .source_fact_closure import build_register, json_bytes, render_report
except ImportError:
    from source_fact_closure import build_register, json_bytes, render_report


INVENTORY_PATH = Path("reconciliation/e2e-inventory/domain-worklist.json")
CATALOG_PATH = Path("catalog/document-index.json")
CANONICAL_ROOT = Path("reconciliation/canonical")
MANIFEST_PATH = CANONICAL_ROOT / "manifest.json"
AUTOMATIC_REGISTER_PATH = CANONICAL_ROOT / "automatic-reconciliation.json"
AUTOMATIC_REPORT_PATH = CANONICAL_ROOT / "automatic-reconciliation.md"
CANONICAL_VERSION = "v0.0.0"
PRIMARY_SOURCE_PREFIX = "PRD/PRD Generator (.md)/"
CODE_PATTERN = re.compile(r"^PRD-[A-Z0-9]+(?:-[A-Z0-9]+)*-[0-9]{3,}$")
AUTO_SOURCE_FACT_STATUS = "RESOLVED_BY_SOURCE_FACT"
HUMAN_DECISION_STATUS = "HUMAN_DECISION_REQUIRED"

SECTION_FAMILIES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "purpose_background",
        "Purpose / Background",
        ("overview", "background", "summary", "ringkasan", "latar belakang", "tujuan"),
    ),
    ("scope", "Scope", ("scope", "ruang lingkup", "in scope", "out scope", "out of scope")),
    (
        "actors_stakeholders",
        "Actors / Stakeholders",
        ("actor", "aktor", "persona", "stakeholder", "pengguna"),
    ),
    (
        "flow_scenarios",
        "Flow / Scenarios",
        ("flow", "alur", "process", "proses", "scenario", "skenario"),
    ),
    ("business_rules", "Business Rules", ("business rule", "aturan bisnis", "rule")),
    (
        "logical_data",
        "Logical Data",
        ("data", "input", "output", "entity", "entitas", "field"),
    ),
    (
        "cases_exceptions",
        "Cases / Exceptions",
        ("case", "condition", "kondisi", "exception", "error", "alternate", "pengecualian"),
    ),
    (
        "acceptance",
        "Acceptance Criteria",
        ("acceptance", "kriteria penerimaan", "criteria"),
    ),
)


class BaselineError(RuntimeError):
    pass


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_json(path: Path) -> Any:
    if not path.is_file():
        raise BaselineError(f"Required file not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BaselineError(f"Cannot read JSON {path}: {exc}") from exc


def atomic_write(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(value)
    temporary.replace(path)


def write_if_changed(path: Path, value: bytes) -> None:
    if path.is_file() and path.read_bytes() == value:
        return
    atomic_write(path, value)


def domain_token(e2e_code: str) -> str:
    token = re.sub(r"^E2E-", "", e2e_code.upper())
    token = re.sub(r"[^A-Z0-9]+", "-", token).strip("-")
    if not token:
        raise BaselineError(f"Cannot derive code token from domain: {e2e_code}")
    return token


def yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def table_text(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", "<br>")


def source_fact_reconciliation_status(relation: dict[str, Any]) -> str:
    if relation.get("verification_status") != "SOURCE_EXPLICIT":
        return ""
    if relation.get("evidence_class") not in {"SOURCE_FACT", "CROSS_SOURCE_FACT"}:
        return ""
    if relation.get("conflict_status") == "NO_CONFLICT_IDENTIFIED":
        return AUTO_SOURCE_FACT_STATUS
    return HUMAN_DECISION_STATUS


def relation_context(relation: dict[str, Any]) -> str:
    parts = []
    for key, label in (
        ("trigger", "Trigger"),
        ("input_context", "Input"),
        ("output_context", "Output"),
        ("status_transition", "Status"),
        ("condition", "Condition"),
    ):
        value = str(relation.get(key, "")).strip()
        if value:
            parts.append(f"{label}: {value}")
    return "<br>".join(table_text(item) for item in parts) or "-"


def source_path(repo: Path, relative: str) -> Path:
    if not relative.startswith(PRIMARY_SOURCE_PREFIX) or not relative.endswith(".md"):
        raise BaselineError(f"Ineligible primary source path: {relative}")
    root = (repo / "source/original").resolve()
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root):
        raise BaselineError(f"Source path escapes source/original: {relative}")
    return candidate


def heading_map(headings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    texts = [str(item.get("text", "")).strip() for item in headings if item.get("text")]
    result = []
    for key, label, tokens in SECTION_FAMILIES:
        matched = [heading for heading in texts if any(token in heading.casefold() for token in tokens)]
        result.append(
            {
                "section_family": key,
                "label": label,
                "status": (
                    "SOURCE_HEADING_DETECTED"
                    if matched
                    else "NO_MATCHING_SOURCE_HEADING_DETECTED"
                ),
                "matched_headings": matched,
            }
        )
    return result


def load_registry(repo: Path) -> dict[str, dict[str, str]]:
    path = repo / MANIFEST_PATH
    if not path.is_file():
        return {}
    manifest = load_json(path)
    registry: dict[str, dict[str, str]] = {}
    for item in manifest.get("code_registry", []):
        content_id = str(item.get("content_id", ""))
        code = str(item.get("document_code", ""))
        assigned_e2e = str(item.get("assigned_e2e_code", ""))
        if not content_id or not code or not assigned_e2e:
            raise BaselineError("Existing canonical code registry is incomplete.")
        if content_id in registry:
            raise BaselineError(f"Duplicate content ID in code registry: {content_id}")
        registry[content_id] = {
            "document_code": code,
            "assigned_e2e_code": assigned_e2e,
        }
    return registry


def assign_codes(
    inventory: dict[str, Any], registry: dict[str, dict[str, str]]
) -> dict[str, dict[str, str]]:
    used_codes: dict[str, str] = {}
    next_number: dict[str, int] = {}
    for content_id, assignment in registry.items():
        code = assignment["document_code"]
        if not CODE_PATTERN.fullmatch(code):
            raise BaselineError(f"Invalid existing canonical code: {code}")
        if code in used_codes and used_codes[code] != content_id:
            raise BaselineError(f"Canonical code is reused: {code}")
        used_codes[code] = content_id
        match = re.match(r"^PRD-(.+)-([0-9]+)$", code)
        if match:
            next_number[match.group(1)] = max(next_number.get(match.group(1), 1), int(match.group(2)) + 1)

    for domain in inventory.get("domains", []):
        e2e_code = str(domain.get("e2e_code", ""))
        token = domain_token(e2e_code)
        documents = sorted(
            domain.get("documents", []),
            key=lambda item: (int(item.get("worklist_order") or 0), str(item.get("content_id", ""))),
        )
        for document in documents:
            content_id = str(document.get("content_id", ""))
            if not content_id:
                raise BaselineError(f"Document without content_id in {e2e_code}")
            if content_id in registry:
                continue
            number = next_number.get(token, 1)
            while True:
                code = f"PRD-{token}-{number:03d}"
                number += 1
                if code not in used_codes:
                    break
            next_number[token] = number
            registry[content_id] = {
                "document_code": code,
                "assigned_e2e_code": e2e_code,
            }
            used_codes[code] = content_id
    return registry


def render_document(
    *,
    document_code: str,
    e2e_code: str,
    e2e_title: str,
    document: dict[str, Any],
    source_sha256: str,
    mappings: list[dict[str, Any]],
) -> bytes:
    representations = document.get("source_representations", [])
    source_ids = [str(item.get("document_id", "")) for item in representations]
    paths = [str(item.get("source_path", "")) for item in representations]
    title = str(document.get("title", ""))
    content_id = str(document.get("content_id", ""))
    primary_document_id = str(document.get("document_id", ""))
    primary_path = str(document.get("source_path", ""))

    lines = [
        "---",
        'schema_version: "1"',
        'artifact_type: "CANONICAL_PRD"',
        f"document_code: {yaml_string(document_code)}",
        'code_status: "BOOTSTRAPPED_CANONICAL_V0"',
        f"canonical_version: {yaml_string(CANONICAL_VERSION)}",
        'baseline_status: "BOOTSTRAPPED"',
        f"owner_e2e_code: {yaml_string(e2e_code)}",
        f"owner_e2e_title: {yaml_string(e2e_title)}",
        f"source_content_id: {yaml_string(content_id)}",
        f"primary_source_document_id: {yaml_string(primary_document_id)}",
        f"primary_source_path: {yaml_string(primary_path)}",
        f"source_sha256: {yaml_string(source_sha256)}",
        f"source_document_ids: {json.dumps(source_ids, ensure_ascii=False)}",
        f"source_paths: {json.dumps(paths, ensure_ascii=False)}",
        "---",
        "",
        f"# {document_code} - {title}",
        "",
        "> Canonical bootstrap version 0. Formatting metadata is generated without changing source meaning.",
        "> The complete original Markdown payload below is preserved byte-for-byte from the primary source.",
        "",
        "## Document Control",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Canonical document code | `{document_code}` |",
        f"| Canonical version | `{CANONICAL_VERSION}` |",
        f"| Original title | {table_text(title)} |",
        f"| Owner E2E worklist | `{e2e_code}` - {table_text(e2e_title)} |",
        f"| Primary original document | `{primary_document_id}` |",
        f"| Original content ID | `{content_id}` |",
        f"| Original source path | `{table_text(primary_path)}` |",
        f"| Original SHA-256 | `{source_sha256}` |",
        "| Baseline status | `BOOTSTRAPPED` |",
        "| Semantic changes | `NONE` |",
        "",
        "## Source Representations",
        "",
        "All rows below contain the same source payload checksum.",
        "",
        "| Document ID | Original path | SHA-256 |",
        "|---|---|---|",
    ]
    for representation in representations:
        lines.append(
            "| `{}` | `{}` | `{}` |".format(
                table_text(str(representation.get("document_id", ""))),
                table_text(str(representation.get("source_path", ""))),
                table_text(str(representation.get("sha256", ""))),
            )
        )
    lines.extend(
        [
            "",
            "## Standard Section Map",
            "",
            "This is a mechanical heading map for navigation. A missing matching heading does not prove that the source context is absent.",
            "",
            "| Standard family | Detection status | Matching original headings |",
            "|---|---|---|",
        ]
    )
    for mapping in mappings:
        matched = "<br>".join(table_text(item) for item in mapping["matched_headings"])
        lines.append(
            f"| {mapping['label']} | `{mapping['status']}` | {matched or '-'} |"
        )
    lines.extend(
        [
            "",
            "## Preserved Original Content",
            "",
            f"<!-- SOURCE_CONTENT_BEGIN document_id={primary_document_id} sha256={source_sha256} -->",
            "",
        ]
    )
    return ("\n".join(lines) + "\n").encode("utf-8")


def render_e2e_context(
    *,
    domain: dict[str, Any],
    relations: list[dict[str, Any]],
    code_by_document_id: dict[str, str],
    inventory_sha256: str,
) -> bytes:
    e2e_code = str(domain.get("e2e_code", ""))
    title = str(domain.get("title", ""))
    owner_documents = domain.get("documents", [])
    within_relations = [
        relation
        for relation in relations
        if relation.get("source_domain_code") == e2e_code
        and relation.get("target_domain_code") == e2e_code
    ]
    cross_relations = [
        relation
        for relation in relations
        if e2e_code
        in {
            str(relation.get("source_domain_code", "")),
            str(relation.get("target_domain_code", "")),
        }
        and relation not in within_relations
    ]
    relevant_relations = within_relations + cross_relations
    auto_reconciled_relations = [
        relation
        for relation in relevant_relations
        if source_fact_reconciliation_status(relation) == AUTO_SOURCE_FACT_STATUS
    ]
    human_decision_relations = [
        relation
        for relation in relevant_relations
        if source_fact_reconciliation_status(relation) == HUMAN_DECISION_STATUS
    ]
    lines = [
        "---",
        'schema_version: "1"',
        'artifact_type: "CANONICAL_E2E_CONTEXT"',
        f"e2e_code: {yaml_string(e2e_code)}",
        f"canonical_version: {yaml_string(CANONICAL_VERSION)}",
        'baseline_status: "BOOTSTRAPPED"',
        f"source_inventory_sha256: {yaml_string(inventory_sha256)}",
        "---",
        "",
        f"# {e2e_code} - {title}",
        "",
        "> Canonical E2E version 0 is a navigation and flow-review baseline.",
        "> Worklist order and mechanical relations remain routing evidence, not approved business sequence or requirements.",
        "",
        "## Document Control",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| E2E code | `{e2e_code}` |",
        f"| Canonical version | `{CANONICAL_VERSION}` |",
        f"| Baseline status | `BOOTSTRAPPED` |",
        f"| Domain status | `{table_text(str(domain.get('status', '')) or '-')}` |",
        f"| Domain origin | `{table_text(str(domain.get('origin', '')) or '-')}` |",
        f"| Owner PRDs | {len(owner_documents)} |",
        f"| Within-domain relations | {len(within_relations)} |",
        f"| Cross-domain relations | {len(cross_relations)} |",
        f"| Automatically reconciled source facts | {len(auto_reconciled_relations)} |",
        f"| Source-explicit issues requiring human decision | {len(human_decision_relations)} |",
        "| Semantic changes from source | `NONE` |",
        "",
        "## Purpose",
        "",
        str(domain.get("purpose", "")).strip() or "NOT_DEFINED_IN_INVENTORY",
        "",
        "## Owner PRD Worklist",
        "",
        "Worklist order is used for review routing. It is not automatically a confirmed end-to-end sequence.",
        "",
        "| Order | Stage | Canonical PRD | Original title | Assignment evidence | Review status |",
        "|---:|---|---|---|---|---|",
    ]
    for document in owner_documents:
        document_id = str(document.get("document_id", ""))
        document_code = code_by_document_id.get(document_id, "")
        link = f"[{document_code}](../prds/{document_code}.md)" if document_code else "-"
        assignment = "{} / {} / {}".format(
            str(document.get("assignment_status", "")) or "-",
            str(document.get("assignment_confidence", "")) or "-",
            str(document.get("assignment_basis", "")) or "-",
        )
        lines.append(
            "| {} | `{}` | {} | {} | {} | `{}` |".format(
                document.get("worklist_order", ""),
                table_text(str(document.get("worklist_stage", "")) or "-"),
                link,
                table_text(str(document.get("title", ""))),
                table_text(assignment),
                table_text(str(document.get("review_status", "")) or "-"),
            )
        )

    lines.extend(
        [
            "",
            "## Within-Domain Relations",
            "",
            "| Relation | From | To | Type | Evidence | Verification | Source reference |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    if not within_relations:
        lines.append("| - | - | - | - | - | - | - |")
    for relation in within_relations:
        source_code = code_by_document_id.get(str(relation.get("source_document_id", "")), "-")
        target_code = code_by_document_id.get(str(relation.get("target_document_id", "")), "-")
        lines.append(
            "| `{}` | `{}` | `{}` | `{}` | `{}` | `{}` | {} |".format(
                table_text(str(relation.get("relation_id", ""))),
                table_text(source_code),
                table_text(target_code),
                table_text(str(relation.get("relationship_type", ""))),
                table_text(str(relation.get("evidence_class", ""))),
                table_text(str(relation.get("verification_status", ""))),
                table_text(str(relation.get("evidence_reference", "")) or "-"),
            )
        )

    lines.extend(
        [
            "",
            "## Cross-Domain Relations",
            "",
            "| Direction | Local PRD | Related domain | Related PRD | Type | Evidence | Verification | Source reference |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    if not cross_relations:
        lines.append("| - | - | - | - | - | - | - | - |")
    for relation in cross_relations:
        outgoing = str(relation.get("source_domain_code", "")) == e2e_code
        local_id = str(
            relation.get("source_document_id" if outgoing else "target_document_id", "")
        )
        related_id = str(
            relation.get("target_document_id" if outgoing else "source_document_id", "")
        )
        related_domain = str(
            relation.get("target_domain_code" if outgoing else "source_domain_code", "")
        )
        lines.append(
            "| `{}` | `{}` | `{}` | `{}` | `{}` | `{}` | `{}` | {} |".format(
                "OUTGOING" if outgoing else "INCOMING",
                table_text(code_by_document_id.get(local_id, "-")),
                table_text(related_domain or "-"),
                table_text(code_by_document_id.get(related_id, "-")),
                table_text(str(relation.get("relationship_type", ""))),
                table_text(str(relation.get("evidence_class", ""))),
                table_text(str(relation.get("verification_status", ""))),
                table_text(str(relation.get("evidence_reference", "")) or "-"),
            )
        )

    if auto_reconciled_relations:
        lines.extend(
            [
                "",
                "## Automatic Source-Fact Reconciliation",
                "",
                "The relations below are closed without a human decision because the eligible source is explicit, the canonical payload is verified, and no conflict is identified. This records existing source facts only; it does not expand PRD scope or approve a repository release.",
                "",
                "| Relation | From | To | Type | Source-backed context | Evidence | Reconciliation status |",
                "|---|---|---|---|---|---|---|",
            ]
        )
        for relation in auto_reconciled_relations:
            source_code = code_by_document_id.get(
                str(relation.get("source_document_id", "")), "-"
            )
            target_code = code_by_document_id.get(
                str(relation.get("target_document_id", "")), "-"
            )
            lines.append(
                "| `{}` | `{}` | `{}` | `{}` | {} | {} | `{}` |".format(
                    table_text(str(relation.get("relation_id", ""))),
                    table_text(source_code),
                    table_text(target_code),
                    table_text(str(relation.get("relationship_type", ""))),
                    relation_context(relation),
                    table_text(str(relation.get("evidence_reference", "")) or "-"),
                    AUTO_SOURCE_FACT_STATUS,
                )
            )

    if human_decision_relations:
        lines.extend(
            [
                "",
                "## Source-Explicit Issues Requiring Human Decision",
                "",
                "These relations are not closed automatically because the eligible sources expose a conflict or semantic choice.",
                "",
                "| Relation | From | To | Type | Issue | Evidence | Status |",
                "|---|---|---|---|---|---|---|",
            ]
        )
        for relation in human_decision_relations:
            source_code = code_by_document_id.get(
                str(relation.get("source_document_id", "")), "-"
            )
            target_code = code_by_document_id.get(
                str(relation.get("target_document_id", "")), "-"
            )
            issue = str(relation.get("notes", "")).strip() or relation_context(
                relation
            )
            lines.append(
                "| `{}` | `{}` | `{}` | `{}` | {} | {} | `{}` |".format(
                    table_text(str(relation.get("relation_id", ""))),
                    table_text(source_code),
                    table_text(target_code),
                    table_text(str(relation.get("relationship_type", ""))),
                    table_text(issue),
                    table_text(str(relation.get("evidence_reference", "")) or "-"),
                    HUMAN_DECISION_STATUS,
                )
            )

    lines.extend(
        [
            "",
            "## Evidence Interpretation",
            "",
            "- `SOURCE_FACT`, `CROSS_SOURCE_FACT`, or `SOURCE_EXPLICIT` must retain a trace to the eligible original PRD.",
            "- `MECHANICAL_CANDIDATE` and `REVIEW_REQUIRED` are discovery evidence only and remain reconciliation work items.",
            "- This E2E context links PRDs; it does not absorb or rewrite the requirement scope stored in each canonical PRD.",
            "",
        ]
    )
    return "\n".join(lines).encode("utf-8")


def render_index(
    documents: list[dict[str, Any]], e2e_contexts: list[dict[str, Any]]
) -> bytes:
    lines = [
        "# Canonical PRD Baseline v0",
        "",
        "This index lists the canonical bootstrap baseline. Codes and wrappers are standardized; complete original PRD payloads remain unchanged.",
        "",
        "| Code | Owner domain | Original title | Original document |",
        "|---|---|---|---|",
    ]
    for document in documents:
        lines.append(
            "| [{}](<{}>) | `{}` | {} | `{}` |".format(
                document["document_code"],
                Path(document["path"]).relative_to(CANONICAL_ROOT).as_posix(),
                document["owner_e2e_code"],
                table_text(document["original_title"]),
                document["primary_source_document_id"],
            )
        )
    lines.append("")
    lines.extend(
        [
            "## E2E Contexts",
            "",
            "| E2E | Domain | Owner PRDs | Relations | Auto source facts | Human decisions |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for context in e2e_contexts:
        lines.append(
            "| [{}](<{}>) | {} | {} | {} | {} | {} |".format(
                context["e2e_code"],
                Path(context["path"]).relative_to(CANONICAL_ROOT).as_posix(),
                table_text(context["title"]),
                context["document_count"],
                context["relation_count"],
                context.get("automatically_reconciled_source_fact_count", 0),
                context.get("human_decision_required_count", 0),
            )
        )
    lines.append("")
    return "\n".join(lines).encode("utf-8")


def render_readme(
    inventory: dict[str, Any],
    documents: list[dict[str, Any]],
    e2e_contexts: list[dict[str, Any]],
) -> bytes:
    lines = [
        "# Canonical Baseline v0",
        "",
        "This directory is the deterministic canonical version 0 bootstrap generated from eligible original Markdown PRDs.",
        "",
        "- Original files under `source/original/` remain immutable.",
        "- Each unique source payload receives one stable code using `PRD-<DOMAIN>-<NNN>`.",
        "- Generated canonical documents use one metadata wrapper and append the complete selected original payload byte-for-byte.",
        "- The section map is mechanical navigation metadata, not a semantic completeness claim.",
        "- Version `v0.0.0` is a bootstrap baseline ready for reconciliation consumption; it is not an approved Git release or tag.",
        "- Reconciliation may enrich later canonical versions only from source facts or explicit user-confirmed decisions.",
        "- Source-explicit, non-conflicting E2E relations are recorded as `RESOLVED_BY_SOURCE_FACT`; source conflicts remain `HUMAN_DECISION_REQUIRED`.",
        "- `prds/` stores the complete document requirements; `e2e/` stores worklist and relationship context without expanding PRD scope.",
        "",
        "## Coverage",
        "",
        f"- Owner domains: {inventory.get('domain_count', 0)}",
        f"- Eligible source files: {inventory.get('eligible_file_count', 0)}",
        f"- Unique source PRDs: {inventory.get('unique_prd_count', 0)}",
        f"- Generated canonical PRDs: {len(documents)}",
        f"- Generated canonical E2E contexts: {len(e2e_contexts)}",
        "",
        "## Regenerate and Validate",
        "",
        "```bash",
        "python3 scripts/bootstrap_prd_baseline.py build --repo neurovi-prd",
        "python3 scripts/bootstrap_prd_baseline.py validate --repo neurovi-prd",
        "```",
        "",
        "See [index.md](index.md) for the document list and `manifest.json` for machine-readable provenance.",
        "See [automatic-reconciliation.md](automatic-reconciliation.md) for the full scanner-candidate source-fact closure register.",
        "",
    ]
    return "\n".join(lines).encode("utf-8")


def inventory_documents(inventory: dict[str, Any]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    result = []
    seen: set[str] = set()
    for domain in inventory.get("domains", []):
        for document in sorted(
            domain.get("documents", []),
            key=lambda item: (int(item.get("worklist_order") or 0), str(item.get("content_id", ""))),
        ):
            content_id = str(document.get("content_id", ""))
            if content_id in seen:
                raise BaselineError(f"Content has more than one owner domain: {content_id}")
            seen.add(content_id)
            result.append((domain, document))
    expected = int(inventory.get("unique_prd_count", len(result)))
    if len(result) != expected:
        raise BaselineError(f"Inventory unique count mismatch: expected={expected}, actual={len(result)}")
    return result


def build(repo: Path, prune: bool = False) -> dict[str, Any]:
    repo = repo.resolve()
    inventory_file = repo / INVENTORY_PATH
    inventory = load_json(inventory_file)
    if inventory.get("inventory_type") != "E2E_DOMAIN_WORKLIST":
        raise BaselineError("Active inventory is not an E2E domain worklist.")
    catalog = load_json(repo / CATALOG_PATH)
    catalog_by_id = {
        str(item.get("document_id", "")): item for item in catalog.get("documents", [])
    }
    registry = assign_codes(inventory, load_registry(repo))
    manifest_documents: list[dict[str, Any]] = []
    expected_prd_outputs: set[Path] = set()

    for domain, document in inventory_documents(inventory):
        e2e_code = str(domain.get("e2e_code", ""))
        e2e_title = str(domain.get("title", ""))
        content_id = str(document.get("content_id", ""))
        assignment = registry[content_id]
        document_code = assignment["document_code"]
        primary_document_id = str(document.get("document_id", ""))
        primary_relative = str(document.get("source_path", ""))
        primary = source_path(repo, primary_relative)
        if not primary.is_file():
            raise BaselineError(f"Primary source does not exist: {primary_relative}")
        raw = primary.read_bytes()
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise BaselineError(f"Primary source is not UTF-8: {primary_relative}") from exc
        source_sha256 = sha256_bytes(raw)

        representations = document.get("source_representations", [])
        if not representations:
            raise BaselineError(f"Source representations missing: {content_id}")
        representation_ids = set()
        for representation in representations:
            representation_id = str(representation.get("document_id", ""))
            relative = str(representation.get("source_path", ""))
            expected_sha = str(representation.get("sha256", ""))
            representation_file = source_path(repo, relative)
            if not representation_file.is_file():
                raise BaselineError(f"Source representation does not exist: {relative}")
            actual_sha = sha256_bytes(representation_file.read_bytes())
            if actual_sha != expected_sha or actual_sha != source_sha256:
                raise BaselineError(f"Source representation checksum mismatch: {relative}")
            representation_ids.add(representation_id)
        if primary_document_id not in representation_ids:
            raise BaselineError(f"Primary document is not listed as a representation: {primary_document_id}")

        catalog_document = catalog_by_id.get(primary_document_id)
        if not catalog_document:
            raise BaselineError(f"Primary document is missing from catalog: {primary_document_id}")
        if str(catalog_document.get("source_path", "")) != primary_relative:
            raise BaselineError(f"Catalog source path mismatch: {primary_document_id}")
        mappings = heading_map(catalog_document.get("headings", []))
        header = render_document(
            document_code=document_code,
            e2e_code=e2e_code,
            e2e_title=e2e_title,
            document=document,
            source_sha256=source_sha256,
            mappings=mappings,
        )
        output_relative = CANONICAL_ROOT / "prds" / f"{document_code}.md"
        output = repo / output_relative
        generated = header + raw
        write_if_changed(output, generated)
        expected_prd_outputs.add(output.resolve())
        manifest_documents.append(
            {
                "document_code": document_code,
                "code_status": "BOOTSTRAPPED_CANONICAL_V0",
                "canonical_version": CANONICAL_VERSION,
                "owner_e2e_code": e2e_code,
                "owner_e2e_title": e2e_title,
                "worklist_order": document.get("worklist_order"),
                "worklist_stage": document.get("worklist_stage", ""),
                "content_id": content_id,
                "original_title": document.get("title", ""),
                "primary_source_document_id": primary_document_id,
                "primary_source_path": primary_relative,
                "source_sha256": source_sha256,
                "source_representations": representations,
                "standard_section_map": mappings,
                "path": output_relative.as_posix(),
                "payload_offset": len(header),
                "payload_length": len(raw),
                "generated_sha256": sha256_bytes(generated),
                "semantic_changes": "NONE",
            }
        )

    prd_root = repo / CANONICAL_ROOT / "prds"
    existing_outputs = {path.resolve() for path in prd_root.glob("PRD-*.md")} if prd_root.is_dir() else set()
    stale = sorted(existing_outputs - expected_prd_outputs)
    if stale and not prune:
        relative = [path.relative_to(repo).as_posix() for path in stale]
        raise BaselineError(f"Stale generated PRDs detected; rerun with --prune: {relative}")
    for path in stale:
        path.unlink()

    active_content_ids = {item["content_id"] for item in manifest_documents}
    code_registry = [
        {
            "content_id": content_id,
            "document_code": assignment["document_code"],
            "assigned_e2e_code": assignment["assigned_e2e_code"],
            "active": content_id in active_content_ids,
        }
        for content_id, assignment in sorted(
            registry.items(), key=lambda item: item[1]["document_code"]
        )
    ]
    code_by_document_id = {
        str(representation.get("document_id", "")): document["document_code"]
        for document in manifest_documents
        for representation in document.get("source_representations", [])
        if representation.get("document_id")
    }
    inventory_sha256 = sha256_bytes(inventory_file.read_bytes())
    relations = [
        dict(relation)
        for relation in inventory.get("relations", [])
        if isinstance(relation, dict)
    ]
    automatically_reconciled_relations = [
        relation
        for relation in relations
        if source_fact_reconciliation_status(relation) == AUTO_SOURCE_FACT_STATUS
    ]
    human_decision_relations = [
        relation
        for relation in relations
        if source_fact_reconciliation_status(relation) == HUMAN_DECISION_STATUS
    ]
    automatic_register = build_register(
        repo=repo,
        inventory=inventory,
        manifest_documents=manifest_documents,
        catalog_by_id=catalog_by_id,
        inventory_sha256=inventory_sha256,
    )
    automatic_register_bytes = json_bytes(automatic_register)
    automatic_report_bytes = render_report(automatic_register)
    write_if_changed(repo / AUTOMATIC_REGISTER_PATH, automatic_register_bytes)
    write_if_changed(repo / AUTOMATIC_REPORT_PATH, automatic_report_bytes)
    manifest_e2e_contexts: list[dict[str, Any]] = []
    expected_e2e_outputs: set[Path] = set()
    for domain in inventory.get("domains", []):
        if not isinstance(domain, dict):
            continue
        e2e_code = str(domain.get("e2e_code", ""))
        if not e2e_code:
            raise BaselineError("Domain without e2e_code in active inventory")
        domain_relations = [
            relation
            for relation in relations
            if e2e_code
            in {
                str(relation.get("source_domain_code", "")),
                str(relation.get("target_domain_code", "")),
            }
        ]
        domain_auto_reconciled = [
            relation
            for relation in domain_relations
            if source_fact_reconciliation_status(relation) == AUTO_SOURCE_FACT_STATUS
        ]
        domain_human_decisions = [
            relation
            for relation in domain_relations
            if source_fact_reconciliation_status(relation) == HUMAN_DECISION_STATUS
        ]
        generated = render_e2e_context(
            domain=domain,
            relations=relations,
            code_by_document_id=code_by_document_id,
            inventory_sha256=inventory_sha256,
        )
        output_relative = CANONICAL_ROOT / "e2e" / f"{e2e_code}.md"
        output = repo / output_relative
        write_if_changed(output, generated)
        expected_e2e_outputs.add(output.resolve())
        manifest_e2e_contexts.append(
            {
                "e2e_code": e2e_code,
                "title": str(domain.get("title", "")),
                "canonical_version": CANONICAL_VERSION,
                "path": output_relative.as_posix(),
                "document_count": len(domain.get("documents", [])),
                "relation_count": len(domain_relations),
                "automatically_reconciled_source_fact_count": len(
                    domain_auto_reconciled
                ),
                "human_decision_required_count": len(domain_human_decisions),
                "generated_sha256": sha256_bytes(generated),
                "semantic_changes": "NONE",
            }
        )

    e2e_root = repo / CANONICAL_ROOT / "e2e"
    existing_e2e_outputs = (
        {path.resolve() for path in e2e_root.glob("E2E-*.md")}
        if e2e_root.is_dir()
        else set()
    )
    stale_e2e = sorted(existing_e2e_outputs - expected_e2e_outputs)
    if stale_e2e and not prune:
        relative = [path.relative_to(repo).as_posix() for path in stale_e2e]
        raise BaselineError(
            f"Stale generated E2E contexts detected; rerun with --prune: {relative}"
        )
    for path in stale_e2e:
        path.unlink()

    manifest = {
        "schema_version": 1,
        "artifact_type": "CANONICAL_BASELINE_MANIFEST",
        "canonical_version": CANONICAL_VERSION,
        "baseline_status": "BOOTSTRAPPED",
        "release_status": "UNRELEASED",
        "consumption_status": "READY_FOR_RECONCILIATION",
        "generator_version": 1,
        "code_pattern": "PRD-<DOMAIN>-<NNN>",
        "source_inventory_path": INVENTORY_PATH.as_posix(),
        "source_inventory_sha256": sha256_bytes(inventory_file.read_bytes()),
        "source_inventory_version": inventory.get("inventory_version", ""),
        "eligible_file_count": inventory.get("eligible_file_count", 0),
        "unique_prd_count": inventory.get("unique_prd_count", 0),
        "generated_prd_count": len(manifest_documents),
        "generated_e2e_count": len(manifest_e2e_contexts),
        "domain_count": inventory.get("domain_count", 0),
        "semantic_changes": "NONE",
        "automatic_source_fact_reconciliation_status": "COMPLETED",
        "automatically_reconciled_source_fact_count": len(
            automatically_reconciled_relations
        ),
        "human_decision_required_count": len(human_decision_relations),
        "automatic_candidate_reconciliation": {
            "status": "COMPLETED",
            "register_path": AUTOMATIC_REGISTER_PATH.as_posix(),
            "register_sha256": sha256_bytes(automatic_register_bytes),
            "report_path": AUTOMATIC_REPORT_PATH.as_posix(),
            "report_sha256": sha256_bytes(automatic_report_bytes),
            **automatic_register["summary"],
        },
        "code_registry": code_registry,
        "documents": manifest_documents,
        "e2e_contexts": manifest_e2e_contexts,
    }
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    write_if_changed(repo / MANIFEST_PATH, manifest_bytes)
    write_if_changed(
        repo / CANONICAL_ROOT / "index.md",
        render_index(manifest_documents, manifest_e2e_contexts),
    )
    write_if_changed(
        repo / CANONICAL_ROOT / "README.md",
        render_readme(inventory, manifest_documents, manifest_e2e_contexts),
    )
    return validate(repo)


def validate(repo: Path) -> dict[str, Any]:
    repo = repo.resolve()
    inventory_file = repo / INVENTORY_PATH
    inventory = load_json(inventory_file)
    manifest = load_json(repo / MANIFEST_PATH)
    errors: list[str] = []
    if manifest.get("artifact_type") != "CANONICAL_BASELINE_MANIFEST":
        errors.append("Invalid canonical manifest type")
    if manifest.get("canonical_version") != CANONICAL_VERSION:
        errors.append("Canonical manifest is not bootstrap version v0.0.0")
    if manifest.get("source_inventory_sha256") != sha256_bytes(inventory_file.read_bytes()):
        errors.append("Canonical manifest was generated from a different E2E inventory")

    relations = [
        relation
        for relation in inventory.get("relations", [])
        if isinstance(relation, dict)
    ]
    expected_auto_count = sum(
        source_fact_reconciliation_status(relation) == AUTO_SOURCE_FACT_STATUS
        for relation in relations
    )
    expected_human_count = sum(
        source_fact_reconciliation_status(relation) == HUMAN_DECISION_STATUS
        for relation in relations
    )
    if manifest.get("automatic_source_fact_reconciliation_status") != "COMPLETED":
        errors.append("Automatic source-fact reconciliation is not complete")
    if manifest.get("automatically_reconciled_source_fact_count") != expected_auto_count:
        errors.append("Automatic source-fact reconciliation count is inconsistent")
    if manifest.get("human_decision_required_count") != expected_human_count:
        errors.append("Human-decision relation count is inconsistent")

    automatic_summary = manifest.get("automatic_candidate_reconciliation", {})
    register_path = repo / AUTOMATIC_REGISTER_PATH
    report_path = repo / AUTOMATIC_REPORT_PATH
    if automatic_summary.get("status") != "COMPLETED":
        errors.append("Automatic candidate reconciliation is not complete")
    if not register_path.is_file():
        errors.append("Automatic reconciliation register is missing")
    elif automatic_summary.get("register_sha256") != sha256_bytes(
        register_path.read_bytes()
    ):
        errors.append("Automatic reconciliation register checksum changed")
    if not report_path.is_file():
        errors.append("Automatic reconciliation report is missing")
    elif automatic_summary.get("report_sha256") != sha256_bytes(
        report_path.read_bytes()
    ):
        errors.append("Automatic reconciliation report checksum changed")
    if register_path.is_file():
        try:
            register = load_json(register_path)
        except BaselineError as exc:
            errors.append(str(exc))
        else:
            try:
                expected_register = build_register(
                    repo=repo,
                    inventory=inventory,
                    manifest_documents=manifest.get("documents", []),
                    catalog_by_id={
                        str(item.get("document_id", "")): item
                        for item in load_json(repo / CATALOG_PATH).get("documents", [])
                    },
                    inventory_sha256=sha256_bytes(inventory_file.read_bytes()),
                )
            except (KeyError, UnicodeDecodeError, ValueError) as exc:
                errors.append(f"Automatic reconciliation verification failed: {exc}")
            else:
                if register != expected_register:
                    errors.append(
                        "Automatic reconciliation register is inconsistent with verified canonical payloads"
                    )
                elif automatic_summary.get("candidate_count") != register.get(
                    "summary", {}
                ).get("candidate_count"):
                    errors.append("Automatic reconciliation candidate count is inconsistent")

    inventory_rows = inventory_documents(inventory)
    active_content_ids = {str(document.get("content_id", "")) for _, document in inventory_rows}
    manifest_documents = manifest.get("documents", [])
    manifest_by_content = {str(item.get("content_id", "")): item for item in manifest_documents}
    if len(manifest_by_content) != len(manifest_documents):
        errors.append("Duplicate content IDs in canonical manifest")
    if set(manifest_by_content) != active_content_ids:
        errors.append("Canonical coverage does not match active unique PRDs")

    registry = manifest.get("code_registry", [])
    codes = [str(item.get("document_code", "")) for item in registry]
    registry_content_ids = [str(item.get("content_id", "")) for item in registry]
    if len(codes) != len(set(codes)):
        errors.append("Canonical document code is reused")
    if len(registry_content_ids) != len(set(registry_content_ids)):
        errors.append("Canonical registry content ID is duplicated")
    invalid_codes = [code for code in codes if not CODE_PATTERN.fullmatch(code)]
    if invalid_codes:
        errors.append(f"Invalid canonical codes: {invalid_codes}")

    expected_outputs: set[Path] = set()
    for _, inventory_document in inventory_rows:
        content_id = str(inventory_document.get("content_id", ""))
        item = manifest_by_content.get(content_id)
        if not item:
            continue
        relative_output = Path(str(item.get("path", "")))
        expected_path = CANONICAL_ROOT / "prds" / f"{item.get('document_code', '')}.md"
        if relative_output != expected_path:
            errors.append(f"Unexpected generated path for {content_id}: {relative_output}")
            continue
        output = repo / relative_output
        expected_outputs.add(output.resolve())
        if not output.is_file():
            errors.append(f"Generated canonical PRD missing: {relative_output}")
            continue
        primary_relative = str(item.get("primary_source_path", ""))
        try:
            primary = source_path(repo, primary_relative)
        except BaselineError as exc:
            errors.append(str(exc))
            continue
        if not primary.is_file():
            errors.append(f"Primary original missing: {primary_relative}")
            continue
        raw = primary.read_bytes()
        source_sha = sha256_bytes(raw)
        if source_sha != item.get("source_sha256"):
            errors.append(f"Original checksum changed: {primary_relative}")
        generated = output.read_bytes()
        if sha256_bytes(generated) != item.get("generated_sha256"):
            errors.append(f"Generated checksum changed: {relative_output}")
        offset = item.get("payload_offset")
        length = item.get("payload_length")
        if (
            not isinstance(offset, int)
            or not isinstance(length, int)
            or length != len(raw)
            or generated[offset : offset + length] != raw
            or len(generated) != offset + length
        ):
            errors.append(f"Original payload is not preserved byte-for-byte: {relative_output}")

        for representation in item.get("source_representations", []):
            relative = str(representation.get("source_path", ""))
            expected_sha = str(representation.get("sha256", ""))
            try:
                representation_path = source_path(repo, relative)
            except BaselineError as exc:
                errors.append(str(exc))
                continue
            if not representation_path.is_file():
                errors.append(f"Original representation missing: {relative}")
                continue
            if sha256_bytes(representation_path.read_bytes()) != expected_sha:
                errors.append(f"Original representation checksum changed: {relative}")

    prd_root = repo / CANONICAL_ROOT / "prds"
    actual_outputs = {path.resolve() for path in prd_root.glob("PRD-*.md")} if prd_root.is_dir() else set()
    if actual_outputs != expected_outputs:
        errors.append("Generated PRD files do not exactly match the canonical manifest")

    manifest_e2e_contexts = manifest.get("e2e_contexts", [])
    inventory_domains = {
        str(domain.get("e2e_code", "")): domain
        for domain in inventory.get("domains", [])
        if isinstance(domain, dict)
    }
    e2e_by_code = {
        str(item.get("e2e_code", "")): item
        for item in manifest_e2e_contexts
        if isinstance(item, dict)
    }
    if int(manifest.get("generated_e2e_count", -1)) != len(manifest_e2e_contexts):
        errors.append("Canonical E2E manifest count is inconsistent")
    if set(e2e_by_code) != set(inventory_domains):
        errors.append("Canonical E2E coverage does not match active domains")
    expected_e2e_outputs: set[Path] = set()
    for e2e_code, item in e2e_by_code.items():
        relative_output = Path(str(item.get("path", "")))
        expected_path = CANONICAL_ROOT / "e2e" / f"{e2e_code}.md"
        if relative_output != expected_path:
            errors.append(f"Unexpected generated E2E path for {e2e_code}: {relative_output}")
            continue
        output = repo / relative_output
        expected_e2e_outputs.add(output.resolve())
        if not output.is_file():
            errors.append(f"Generated canonical E2E missing: {relative_output}")
            continue
        if sha256_bytes(output.read_bytes()) != item.get("generated_sha256"):
            errors.append(f"Generated canonical E2E checksum changed: {relative_output}")
        domain_relations = [
            relation
            for relation in relations
            if e2e_code
            in {
                str(relation.get("source_domain_code", "")),
                str(relation.get("target_domain_code", "")),
            }
        ]
        expected_domain_auto = sum(
            source_fact_reconciliation_status(relation) == AUTO_SOURCE_FACT_STATUS
            for relation in domain_relations
        )
        expected_domain_human = sum(
            source_fact_reconciliation_status(relation) == HUMAN_DECISION_STATUS
            for relation in domain_relations
        )
        if item.get("automatically_reconciled_source_fact_count") != expected_domain_auto:
            errors.append(
                f"Automatic source-fact count is inconsistent for {e2e_code}"
            )
        if item.get("human_decision_required_count") != expected_domain_human:
            errors.append(f"Human-decision count is inconsistent for {e2e_code}")
    e2e_root = repo / CANONICAL_ROOT / "e2e"
    actual_e2e_outputs = (
        {path.resolve() for path in e2e_root.glob("E2E-*.md")}
        if e2e_root.is_dir()
        else set()
    )
    if actual_e2e_outputs != expected_e2e_outputs:
        errors.append("Generated E2E files do not exactly match the canonical manifest")
    for required in (repo / CANONICAL_ROOT / "README.md", repo / CANONICAL_ROOT / "index.md"):
        if not required.is_file():
            errors.append(f"Canonical navigation file missing: {required.relative_to(repo)}")

    return {
        "valid": not errors,
        "domain_count": inventory.get("domain_count", 0),
        "eligible_file_count": inventory.get("eligible_file_count", 0),
        "unique_prd_count": inventory.get("unique_prd_count", 0),
        "generated_prd_count": len(manifest_documents),
        "generated_e2e_count": len(manifest_e2e_contexts),
        "registered_code_count": len(registry),
        "errors": errors,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build or validate the lossless canonical PRD version 0 baseline from the active E2E inventory."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--repo", required=True, type=Path)
    build_parser.add_argument("--prune", action="store_true")
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--repo", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = build(args.repo, args.prune) if args.command == "build" else validate(args.repo)
    except (BaselineError, OSError) as exc:
        print(json.dumps({"valid": False, "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
