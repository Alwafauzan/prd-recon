#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


class InventoryError(RuntimeError):
    pass


def default_repo() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "catalog/document-index.json").is_file() and (parent / "reconciliation").is_dir():
            return parent
    return Path.cwd()


def read_json(path: Path) -> Any:
    if not path.is_file():
        raise InventoryError(f"Required inventory file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_domains(repo: Path) -> list[dict[str, Any]]:
    path = repo / "reconciliation/e2e-inventory/e2e-domain-inventory.json"
    return read_json(path).get("domains", [])


def load_documents(repo: Path) -> list[dict[str, Any]]:
    path = repo / "catalog/document-index.json"
    return read_json(path).get("documents", [])


def load_coverage(repo: Path) -> dict[str, dict[str, str]]:
    path = repo / "reconciliation/e2e-inventory/document-e2e-coverage.csv"
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {row["document_id"]: row for row in csv.DictReader(handle)}


def resolve_domain(query: str, domains: list[dict[str, Any]]) -> dict[str, Any]:
    folded = query.casefold().strip()
    exact_code = [item for item in domains if item.get("e2e_code", "").casefold() == folded]
    if len(exact_code) == 1:
        return exact_code[0]
    exact_title = [item for item in domains if item.get("title", "").casefold() == folded]
    if len(exact_title) == 1:
        return exact_title[0]
    partial = [
        item
        for item in domains
        if folded in item.get("e2e_code", "").casefold() or folded in item.get("title", "").casefold()
    ]
    if len(partial) == 1:
        return partial[0]
    if partial:
        choices = ", ".join(f"{item['e2e_code']} ({item['title']})" for item in partial)
        raise InventoryError(f"Ambiguous E2E query. Confirm one of: {choices}")
    raise InventoryError(f"No E2E matches: {query}")


def aggregate_candidates(domain: dict[str, Any]) -> list[dict[str, Any]]:
    grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in domain.get("flow_title_candidates", []):
        grouped[candidate["candidate_document_id"]].append({**candidate, "matched_context": "PROCESS_TITLE"})
    for node in domain.get("nodes", []):
        for candidate in node.get("document_candidates", []):
            grouped[candidate["candidate_document_id"]].append(
                {**candidate, "matched_context": node.get("node_label", node.get("node_id", ""))}
            )

    rows = []
    for document_id, matches in grouped.items():
        first = matches[0]
        rows.append(
            {
                "document_id": document_id,
                "title": first.get("candidate_title", ""),
                "source_path": first.get("source_path", ""),
                "artifact_type": first.get("artifact_type", ""),
                "max_score": max(int(item.get("match_score", 0)) for item in matches),
                "candidate_statuses": sorted({item.get("candidate_status", "") for item in matches}),
                "matched_contexts": sorted({item.get("matched_context", "") for item in matches}),
                "relationship_status": "MECHANICAL_CANDIDATE",
            }
        )
    return sorted(rows, key=lambda item: (-item["max_score"], item["title"].casefold(), item["document_id"]))


def command_list_e2e(repo: Path) -> list[dict[str, Any]]:
    return [
        {
            "e2e_code": item.get("e2e_code", ""),
            "title": item.get("title", ""),
            "status": item.get("status", ""),
            "origin": item.get("origin", ""),
            "explicit_membership_count": item.get("explicit_membership_count", 0),
            "candidate_match_count": item.get("candidate_match_count", 0),
        }
        for item in sorted(load_domains(repo), key=lambda row: row.get("e2e_code", ""))
    ]


def command_show_e2e(repo: Path, query: str) -> dict[str, Any]:
    domain = resolve_domain(query, load_domains(repo))
    return {
        "e2e_code": domain.get("e2e_code", ""),
        "title": domain.get("title", ""),
        "status": domain.get("status", ""),
        "origin": domain.get("origin", ""),
        "boundary_warning": "Candidate until explicitly confirmed by the user",
        "source_flow": {
            "document_id": domain.get("flow_document_id", ""),
            "source_path": domain.get("source_path", ""),
        },
        "explicit_memberships": domain.get("explicit_memberships", []),
        "mechanical_candidates": aggregate_candidates(domain),
        "nodes": [
            {
                "node_order": node.get("node_order"),
                "node_id": node.get("node_id", ""),
                "node_label": node.get("node_label", ""),
            }
            for node in domain.get("nodes", [])
        ],
        "edges": domain.get("edges", []),
    }


def command_find_document(repo: Path, query: str) -> list[dict[str, Any]]:
    folded = query.casefold().strip()
    coverage = load_coverage(repo)
    matches = []
    for document in load_documents(repo):
        values = [document.get("document_id", ""), document.get("title", ""), document.get("source_path", "")]
        if not any(folded in value.casefold() for value in values):
            continue
        coverage_row = coverage.get(document.get("document_id", ""), {})
        matches.append(
            {
                "document_id": document.get("document_id", ""),
                "content_id": document.get("content_id", ""),
                "title": document.get("title", ""),
                "source_path": document.get("source_path", ""),
                "extension": document.get("extension", ""),
                "coverage_status": coverage_row.get("coverage_status", ""),
                "explicit_process_ids": coverage_row.get("explicit_process_ids", ""),
                "mechanical_candidate_e2e_codes": coverage_row.get("mechanical_candidate_e2e_codes", ""),
                "source_flow_e2e_codes": coverage_row.get("source_flow_e2e_codes", ""),
            }
        )
    return sorted(matches, key=lambda item: (item["title"].casefold(), item["source_path"].casefold()))


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
    family_results = {}
    for family, tokens in FORMAT_FAMILIES.items():
        family_results[family] = {
            "status": "PRESENT" if any(token in joined for token in tokens) else "FORMAT_GAP_CANDIDATE",
            "matched_headings": [heading for heading in headings if any(token in heading.casefold() for token in tokens)],
        }
    return {
        "document_id": document_id,
        "title": document.get("title", ""),
        "source_path": document.get("source_path", ""),
        "warning": "A missing heading is a format-gap candidate, not proof that source context is absent.",
        "heading_count": len(headings),
        "format_families": family_results,
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
    parser = argparse.ArgumentParser(description="Read-only Neurovi E2E and PRD inventory inspector")
    parser.add_argument("--repo", type=Path, default=default_repo(), help="Neurovi PRD repository root")
    parser.add_argument("--json", action="store_true", help="Print JSON")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list-e2e", help="List E2E candidates")

    show_e2e = subparsers.add_parser("show-e2e", help="Show one E2E and separated evidence classes")
    show_e2e.add_argument("--e2e", required=True, help="E2E code or name")

    find_document = subparsers.add_parser("find-document", help="Find documents by ID, title, or path")
    find_document.add_argument("--query", required=True)

    scan_format = subparsers.add_parser("scan-format", help="Scan source heading families without editing")
    scan_format.add_argument("--document", required=True, help="Document ID")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
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
