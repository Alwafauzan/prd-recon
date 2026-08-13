#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from scan_gaps import (
    GapScanError,
    default_repo,
    load_inventory,
    resolve_e2e,
    scan_business_cases_e2e,
    scan_main_flow,
)


FLOW_CHECK_COUNT = 5

STATUS_LABELS = {
    "NO_REVIEW_CANDIDATE": "Tidak ada kandidat review",
    "MAIN_FLOW_REVIEW": "Tinjau alur utama",
    "BUSINESS_CASE_REVIEW": "Tinjau detail proses",
    "BOTH_REVIEW": "Tinjau alur dan detail",
}


def percentage(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 1)


def document_status(main_candidates: int, detail_candidates: int) -> str:
    if main_candidates and detail_candidates:
        return "BOTH_REVIEW"
    if main_candidates:
        return "MAIN_FLOW_REVIEW"
    if detail_candidates:
        return "BUSINESS_CASE_REVIEW"
    return "NO_REVIEW_CANDIDATE"


def scan_flow_health(repo: Path, query: str) -> dict[str, Any]:
    main_flow = scan_main_flow(repo, query)
    business_cases = scan_business_cases_e2e(
        repo, main_flow["e2e"]["e2e_code"]
    )
    detail_by_document = {
        row["document_id"]: row for row in business_cases["documents"]
    }
    documents = []
    for flow_document in main_flow["ordered_documents"]:
        document_id = flow_document["document_id"]
        detail_document = detail_by_document.get(document_id, {})
        flow_detected = sum(
            status == "SOURCE_CONTEXT_PRESENT"
            for status in flow_document.get("flow_checks", {}).values()
        )
        flow_candidates = int(flow_document.get("gap_candidate_count", 0))
        families = detail_document.get("families", [])
        detail_structured = sum(
            row.get("status") == "SECTION_PRESENT" for row in families
        )
        detail_unstructured = sum(
            row.get("status") == "CONTEXT_PRESENT_UNSTRUCTURED"
            for row in families
        )
        detail_detected = detail_structured + detail_unstructured
        detail_total = len(families)
        detail_candidates = int(
            detail_document.get("business_case_candidate_count", 0)
        )
        explicit_marker_count = len(
            detail_document.get("explicit_gap_markers", [])
        )
        status = document_status(flow_candidates, detail_candidates)
        documents.append(
            {
                "worklist_order": flow_document.get("worklist_order", 0),
                "worklist_stage": flow_document.get("worklist_stage", ""),
                "document_id": document_id,
                "title": flow_document.get("title", ""),
                "source_path": flow_document.get("source_path", ""),
                "main_flow": {
                    "detected_check_count": flow_detected,
                    "check_count": FLOW_CHECK_COUNT,
                    "detected_coverage_percent": percentage(
                        flow_detected, FLOW_CHECK_COUNT
                    ),
                    "review_candidate_count": flow_candidates,
                },
                "business_cases": {
                    "detected_context_count": detail_detected,
                    "structured_context_count": detail_structured,
                    "unstructured_context_count": detail_unstructured,
                    "context_count": detail_total,
                    "detected_coverage_percent": percentage(
                        detail_detected, detail_total
                    ),
                    "review_candidate_count": detail_candidates,
                    "explicit_marker_count": explicit_marker_count,
                    "candidate_families": detail_document.get(
                        "gap_candidate_families", []
                    ),
                },
                "combined_detected_coverage_percent": percentage(
                    flow_detected + detail_detected,
                    FLOW_CHECK_COUNT + detail_total,
                ),
                "review_candidate_count": flow_candidates + detail_candidates,
                "status": status,
                "status_label": STATUS_LABELS[status],
            }
        )

    document_count = len(documents)
    flow_detected_total = sum(
        row["main_flow"]["detected_check_count"] for row in documents
    )
    flow_check_total = sum(row["main_flow"]["check_count"] for row in documents)
    detail_detected_total = sum(
        row["business_cases"]["detected_context_count"] for row in documents
    )
    detail_context_total = sum(
        row["business_cases"]["context_count"] for row in documents
    )
    relation_candidates = int(
        main_flow["summary"].get("relation_gap_candidate_count", 0)
    )
    source_explicit_gaps = sum(
        row.get("evidence_class") == "SOURCE_EXPLICIT_GAP"
        for row in main_flow.get("gap_candidates", [])
    )
    documents_without_candidates = sum(
        row["status"] == "NO_REVIEW_CANDIDATE" for row in documents
    )
    return {
        "e2e_code": main_flow["e2e"]["e2e_code"],
        "title": main_flow["e2e"]["title"],
        "purpose": main_flow["e2e"].get("purpose", ""),
        "document_count": document_count,
        "documents_without_review_candidates": documents_without_candidates,
        "documents_needing_review": document_count - documents_without_candidates,
        "main_flow": {
            "detected_check_count": flow_detected_total,
            "check_count": flow_check_total,
            "detected_coverage_percent": percentage(
                flow_detected_total, flow_check_total
            ),
            "documents_needing_review": sum(
                row["main_flow"]["review_candidate_count"] > 0
                for row in documents
            ),
            "document_review_candidate_count": sum(
                row["main_flow"]["review_candidate_count"] for row in documents
            ),
            "relation_review_candidate_count": relation_candidates,
            "source_explicit_gap_count": source_explicit_gaps,
        },
        "business_cases": {
            "detected_context_count": detail_detected_total,
            "structured_context_count": sum(
                row["business_cases"]["structured_context_count"]
                for row in documents
            ),
            "unstructured_context_count": sum(
                row["business_cases"]["unstructured_context_count"]
                for row in documents
            ),
            "context_count": detail_context_total,
            "detected_coverage_percent": percentage(
                detail_detected_total, detail_context_total
            ),
            "documents_needing_review": sum(
                row["business_cases"]["review_candidate_count"] > 0
                for row in documents
            ),
            "review_candidate_count": sum(
                row["business_cases"]["review_candidate_count"]
                for row in documents
            ),
            "explicit_marker_count": sum(
                row["business_cases"]["explicit_marker_count"]
                for row in documents
            ),
        },
        "combined_detected_coverage_percent": percentage(
            flow_detected_total + detail_detected_total,
            flow_check_total + detail_context_total,
        ),
        "flow_relation_count": int(
            main_flow["summary"].get("flow_relation_count", 0)
        ),
        "cross_domain_flow_relation_count": int(
            main_flow["summary"].get("cross_domain_flow_relation_count", 0)
        ),
        "documents": documents,
    }


