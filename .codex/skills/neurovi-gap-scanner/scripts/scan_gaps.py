#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


class GapScanError(RuntimeError):
    pass


SECTION_FAMILIES = {
    "PURPOSE_BACKGROUND": {
        "heading": ("overview", "background", "ringkasan", "latar belakang", "tujuan"),
        "text": ("latar belakang", "tujuan dokumen", "brief summary"),
    },
    "SCOPE": {
        "heading": ("in scope", "scope", "ruang lingkup"),
        "text": ("dalam cakupan", "ruang lingkup", "in scope"),
    },
    "OUT_OF_SCOPE": {
        "heading": ("out of scope", "out scope", "di luar scope", "tidak termasuk"),
        "text": ("out of scope", "di luar cakupan", "tidak termasuk dalam scope"),
    },
    "ACTORS_STAKEHOLDERS": {
        "heading": ("actor", "aktor", "persona", "stakeholder", "pengguna"),
        "text": ("aktor utama", "pengguna sistem", "stakeholder"),
    },
    "TRIGGER_PRECONDITIONS": {
        "heading": ("precondition", "prasyarat", "prerequisite", "trigger", "pemicu"),
        "text": ("precondition", "prasyarat", "dipicu ketika", "trigger"),
    },
    "MAIN_FLOW": {
        "heading": ("main flow", "alur utama", "business process", "proses bisnis", "to-be"),
        "text": ("main flow", "alur utama", "proses bisnis"),
    },
    "ALTERNATE_FLOW": {
        "heading": ("alternate flow", "alternative flow", "alur alternatif", "skenario alternatif"),
        "text": ("alternate flow", "alur alternatif", "skenario alternatif"),
    },
    "ERROR_EXCEPTION": {
        "heading": ("error", "exception", "pengecualian", "kegagalan"),
        "text": ("error handling", "exception", "jika gagal", "kondisi gagal"),
    },
    "CASES_CONDITIONS": {
        "heading": ("case", "condition", "kondisi", "skenario"),
        "text": ("skenario", "case", "kondisi ketika"),
    },
    "BUSINESS_RULES": {
        "heading": ("business rule", "aturan bisnis"),
        "text": ("business rule", "aturan bisnis"),
    },
    "LOGICAL_DATA_FLOW": {
        "heading": ("data requirement", "data flow", "alur data", "spesifikasi field", "input", "output"),
        "text": ("data input", "data output", "alur data", "data requirement"),
    },
    "STATUS_LIFECYCLE": {
        "heading": ("status", "lifecycle", "state transition", "transisi status"),
        "text": ("status berubah", "state transition", "transisi status", "lifecycle"),
    },
    "DEPENDENCIES_INTEGRATION": {
        "heading": ("dependency", "dependensi", "integration", "integrasi", "related feature"),
        "text": ("bergantung pada", "dependensi", "integrasi dengan", "related feature"),
    },
    "ACCEPTANCE_CRITERIA": {
        "heading": ("acceptance criteria", "kriteria penerimaan", "acceptance"),
        "text": ("acceptance criteria", "kriteria penerimaan"),
    },
}

EXPLICIT_GAP_MARKERS = (
    "tbd",
    "to be defined",
    "belum ditentukan",
    "belum didefinisikan",
    "belum tersedia",
    "not defined",
)


def default_repo() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "catalog/document-index.json").is_file() and (parent / "reconciliation").is_dir():
            return parent
    return Path.cwd()


