#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable


AUTO_STATUS = "RESOLVED_BY_SOURCE_FACT"
HUMAN_STATUS = "HUMAN_DECISION_REQUIRED"
SOURCE_GAP_STATUS = "OPEN_SOURCE_EXPLICIT_GAP"
OPEN_STATUS = "OPEN_INSUFFICIENT_SOURCE_EVIDENCE"
EXCLUDED_STATUS = "EXCLUDED_NON_ACTIVE_SOURCE_EVIDENCE"

DETAIL_SECTION_FAMILIES = {
    "OUT_OF_SCOPE": {
        "heading": ("out of scope", "out scope", "di luar scope", "tidak termasuk"),
        "text": ("out of scope", "di luar cakupan", "tidak termasuk dalam scope"),
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

EXCLUDED_HEADING_TOKENS = (
    "revision history",
    "document history",
    "change history",
    "change log",
    "changelog",
    "riwayat perubahan",
    "riwayat revisi",
    "asumsi",
    "assumption",
    "pertanyaan terbuka",
    "open question",
)

ASSUMPTION_TOKENS = (
    "[asumsi]",
    "[asumsi ",
    "[assumption]",
    "[assumption ",
    "[perlu konfirmasi]",
    "[perlu konfirmasi ",
    "[perlu dikonfirmasi]",
    "[perlu dikonfirmasi ",
)

UNRESOLVED_TOKENS = (
    "[perlu konfirmasi]",
    "[perlu konfirmasi ",
    "[perlu dikonfirmasi]",
    "[perlu dikonfirmasi ",
    "perlu dikonfirmasi",
    "belum diputuskan",
    "belum ditentukan",
    "belum didefinisikan",
    "to be defined",
    "not defined",
    "tbd",
)

FUTURE_ONLY_TOKENS = (
    "phase 2",
    "fase 2",
    "phase 3",
    "fase 3",
    "future",
)

MAIN_SECTION_TOKENS = (
    "flow",
    "alur",
    "workflow",
    "process",
    "proses",
    "requirement",
    "feature",
    "fitur",
    "related",
    "dependency",
    "dependensi",
    "integration",
    "integrasi",
    "contract",
    "kontrak",
    "scope",
    "acceptance",
    "rule",
    "aturan",
    "data",
)

DETAIL_PATTERNS = {
    "OUT_OF_SCOPE": (
        r"\bout[ -]?of[ -]?scope\b",
        r"\bdi luar (?:ruang lingkup|cakupan|scope)\b",
        r"\btidak termasuk dalam (?:ruang lingkup|cakupan|scope)\b",
    ),
    "ALTERNATE_FLOW": (
        r"(?:^|[:|.)-]\s*)(?:jika|bila|apabila|ketika|saat(?! ini\b))\b.*\b(?:sistem|proses|order|aksi|form|opsi|status)\b.*\b(?:menolak|ditolak|menampilkan (?:error|pesan|modal|warning|peringatan)|kembali|dibatalkan|tidak menyimpan|tidak membentuk|tidak melanjutkan|dialihkan|diarahkan|fallback|retry|dikunci|dinonaktifkan|diblokir)\b",
        r"\b(?:skenario|alur)\s+(?:alternatif|alternative|alternate)\b",
    ),
    "ERROR_EXCEPTION": (
        r"\bsistem\s+(?:menolak|memblokir|menampilkan)\b.*\b(?:error|gagal|invalid|tidak valid|duplikat|konflik|peringatan|pesan)\b",
        r"(?:^|[:|.)-]\s*)(?:jika|bila|apabila|ketika)\b.*\b(?:gagal|invalid|tidak valid|duplikat|error|konflik)\b.*\b(?:menolak|menampilkan|kembali|tidak menyimpan|dibatalkan|diblokir|retry)\b",
        r"\b(?:error state|error aktif|exception|pengecualian|kegagalan)\b.*\b(?:ditampilkan|ditolak|ditangani|retry|tidak menyimpan|menghentikan)\b",
    ),
    "CASES_CONDITIONS": (
        r"(?:^|[:|.)-]\s*)(?:jika|bila|apabila|ketika)\b.*(?:->|\u2192|\bmaka\b|\bsistem\b|\bwajib\b|\bhanya\b|\btidak\b|\bdapat\b)",
        r"\b(?:gateway|case type|kondisi)\b.*\b(?:jika|bila|valid|tidak|aktif|nonaktif|tersedia)\b",
    ),
    "BUSINESS_RULES": (
        r"(?:^|[|*\s])br[- _][a-z0-9]+(?:\b|\s*[:|])",
        r"\b(?:business rules?|aturan bisnis)\b",
    ),
    "VALIDATION_BEHAVIOR": (
        r"\bsistem\b.*\b(?:memvalidasi|validasi|menolak|memblokir)\b",
        r"\b(?:wajib|tidak boleh|harus valid|unik)\b.*\b(?:menolak|validasi|error|pesan|simpan|dipilih|diisi)\b",
    ),
    "ACCEPTANCE_CRITERIA": (
        r"(?:^|[|*\s])ac[- _]?[0-9]+(?:\b|\s*[:|])",
        r"\b(?:acceptance criteria|kriteria penerimaan)\b",
    ),
}

MAIN_PATTERNS = {
    "trigger_input": (
        r"\b(?:pengguna|user|admin|kasir|dokter|petugas|sistem)\b.*\b(?:membuka|memilih|mengakses|klik|mengisi|memuat|menginput)\b",
        r"\b(?:trigger|pemicu|precondition|prasyarat)\b",
    ),
    "sequence": (
        r"(?:->|\u2192).*(?:->|\u2192)",
        r"\b(?:alur utama|main flow|workflow|business process|proses bisnis)\b",
    ),
    "handoff": (
        r"\b(?:mengonsumsi|dikonsumsi|handoff|berpindah ke|diteruskan|mengirim|mengacu pada|bersumber dari|sumber autofill|tersedia sebagai lookup|direfleksikan)\b",
        r"(?:->|\u2192).*\b(?:frontend|backend|modul|tab|dashboard|registry|lookup|g2|a53|spri|warrant)\b",
    ),
    "output": (
        r"\b(?:sistem|api|endpoint|frontend|backend|modul|registry)\b.*\b(?:menampilkan|mengembalikan|menyimpan|mencatat|merender|menghasilkan|membentuk|menyediakan)\b",
        r"\b(?:tersimpan|disimpan|tercatat|terbentuk|tersedia sebagai lookup|ditampilkan)\b",
    ),
    "status_transition": (
        r"\bstatus\b.*(?:->|\u2192|\bmenjadi\b|\bberubah\b|\bdari\b.*\bke\b)",
        r"\b(?:aktif|nonaktif|open|locked|paid|saved|pending)\b.*(?:->|\u2192).*\b(?:aktif|nonaktif|open|locked|paid|saved|pending)\b",
    ),
    "alternate_cases": (
        r"(?:^|[:|.)-]\s*)(?:jika|bila|apabila|ketika|saat(?! ini\b))\b.*\b(?:sistem|proses|order|aksi|form|opsi|status)\b.*\b(?:menolak|ditolak|menampilkan (?:error|pesan|modal|warning|peringatan)|kembali|dibatalkan|tidak menyimpan|tidak membentuk|tidak melanjutkan|dialihkan|diarahkan|fallback|retry|dikunci|dinonaktifkan|diblokir)\b",
    ),
}


def _fold(value: str) -> str:
    return " ".join(value.casefold().split())


def _sha1_id(*parts: str) -> str:
    payload = "|".join(parts).encode("utf-8")
    return hashlib.sha1(payload).hexdigest()[:14].upper()


def _matches(value: str, patterns: Iterable[str]) -> bool:
    folded = _fold(value)
    return any(re.search(pattern, folded) for pattern in patterns)


def active_source_lines(content: str) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    headings: list[tuple[int, str]] = []
    excluded_section = False
    revision_table = False
    fenced = False

    for line_number, raw_line in enumerate(content.splitlines(), start=1):
        stripped = raw_line.strip()
        folded = _fold(stripped)
        if stripped.startswith("```"):
            fenced = not fenced
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            level = len(heading.group(1))
            heading_text = heading.group(2).strip()
            headings = [(item_level, text) for item_level, text in headings if item_level < level]
            headings.append((level, heading_text))
            excluded_section = any(
                token in _fold(heading_text) for token in EXCLUDED_HEADING_TOKENS
            )
            revision_table = False

        if stripped.startswith("|") and (
            ("versi" in folded or "version" in folded)
            and ("deskripsi" in folded or "description" in folded)
            and ("tanggal" in folded or "date" in folded)
        ):
            revision_table = True
            continue
        if revision_table:
            if stripped.startswith("|") or not stripped:
                continue
            revision_table = False

        exclusion_reason = ""
        if fenced:
            exclusion_reason = "FENCED_EXAMPLE_OR_DIAGRAM"
        elif excluded_section:
            exclusion_reason = "NON_ACTIVE_SECTION"
        elif any(token in folded for token in ASSUMPTION_TOKENS):
            exclusion_reason = "ASSUMPTION_OR_PENDING_CONFIRMATION"
        elif any(token in folded for token in UNRESOLVED_TOKENS):
            exclusion_reason = "UNRESOLVED_SOURCE_MARKER"
        elif any(token in folded for token in FUTURE_ONLY_TOKENS) and not any(
            token in folded for token in ("phase 1", "fase 1", "mvp", "saat ini")
        ):
            exclusion_reason = "FUTURE_PHASE_ONLY"

        if stripped and not re.fullmatch(r"[-:| ]+", stripped):
            lines.append(
                {
                    "line": line_number,
                    "text": stripped,
                    "heading_path": [text for _, text in headings],
                    "eligible": not exclusion_reason,
                    "exclusion_reason": exclusion_reason,
                }
            )
    return lines


def detail_gap_candidate_families(
    headings: list[dict[str, Any]], content: str
) -> list[str]:
    heading_texts = [str(item.get("text", "")) for item in headings]
    folded_headings = [_fold(item) for item in heading_texts]
    folded_content = _fold(content)
    candidates = []
    for family, patterns in DETAIL_SECTION_FAMILIES.items():
        heading_present = any(
            any(token in heading for token in patterns["heading"])
            for heading in folded_headings
        )
        text_present = any(token in folded_content for token in patterns["text"])
        if not heading_present and not text_present:
            candidates.append(family)
    return candidates


def _section_is_relevant(line: dict[str, Any]) -> bool:
    path = " ".join(_fold(item) for item in line.get("heading_path", []))
    return not path or any(token in path for token in MAIN_SECTION_TOKENS)


def _evidence_has_requirement_assertion(candidate_type: str, text: str) -> bool:
    folded = _fold(text)
    if candidate_type == "CASES_CONDITIONS":
        return any(
            token in folded
            for token in (
                "jika ",
                "bila ",
                "apabila ",
                "ketika ",
                "gateway",
                "case type",
                "kondisi ",
                "syarat ",
                "hanya ",
            )
        )
    if candidate_type == "BUSINESS_RULES":
        return bool(
            re.search(r"(?:^|[|*\s])br[- _][a-z0-9]+(?:\b|\s*[:|])", folded)
            or "business rule" in folded
            or "aturan bisnis" in folded
        )
    if candidate_type == "ACCEPTANCE_CRITERIA":
        return bool(
            re.search(r"(?:^|[|*\s])ac[- _]?[0-9]+(?:\b|\s*[:|])", folded)
            or "acceptance criteria" in folded
            or "kriteria penerimaan" in folded
        )
    return True


def find_literal_evidence(
    content: str, candidate_type: str, *, main_flow: bool
) -> dict[str, Any]:
    patterns = MAIN_PATTERNS[candidate_type] if main_flow else DETAIL_PATTERNS[candidate_type]
    lines = active_source_lines(content)
    matching = [
        line
        for line in lines
        if _matches(line["text"], patterns)
        and _evidence_has_requirement_assertion(candidate_type, line["text"])
        and (not main_flow or _section_is_relevant(line))
    ]
    eligible = [line for line in matching if line["eligible"]]
    if eligible:
        line = eligible[0]
        return {
            "status": AUTO_STATUS,
            "evidence_line": line["line"],
            "evidence_excerpt": line["text"],
            "heading_path": line["heading_path"],
            "reason": "LITERAL_ACTIVE_SOURCE_FACT",
        }

    excluded = matching[0] if matching else None
    if excluded:
        reason = excluded["exclusion_reason"]
        status = SOURCE_GAP_STATUS if reason == "UNRESOLVED_SOURCE_MARKER" else EXCLUDED_STATUS
        return {
            "status": status,
            "evidence_line": excluded["line"],
            "evidence_excerpt": excluded["text"],
            "heading_path": excluded["heading_path"],
            "reason": reason,
        }
    return {
        "status": OPEN_STATUS,
        "evidence_line": None,
        "evidence_excerpt": "",
        "heading_path": [],
        "reason": "NO_LITERAL_ACTIVE_SOURCE_FACT_FOUND",
    }


def _candidate_item(
    *,
    mode: str,
    e2e_code: str,
    document: dict[str, Any],
    candidate_type: str,
    result: dict[str, Any],
) -> dict[str, Any]:
    document_code = str(document.get("document_code", ""))
    content_id = str(document.get("content_id", ""))
    source_path = str(document.get("primary_source_path", ""))
    line = result.get("evidence_line")
    return {
        "reconciliation_id": "AR-" + _sha1_id(mode, content_id, candidate_type),
        "reconciliation_mode": mode,
        "e2e_code": e2e_code,
        "document_code": document_code,
        "document_id": document.get("primary_source_document_id", ""),
        "content_id": content_id,
        "title": document.get("original_title", ""),
        "candidate_type": candidate_type,
        "candidate_evidence_class": "MECHANICAL_GAP_CANDIDATE",
        "reconciliation_status": result["status"],
        "resolution_decision_id": "",
        "evidence_class": (
            "SOURCE_FACT" if result["status"] == AUTO_STATUS else ""
        ),
        "verification_status": (
            "SOURCE_EXPLICIT" if result["status"] == AUTO_STATUS else "REVIEW_REQUIRED"
        ),
        "conflict_status": (
            "NO_CONFLICT_IDENTIFIED"
            if result["status"] == AUTO_STATUS
            else "NOT_CLOSED_AUTOMATICALLY"
        ),
        "evidence_reference": f"{source_path}:{line}" if line else "",
        "evidence_excerpt": result.get("evidence_excerpt", ""),
        "source_heading_path": result.get("heading_path", []),
        "reason": result.get("reason", ""),
        "scope_effect": "NONE",
        "requirement_change": "NONE",
    }


def _explicit_marker_items(
    *, e2e_code: str, document: dict[str, Any], content: str
) -> list[dict[str, Any]]:
    source_path = str(document.get("primary_source_path", ""))
    content_id = str(document.get("content_id", ""))
    active_by_line = {item["line"]: item for item in active_source_lines(content)}
    items = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        folded = _fold(line)
        markers = [
            marker
            for marker in EXPLICIT_GAP_MARKERS
            if re.search(rf"\b{re.escape(marker)}\b", folded)
        ]
        if not markers:
            continue
        source_line = active_by_line.get(line_number, {})
        exclusion_reason = str(source_line.get("exclusion_reason", ""))
        if "belum tersedia" in markers and any(
            token in folded
            for token in (
                "jika ",
                "bila ",
                "apabila ",
                "ketika ",
                "fallback",
                "input manual",
                "tetap dapat",
                "tidak melakukan autofill",
            )
        ):
            exclusion_reason = "CONTEXTUAL_ABSENCE_WITH_DEFINED_BEHAVIOR"
        status = (
            EXCLUDED_STATUS
            if exclusion_reason in {
                "NON_ACTIVE_SECTION",
                "FENCED_EXAMPLE_OR_DIAGRAM",
                "FUTURE_PHASE_ONLY",
                "ASSUMPTION_OR_PENDING_CONFIRMATION",
                "CONTEXTUAL_ABSENCE_WITH_DEFINED_BEHAVIOR",
            }
            else SOURCE_GAP_STATUS
        )
        items.append(
            {
                "reconciliation_id": "AR-"
                + _sha1_id("BUSINESS_CASES", content_id, "MARKER", str(line_number)),
                "reconciliation_mode": "BUSINESS_CASES",
                "e2e_code": e2e_code,
                "document_code": document.get("document_code", ""),
                "document_id": document.get("primary_source_document_id", ""),
                "content_id": content_id,
                "title": document.get("original_title", ""),
                "candidate_type": "EXPLICIT_UNRESOLVED_MARKER",
                "candidate_evidence_class": "SOURCE_EXPLICIT_GAP",
                "reconciliation_status": status,
                "resolution_decision_id": "",
                "evidence_class": "",
                "verification_status": "SOURCE_EXPLICIT",
                "conflict_status": "NOT_CLOSED_AUTOMATICALLY",
                "evidence_reference": f"{source_path}:{line_number}",
                "evidence_excerpt": line.strip(),
                "source_heading_path": source_line.get("heading_path", []),
                "markers": markers,
                "reason": exclusion_reason or "SOURCE_EXPLICIT_UNRESOLVED_MARKER",
                "scope_effect": "NONE",
                "requirement_change": "NONE",
            }
        )
        if len(items) >= 20:
            break
    return items


def build_register(
    *,
    repo: Path,
    inventory: dict[str, Any],
    manifest_documents: list[dict[str, Any]],
    catalog_by_id: dict[str, dict[str, Any]],
    inventory_sha256: str,
) -> dict[str, Any]:
    manifest_by_content = {
        str(item.get("content_id", "")): item for item in manifest_documents
    }
    items: list[dict[str, Any]] = []
    scanned_documents = 0

    for domain in inventory.get("domains", []):
        e2e_code = str(domain.get("e2e_code", ""))
        for membership in domain.get("documents", []):
            content_id = str(membership.get("content_id", ""))
            document = manifest_by_content[content_id]
            amendment = document.get("amendment") or {}
            if amendment.get("status") == "DECISION_APPLIED":
                # Decision-applied canonical documents no longer embed the
                # untouched source payload. Automatic source-fact scanning
                # must read the verified original payload instead.
                source_root = (repo / "source/original").resolve()
                primary = (source_root / str(document["primary_source_path"])).resolve()
                if source_root not in primary.parents:
                    raise ValueError(
                        f"Source path escapes source/original: {document['primary_source_path']}"
                    )
                raw = primary.read_bytes()
                if hashlib.sha256(raw).hexdigest() != str(document["source_sha256"]):
                    raise ValueError(
                        f"Original checksum changed for amended document: {document['path']}"
                    )
                content = raw.decode("utf-8")
            else:
                canonical_path = repo / str(document["path"])
                generated = canonical_path.read_bytes()
                offset = int(document["payload_offset"])
                length = int(document["payload_length"])
                payload = generated[offset : offset + length]
                if len(generated) != offset + length:
                    raise ValueError(
                        f"Canonical payload boundary is invalid: {document['path']}"
                    )
                content = payload.decode("utf-8")
            scanned_documents += 1

            for aspect, status in membership.get("flow_checks", {}).items():
                if aspect == "alternate_cases" or status == "SOURCE_CONTEXT_PRESENT":
                    continue
                result = find_literal_evidence(content, aspect, main_flow=True)
                items.append(
                    _candidate_item(
                        mode="MAIN_FLOW",
                        e2e_code=e2e_code,
                        document=document,
                        candidate_type=aspect,
                        result=result,
                    )
                )

            catalog_document = catalog_by_id[
                str(document.get("primary_source_document_id", ""))
            ]
            for family in detail_gap_candidate_families(
                catalog_document.get("headings", []), content
            ):
                result = find_literal_evidence(content, family, main_flow=False)
                items.append(
                    _candidate_item(
                        mode="BUSINESS_CASES",
                        e2e_code=e2e_code,
                        document=document,
                        candidate_type=family,
                        result=result,
                    )
                )

            if (
                membership.get("flow_checks", {}).get("alternate_cases")
                != "SOURCE_CONTEXT_PRESENT"
            ):
                result = find_literal_evidence(
                    content, "alternate_cases", main_flow=True
                )
                items.append(
                    _candidate_item(
                        mode="BUSINESS_CASES",
                        e2e_code=e2e_code,
                        document=document,
                        candidate_type="ALTERNATE_CASE_CONTEXT",
                        result=result,
                    )
                )

            items.extend(
                _explicit_marker_items(
                    e2e_code=e2e_code, document=document, content=content
                )
            )

    conflicts = []
    resolved_relations = []
    for relation in inventory.get("relations", []):
        if relation.get("verification_status") != "SOURCE_EXPLICIT":
            continue
        if relation.get("evidence_class") not in {
            "SOURCE_FACT",
            "CROSS_SOURCE_FACT",
        }:
            continue
        row = {
            "relation_id": relation.get("relation_id", ""),
            "source_domain_code": relation.get("source_domain_code", ""),
            "target_domain_code": relation.get("target_domain_code", ""),
            "source_document_id": relation.get("source_document_id", ""),
            "target_document_id": relation.get("target_document_id", ""),
            "relationship_type": relation.get("relationship_type", ""),
            "evidence_reference": relation.get("evidence_reference", ""),
            "evidence_excerpt": relation.get("evidence_excerpt", ""),
            "conflict_status": relation.get("conflict_status", ""),
            "reconciliation_status": (
                AUTO_STATUS
                if relation.get("conflict_status") == "NO_CONFLICT_IDENTIFIED"
                else HUMAN_STATUS
            ),
        }
        if row["reconciliation_status"] == AUTO_STATUS:
            resolved_relations.append(row)
        else:
            conflicts.append(row)

    items.sort(
        key=lambda item: (
            item["e2e_code"],
            item["reconciliation_mode"],
            item["document_code"],
            item["candidate_type"],
            item["evidence_reference"],
        )
    )
    status_counts: dict[str, int] = {}
    for item in items:
        status = str(item["reconciliation_status"])
        status_counts[status] = status_counts.get(status, 0) + 1
    mode_counts = {
        mode: {
            "candidate_count": sum(
                item["reconciliation_mode"] == mode for item in items
            ),
            "resolved_by_source_fact_count": sum(
                item["reconciliation_mode"] == mode
                and item["reconciliation_status"] == AUTO_STATUS
                for item in items
            ),
        }
        for mode in ("MAIN_FLOW", "BUSINESS_CASES")
    }
    return {
        "schema_version": 1,
        "artifact_type": "AUTOMATIC_SOURCE_FACT_RECONCILIATION_REGISTER",
        "canonical_version": "v0.0.0",
        "source_inventory_sha256": inventory_sha256,
        "source_policy": {
            "primary_source": "verified canonical payload matched byte-for-byte to eligible original Markdown PRD",
            "citation_authority": "source/original/PRD/PRD Generator (.md)/ path and line",
            "automatic_closure_rule": "literal active source fact with no identified conflict or unresolved marker",
            "requirement_change": "NONE",
        },
        "summary": {
            "scanned_document_count": scanned_documents,
            "candidate_count": len(items),
            "resolved_by_source_fact_count": status_counts.get(AUTO_STATUS, 0),
            "candidate_human_decision_required_count": status_counts.get(
                HUMAN_STATUS, 0
            ),
            "human_decision_required_count": status_counts.get(HUMAN_STATUS, 0)
            + len(conflicts),
            "open_source_explicit_gap_count": status_counts.get(
                SOURCE_GAP_STATUS, 0
            ),
            "open_insufficient_evidence_count": status_counts.get(OPEN_STATUS, 0),
            "excluded_non_active_evidence_count": status_counts.get(
                EXCLUDED_STATUS, 0
            ),
            "source_explicit_relation_resolved_count": len(resolved_relations),
            "source_explicit_relation_conflict_count": len(conflicts),
            "mode_counts": mode_counts,
        },
        "items": items,
        "resolved_source_relations": resolved_relations,
        "human_decision_required_relations": conflicts,
    }


def render_report(register: dict[str, Any]) -> bytes:
    summary = register["summary"]
    lines = [
        "# Automatic Source-Fact Reconciliation Register",
        "",
        "> This report records scanner candidates only when a literal active source fact is found. It does not add, rewrite, or remove any PRD requirement.",
        "",
        f"- Scanned canonical PRDs: `{summary['scanned_document_count']}`",
        f"- Scanner candidates reviewed: `{summary['candidate_count']}`",
        f"- Closed from literal source facts: `{summary['resolved_by_source_fact_count']}`",
        f"- Human decision required: `{summary['human_decision_required_count']}`",
        f"- Source-explicit gaps kept open: `{summary['open_source_explicit_gap_count']}`",
        f"- Open due to insufficient evidence: `{summary['open_insufficient_evidence_count']}`",
        f"- Excluded non-active evidence: `{summary['excluded_non_active_evidence_count']}`",
        f"- Existing source-explicit relations closed: `{summary['source_explicit_relation_resolved_count']}`",
        f"- Existing source conflicts kept open: `{summary['source_explicit_relation_conflict_count']}`",
        "",
        "## Results",
        "",
        "| ID | Mode | E2E | PRD | Candidate | Status | Literal evidence | Reason |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for item in register["items"]:
        evidence = str(item.get("evidence_excerpt", "")).replace("|", "\\|")
        evidence = evidence.replace("\n", " ")
        if len(evidence) > 280:
            evidence = evidence[:277] + "..."
        reference = item.get("evidence_reference", "")
        literal = f"{evidence}<br>`{reference}`" if reference else "-"
        lines.append(
            "| `{}` | `{}` | `{}` | `{}` | `{}` | `{}` | {} | `{}` |".format(
                item["reconciliation_id"],
                item["reconciliation_mode"],
                item["e2e_code"],
                item["document_code"],
                item["candidate_type"],
                item["reconciliation_status"],
                literal,
                item["reason"],
            )
        )
    lines.append("")
    return "\n".join(lines).encode("utf-8")


def json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