def build_health_report(flows: list[dict[str, Any]]) -> dict[str, Any]:
    flows.sort(key=lambda row: (row["title"].casefold(), row["e2e_code"]))
    document_ids = {
        document["document_id"]
        for flow in flows
        for document in flow["documents"]
    }
    document_count = sum(flow["document_count"] for flow in flows)
    flow_detected = sum(
        flow["main_flow"]["detected_check_count"] for flow in flows
    )
    flow_checks = sum(flow["main_flow"]["check_count"] for flow in flows)
    detail_detected = sum(
        flow["business_cases"]["detected_context_count"] for flow in flows
    )
    detail_contexts = sum(
        flow["business_cases"]["context_count"] for flow in flows
    )
    return {
        "report": "DOCUMENT_HEALTH",
        "authority": "DIAGNOSTIC_ONLY",
        "scope": (
            "Statistik kelengkapan konteks yang terdeteksi pada PRD owner-domain. "
            "Hasil bukan penilaian kebenaran semantik dan tidak mengubah dokumen."
        ),
        "summary": {
            "flow_count": len(flows),
            "document_count": document_count,
            "unique_document_count": len(document_ids),
            "duplicate_owner_document_count": document_count - len(document_ids),
            "documents_without_review_candidates": sum(
                flow["documents_without_review_candidates"] for flow in flows
            ),
            "documents_needing_review": sum(
                flow["documents_needing_review"] for flow in flows
            ),
            "main_flow": {
                "detected_check_count": flow_detected,
                "check_count": flow_checks,
                "detected_coverage_percent": percentage(
                    flow_detected, flow_checks
                ),
                "documents_needing_review": sum(
                    flow["main_flow"]["documents_needing_review"]
                    for flow in flows
                ),
                "document_review_candidate_count": sum(
                    flow["main_flow"]["document_review_candidate_count"]
                    for flow in flows
                ),
                "relation_review_candidate_count": sum(
                    flow["main_flow"]["relation_review_candidate_count"]
                    for flow in flows
                ),
                "source_explicit_gap_count": sum(
                    flow["main_flow"]["source_explicit_gap_count"]
                    for flow in flows
                ),
            },
            "business_cases": {
                "detected_context_count": detail_detected,
                "structured_context_count": sum(
                    flow["business_cases"]["structured_context_count"]
                    for flow in flows
                ),
                "unstructured_context_count": sum(
                    flow["business_cases"]["unstructured_context_count"]
                    for flow in flows
                ),
                "context_count": detail_contexts,
                "detected_coverage_percent": percentage(
                    detail_detected, detail_contexts
                ),
                "documents_needing_review": sum(
                    flow["business_cases"]["documents_needing_review"]
                    for flow in flows
                ),
                "review_candidate_count": sum(
                    flow["business_cases"]["review_candidate_count"]
                    for flow in flows
                ),
                "explicit_marker_count": sum(
                    flow["business_cases"]["explicit_marker_count"]
                    for flow in flows
                ),
            },
            "combined_detected_coverage_percent": percentage(
                flow_detected + detail_detected,
                flow_checks + detail_contexts,
            ),
        },
        "flows": flows,
        "warning": (
            "Kandidat review berasal dari pemeriksaan struktur, istilah, inventaris, "
            "dan relasi sumber. Kandidat bukan defect pasti sampai bukti dibaca dan "
            "dikonfirmasi melalui proses rekonsiliasi yang sesuai."
        ),
    }