def read_json(path: Path) -> Any:
    if not path.is_file():
        raise GapScanError(f"Required file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_optional(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_domains(repo: Path) -> list[dict[str, Any]]:
    path = repo / "reconciliation/e2e-inventory/e2e-domain-inventory.json"
    return read_json(path).get("domains", [])


def load_documents(repo: Path) -> dict[str, dict[str, Any]]:
    path = repo / "catalog/document-index.json"
    return {item["document_id"]: item for item in read_json(path).get("documents", [])}


def load_coverage(repo: Path) -> dict[str, dict[str, str]]:
    path = repo / "reconciliation/e2e-inventory/document-e2e-coverage.csv"
    return {row["document_id"]: row for row in read_csv_optional(path)}


def resolve_e2e(query: str, domains: list[dict[str, Any]]) -> dict[str, Any]:
    folded = query.casefold().strip()
    for key in ("e2e_code", "title"):
        matches = [item for item in domains if item.get(key, "").casefold() == folded]
        if len(matches) == 1:
            return matches[0]
    partial = [
        item
        for item in domains
        if folded in item.get("e2e_code", "").casefold() or folded in item.get("title", "").casefold()
    ]
    if len(partial) == 1:
        return partial[0]
    if partial:
        choices = ", ".join(f"{item['e2e_code']} ({item['title']})" for item in partial)
        raise GapScanError(f"Ambiguous E2E. Choose one of: {choices}")
    raise GapScanError(f"No E2E matches: {query}")


def resolve_document(query: str, documents: dict[str, dict[str, Any]]) -> dict[str, Any]:
    folded = query.casefold().strip()
    if query in documents:
        return documents[query]
    for key in ("title", "source_path"):
        matches = [item for item in documents.values() if item.get(key, "").casefold() == folded]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            choices = ", ".join(f"{item['document_id']} ({item['title']})" for item in matches[:20])
            raise GapScanError(f"Ambiguous document. Choose one of: {choices}")
    partial = [
        item
        for item in documents.values()
        if folded in item.get("document_id", "").casefold()
        or folded in item.get("title", "").casefold()
        or folded in item.get("source_path", "").casefold()
    ]
    if len(partial) == 1:
        return partial[0]
    if partial:
        choices = ", ".join(f"{item['document_id']} ({item['title']})" for item in partial[:20])
        raise GapScanError(f"Ambiguous document. Choose one of: {choices}")
    raise GapScanError(f"No document matches: {query}")


def workspace_rows(repo: Path, e2e_code: str) -> dict[str, list[dict[str, str]]]:
    workspace = repo / "reconciliation/workspaces" / e2e_code
    return {
        "selections": read_csv_optional(workspace / "document-selection.csv"),
        "traces": read_csv_optional(workspace / "context-trace.csv"),
        "defects": read_csv_optional(workspace / "defect-register.csv"),
        "interviews": read_csv_optional(workspace / "interview-register.csv"),
    }


def split_codes(value: str) -> set[str]:
    return {item for item in value.split("|") if item}


def document_content(repo: Path, document_id: str) -> str:
    path = repo / "documents" / document_id / "content.md"
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


def scan_document_internal(repo: Path, document: dict[str, Any]) -> dict[str, Any]:
    headings = [item.get("text", "") for item in document.get("headings", [])]
    if document.get("extension", "").casefold() in {".mmd", ".json", ".html", ".svg"}:
        return {
            "document_id": document["document_id"],
            "title": document.get("title", ""),
            "source_path": document.get("source_path", ""),
            "content_id": document.get("content_id", ""),
            "artifact_type_warning": "Non-PRD artifact; internal PRD context scan is not applicable.",
            "context_family_count": 0,
            "gap_candidate_count": 0,
            "gap_candidate_families": [],
            "families": [],
            "explicit_gap_markers": [],
        }
    folded_headings = [item.casefold() for item in headings]
    content = document_content(repo, document["document_id"])
    folded_content = content.casefold()
    families = []
    for family, patterns in SECTION_FAMILIES.items():
        matched_headings = [
            heading
            for heading, folded in zip(headings, folded_headings)
            if any(token in folded for token in patterns["heading"])
        ]
        matched_terms = sorted({token for token in patterns["text"] if token in folded_content})
        if matched_headings:
            status = "SECTION_PRESENT"
        elif matched_terms:
            status = "CONTEXT_PRESENT_UNSTRUCTURED"
        else:
            status = "CONTEXT_GAP_CANDIDATE"
        families.append(
            {
                "context_family": family,
                "status": status,
                "matched_headings": matched_headings,
                "matched_terms": matched_terms,
                "evidence_class": "MECHANICAL_GAP_CANDIDATE" if status == "CONTEXT_GAP_CANDIDATE" else "MECHANICAL_STRUCTURE_EVIDENCE",
            }
        )

    explicit_markers = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        folded = line.casefold()
        markers = [marker for marker in EXPLICIT_GAP_MARKERS if re.search(rf"\b{re.escape(marker)}\b", folded)]
        if markers:
            explicit_markers.append(
                {
                    "line": line_number,
                    "markers": markers,
                    "text": line.strip()[:300],
                    "status": "EXPLICIT_GAP_MARKER_CANDIDATE",
                }
            )
        if len(explicit_markers) >= 20:
            break

    gap_families = [item["context_family"] for item in families if item["status"] == "CONTEXT_GAP_CANDIDATE"]
    return {
        "document_id": document["document_id"],
        "title": document.get("title", ""),
        "source_path": document.get("source_path", ""),
        "content_id": document.get("content_id", ""),
        "artifact_type_warning": "Scan is structural and lexical; verify context manually.",
        "context_family_count": len(families),
        "gap_candidate_count": len(gap_families) + len(explicit_markers),
        "gap_candidate_families": gap_families,
        "families": families,
        "explicit_gap_markers": explicit_markers,
    }


def related_documents(domain: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}

    def add(document_id: str, evidence: str, title: str = "", source_path: str = "", score: int = 0) -> None:
        if not document_id:
            return
        row = rows.setdefault(
            document_id,
            {
                "document_id": document_id,
                "title": title,
                "source_path": source_path,
                "relationship_evidence": set(),
                "matched_contexts": set(),
                "max_match_score": 0,
            },
        )
        row["relationship_evidence"].add(evidence)
        row["max_match_score"] = max(row["max_match_score"], score)

    add(domain.get("flow_document_id", ""), "SOURCE_FLOW", domain.get("title", ""), domain.get("source_path", ""))
    for membership in domain.get("explicit_memberships", []):
        add(
            membership.get("document_id", ""),
            "SOURCE_EXPLICIT_MEMBERSHIP",
            membership.get("document_title", ""),
            membership.get("source_path", ""),
        )
    candidate_sources = [("PROCESS_TITLE", domain.get("flow_title_candidates", []))]
    candidate_sources.extend(
        (node.get("node_label", node.get("node_id", "")), node.get("document_candidates", []))
        for node in domain.get("nodes", [])
    )
    for context, candidates in candidate_sources:
        for candidate in candidates:
            document_id = candidate.get("candidate_document_id", "")
            add(
                document_id,
                candidate.get("candidate_status", "MECHANICAL_CANDIDATE"),
                candidate.get("candidate_title", ""),
                candidate.get("source_path", ""),
                int(candidate.get("match_score", 0)),
            )
            if document_id:
                rows[document_id]["matched_contexts"].add(context)
    return rows


def e2e_gap_summary(repo: Path, domain: dict[str, Any]) -> dict[str, Any]:
    rows = workspace_rows(repo, domain["e2e_code"])
    gap_types: list[str] = []
    counts: dict[str, int] = {}

    def gap(gap_type: str, count: int = 1) -> None:
        if count <= 0:
            return
        gap_types.append(gap_type)
        counts[gap_type] = count

    if domain.get("origin") == "mermaid-source" and domain.get("status") not in {"CONFIRMED", "BASELINED"}:
        gap("UNCONFIRMED_E2E_BOUNDARY")
    if int(domain.get("explicit_membership_count", 0)) == 0:
        gap("NO_EXPLICIT_DOCUMENT_MEMBERSHIP")
    confirmed_selections = [
        row for row in rows["selections"] if row.get("selection_status") in {"CONFIRMED_INCLUDE", "CONTEXT_ONLY"}
    ]
    if not confirmed_selections:
        gap("NO_CONFIRMED_DOCUMENT_SELECTION")
    nodes_without_candidates = [node for node in domain.get("nodes", []) if not node.get("document_candidates")]
    gap("FLOW_NODE_WITHOUT_DOCUMENT_CANDIDATE", len(nodes_without_candidates))
    relationships = related_documents(domain)
    candidate_ids = {
        document_id
        for document_id, relationship in relationships.items()
        if any("CANDIDATE" in evidence for evidence in relationship["relationship_evidence"])
    }
    reviewed_ids = {row.get("document_id", "") for row in rows["selections"]}
    gap("MECHANICAL_CANDIDATES_UNREVIEWED", len(candidate_ids - reviewed_ids))
    confirmed_traces = [row for row in rows["traces"] if row.get("approval_status") in {"USER_CONFIRMED", "CONFIRMED"}]
    if domain.get("edges") and not confirmed_traces:
        gap("NO_CONFIRMED_CONTEXT_TRACE", len(domain.get("edges", [])))
    open_defects = [
        row
        for row in rows["defects"]
        if row.get("status") in {"OPEN", "AWAITING_USER_DECISION"}
    ]
    gap("OPEN_RECONCILIATION_DEFECT", len(open_defects))
    open_interviews = [
        row
        for row in rows["interviews"]
        if row.get("status") in {"SKIPPED_BY_USER", "DEFERRED", "UNKNOWN", "PENDING", "CANDIDATE_FROM_RELATED_ANSWER"}
    ]
    gap("SKIPPED_OR_DEFERRED_QUESTION", len(open_interviews))
    return {
        "e2e_code": domain.get("e2e_code", ""),
        "title": domain.get("title", ""),
        "status": domain.get("status", ""),
        "evidence_class": "USER_CONFIRMED_GAP" if open_defects else "MECHANICAL_GAP_CANDIDATE",
        "gap_candidate_count": sum(counts.values()),
        "open_confirmed_gap_count": len(open_defects),
        "gap_types": gap_types,
        "gap_type_counts": counts,
    }


def scan_all_e2e(repo: Path) -> dict[str, Any]:
    rows = [e2e_gap_summary(repo, domain) for domain in load_domains(repo)]
    rows = [row for row in rows if row["gap_candidate_count"] > 0]
    rows.sort(key=lambda row: (-row["open_confirmed_gap_count"], -row["gap_candidate_count"], row["e2e_code"]))
    return {
        "scan_mode": "ALL_E2E",
        "authority": "DIAGNOSTIC_ONLY",
        "e2e_with_gaps_count": len(rows),
        "e2e": rows,
        "warning": "Mechanical findings are review candidates, not approved semantic defects.",
    }


def scan_e2e(repo: Path, query: str) -> dict[str, Any]:
    domains = load_domains(repo)
    domain = resolve_e2e(query, domains)
    documents = load_documents(repo)
    related = related_documents(domain)
    rows = workspace_rows(repo, domain["e2e_code"])
    selections = {row.get("document_id", ""): row for row in rows["selections"]}
    mapped_documents = []
    content_groups: defaultdict[str, list[str]] = defaultdict(list)
    for document_id, relationship in related.items():
        document = documents.get(document_id, {})
        if document.get("content_id"):
            content_groups[document["content_id"]].append(document_id)
        internal = scan_document_internal(repo, document) if document else None
        selection = selections.get(document_id, {})
        mapped_documents.append(
            {
                "document_id": document_id,
                "title": document.get("title", relationship.get("title", "")),
                "source_path": document.get("source_path", relationship.get("source_path", "")),
                "content_id": document.get("content_id", ""),
                "relationship_evidence": sorted(relationship["relationship_evidence"]),
                "approval_status": selection.get("selection_status", "UNREVIEWED"),
                "max_match_score": relationship["max_match_score"],
                "matched_contexts": sorted(relationship["matched_contexts"]),
                "internal_gap_candidate_count": internal["gap_candidate_count"] if internal else 0,
                "internal_gap_candidate_families": internal["gap_candidate_families"] if internal else [],
            }
        )
    mapped_documents.sort(key=lambda row: (row["approval_status"] == "UNREVIEWED", -row["max_match_score"], row["title"].casefold()))

    duplicate_groups = [
        {"content_id": content_id, "document_ids": document_ids}
        for content_id, document_ids in sorted(content_groups.items())
        if len(document_ids) > 1
    ]
    node_gaps = [
        {
            "node_id": node.get("node_id", ""),
            "node_label": node.get("node_label", ""),
            "gap_type": "FLOW_NODE_WITHOUT_DOCUMENT_CANDIDATE",
            "evidence_class": "MECHANICAL_GAP_CANDIDATE",
        }
        for node in domain.get("nodes", [])
        if not node.get("document_candidates")
    ]
    node_documents = {
        node.get("node_id", ""): sorted(
            {candidate.get("candidate_document_id", "") for candidate in node.get("document_candidates", []) if candidate.get("candidate_document_id")}
        )
        for node in domain.get("nodes", [])
    }
    handoff_gap_candidates = []
    for edge in domain.get("edges", []):
        from_documents = node_documents.get(edge.get("from_node", ""), [])
        to_documents = node_documents.get(edge.get("to_node", ""), [])
        gap_type = "UNCONFIRMED_DOCUMENT_HANDOFF"
        if not from_documents or not to_documents:
            gap_type = "UNMAPPED_HANDOFF_ENDPOINT"
        handoff_gap_candidates.append(
            {
                "from_node": edge.get("from_node", ""),
                "to_node": edge.get("to_node", ""),
                "edge_label": edge.get("edge_label", ""),
                "from_document_candidates": from_documents,
                "to_document_candidates": to_documents,
                "gap_type": gap_type,
                "evidence_class": "MECHANICAL_GAP_CANDIDATE",
                "reason": "No confirmed document context trace links this source-flow edge.",
            }
        )
    confirmed_traces = [row for row in rows["traces"] if row.get("approval_status") in {"USER_CONFIRMED", "CONFIRMED"}]
    cross_document_gaps = []
    if domain.get("edges") and not confirmed_traces:
        cross_document_gaps.append(
            {
                "gap_type": "NO_CONFIRMED_CONTEXT_TRACE",
                "evidence_class": "MECHANICAL_GAP_CANDIDATE",
                "affected_edge_count": len(domain.get("edges", [])),
                "evidence": "No confirmed context-trace rows found for this E2E workspace.",
            }
        )
    unreviewed = [row for row in mapped_documents if row["approval_status"] == "UNREVIEWED" and "SOURCE_FLOW" not in row["relationship_evidence"]]
    if unreviewed:
        cross_document_gaps.append(
            {
                "gap_type": "RELATIONSHIP_UNCONFIRMED",
                "evidence_class": "MECHANICAL_GAP_CANDIDATE",
                "affected_document_count": len(unreviewed),
                "evidence": "Related document candidates have no include/context/take-off decision.",
            }
        )
    if duplicate_groups:
        cross_document_gaps.append(
            {
                "gap_type": "SOURCE_REPRESENTATION_AMBIGUOUS",
                "evidence_class": "MECHANICAL_GAP_CANDIDATE",
                "duplicate_group_count": len(duplicate_groups),
                "evidence": "Multiple related document IDs share exact content IDs.",
            }
        )

    open_defects = [row for row in rows["defects"] if row.get("status") in {"OPEN", "AWAITING_USER_DECISION"}]
    open_interviews = [
        row
        for row in rows["interviews"]
        if row.get("status") in {"SKIPPED_BY_USER", "DEFERRED", "UNKNOWN", "PENDING", "CANDIDATE_FROM_RELATED_ANSWER"}
    ]
    return {
        "scan_mode": "E2E",
        "authority": "DIAGNOSTIC_ONLY",
        "e2e": {
            "e2e_code": domain.get("e2e_code", ""),
            "title": domain.get("title", ""),
            "status": domain.get("status", ""),
            "source_flow_document_id": domain.get("flow_document_id", ""),
            "source_path": domain.get("source_path", ""),
            "node_count": domain.get("node_count", 0),
            "edge_count": domain.get("edge_count", 0),
        },
        "summary": e2e_gap_summary(repo, domain),
        "mapped_documents": mapped_documents,
        "cross_document_gaps": cross_document_gaps,
        "handoff_gap_candidates": handoff_gap_candidates,
        "flow_node_gaps": node_gaps,
        "duplicate_content_groups": duplicate_groups,
        "open_confirmed_defects": open_defects,
        "unresolved_interview_questions": open_interviews,
        "warning": "Mechanical candidates require review before reconciliation decisions.",
    }


def document_related_e2e(repo: Path, document_id: str) -> list[dict[str, Any]]:
    related = []
    for domain in load_domains(repo):
        evidence = set()
        if domain.get("flow_document_id") == document_id:
            evidence.add("SOURCE_FLOW")
        if any(item.get("document_id") == document_id for item in domain.get("explicit_memberships", [])):
            evidence.add("SOURCE_EXPLICIT_MEMBERSHIP")
        candidates = related_documents(domain)
        if document_id in candidates:
            evidence.update(candidates[document_id]["relationship_evidence"])
        rows = workspace_rows(repo, domain["e2e_code"])
        selection = next((row for row in rows["selections"] if row.get("document_id") == document_id), None)
        if evidence or selection:
            related.append(
                {
                    "e2e_code": domain.get("e2e_code", ""),
                    "title": domain.get("title", ""),
                    "evidence": sorted(evidence),
                    "approval_status": selection.get("selection_status", "UNREVIEWED") if selection else "UNREVIEWED",
                }
            )
    return sorted(related, key=lambda row: row["e2e_code"])


def document_register_findings(repo: Path, document_id: str) -> dict[str, Any]:
    defects = []
    interviews = []
    workspaces = repo / "reconciliation/workspaces"
    if not workspaces.is_dir():
        return {"open_defects": defects, "unresolved_questions": interviews}
    for workspace in workspaces.iterdir():
        if not workspace.is_dir():
            continue
        for row in read_csv_optional(workspace / "defect-register.csv"):
            if document_id in row.get("document_ids", "") and row.get("status") in {"OPEN", "AWAITING_USER_DECISION"}:
                defects.append(row)
        for row in read_csv_optional(workspace / "interview-register.csv"):
            if document_id in row.get("document_ids", "") and row.get("status") in {
                "SKIPPED_BY_USER", "DEFERRED", "UNKNOWN", "PENDING", "CANDIDATE_FROM_RELATED_ANSWER"
            }:
                interviews.append(row)
    return {"open_defects": defects, "unresolved_questions": interviews}


def scan_document(repo: Path, query: str) -> dict[str, Any]:
    documents = load_documents(repo)
    document = resolve_document(query, documents)
    internal = scan_document_internal(repo, document)
    registers = document_register_findings(repo, document["document_id"])
    return {
        "scan_mode": "DOCUMENT",
        "authority": "DIAGNOSTIC_ONLY",
        "document": internal,
        "related_e2e": document_related_e2e(repo, document["document_id"]),
        "open_confirmed_defects": registers["open_defects"],
        "unresolved_interview_questions": registers["unresolved_questions"],
        "warning": "Missing headings are format/context candidates, not proof that source facts are absent.",
    }


def markdown_escape(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")


def print_markdown(result: dict[str, Any]) -> None:
    mode = result["scan_mode"]
    if mode == "ALL_E2E":
        print("# E2E Gap Scan")
        print()
        print(result["warning"])
        print()
        print("| E2E | Title | Status | Gap candidates | Open confirmed | Primary gap types |")
        print("|---|---|---|---:|---:|---|")
        for row in result["e2e"]:
            print(
                f"| {row['e2e_code']} | {markdown_escape(row['title'])} | {row['status']} | "
                f"{row['gap_candidate_count']} | {row['open_confirmed_gap_count']} | "
                f"{markdown_escape(', '.join(row['gap_types']))} |"
            )
        return

    if mode == "E2E":
        e2e = result["e2e"]
        print(f"# {e2e['e2e_code']} - {e2e['title']} Gap Scan")
        print()
        print(result["warning"])
        print()
        print("## Cross-Document Gaps")
        print()
        if not result["cross_document_gaps"]:
            print("No cross-document gap candidates detected mechanically.")
        for gap in result["cross_document_gaps"]:
            print(f"- `{gap['gap_type']}`: {gap['evidence']}")
        print()
        print("## Related Documents")
        print()
        print("| Document | Title | Evidence | Approval | Internal gaps |")
        print("|---|---|---|---|---:|")
        for row in result["mapped_documents"]:
            print(
                f"| {row['document_id']} | {markdown_escape(row['title'])} | "
                f"{markdown_escape(', '.join(row['relationship_evidence']))} | {row['approval_status']} | "
                f"{row['internal_gap_candidate_count']} |"
            )
        print()
        print(f"Flow nodes without document candidates: `{len(result['flow_node_gaps'])}`")
        print(f"Flow handoffs without confirmed document traces: `{len(result['handoff_gap_candidates'])}`")
        print(f"Open confirmed defects: `{len(result['open_confirmed_defects'])}`")
        print(f"Unresolved interview questions: `{len(result['unresolved_interview_questions'])}`")
        return

    document = result["document"]
    print(f"# {document['document_id']} - {document['title']} Gap Scan")
    print()
    print(result["warning"])
    print()
    print(f"Source: `{document['source_path']}`")
    print()
    print("| Context family | Status | Matched headings/terms |")
    print("|---|---|---|")
    for family in document["families"]:
        evidence = family["matched_headings"] or family["matched_terms"]
        print(
            f"| {family['context_family']} | {family['status']} | "
            f"{markdown_escape('; '.join(evidence)) or '-'} |"
        )
    print()
    print(f"Gap candidates: `{document['gap_candidate_count']}`")
    print(f"Explicit marker candidates: `{len(document['explicit_gap_markers'])}`")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only Neurovi E2E and PRD context gap scanner")
    parser.add_argument("--repo", type=Path, default=default_repo())
    parser.add_argument("--json", action="store_true")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--e2e", help="E2E code or name")
    group.add_argument("--document", help="Document ID or name")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo = args.repo.resolve()
    try:
        if args.e2e:
            result = scan_e2e(repo, args.e2e)
        elif args.document:
            result = scan_document(repo, args.document)
        else:
            result = scan_all_e2e(repo)
    except (GapScanError, json.JSONDecodeError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_markdown(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
