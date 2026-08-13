#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


class InventoryError(RuntimeError):
    pass


INVENTORY_PATH = Path("reconciliation/e2e-inventory/domain-worklist.json")
DOCUMENT_INDEX_PATH = Path("reconciliation/e2e-inventory/document-domain-index.csv")


def default_repo() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / INVENTORY_PATH).is_file():
            return parent
    return Path.cwd()


def read_json(path: Path) -> Any:
    if not path.is_file():
        raise InventoryError(f"Required inventory file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_inventory(repo: Path) -> dict[str, Any]:
    value = read_json(repo / INVENTORY_PATH)
    if value.get("inventory_type") != "E2E_DOMAIN_WORKLIST":
        raise InventoryError("The active inventory is not an E2E domain worklist.")
    return value


def load_documents(repo: Path) -> list[dict[str, Any]]:
    return read_json(repo / "catalog/document-index.json").get("documents", [])


def load_document_index(repo: Path) -> list[dict[str, str]]:
    path = repo / DOCUMENT_INDEX_PATH
    if not path.is_file():
        raise InventoryError(f"Required inventory file not found: {path}")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def resolve_domain(query: str, domains: list[dict[str, Any]]) -> dict[str, Any]:
    folded = query.casefold().strip()
    exact = [item for item in domains if item.get("e2e_code", "").casefold() == folded]
    if len(exact) == 1:
        return exact[0]
    exact = [item for item in domains if item.get("title", "").casefold() == folded]
    if len(exact) == 1:
        return exact[0]
    partial = [
        item
        for item in domains
        if folded in item.get("e2e_code", "").casefold()
        or folded in item.get("title", "").casefold()
    ]
    if len(partial) == 1:
        return partial[0]
    if partial:
        choices = ", ".join(f"{item['e2e_code']} ({item['title']})" for item in partial)
        raise InventoryError(f"Ambiguous E2E domain. Confirm one of: {choices}")
    raise InventoryError(f"No E2E domain matches: {query}")


def command_list_e2e(repo: Path) -> list[dict[str, Any]]:
    return [
        {
            "e2e_code": item.get("e2e_code", ""),
            "title": item.get("title", ""),
            "status": item.get("status", ""),
            "origin": item.get("origin", ""),
            "document_count": item.get("document_count", 0),
            "relation_count": item.get("relation_count", 0),
            "cross_domain_relation_count": item.get("cross_domain_relation_count", 0),
            "review_required_count": item.get("review_required_count", 0),
        }
        for item in sorted(load_inventory(repo)["domains"], key=lambda row: row.get("e2e_code", ""))
    ]


def command_show_e2e(repo: Path, query: str) -> dict[str, Any]:
    inventory = load_inventory(repo)
    domain = resolve_domain(query, inventory["domains"])
    relation_ids = set(domain.get("relation_ids", []))
    relations = [row for row in inventory.get("relations", []) if row.get("relation_id") in relation_ids]
    mapped_documents = []
    for item in domain.get("documents", []):
        mapped_documents.append(
            {
                "document_id": item.get("document_id", ""),
                "content_id": item.get("content_id", ""),
                "title": item.get("title", ""),
                "source_path": item.get("source_path", ""),
                "relationship_evidence": ["OWNER_DOMAIN"],
                "worklist_status": "OWNER_WORKLIST",
                "relationship_role": "PRIMARY_SCOPE",
                "worklist_stage": item.get("worklist_stage", ""),
                "worklist_order": item.get("worklist_order"),
                "assignment_status": item.get("assignment_status", ""),
                "assignment_confidence": item.get("assignment_confidence", ""),
                "review_status": item.get("review_status", ""),
                "source_representations": item.get("source_representations", []),
                "flow_checks": item.get("flow_checks", {}),
            }
        )
    related = {}
    owner_ids = {item["content_id"] for item in mapped_documents}
    document_by_content = {
        document.get("content_id", ""): document for document in load_document_index(repo)
    }
    for relation in relations:
        for side, role in (("source", "UPSTREAM"), ("target", "DOWNSTREAM")):
            content_id = relation.get(f"{side}_content_id", "")
            if not content_id or content_id in owner_ids:
                continue
            row = document_by_content.get(content_id, {})
            relationship = related.setdefault(
                content_id,
                {
                    "document_id": row.get("representative_document_id", relation.get(f"{side}_document_id", "")),
                    "content_id": content_id,
                    "title": row.get("representative_title", relation.get(f"{side}_title", "")),
                    "source_path": row.get("representative_source_path", ""),
                    "relationship_evidence": [],
                    "worklist_status": "RELATED_CONTEXT",
                    "relationship_role": role,
                    "owner_domain_code": row.get("owner_domain_code", relation.get(f"{side}_domain_code", "")),
                    "selectable_source_document": True,
                },
            )
            relationship["relationship_evidence"].append(relation["relation_id"])
    mapped_documents.extend(related.values())
    return {
        "e2e_code": domain.get("e2e_code", ""),
        "title": domain.get("title", ""),
        "status": domain.get("status", ""),
        "origin": domain.get("origin", ""),
        "routing_note": (
            "Domain and owner PRDs are automatic flow-checking routes. Assignment "
            "metadata is not a source fact and does not require user confirmation."
        ),
        "purpose": domain.get("purpose", ""),
        "document_count": domain.get("document_count", 0),
        "relation_count": domain.get("relation_count", 0),
        "cross_domain_relation_count": domain.get("cross_domain_relation_count", 0),
        "worklist": domain.get("documents", []),
        "mapped_documents": mapped_documents,
        "relations": relations,
        "explicit_memberships": [],
        "mechanical_candidates": [],
        "nodes": [],
        "edges": [],
    }


def command_find_document(repo: Path, query: str) -> list[dict[str, Any]]:
    folded = query.casefold().strip()
    rows = []
    for item in load_document_index(repo):
        values = (
            item.get("representative_document_id", ""),
            item.get("source_document_ids", ""),
            item.get("representative_title", ""),
            item.get("representative_source_path", ""),
            item.get("source_paths", ""),
            item.get("content_id", ""),
        )
        if not any(folded in value.casefold() for value in values):
            continue
        rows.append(item)
    return sorted(rows, key=lambda item: (item["owner_domain_code"], item["representative_title"].casefold()))


FORMAT_FAMILIES = {
    "overview_or_background": ("overview", "background", "summary", "ringkasan", "latar belakang"),
    "scope": ("scope", "ruang lingkup", "in scope", "out scope", "out of scope"),
    "actors_or_stakeholders": ("actor", "aktor", "persona", "stakeholder", "pengguna"),
    "flow_or_scenarios": ("flow", "alur", "process", "proses", "scenario", "skenario"),
    "business_rules": ("business rule", "aturan bisnis", "rule"),
    "logical_data": ("data", "input", "output", "entity", "entitas"),
    "cases_or_exceptions": ("case", "condition", "kondisi", "exception", "error", "alternate"),
    "acceptance": ("acceptance", "kriteria penerimaan", "criteria"),
}


def command_scan_format(repo: Path, document_id: str) -> dict[str, Any]:
    documents = {item.get("document_id", ""): item for item in load_documents(repo)}
    if document_id not in documents:
        raise InventoryError(f"Document not found: {document_id}")
    document = documents[document_id]
    headings = [item.get("text", "") for item in document.get("headings", [])]
    joined = "\n".join(headings).casefold()
    return {
        "document_id": document_id,
        "title": document.get("title", ""),
        "source_path": document.get("source_path", ""),
        "warning": "A missing heading is a format-gap candidate, not proof that source context is absent.",
        "heading_count": len(headings),
        "format_families": {
            family: {
                "status": "PRESENT" if any(token in joined for token in tokens) else "FORMAT_GAP_CANDIDATE",
                "matched_headings": [
                    heading for heading in headings if any(token in heading.casefold() for token in tokens)
                ],
            }
            for family, tokens in FORMAT_FAMILIES.items()
        },
    }


def print_markdown(value: Any) -> None:
    if isinstance(value, list):
        if not value:
            print("No results.")
            return
        fields = list(value[0].keys())
        print("| " + " | ".join(fields) + " |")
        print("|" + "|".join("---" for _ in fields) + "|")
        for row in value:
            print("| " + " | ".join(str(row.get(field, "")).replace("|", "\\|") for field in fields) + " |")
        return
    print(json.dumps(value, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only Neurovi E2E domain worklist inspector")
    parser.add_argument("--repo", type=Path, default=default_repo())
    parser.add_argument("--json", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list-e2e", help="List E2E domain worklists")
    show_e2e = subparsers.add_parser("show-e2e", help="Show one E2E domain worklist")
    show_e2e.add_argument("--e2e", required=True)
    find_document = subparsers.add_parser("find-document", help="Find eligible PRDs and their owner domain")
    find_document.add_argument("--query", required=True)
    scan_format = subparsers.add_parser("scan-format", help="Scan source heading families")
    scan_format.add_argument("--document", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo = args.repo.resolve()
    try:
        if args.command == "list-e2e":
            result = command_list_e2e(repo)
        elif args.command == "show-e2e":
            result = command_show_e2e(repo, args.e2e)
        elif args.command == "find-document":
            result = command_find_document(repo, args.query)
        else:
            result = command_scan_format(repo, args.document)
    except (InventoryError, json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_markdown(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