def scan_repository_health(repo: Path) -> dict[str, Any]:
    inventory = load_inventory(repo)
    return build_health_report(
        [
            scan_flow_health(repo, domain["e2e_code"])
            for domain in inventory.get("domains", [])
        ]
    )


def markdown_escape(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")


def print_summary(summary: dict[str, Any]) -> None:
    main = summary["main_flow"]
    detail = summary["business_cases"]
    print(
        f"- Flow bisnis: **{summary['flow_count']}**; PRD unik: "
        f"**{summary['unique_document_count']}**."
    )
    print(
        f"- Cakupan alur utama terdeteksi: **{main['detected_coverage_percent']}%** "
        f"({main['detected_check_count']}/{main['check_count']} pemeriksaan)."
    )
    print(
        f"- Cakupan detail proses terdeteksi: "
        f"**{detail['detected_coverage_percent']}%** "
        f"({detail['detected_context_count']}/{detail['context_count']} konteks)."
    )
    print(
        f"- PRD tanpa kandidat review: **{summary['documents_without_review_candidates']}**; "
        f"perlu ditinjau: **{summary['documents_needing_review']}**."
    )
    print(
        f"- Penanda isi belum selesai: **{detail['explicit_marker_count']}**; "
        f"gap sumber eksplisit pada alur: **{main['source_explicit_gap_count']}**."
    )


def print_flow_table(flows: list[dict[str, Any]]) -> None:
    print("| Flow bisnis | PRD | Alur terdeteksi | Detail terdeteksi | PRD perlu ditinjau | Marker |")
    print("|---|---:|---:|---:|---:|---:|")
    for flow in flows:
        print(
            f"| {markdown_escape(flow['title'])} (`{flow['e2e_code']}`) | "
            f"{flow['document_count']} | "
            f"{flow['main_flow']['detected_coverage_percent']}% | "
            f"{flow['business_cases']['detected_coverage_percent']}% | "
            f"{flow['documents_needing_review']} | "
            f"{flow['business_cases']['explicit_marker_count']} |"
        )


def print_document_table(documents: list[dict[str, Any]]) -> None:
    print("| Urutan | Dokumen | Alur | Detail | Kandidat review | Status |")
    print("|---:|---|---:|---:|---:|---|")
    for row in documents:
        print(
            f"| {row['worklist_order']} | {markdown_escape(row['title'])} | "
            f"{row['main_flow']['detected_check_count']}/{row['main_flow']['check_count']} | "
            f"{row['business_cases']['detected_context_count']}/{row['business_cases']['context_count']} | "
            f"{row['review_candidate_count']} | {row['status_label']} |"
        )


def print_flow_report(report: dict[str, Any], selected: str | None) -> None:
    if selected:
        flow = next(
            row for row in report["flows"] if row["e2e_code"] == selected
        )
        print(f"# Kesehatan Dokumen - {flow['title']}")
        print()
        print(report["scope"])
        print()
        print(
            f"PRD: **{flow['document_count']}**; cakupan alur terdeteksi: "
            f"**{flow['main_flow']['detected_coverage_percent']}%**; cakupan "
            f"detail terdeteksi: **{flow['business_cases']['detected_coverage_percent']}%**."
        )
        print(
            f"PRD tanpa kandidat review: **{flow['documents_without_review_candidates']}**; "
            f"perlu ditinjau: **{flow['documents_needing_review']}**."
        )
        print()
        print_document_table(flow["documents"])
    else:
        print("# Kesehatan Dokumen per Flow Bisnis")
        print()
        print(report["scope"])
        print()
        print_summary(report["summary"])
        print()
        print_flow_table(report["flows"])
    print()
    print(report["warning"])


def print_overall_report(report: dict[str, Any]) -> None:
    print("# Kesehatan Dokumen Keseluruhan")
    print()
    print(report["scope"])
    print()
    print_summary(report["summary"])
    print()
    print("## Flow dengan kandidat review terbanyak")
    print()
    priority = sorted(
        report["flows"],
        key=lambda row: (
            -row["documents_needing_review"],
            row["combined_detected_coverage_percent"],
            row["title"].casefold(),
        ),
    )[:10]
    print_flow_table(priority)
    print()
    print(report["warning"])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only Neurovi document health statistics"
    )
    parser.add_argument("--repo", type=Path, default=default_repo())
    parser.add_argument("--json", action="store_true")
    subparsers = parser.add_subparsers(dest="report", required=True)
    flow = subparsers.add_parser("flow", help="Show health per business flow")
    flow.add_argument("--e2e", help="Optional E2E code or name")
    subparsers.add_parser("all", help="Show overall repository health")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo = args.repo.resolve()
    try:
        selected_code = None
        if args.report == "flow" and args.e2e:
            inventory = load_inventory(repo)
            selected_code = resolve_e2e(
                args.e2e, inventory.get("domains", [])
            )["e2e_code"]
            report = build_health_report(
                [scan_flow_health(repo, selected_code)]
            )
        else:
            report = scan_repository_health(repo)
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        elif args.report == "flow":
            print_flow_report(report, selected_code)
        else:
            print_overall_report(report)
    except (GapScanError, json.JSONDecodeError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
