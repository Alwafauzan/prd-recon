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


INVENTORY_PATH = Path("reconciliation/e2e-inventory/domain-worklist.json")


def default_repo() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / INVENTORY_PATH).is_file():
            return parent
    return Path.cwd()


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.findall(r"[a-z0-9]+", value))


def load_inventory(repo: Path) -> dict[str, Any]:
    path = repo / INVENTORY_PATH
    if not path.is_file():
        raise ShowE2EError(f"E2E domain worklist not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("inventory_type") != "E2E_DOMAIN_WORKLIST" or not isinstance(
        payload.get("domains"), list
    ):
        raise ShowE2EError(f"Invalid E2E domain worklist: {path}")
    return payload


def candidate_view(domain: dict[str, Any]) -> dict[str, Any]:
    return {
        "e2e_code": domain.get("e2e_code", ""),
        "title": domain.get("title", ""),
        "domain_group": domain.get("domain_group", ""),
        "status": domain.get("status", ""),
        "document_count": domain.get("document_count", 0),
        "relation_count": domain.get("relation_count", 0),
        "cross_domain_relation_count": domain.get("cross_domain_relation_count", 0),
        "review_required_count": domain.get("review_required_count", 0),
    }


def resolve_e2e(domains: list[dict[str, Any]], selector: str) -> dict[str, Any]:
    selector = selector.strip()
    if not selector:
        raise ShowE2EError("E2E selector is empty.")
    folded = selector.casefold()
    exact_code = [item for item in domains if item.get("e2e_code", "").casefold() == folded]
    if exact_code:
        return exact_code[0]
    target = normalize(selector)
    exact_title = [item for item in domains if normalize(item.get("title", "")) == target]
    if len(exact_title) == 1:
        return exact_title[0]
    tokens = target.split()
    partial = []
    for domain in domains:
        haystack = normalize(
            " ".join(
                (
                    domain.get("e2e_code", ""),
                    domain.get("title", ""),
                    domain.get("domain_group", ""),
                )
            )
        )
        if target in haystack or (tokens and all(token in haystack for token in tokens)):
            partial.append(domain)
    if len(partial) == 1:
        return partial[0]
    if partial:
        raise ShowE2EError(
            f"E2E selector is ambiguous: {selector}",
            [candidate_view(item) for item in partial],
        )
    raise ShowE2EError(f"No E2E domain matches: {selector}")


def filter_domains(
    domains: list[dict[str, Any]], query: str | None, group: str | None, status: str | None
) -> list[dict[str, Any]]:
    matches = domains
    if query:
        tokens = normalize(query).split()
        matches = [
            item
            for item in matches
            if all(
                token
                in normalize(
                    " ".join(
                        (
                            item.get("e2e_code", ""),
                            item.get("title", ""),
                            item.get("domain_group", ""),
                            item.get("status", ""),
                        )
                    )
                )
                for token in tokens
            )
        ]
    if group:
        target = normalize(group)
        matches = [item for item in matches if target in normalize(item.get("domain_group", ""))]
    if status:
        target = normalize(status)
        matches = [item for item in matches if target == normalize(item.get("status", ""))]
    return sorted(matches, key=lambda item: (item.get("domain_group", ""), item.get("title", "")))


def inventory_payload(
    inventory: dict[str, Any], query: str | None, group: str | None, status: str | None, limit: int
) -> dict[str, Any]:
    domains = filter_domains(inventory["domains"], query, group, status)
    visible = domains[:limit]
    return {
        "mode": "inventory",
        "evidence_notice": (
            "Domain E2E adalah worklist pemeriksaan flow. Setiap PRD unik memiliki satu owner; "
            "pemakaian lintas domain ditampilkan sebagai relasi, bukan kepemilikan ganda."
        ),
        "inventory_counts": {
            "eligible_file_count": inventory.get("eligible_file_count", 0),
            "unique_prd_count": inventory.get("unique_prd_count", 0),
            "assigned_unique_prd_count": inventory.get("assigned_unique_prd_count", 0),
            "unassigned_unique_prd_count": inventory.get("unassigned_unique_prd_count", 0),
            "domain_count": inventory.get("domain_count", len(inventory["domains"])),
            "relation_count": inventory.get("relation_count", 0),
            "cross_domain_relation_count": inventory.get("cross_domain_relation_count", 0),
        },
        "filters": {"query": query, "group": group, "status": status},
        "total_matches": len(domains),
        "shown": len(visible),
        "group_counts": dict(sorted(Counter(item.get("domain_group", "") for item in domains).items())),
        "status_counts": dict(sorted(Counter(item.get("status", "") for item in domains).items())),
        "domains": [candidate_view(item) for item in visible],
    }


