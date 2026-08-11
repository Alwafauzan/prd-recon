#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


class ShowE2EError(RuntimeError):
    def __init__(self, message: str, candidates: list[dict[str, Any]] | None = None):
        super().__init__(message)
        self.candidates = candidates or []


def default_repo() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "reconciliation/e2e-inventory/e2e-domain-inventory.json").is_file():
            return parent
    return Path.cwd()


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.findall(r"[a-z0-9]+", value))


def load_inventory(repo: Path) -> dict[str, Any]:
    path = repo / "reconciliation/e2e-inventory/e2e-domain-inventory.json"
    if not path.is_file():
        raise ShowE2EError(f"E2E inventory not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload.get("domains"), list):
        raise ShowE2EError(f"Invalid E2E inventory: {path}")
    return payload


def candidate_view(domain: dict[str, Any]) -> dict[str, Any]:
    return {
        "e2e_code": domain.get("e2e_code", ""),
        "title": domain.get("title", ""),
        "macro_group": domain.get("macro_group", ""),
        "status": domain.get("status", ""),
    }


def resolve_e2e(domains: list[dict[str, Any]], selector: str) -> dict[str, Any]:
    selector = selector.strip()
    if not selector:
        raise ShowE2EError("E2E selector is empty.")

    folded = selector.casefold()
    exact_code = [
        domain for domain in domains if domain.get("e2e_code", "").casefold() == folded
    ]
    if exact_code:
        return exact_code[0]

    target = normalize(selector)
    exact_title = [
        domain for domain in domains if normalize(domain.get("title", "")) == target
    ]
    if len(exact_title) == 1:
        return exact_title[0]
    if len(exact_title) > 1:
        raise ShowE2EError(
            f"E2E selector is ambiguous: {selector}",
            [candidate_view(domain) for domain in exact_title],
        )

    tokens = target.split()
    partial = []
    for domain in domains:
        haystack = normalize(
            " ".join(
                [
                    domain.get("e2e_code", ""),
                    domain.get("title", ""),
                    domain.get("macro_group", ""),
                ]
            )
        )
        if target in haystack or (tokens and all(token in haystack for token in tokens)):
            partial.append(domain)

    if len(partial) == 1:
        return partial[0]
    if len(partial) > 1:
        raise ShowE2EError(
            f"E2E selector is ambiguous: {selector}",
            [candidate_view(domain) for domain in partial],
        )
    raise ShowE2EError(f"No E2E matches: {selector}")


def filter_domains(
    domains: list[dict[str, Any]],
    query: str | None,
    macro_group: str | None,
    status: str | None,
) -> list[dict[str, Any]]:
    matches = domains

    if query:
        tokens = normalize(query).split()
        matches = [
            domain
            for domain in matches
            if all(
                token
                in normalize(
                    " ".join(
                        [
                            domain.get("e2e_code", ""),
                            domain.get("title", ""),
                            domain.get("macro_group", ""),
                            domain.get("status", ""),
                        ]
                    )
                )
                for token in tokens
            )
        ]

    if macro_group:
        target = normalize(macro_group)
        matches = [
            domain
            for domain in matches
            if target in normalize(domain.get("macro_group", ""))
        ]

    if status:
        target = normalize(status)
        matches = [
            domain for domain in matches if target == normalize(domain.get("status", ""))
        ]

    return sorted(
        matches,
        key=lambda domain: (
            domain.get("macro_group", "").casefold(),
            domain.get("e2e_code", "").casefold(),
        ),
    )


def inventory_payload(
    inventory: dict[str, Any],
    query: str | None,
    macro_group: str | None,
    status: str | None,
    limit: int,
) -> dict[str, Any]:
    domains = filter_domains(inventory["domains"], query, macro_group, status)
    visible = domains[:limit]
    return {
        "mode": "inventory",
        "evidence_notice": (
            "E2E boundaries are inventory candidates unless the exact status states otherwise; "
            "mechanical candidate matches are not approved document memberships."
        ),
        "inventory_counts": {
            "source_flow_count": inventory.get("source_flow_count", 0),
            "e2e_domain_count": inventory.get("e2e_domain_count", len(inventory["domains"])),
            "manual_e2e_count": inventory.get("manual_e2e_count", 0),
            "reference_flow_count": inventory.get("reference_flow_count", 0),
            "duplicate_flow_count": inventory.get("duplicate_flow_count", 0),
        },
        "filters": {
            "query": query,
            "macro_group": macro_group,
            "status": status,
        },
        "total_matches": len(domains),
        "shown": len(visible),
        "group_counts": dict(
            sorted(Counter(domain.get("macro_group", "") for domain in domains).items())
        ),
        "status_counts": dict(
            sorted(Counter(domain.get("status", "") for domain in domains).items())
        ),
        "domains": [
            candidate_view(domain)
            | {
                "node_count": domain.get("node_count", 0),
                "edge_count": domain.get("edge_count", 0),
                "explicit_process_ids": domain.get("explicit_process_ids", ""),
                "explicit_membership_count": domain.get("explicit_membership_count", 0),
                "manual_stage_count": domain.get("manual_stage_count", 0),
                "manual_candidate_membership_count": domain.get(
                    "manual_candidate_membership_count", 0
                ),
                "candidate_match_count": domain.get("candidate_match_count", 0),
            }
            for domain in visible
        ],
    }


def detail_payload(domain: dict[str, Any]) -> dict[str, Any]:
    nodes = [
        {
            "order": node.get("node_order"),
            "node_id": node.get("node_id"),
            "label": node.get("node_label"),
            "shape": node.get("node_shape"),
            "source_line": node.get("first_line"),
            "mechanical_candidate_count": len(node.get("document_candidates", [])),
        }
        for node in domain.get("nodes", [])
    ]
    edges = [
        {
            "order": edge.get("edge_order"),
            "from_node": edge.get("from_node"),
            "to_node": edge.get("to_node"),
            "label": edge.get("edge_label", ""),
            "source_line_number": edge.get("source_line_number"),
            "source_line": edge.get("source_line"),
        }
        for edge in domain.get("edges", [])
    ]
    memberships = sorted(
        domain.get("explicit_memberships", []),
        key=lambda item: (item.get("process_code", ""), item.get("stage_code", "")),
    )
    return {
        "mode": "detail",
        "evidence_notice": (
            "Nodes and edges are literal source-flow extraction. Source-explicit memberships "
            "are separate from mechanical document candidates."
        ),
        "e2e": candidate_view(domain)
        | {
            "origin": domain.get("origin", ""),
            "flow_id": domain.get("flow_id", ""),
            "flow_document_id": domain.get("flow_document_id", ""),
            "source_path": f"source/original/{domain.get('source_path', '')}",
            "node_count": domain.get("node_count", len(nodes)),
            "edge_count": domain.get("edge_count", len(edges)),
            "explicit_process_ids": [
                item
                for item in domain.get("explicit_process_ids", "").split("|")
                if item
            ],
            "explicit_membership_count": domain.get("explicit_membership_count", 0),
            "manual_stage_count": domain.get("manual_stage_count", 0),
            "manual_candidate_membership_count": domain.get(
                "manual_candidate_membership_count", 0
            ),
            "candidate_match_count": domain.get("candidate_match_count", 0),
            "notes": domain.get("notes", ""),
        },
        "nodes": nodes,
        "edges": edges,
        "source_explicit_memberships": [
            {
                "process_code": item.get("process_code", ""),
                "stage_code": item.get("stage_code", ""),
                "document_id": item.get("document_id", ""),
                "document_title": item.get("document_title", ""),
                "role": item.get("membership_role", ""),
                "status": item.get("membership_status", ""),
                "basis": item.get("basis", ""),
                "notes": item.get("notes", ""),
                "source_path": (
                    f"source/original/{item.get('source_path', '')}"
                    if item.get("source_path")
                    else ""
                ),
            }
            for item in memberships
        ],
    }


def render_inventory(payload: dict[str, Any]) -> str:
    counts = payload["inventory_counts"]
    lines = [
        "# E2E Inventory",
        "",
        f"> {payload['evidence_notice']}",
        "",
        f"- Total E2E domains: {counts['e2e_domain_count']}",
        f"- Matching current filter: {payload['total_matches']}",
        f"- Shown: {payload['shown']}",
        f"- Source flows: {counts['source_flow_count']}",
        f"- Manual E2Es: {counts['manual_e2e_count']}",
        "",
    ]

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for domain in payload["domains"]:
        grouped[domain["macro_group"]].append(domain)

    for macro_group in sorted(grouped):
        lines.append(f"## {macro_group}")
        lines.append("")
        for domain in grouped[macro_group]:
            process_ids = domain.get("explicit_process_ids") or "-"
            lines.append(
                f"- {domain['e2e_code']} | {domain['title']} | {domain['status']} | "
                f"nodes={domain['node_count']} edges={domain['edge_count']} | "
                f"explicit_paths={process_ids} | "
                f"source_memberships={domain['explicit_membership_count']} | "
                f"mechanical_candidates={domain['candidate_match_count']}"
            )
        lines.append("")

    if payload["shown"] < payload["total_matches"]:
        lines.append(
            "Result truncated. Use --query, --group, --status, or increase --limit."
        )
    return "\n".join(lines).rstrip() + "\n"


def render_detail(payload: dict[str, Any]) -> str:
    e2e = payload["e2e"]
    process_ids = "|".join(e2e["explicit_process_ids"]) or "-"
    lines = [
        f"# {e2e['e2e_code']} - {e2e['title']}",
        "",
        f"> {payload['evidence_notice']}",
        "",
        f"- Status: {e2e['status']}",
        f"- Macro group: {e2e['macro_group']}",
        f"- Origin: {e2e['origin']}",
        f"- Source flow document: {e2e['flow_document_id']}",
        f"- Source path: {e2e['source_path']}",
        f"- Nodes / edges: {e2e['node_count']} / {e2e['edge_count']}",
        f"- Explicit process paths: {process_ids}",
        f"- Source-explicit memberships: {e2e['explicit_membership_count']}",
        f"- Mechanical candidate matches: {e2e['candidate_match_count']}",
        f"- Notes: {e2e['notes'] or '-'}",
        "",
        "## Flow Nodes",
        "",
    ]

    for node in payload["nodes"]:
        lines.append(
            f"{node['order']}. {node['node_id']} | {node['label']} | "
            f"shape={node['shape']} | source_line={node['source_line']} | "
            f"mechanical_candidates={node['mechanical_candidate_count']}"
        )

    lines.extend(["", "## Flow Edges", ""])
    for edge in payload["edges"]:
        label = edge["label"] or "-"
        lines.append(
            f"{edge['order']}. {edge['from_node']} -> {edge['to_node']} | "
            f"label={label} | source_line={edge['source_line_number']}"
        )

    lines.extend(["", "## Source-Explicit Document Memberships", ""])
    if not payload["source_explicit_memberships"]:
        lines.append("- None.")
    else:
        for membership in payload["source_explicit_memberships"]:
            note = membership["notes"] or "-"
            lines.append(
                f"- {membership['process_code']}/{membership['stage_code']} | "
                f"{membership['document_id']} | {membership['document_title']} | "
                f"role={membership['role']} | status={membership['status']} | "
                f"notes={note}"
            )
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Display the read-only Neurovi E2E inventory."
    )
    parser.add_argument("selector", nargs="?", help="E2E code or name")
    parser.add_argument("--e2e", help="E2E code or name")
    parser.add_argument("--query", help="Filter code, title, group, or status")
    parser.add_argument("--group", help="Filter macro group")
    parser.add_argument("--status", help="Filter exact inventory status")
    parser.add_argument("--limit", type=int, default=100, help="Maximum list entries")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    parser.add_argument("--repo", type=Path, default=default_repo(), help="Repository root")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.limit < 1:
            raise ShowE2EError("--limit must be at least 1.")
        if args.e2e and args.selector:
            raise ShowE2EError("Use either a positional selector or --e2e, not both.")

        inventory = load_inventory(args.repo.resolve())
        selector = args.e2e or args.selector
        if selector:
            if args.query or args.group or args.status:
                raise ShowE2EError(
                    "List filters cannot be combined with a single E2E selector."
                )
            domain = resolve_e2e(inventory["domains"], selector)
            payload = detail_payload(domain)
            output = (
                json.dumps(payload, ensure_ascii=False, indent=2)
                if args.json
                else render_detail(payload)
            )
        else:
            payload = inventory_payload(
                inventory, args.query, args.group, args.status, args.limit
            )
            output = (
                json.dumps(payload, ensure_ascii=False, indent=2)
                if args.json
                else render_inventory(payload)
            )
        print(output, end="")
        return 0
    except (OSError, json.JSONDecodeError, ShowE2EError) as error:
        candidates = error.candidates if isinstance(error, ShowE2EError) else []
        payload = {"error": str(error), "candidates": candidates}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"Error: {error}", file=sys.stderr)
            for candidate in candidates:
                print(
                    f"- {candidate['e2e_code']} | {candidate['title']} | "
                    f"{candidate['macro_group']} | {candidate['status']}",
                    file=sys.stderr,
                )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
