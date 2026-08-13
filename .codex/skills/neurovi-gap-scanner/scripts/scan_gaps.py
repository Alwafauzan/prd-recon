#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
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
    "VALIDATION_BEHAVIOR": {
        "heading": ("validation", "validasi", "constraint", "batasan"),
        "text": ("validasi", "harus valid", "tidak boleh", "wajib diisi"),
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

MAIN_FLOW_FAMILIES = (
    "PURPOSE_BACKGROUND",
    "SCOPE",
    "ACTORS_STAKEHOLDERS",
    "TRIGGER_PRECONDITIONS",
    "MAIN_FLOW",
    "LOGICAL_DATA_FLOW",
    "STATUS_LIFECYCLE",
    "DEPENDENCIES_INTEGRATION",
)

BUSINESS_CASE_FAMILIES = (
    "OUT_OF_SCOPE",
    "ALTERNATE_FLOW",
    "ERROR_EXCEPTION",
    "CASES_CONDITIONS",
    "BUSINESS_RULES",
    "VALIDATION_BEHAVIOR",
    "ACCEPTANCE_CRITERIA",
)

FLOW_CHECK_LABELS = {
    "trigger_input": "Pemicu dan input awal",
    "sequence": "Urutan proses",
    "handoff": "Perpindahan ke proses berikutnya",
    "output": "Hasil proses",
    "status_transition": "Perubahan status",
}

FLOW_STATUS_LABELS = {
    "SOURCE_CONTEXT_PRESENT": "Sudah ditemukan",
    "REVIEW_REQUIRED": "Perlu ditinjau",
    "NOT_EVALUATED": "Belum diperiksa",
}

BUSINESS_CASE_LABELS = {
    "OUT_OF_SCOPE": "Batas kasus yang tidak termasuk",
    "ALTERNATE_FLOW": "Skenario alternatif",
    "ERROR_EXCEPTION": "Kegagalan dan pengecualian",
    "CASES_CONDITIONS": "Kasus dan kondisi",
    "BUSINESS_RULES": "Aturan bisnis",
    "VALIDATION_BEHAVIOR": "Validasi",
    "ACCEPTANCE_CRITERIA": "Kriteria penerimaan",
}

CONTEXT_STATUS_LABELS = {
    "SECTION_PRESENT": "Sudah dijelaskan",
    "CONTEXT_PRESENT_UNSTRUCTURED": "Ditemukan, tetapi belum terstruktur",
    "CONTEXT_GAP_CANDIDATE": "Perlu ditinjau",
}

FLOW_RELATION_REQUIREMENTS = {
    "ENTRY_POINT_TO": ("trigger",),
    "PRODUCES": ("output_context",),
    "HANDOFF_TO": ("output_context", "status_transition", "condition"),
    "ACTIVATES": ("status_transition",),
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


def load_inventory(repo: Path) -> dict[str, Any]:
    path = repo / "reconciliation/e2e-inventory/domain-worklist.json"
    return read_json(path)


def load_documents(repo: Path) -> dict[str, dict[str, Any]]:
    path = repo / "catalog/document-index.json"
    return {item["document_id"]: item for item in read_json(path).get("documents", [])}


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


def document_content(repo: Path, document_id: str) -> str:
    path = repo / "documents" / document_id / "content.md"
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


def scan_document_internal(
    repo: Path,
    document: dict[str, Any],
    context_families: tuple[str, ...] | None = None,
    include_explicit_markers: bool = True,
) -> dict[str, Any]:
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
    selected_families = context_families or tuple(SECTION_FAMILIES)
    for family in selected_families:
        patterns = SECTION_FAMILIES[family]
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
    if include_explicit_markers:
        for line_number, line in enumerate(content.splitlines(), start=1):
            folded = line.casefold()
            markers = [
                marker
                for marker in EXPLICIT_GAP_MARKERS
                if re.search(rf"\b{re.escape(marker)}\b", folded)
            ]
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


def flow_relation_evidence(relation: dict[str, Any]) -> dict[str, str]:
    return {
        field: str(relation.get(field, "")).strip()
        for field in (
            "trigger",
            "input_context",
            "output_context",
            "status_transition",
            "condition",
        )
        if str(relation.get(field, "")).strip()
    }


def is_flow_relation(relation: dict[str, Any]) -> bool:
    return (
        relation.get("relationship_type") in FLOW_RELATION_REQUIREMENTS
        or bool(flow_relation_evidence(relation))
    )


def scan_main_flow(repo: Path, query: str) -> dict[str, Any]:
    inventory = load_inventory(repo)
    domain = resolve_e2e(query, inventory.get("domains", []))
    relation_ids = set(domain.get("relation_ids", []))
    relations = [
        relation
        for relation in inventory.get("relations", [])
        if relation.get("relation_id") in relation_ids
    ]
    flow_relations = [relation for relation in relations if is_flow_relation(relation)]

    documents = []
    flow_gap_candidates = []
    for membership in sorted(
        domain.get("documents", []), key=lambda item: item.get("worklist_order", 0)
    ):
        checks = {
            key: membership.get("flow_checks", {}).get(key, "NOT_EVALUATED")
            for key in FLOW_CHECK_LABELS
        }
        document_gaps = []
        for key, status in checks.items():
            if status == "SOURCE_CONTEXT_PRESENT":
                continue
            finding = {
                "gap_type": f"{key.upper()}_REVIEW_REQUIRED",
                "evidence_class": "MECHANICAL_GAP_CANDIDATE",
                "document_id": membership.get("document_id", ""),
                "title": membership.get("title", ""),
                "source_path": membership.get("source_path", ""),
                "worklist_order": membership.get("worklist_order", 0),
                "worklist_stage": membership.get("worklist_stage", ""),
                "flow_aspect": key,
                "flow_aspect_label": FLOW_CHECK_LABELS[key],
                "status": status,
                "reason": (
                    "Inventaris belum menemukan konteks sumber yang cukup untuk "
                    f"{FLOW_CHECK_LABELS[key].casefold()}."
                ),
            }
            document_gaps.append(finding)
            flow_gap_candidates.append(finding)
        documents.append(
            {
                "worklist_order": membership.get("worklist_order", 0),
                "worklist_stage": membership.get("worklist_stage", ""),
                "document_id": membership.get("document_id", ""),
                "title": membership.get("title", ""),
                "source_path": membership.get("source_path", ""),
                "flow_checks": checks,
                "gap_candidate_count": len(document_gaps),
                "gap_candidates": document_gaps,
            }
        )

    relation_gaps = []
    relation_rows = []
    for relation in flow_relations:
        relation_type = str(relation.get("relationship_type", ""))
        evidence = flow_relation_evidence(relation)
        required_fields = FLOW_RELATION_REQUIREMENTS.get(relation_type, ())
        if required_fields and not any(evidence.get(field) for field in required_fields):
            relation_gaps.append(
                {
                    "gap_type": "UNDEFINED_FLOW_HANDOFF_CONTEXT",
                    "evidence_class": "MECHANICAL_GAP_CANDIDATE",
                    "relation_id": relation.get("relation_id", ""),
                    "source_title": relation.get("source_title", ""),
                    "target_title": relation.get("target_title", ""),
                    "reason": "Relasi flow eksplisit belum memiliki konteks handoff yang diperlukan.",
                    "evidence_reference": relation.get("evidence_reference", ""),
                }
            )
        if relation.get("conflict_status") == "CONFLICT_FOUND":
            relation_gaps.append(
                {
                    "gap_type": "CONFLICTING_FLOW_CONTEXT",
                    "evidence_class": "SOURCE_EXPLICIT_GAP",
                    "relation_id": relation.get("relation_id", ""),
                    "source_title": relation.get("source_title", ""),
                    "target_title": relation.get("target_title", ""),
                    "reason": relation.get("notes", "Konflik konteks flow ditemukan."),
                    "evidence_reference": relation.get("evidence_reference", ""),
                }
            )
        relation_rows.append(
            {
                "relation_id": relation.get("relation_id", ""),
                "source_document_id": relation.get("source_document_id", ""),
                "source_title": relation.get("source_title", ""),
                "source_domain_code": relation.get("source_domain_code", ""),
                "target_document_id": relation.get("target_document_id", ""),
                "target_title": relation.get("target_title", ""),
                "target_domain_code": relation.get("target_domain_code", ""),
                "relationship_type": relation_type,
                "relation_scope": relation.get("relation_scope", ""),
                "flow_evidence": evidence,
                "verification_status": relation.get("verification_status", ""),
                "conflict_status": relation.get("conflict_status", ""),
                "evidence_reference": relation.get("evidence_reference", ""),
            }
        )

    all_gaps = flow_gap_candidates + relation_gaps
    return {
        "scanner": "MAIN_FLOW",
        "scan_mode": "MAIN_FLOW_E2E",
        "authority": "DIAGNOSTIC_ONLY",
        "scope": (
            "Kesinambungan alur bisnis utama: pemicu, urutan, handoff, hasil, "
            "status, kelanjutan lintas domain, dan konflik flow."
        ),
        "e2e": {
            "e2e_code": domain.get("e2e_code", ""),
            "title": domain.get("title", ""),
            "purpose": domain.get("purpose", ""),
            "document_count": len(documents),
        },
        "summary": {
            "gap_candidate_count": len(all_gaps),
            "document_gap_candidate_count": len(flow_gap_candidates),
            "relation_gap_candidate_count": len(relation_gaps),
            "flow_relation_count": len(relation_rows),
            "cross_domain_flow_relation_count": sum(
                row["relation_scope"] == "CROSS_DOMAIN" for row in relation_rows
            ),
            "supporting_relation_count": len(relations) - len(relation_rows),
        },
        "ordered_documents": documents,
        "flow_relations": relation_rows,
        "gap_candidates": all_gaps,
        "excluded_detail_families": list(BUSINESS_CASE_FAMILIES),
        "warning": (
            "Scanner ini tidak menilai skenario alternatif, error, validasi rinci, "
            "atau acceptance criteria. Relasi referensi tanpa bukti flow dipakai "
            "sebagai konteks penunjang dan tidak dihitung sebagai handoff."
        ),
    }


def document_related_e2e(repo: Path, document_id: str) -> list[dict[str, Any]]:
    inventory = load_inventory(repo)
    related = []
    for domain in inventory.get("domains", []):
        evidence = set()
        for membership in domain.get("documents", []):
            representation_ids = {
                row.get("document_id", "")
                for row in membership.get("source_representations", [])
            }
            if document_id == membership.get("document_id") or document_id in representation_ids:
                evidence.add("OWNER_DOMAIN")
        for relation in inventory.get("relations", []):
            if relation.get("source_document_id") == document_id or relation.get("target_document_id") == document_id:
                if relation.get("source_domain_code") == domain.get("e2e_code") or relation.get("target_domain_code") == domain.get("e2e_code"):
                    evidence.add(f"RELATION:{relation.get('relation_id', '')}")
        if evidence:
            related.append(
                {
                    "e2e_code": domain.get("e2e_code", ""),
                    "title": domain.get("title", ""),
                    "evidence": sorted(evidence),
                    "worklist_status": (
                        "OWNER_WORKLIST" if "OWNER_DOMAIN" in evidence else "RELATED_CONTEXT"
                    ),
                }
            )
    return sorted(related, key=lambda row: row["e2e_code"])


def eligible_document_ids(inventory: dict[str, Any]) -> set[str]:
    document_ids = set()
    for domain in inventory.get("domains", []):
        for membership in domain.get("documents", []):
            document_ids.add(membership.get("document_id", ""))
            document_ids.update(
                row.get("document_id", "")
                for row in membership.get("source_representations", [])
            )
    return {document_id for document_id in document_ids if document_id}


def membership_case_check(
    inventory: dict[str, Any], document_id: str
) -> list[dict[str, str]]:
    checks = []
    for domain in inventory.get("domains", []):
        for membership in domain.get("documents", []):
            representation_ids = {
                row.get("document_id", "")
                for row in membership.get("source_representations", [])
            }
            if document_id != membership.get("document_id") and document_id not in representation_ids:
                continue
            checks.append(
                {
                    "e2e_code": domain.get("e2e_code", ""),
                    "e2e_title": domain.get("title", ""),
                    "status": membership.get("flow_checks", {}).get(
                        "alternate_cases", "NOT_EVALUATED"
                    ),
                }
            )
    return checks


def business_case_document_result(
    repo: Path,
    document: dict[str, Any],
    inventory: dict[str, Any],
) -> dict[str, Any]:
    internal = scan_document_internal(
        repo,
        document,
        context_families=BUSINESS_CASE_FAMILIES,
        include_explicit_markers=True,
    )
    case_checks = membership_case_check(inventory, document["document_id"])
    inventory_candidates = [
        row for row in case_checks if row["status"] != "SOURCE_CONTEXT_PRESENT"
    ]
    return {
        **internal,
        "inventory_case_checks": case_checks,
        "inventory_case_candidate_count": len(inventory_candidates),
        "business_case_candidate_count": (
            internal["gap_candidate_count"] + len(inventory_candidates)
        ),
    }


def scan_business_cases_document(repo: Path, query: str) -> dict[str, Any]:
    inventory = load_inventory(repo)
    documents = load_documents(repo)
    document = resolve_document(query, documents)
    if document["document_id"] not in eligible_document_ids(inventory):
        raise GapScanError(
            "Document is not an eligible original Markdown PRD in the domain inventory."
        )
    result = business_case_document_result(repo, document, inventory)
    return {
        "scanner": "BUSINESS_CASES",
        "scan_mode": "BUSINESS_CASES_DOCUMENT",
        "authority": "DIAGNOSTIC_ONLY",
        "scope": (
            "Detail kasus bisnis: batas kasus, skenario alternatif, error, kondisi, "
            "aturan bisnis, validasi, dan acceptance criteria."
        ),
        "document": result,
        "related_e2e": document_related_e2e(repo, document["document_id"]),
        "excluded_main_flow_families": list(MAIN_FLOW_FAMILIES),
        "warning": (
            "Keluarga konteks yang tidak terdeteksi adalah kandidat review, bukan "
            "bukti bahwa fakta bisnis tidak ada. Informasi dapat ditulis dengan "
            "heading atau istilah yang berbeda."
        ),
    }


def scan_business_cases_e2e(repo: Path, query: str) -> dict[str, Any]:
    inventory = load_inventory(repo)
    domain = resolve_e2e(query, inventory.get("domains", []))
    documents = load_documents(repo)
    rows = []
    for membership in sorted(
        domain.get("documents", []), key=lambda item: item.get("worklist_order", 0)
    ):
        document = documents.get(membership.get("document_id", ""))
        if not document:
            continue
        result = business_case_document_result(repo, document, inventory)
        rows.append(
            {
                **result,
                "worklist_order": membership.get("worklist_order", 0),
                "worklist_stage": membership.get("worklist_stage", ""),
            }
        )
    rows_with_candidates = [
        row for row in rows if row["business_case_candidate_count"] > 0
    ]
    return {
        "scanner": "BUSINESS_CASES",
        "scan_mode": "BUSINESS_CASES_E2E",
        "authority": "DIAGNOSTIC_ONLY",
        "scope": (
            "Agregasi detail kasus bisnis pada PRD utama dalam satu domain E2E."
        ),
        "e2e": {
            "e2e_code": domain.get("e2e_code", ""),
            "title": domain.get("title", ""),
            "purpose": domain.get("purpose", ""),
            "document_count": len(rows),
        },
        "summary": {
            "document_count": len(rows),
            "documents_with_candidates": len(rows_with_candidates),
            "gap_candidate_count": sum(
                row["business_case_candidate_count"] for row in rows
            ),
        },
        "documents": rows,
        "excluded_main_flow_families": list(MAIN_FLOW_FAMILIES),
        "warning": (
            "Hasil agregat menunjukkan PRD yang perlu dibaca lebih rinci. Keluarga "
            "konteks yang tidak terdeteksi bukan bukti bahwa fakta bisnis tidak ada."
        ),
    }


def scan_business_cases(repo: Path, query: str, scope: str = "auto") -> dict[str, Any]:
    if scope == "e2e":
        return scan_business_cases_e2e(repo, query)
    if scope == "document":
        return scan_business_cases_document(repo, query)

    inventory = load_inventory(repo)
    folded = query.casefold().strip()
    exact_domains = [
        domain
        for domain in inventory.get("domains", [])
        if folded in {
            str(domain.get("e2e_code", "")).casefold(),
            str(domain.get("title", "")).casefold(),
        }
    ]
    if len(exact_domains) == 1:
        return scan_business_cases_e2e(repo, exact_domains[0]["e2e_code"])
    if query.upper().startswith("E2E-"):
        return scan_business_cases_e2e(repo, query)
    return scan_business_cases_document(repo, query)


def markdown_escape(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")


def print_main_flow_markdown(result: dict[str, Any]) -> None:
    e2e = result["e2e"]
    summary = result["summary"]
    print(f"# Pemeriksaan Alur Utama - {e2e['title']}")
    print()
    print(result["scope"])
    print()
    print(
        f"Diperiksa: `{e2e['document_count']}` PRD utama dan "
        f"`{summary['flow_relation_count']}` relasi flow eksplisit."
    )
    print(f"Kandidat yang perlu ditinjau: `{summary['gap_candidate_count']}`.")
    print()
    print("## Urutan Proses")
    print()
    print("| Tahap | Dokumen | Pemicu | Urutan | Handoff | Hasil | Status |")
    print("|---:|---|---|---|---|---|---|")
    for row in result["ordered_documents"]:
        checks = row["flow_checks"]
        print(
            f"| {row['worklist_order']} | {markdown_escape(row['title'])} | "
            f"{FLOW_STATUS_LABELS.get(checks['trigger_input'], checks['trigger_input'])} | "
            f"{FLOW_STATUS_LABELS.get(checks['sequence'], checks['sequence'])} | "
            f"{FLOW_STATUS_LABELS.get(checks['handoff'], checks['handoff'])} | "
            f"{FLOW_STATUS_LABELS.get(checks['output'], checks['output'])} | "
            f"{FLOW_STATUS_LABELS.get(checks['status_transition'], checks['status_transition'])} |"
        )
    print()
    print("## Temuan Alur")
    print()
    if not result["gap_candidates"]:
        print("Tidak ada kandidat gap alur utama yang terdeteksi dari inventaris saat ini.")
    for gap in result["gap_candidates"]:
        subject = gap.get("title") or (
            f"{gap.get('source_title', '')} -> {gap.get('target_title', '')}"
        )
        print(
            f"- **{markdown_escape(subject)}** — {gap['reason']}"
        )
    print()
    print("## Handoff Eksplisit")
    print()
    if not result["flow_relations"]:
        print("Belum ada relasi flow eksplisit yang terindeks untuk proses ini.")
    for row in result["flow_relations"]:
        evidence = "; ".join(row["flow_evidence"].values()) or "Konteks flow belum terisi"
        print(
            f"- **{markdown_escape(row['source_title'])} -> "
            f"{markdown_escape(row['target_title'])}**: {markdown_escape(evidence)}"
        )
    print()
    print(result["warning"])


def print_business_case_document_markdown(result: dict[str, Any]) -> None:
    document = result["document"]
    print(f"# Pemeriksaan Kasus Bisnis - {document['title']}")
    print()
    print(result["scope"])
    print()
    print(f"Sumber: `{document['source_path']}`")
    print()
    print("| Area kasus bisnis | Status | Bukti yang ditemukan |")
    print("|---|---|---|")
    for family in document["families"]:
        evidence = family["matched_headings"] or family["matched_terms"]
        print(
            f"| {BUSINESS_CASE_LABELS.get(family['context_family'], family['context_family'])} | "
            f"{CONTEXT_STATUS_LABELS.get(family['status'], family['status'])} | "
            f"{markdown_escape('; '.join(evidence)) or '-'} |"
        )
    print()
    print(
        f"Kandidat detail kasus yang perlu ditinjau: "
        f"`{document['business_case_candidate_count']}`."
    )
    print(
        f"Penanda eksplisit belum selesai: "
        f"`{len(document['explicit_gap_markers'])}`."
    )
    print()
    print(result["warning"])


def print_business_case_e2e_markdown(result: dict[str, Any]) -> None:
    e2e = result["e2e"]
    summary = result["summary"]
    print(f"# Pemeriksaan Kasus Bisnis - {e2e['title']}")
    print()
    print(result["scope"])
    print()
    print(
        f"PRD diperiksa: `{summary['document_count']}`; PRD dengan kandidat: "
        f"`{summary['documents_with_candidates']}`; total kandidat: "
        f"`{summary['gap_candidate_count']}`."
    )
    print()
    print("| Urutan | Dokumen | Kandidat | Area yang perlu ditinjau |")
    print("|---:|---|---:|---|")
    for document in result["documents"]:
        candidates = [
            BUSINESS_CASE_LABELS.get(
                family["context_family"], family["context_family"]
            )
            for family in document["families"]
            if family["status"] == "CONTEXT_GAP_CANDIDATE"
        ]
        if document["inventory_case_candidate_count"]:
            candidates.append("Kasus alternatif perlu ditinjau")
        if document["explicit_gap_markers"]:
            candidates.append("Ada penanda belum selesai")
        print(
            f"| {document['worklist_order']} | {markdown_escape(document['title'])} | "
            f"{document['business_case_candidate_count']} | "
            f"{markdown_escape(', '.join(candidates)) or '-'} |"
        )
    print()
    print(result["warning"])


def print_markdown(result: dict[str, Any]) -> None:
    mode = result["scan_mode"]
    if mode == "MAIN_FLOW_E2E":
        print_main_flow_markdown(result)
    elif mode == "BUSINESS_CASES_DOCUMENT":
        print_business_case_document_markdown(result)
    elif mode == "BUSINESS_CASES_E2E":
        print_business_case_e2e_markdown(result)
    else:
        raise GapScanError(f"Unsupported scan mode: {mode}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only Neurovi main-flow and business-case scanner"
    )
    parser.add_argument("--repo", type=Path, default=default_repo())
    parser.add_argument("--json", action="store_true")
    subparsers = parser.add_subparsers(dest="scanner", required=True)

    main_flow = subparsers.add_parser(
        "main-flow", help="Scan continuity of one E2E main business flow"
    )
    main_flow.add_argument("--e2e", required=True, help="E2E code or name")

    business_cases = subparsers.add_parser(
        "business-cases", help="Scan detailed business cases in one PRD or E2E"
    )
    target = business_cases.add_mutually_exclusive_group(required=True)
    target.add_argument("--document", help="Document ID or name")
    target.add_argument("--e2e", help="E2E code or name")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo = args.repo.resolve()
    try:
        if args.scanner == "main-flow":
            result = scan_main_flow(repo, args.e2e)
        elif args.document:
            result = scan_business_cases_document(repo, args.document)
        else:
            result = scan_business_cases_e2e(repo, args.e2e)
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