def detail_payload(inventory: dict[str, Any], domain: dict[str, Any]) -> dict[str, Any]:
    relation_ids = set(domain.get("relation_ids", []))
    relations = [row for row in inventory.get("relations", []) if row.get("relation_id") in relation_ids]
    return {
        "mode": "detail",
        "evidence_notice": (
            "Urutan ini adalah worklist review. Assignment mekanis dan relasi REVIEW_REQUIRED "
            "belum menjadi keputusan pengguna."
        ),
        "e2e": candidate_view(domain)
        | {
            "purpose": domain.get("purpose", ""),
            "origin": domain.get("origin", ""),
            "duplicate_representation_count": domain.get("duplicate_representation_count", 0),
        },
        "worklist": domain.get("documents", []),
        "relations": relations,
    }


def render_inventory(payload: dict[str, Any]) -> str:
    counts = payload["inventory_counts"]
    lines = [
        "# E2E Domain Worklists",
        "",
        f"> {payload['evidence_notice']}",
        "",
        f"- Domain: {counts['domain_count']}",
        f"- PRD unik terpetakan: {counts['assigned_unique_prd_count']} / {counts['unique_prd_count']}",
        f"- PRD tanpa domain: {counts['unassigned_unique_prd_count']}",
        f"- Relasi lintas domain: {counts['cross_domain_relation_count']}",
        "",
    ]
    grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for domain in payload["domains"]:
        grouped[domain["domain_group"]].append(domain)
    for group in sorted(grouped):
        lines.extend([f"## {group}", ""])
        for domain in grouped[group]:
            lines.append(
                f"- {domain['e2e_code']} | {domain['title']} | PRD={domain['document_count']} | "
                f"relasi={domain['relation_count']} | lintas-domain={domain['cross_domain_relation_count']} | "
                f"review={domain['review_required_count']}"
            )
        lines.append("")
    if payload["shown"] < payload["total_matches"]:
        lines.append("Result truncated. Gunakan filter atau naikkan --limit.")
    return "\n".join(lines).rstrip() + "\n"


def render_detail(payload: dict[str, Any]) -> str:
    e2e = payload["e2e"]
    lines = [
        f"# {e2e['e2e_code']} - {e2e['title']}",
        "",
        f"> {payload['evidence_notice']}",
        "",
        f"- Tujuan: {e2e['purpose']}",
        f"- Status: {e2e['status']}",
        f"- PRD unik: {e2e['document_count']}",
        f"- Relasi: {e2e['relation_count']}",
        f"- Relasi lintas domain: {e2e['cross_domain_relation_count']}",
        "",
        "## Worklist",
        "",
    ]
    for item in payload["worklist"]:
        pending = [name for name, state in item.get("flow_checks", {}).items() if state == "REVIEW_REQUIRED"]
        lines.append(
            f"{item['worklist_order']}. [{item['worklist_stage']}] {item['title']} | "
            f"{item['document_id']} | owner={e2e['e2e_code']} | "
            f"flow-check={','.join(pending) or 'source-context-present'}"
        )
    lines.extend(["", "## Relasi", ""])
    if not payload["relations"]:
        lines.append("- Tidak ada relasi terindeks.")
    for row in payload["relations"]:
        lines.append(
            f"- {row['source_title']} --{row['relationship_type']}--> {row['target_title']} | "
            f"{row['relation_scope']} | {row['verification_status']} | {row['conflict_status']} | "
            f"{row['evidence_reference']}"
        )
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Display Neurovi E2E domain worklists.")
    parser.add_argument("selector", nargs="?", help="E2E domain code or name")
    parser.add_argument("--e2e", help="E2E domain code or name")
    parser.add_argument("--query", help="Filter code, title, group, or status")
    parser.add_argument("--group", help="Filter domain group")
    parser.add_argument("--status", help="Filter exact status")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--repo", type=Path, default=default_repo())
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.limit < 1:
            raise ShowE2EError("--limit must be at least 1.")
        if args.e2e and args.selector:
            raise ShowE2EError("Use either positional selector or --e2e, not both.")
        inventory = load_inventory(args.repo.resolve())
        selector = args.e2e or args.selector
        if selector:
            if args.query or args.group or args.status:
                raise ShowE2EError("List filters cannot be combined with an E2E selector.")
            payload = detail_payload(inventory, resolve_e2e(inventory["domains"], selector))
            output = json.dumps(payload, ensure_ascii=False, indent=2) if args.json else render_detail(payload)
        else:
            payload = inventory_payload(inventory, args.query, args.group, args.status, args.limit)
            output = json.dumps(payload, ensure_ascii=False, indent=2) if args.json else render_inventory(payload)
        print(output, end="")
        return 0
    except (OSError, json.JSONDecodeError, ShowE2EError) as error:
        candidates = error.candidates if isinstance(error, ShowE2EError) else []
        if args.json:
            print(json.dumps({"error": str(error), "candidates": candidates}, ensure_ascii=False, indent=2))
        else:
            print(f"Error: {error}", file=sys.stderr)
            for item in candidates:
                print(f"- {item['e2e_code']} | {item['title']} | {item['domain_group']}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
