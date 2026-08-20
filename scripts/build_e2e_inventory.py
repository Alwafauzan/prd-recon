#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


PRIMARY_PREFIX = "PRD/PRD Generator (.md)/"
SUPPORTING_MARKDOWN_PATHS = {
    PRIMARY_PREFIX + "Integrasi/Api Doc/APLICARES-KETERSEDIAAN KAMAR.md",
    PRIMARY_PREFIX + "KONTEKS-SESI.md",
    PRIMARY_PREFIX + "Pelayanan (.md)/ringkasan-merge-prd-rj.md",
}

LEGACY_OUTPUTS = {
    "by-e2e-domain.md",
    "by-process.md",
    "candidate-variants.csv",
    "document-e2e-coverage.csv",
    "e2e-domain-inventory.json",
    "e2e-domain-register.csv",
    "flow-document-candidates.csv",
    "flow-edge-register.csv",
    "flow-node-register.csv",
    "flow-register.csv",
    "manual-memberships.csv",
    "manual-processes.csv",
    "manual-stages.csv",
    "membership-register.csv",
    "process-inventory.json",
    "process-register.csv",
    "stage-register.csv",
    "unmapped-documents.csv",
}

DOMAIN_DEFINITIONS = (
    ("E2E-RJ", "Rawat Jalan", "pelayanan-utama", "Alur kunjungan dan pelayanan rawat jalan."),
    ("E2E-RI", "Rawat Inap", "pelayanan-utama", "Admisi, pelayanan, perpindahan, dan keluarnya pasien rawat inap."),
    ("E2E-IGD", "IGD", "pelayanan-utama", "Pendaftaran, asesmen, observasi, dan pelayanan gawat darurat."),
    ("E2E-LAB", "Laboratorium", "pelayanan-penunjang", "Order, konfirmasi, pelaksanaan, dan hasil laboratorium."),
    ("E2E-RAD", "Radiologi", "pelayanan-penunjang", "Pendaftaran, order, konfirmasi, dan hasil radiologi."),
    ("E2E-PA", "Patologi Anatomi", "pelayanan-penunjang", "Order, konfirmasi, dan hasil patologi anatomi."),
    ("E2E-REHAB", "Rehabilitasi Medik", "pelayanan-penunjang", "Penjadwalan, asesmen, dan pelayanan rehabilitasi medik."),
    ("E2E-HD", "Hemodialisa", "pelayanan-penunjang", "Order, penjadwalan, asesmen, dan monitoring hemodialisa."),
    ("E2E-IBS", "IBS dan Operasi", "pelayanan-penunjang", "Permintaan, penjadwalan, pelaksanaan, dan laporan operasi."),
    ("E2E-GIZI", "Gizi", "pelayanan-penunjang", "Order makanan, pemakaian barang, dan pelayanan gizi."),
    ("E2E-FARMASI", "Farmasi", "pelayanan-penunjang", "Pelayanan obat, retur, rekonsiliasi, dan pengaturan farmasi."),
    ("E2E-TRANSFUSI", "Transfusi Darah", "pelayanan-penunjang", "Order, konfirmasi, crossmatch, dan pelayanan transfusi darah."),
    ("E2E-VK", "VK dan Kebidanan", "pelayanan-utama", "Order tindakan dan pelayanan VK/kebidanan."),
    ("E2E-MCU", "Medical Check Up", "pelayanan-utama", "Pendaftaran dan paket pelayanan MCU."),
    ("E2E-AMBULANCE", "Ambulance", "pelayanan-penunjang", "Order dan konfirmasi layanan ambulance."),
    ("E2E-JENAZAH", "Pemulasaraan Jenazah", "pelayanan-penunjang", "Pelayanan pemulasaraan jenazah."),
    ("E2E-EMR", "Rekam Medis dan Dokumentasi Klinis", "pelayanan-lintas-domain", "Dokumentasi klinis yang digunakan lintas unit pelayanan."),
    ("E2E-SURAT", "Administrasi Surat dan Consent", "administrasi-pasien", "Pembuatan surat, persetujuan, penolakan, dan consent."),
    ("E2E-BILLING", "Billing dan Kasir", "administrasi-keuangan", "Tagihan, kasir, deposito, dan penerimaan kas."),
    ("E2E-CASEMIX", "Casemix dan Klaim", "administrasi-keuangan", "Dokumen, pengajuan, penerimaan, dan rekonsiliasi klaim."),
    ("E2E-INVENTORY", "Inventory dan Pengadaan", "backoffice", "Perencanaan, pemesanan, penerimaan, stok, dan distribusi barang."),
    ("E2E-MASTER", "Master Data dan Access Control", "platform", "Siklus master data, konfigurasi, pengguna, role, dan akses."),
    ("E2E-INTEGRASI", "Integrasi Eksternal", "platform", "Pertukaran data dengan BPJS, SATUSEHAT, dan sistem eksternal."),
)

DOMAIN_BY_CODE = {
    code: {"domain_code": code, "title": title, "domain_group": group, "purpose": purpose}
    for code, title, group, purpose in DOMAIN_DEFINITIONS
}

STAGE_ORDER = {
    "FOUNDATION": 10,
    "ENTRY": 20,
    "REQUEST": 30,
    "SCHEDULING": 40,
    "VALIDATION": 50,
    "WORKLIST": 60,
    "ASSESSMENT": 70,
    "EXECUTION": 80,
    "OUTPUT": 90,
    "SETTLEMENT": 100,
    "SUPPORTING": 110,
}

DOCUMENT_INDEX_FIELDS = (
    "content_id",
    "representative_document_id",
    "representative_title",
    "representative_source_path",
    "owner_domain_code",
    "owner_domain_title",
    "worklist_stage",
    "worklist_order",
    "assignment_status",
    "assignment_confidence",
    "assignment_basis",
    "review_status",
    "source_representation_count",
    "source_document_ids",
    "source_paths",
    "incoming_relation_count",
    "outgoing_relation_count",
    "cross_domain_relation_count",
)

RELATION_FIELDS = (
    "relation_id",
    "source_content_id",
    "source_document_id",
    "source_title",
    "source_domain_code",
    "target_content_id",
    "target_document_id",
    "target_title",
    "target_domain_code",
    "relationship_type",
    "relation_scope",
    "trigger",
    "input_context",
    "output_context",
    "status_transition",
    "condition",
    "evidence_reference",
    "evidence_excerpt",
    "evidence_class",
    "verification_status",
    "conflict_status",
    "notes",
)

OVERRIDE_FIELDS = (
    "content_id",
    "owner_domain_code",
    "decision_id",
    "status",
    "notes",
)

DUPLICATE_FIELDS = (
    "content_id",
    "owner_domain_code",
    "representative_document_id",
    "document_ids",
    "source_paths",
    "representation_count",
)

TOKEN_STOPWORDS = {
    "a",
    "and",
    "atau",
    "dan",
    "data",
    "dokumen",
    "draft",
    "final",
    "fix",
    "form",
    "management",
    "manajemen",
    "md",
    "new",
    "neurovi",
    "of",
    "pasien",
    "prd",
    "product",
    "requirement",
    "rev",
    "update",
    "v1",
    "v2",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, fieldnames: Iterable[str], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii").casefold()
    return " ".join(re.findall(r"[a-z0-9]+", value))


def clean_title(value: str, fallback: str) -> str:
    title = re.sub(r"\s+", " ", value or "").strip()
    generic = normalize(title) in {
        "product requirement document",
        "product requirement document prd",
        "prd",
    }
    if title and not generic:
        return title
    stem = Path(fallback).stem
    stem = re.sub(r"^\[?fix\]?\s*", "", stem, flags=re.I)
    stem = re.sub(r"^(?:prd[-_ ]*)+", "", stem, flags=re.I)
    stem = re.sub(r"[-_]+", " ", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    return stem or title or fallback


def eligible_documents(repository: Path) -> list[dict[str, Any]]:
    catalog = read_json(repository / "catalog/document-index.json")
    source_root = repository / "source/original"
    rows = []
    for item in catalog.get("documents", []):
        source_path = str(item.get("source_path", ""))
        if (
            item.get("extension") != ".md"
            or not source_path.startswith(PRIMARY_PREFIX)
            or source_path in SUPPORTING_MARKDOWN_PATHS
            or "/menu-flow/" in source_path
        ):
            continue
        physical = source_root / source_path
        if not physical.is_file():
            raise SystemExit(f"Eligible original PRD is missing: {physical}")
        rows.append(
            {
                **item,
                "title": clean_title(str(item.get("title", "")), source_path),
                "physical_path": physical,
                "relative_primary_path": source_path[len(PRIMARY_PREFIX) :],
            }
        )
    return sorted(rows, key=lambda item: item["source_path"].casefold())


def choose_representative(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return min(
        rows,
        key=lambda item: (
            "draft" in item["source_path"].casefold(),
            "update/" in item["source_path"].casefold(),
            item["source_path"].count("/"),
            len(item["source_path"]),
            item["source_path"].casefold(),
        ),
    )


def load_overrides(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        write_csv(path, OVERRIDE_FIELDS, [])
        return {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [field for field in OVERRIDE_FIELDS if field not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(f"manual-domain-overrides.csv is missing columns: {', '.join(missing)}")
        overrides = {}
        for row_number, row in enumerate(reader, start=2):
            content_id = (row.get("content_id") or "").strip()
            if not content_id:
                continue
            domain_code = (row.get("owner_domain_code") or "").strip()
            if domain_code not in DOMAIN_BY_CODE:
                raise SystemExit(
                    f"manual-domain-overrides.csv row {row_number}: unknown domain {domain_code}"
                )
            overrides[content_id] = {field: (row.get(field) or "").strip() for field in OVERRIDE_FIELDS}
        return overrides


def classify_domain(document: dict[str, Any]) -> tuple[str, str, str, str]:
    relative = document["relative_primary_path"]
    folded = normalize(relative + " " + document["title"])
    top = relative.split("/", 1)[0].casefold()

    if top == "billing":
        return "E2E-BILLING", "SOURCE_FOLDER", "HIGH", "MECHANICAL_PROPOSAL"
    if top == "casemix":
        return "E2E-CASEMIX", "SOURCE_FOLDER", "HIGH", "MECHANICAL_PROPOSAL"
    if top == "farmasi":
        return "E2E-FARMASI", "SOURCE_FOLDER", "HIGH", "MECHANICAL_PROPOSAL"
    if top == "integrasi":
        return "E2E-INTEGRASI", "SOURCE_FOLDER", "HIGH", "MECHANICAL_PROPOSAL"
    if top == "inventory (.md)":
        return "E2E-INVENTORY", "SOURCE_FOLDER", "HIGH", "MECHANICAL_PROPOSAL"
    if top == "emr":
        return "E2E-EMR", "SOURCE_FOLDER", "HIGH", "MECHANICAL_PROPOSAL"
    if top == "surat penunjang":
        return "E2E-SURAT", "SOURCE_FOLDER", "HIGH", "MECHANICAL_PROPOSAL"
    if top == "master data (.md)":
        if "billing" in folded or "deposit" in folded or "tagihan pasien" in folded:
            return "E2E-BILLING", "TITLE_OVERRIDES_SOURCE_FOLDER", "HIGH", "MECHANICAL_PROPOSAL"
        return "E2E-MASTER", "SOURCE_FOLDER", "HIGH", "MECHANICAL_PROPOSAL"
    if top == "pengaturan (.md)":
        if any(token in folded for token in ("farmasi", "harga obat")):
            return "E2E-FARMASI", "TITLE_KEYWORD", "HIGH", "MECHANICAL_PROPOSAL"
        if "tagihan" in folded:
            return "E2E-BILLING", "TITLE_KEYWORD", "HIGH", "MECHANICAL_PROPOSAL"
        return "E2E-MASTER", "SOURCE_FOLDER_FALLBACK", "MEDIUM", "MECHANICAL_PROPOSAL"

    rules = (
        ("E2E-AMBULANCE", ("ambulance",)),
        ("E2E-JENAZAH", ("pemulasaraan jenazah",)),
        ("E2E-TRANSFUSI", ("transfusi darah", "crossmatch", "kantong darah")),
        ("E2E-PA", ("patologi anatomi",)),
        ("E2E-LAB", ("laboratorium",)),
        ("E2E-RAD", ("radiologi",)),
        ("E2E-REHAB", ("rehab medik", "rehabilitasi medik", "rehabilitas medis", "dashboard pelayanan terapi")),
        ("E2E-HD", ("hemodialisa", "hemodialisis", "dashboard hd", "monitoring hd", "asesmen hd")),
        ("E2E-IGD", (" igd ", "pendaftaran igd", "gawat darurat")),
        ("E2E-VK", ("dashboard vk", "tindakan vk", " vk ", "kebidanan")),
        ("E2E-MCU", (" mcu ", "medical check up")),
        ("E2E-RI", ("rawat inap", "tppri", "spri", "pindah bed", "transfer internal", "titip kelas", "ubah dpjp", "discharge pasien", "ews anak", "ews dewasa", "ews neonatus", "update ketersediaan bed", "bina rohani")),
        ("E2E-RJ", ("rawat jalan", "poliklinik", "antrian apm", "display antrean", "dashboard pelayanan integrasi", "general consent rj", "riwayat kunjungan")),
        ("E2E-IBS", ("operasi", "anestesi", "dashboard ibs", "ruang ibs", "bedah non trauma", "bedah trauma")),
        ("E2E-GIZI", ("gizi", "makanan pasien", "menu makanan")),
        ("E2E-FARMASI", ("farmasi", "apotek", "obat", "alat kesehatan")),
        ("E2E-SURAT", ("surat", "consent", "persetujuan", "penolakan", "informasi tindakan kedokteran")),
        ("E2E-EMR", ("resume medis", "ringkasan kesehatan", "jawaban konsulan", "tindakan bhp", "data alergi", "catatan pasien")),
    )
    padded = f" {folded} "
    for domain_code, keywords in rules:
        if any(keyword in padded for keyword in keywords):
            return domain_code, f"TITLE_KEYWORD:{next(keyword for keyword in keywords if keyword in padded).strip()}", "HIGH", "MECHANICAL_PROPOSAL"
    return "E2E-EMR", "CLINICAL_SHARED_FALLBACK", "LOW", "REVIEW_REQUIRED"


def classify_stage(document: dict[str, Any]) -> str:
    value = normalize(document["relative_primary_path"] + " " + document["title"])
    if "master data" in value or "pengaturan" in value or "konfigurasi" in value or "rbac" in value:
        return "FOUNDATION"
    if any(token in value for token in ("pendaftaran", "check in", "apm", "general consent")):
        return "ENTRY"
    if any(token in value for token in ("order", "permintaan", "spri", "pemesanan", "rencana pengadaan")):
        return "REQUEST"
    if any(token in value for token in ("jadwal", "penjadwalan", "waiting list")):
        return "SCHEDULING"
    if any(token in value for token in ("konfirmasi", "verifikasi", "rekonsiliasi")):
        return "VALIDATION"
    if any(token in value for token in ("dashboard", "display", "menu ", "informasi stok")):
        return "WORKLIST"
    if any(token in value for token in ("asesmen", "skrining", "observasi", "ews")):
        return "ASSESSMENT"
    if any(token in value for token in ("hasil", "resume", "discharge", "pulangkan", "surat keterangan", "laporan operasi")):
        return "OUTPUT"
    if any(token in value for token in ("billing", "tagihan", "kasir", "deposit", "klaim")):
        return "SETTLEMENT"
    if any(token in value for token in ("tindakan", "pelayanan", "monitoring", "input", "catatan", "transfer", "pindah", "retur", "distribusi", "penerimaan", "penggunaan")):
        return "EXECUTION"
    return "SUPPORTING"


def source_checks(content: str) -> dict[str, str]:
    folded = normalize(content)
    checks = {
        "trigger_input": ("trigger", "pemicu", "precondition", "prasyarat", "input"),
        "sequence": ("main flow", "alur utama", "business process", "proses bisnis", "skenario"),
        "handoff": ("dependency", "dependensi", "integrasi", "terkait", "dashboard"),
        "output": ("output", "hasil", "tersimpan", "terbentuk"),
        "status_transition": ("status", "transisi", "berubah menjadi"),
        "alternate_cases": ("alternate", "alternatif", "exception", "pengecualian", "jika"),
    }
    return {
        name: "SOURCE_CONTEXT_PRESENT" if any(token in folded for token in tokens) else "REVIEW_REQUIRED"
        for name, tokens in checks.items()
    }


def alias_tokens(value: str) -> list[str]:
    tokens = []
    for token in normalize(value).split():
        if token in TOKEN_STOPWORDS or re.fullmatch(r"[a-z]?\d+[a-z]?", token):
            continue
        tokens.append(token)
    return tokens


def document_aliases(document: dict[str, Any]) -> list[str]:
    values = [document["title"], Path(document["relative_primary_path"]).stem]
    aliases = set()
    for value in values:
        tokens = alias_tokens(value)
        if len(tokens) >= 2:
            alias = " ".join(tokens)
            if len(alias) >= 12:
                aliases.add(alias)
        if len(tokens) >= 4:
            aliases.add(" ".join(tokens[-4:]))
    return sorted(aliases, key=lambda value: (-len(value.split()), -len(value), value))[:4]


def evidence_line(document: dict[str, Any], patterns: Iterable[str]) -> tuple[str, str] | None:
    lines = document["content"].splitlines()
    normalized_patterns = [normalize(pattern) for pattern in patterns if normalize(pattern)]
    for line_number, line in enumerate(lines, start=1):
        folded = normalize(line)
        if any(pattern in folded for pattern in normalized_patterns):
            excerpt = re.sub(r"\s+", " ", line).strip()[:400]
            return f"{document['source_path']}:{line_number}", excerpt
    return None


def evidence_line_in_range(
    document: dict[str, Any], patterns: Iterable[str], start_line: int,
    *, require_all: bool = False,
) -> tuple[str, str] | None:
    lines = document["content"].splitlines()
    normalized_patterns = [normalize(pattern) for pattern in patterns if normalize(pattern)]
    for line_number, line in enumerate(lines, start=1):
        if line_number < start_line:
            continue
        folded = normalize(line)
        matches = (
            all(pattern in folded for pattern in normalized_patterns)
            if require_all
            else any(pattern in folded for pattern in normalized_patterns)
        )
        if matches:
            excerpt = re.sub(r"\s+", " ", line).strip()[:400]
            return f"{document['source_path']}:{line_number}", excerpt
    return None


def relation_id(source_content_id: str, target_content_id: str, relationship_type: str) -> str:
    payload = f"{source_content_id}|{target_content_id}|{relationship_type}".encode("utf-8")
    return "REL-" + hashlib.sha1(payload).hexdigest()[:12].upper()


def relation_row(
    source: dict[str, Any],
    target: dict[str, Any],
    relationship_type: str,
    evidence: tuple[str, str],
    *,
    evidence_class: str,
    verification_status: str,
    conflict_status: str = "NO_CONFLICT_IDENTIFIED",
    trigger: str = "",
    input_context: str = "",
    output_context: str = "",
    status_transition: str = "",
    condition: str = "",
    notes: str = "",
) -> dict[str, Any]:
    return {
        "relation_id": relation_id(source["content_id"], target["content_id"], relationship_type),
        "source_content_id": source["content_id"],
        "source_document_id": source["document_id"],
        "source_title": source["title"],
        "source_domain_code": source["owner_domain_code"],
        "target_content_id": target["content_id"],
        "target_document_id": target["document_id"],
        "target_title": target["title"],
        "target_domain_code": target["owner_domain_code"],
        "relationship_type": relationship_type,
        "relation_scope": "WITHIN_DOMAIN" if source["owner_domain_code"] == target["owner_domain_code"] else "CROSS_DOMAIN",
        "trigger": trigger,
        "input_context": input_context,
        "output_context": output_context,
        "status_transition": status_transition,
        "condition": condition,
        "evidence_reference": evidence[0],
        "evidence_excerpt": evidence[1],
        "evidence_class": evidence_class,
        "verification_status": verification_status,
        "conflict_status": conflict_status,
        "notes": notes,
    }


def explicit_relations(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_suffix = {document["relative_primary_path"]: document for document in documents}
    rules = (
        # Direct operational handoffs with unambiguous source wording and targets.
        {
            "source": "Pelayanan (.md)/PRD-Dashboard-Pelayanan-IGD.md",
            "target": "Pelayanan (.md)/PRD_Transfer_Internal.md",
            "evidence": "target",
            "patterns": ("Dashboard Pelayanan IGD", "Form Transfer Internal"),
            "min_line": 136,
            "type": "ENTRY_POINT_TO",
            "trigger": "Dashboard Pelayanan IGD menjadi entry point Form Transfer Internal.",
        },
        {
            "source": "Pelayanan (.md)/PRD-Dashboard-Pelayanan-IGD.md",
            "target": "Pelayanan (.md)/PRD-Order-Hemodialisa.md",
            "evidence": "target",
            "patterns": ("Entry point IGD", "Rujuk ke Hemodialisa"),
            "min_line": 56,
            "type": "ENTRY_POINT_TO",
            "trigger": "Aksi Rujuk ke Hemodialisa dijalankan dari Dashboard Pelayanan IGD.",
            "output_context": "Order HD yang berhasil dibuat menyebabkan pasien masuk/tersedia pada Dashboard Pelayanan Hemodialisa.",
        },
        {
            "source": "Pelayanan (.md)/NV-171-PRD-Dashboard-Pelayanan-Rawat-Inap-Neurovi-v2-v1.2.md",
            "target": "Pelayanan (.md)/PRD-Order-Hemodialisa.md",
            "evidence": "target",
            "patterns": ("Entry point Rawat Inap", "Rujuk ke Hemodialisa"),
            "min_line": 56,
            "type": "ENTRY_POINT_TO",
            "trigger": "Aksi Rujuk ke Hemodialisa dijalankan dari Dashboard Pelayanan Rawat Inap.",
            "output_context": "Order HD yang berhasil dibuat menyebabkan pasien masuk/tersedia pada Dashboard Pelayanan Hemodialisa.",
        },
        {
            "source": "Pelayanan (.md)/prd-pendaftaran-pendaftaran-rawat-jalan.md",
            "target": "Pelayanan (.md)/PRD-Order-Hemodialisa.md",
            "evidence": "target",
            "patterns": ("Entry point Rawat Jalan", "Order HD / Rujuk ke Hemodialisa"),
            "min_line": 56,
            "type": "ENTRY_POINT_TO",
            "trigger": "Aksi Order HD / Rujuk ke Hemodialisa dijalankan dari Pendaftaran Rawat Jalan.",
            "output_context": "Order HD yang berhasil dibuat menyebabkan pasien masuk/tersedia pada Dashboard Pelayanan Hemodialisa.",
        },
        {
            "source": "Pelayanan (.md)/PRD-Dashboard-Pelayanan-IGD.md",
            "target": "Pelayanan (.md)/PRD-Order-Pemeriksaan-Laboratorium.md",
            "evidence": "target",
            "patterns": ("Dashboard Pelayanan IGD", "Entry point"),
            "min_line": 100,
            "type": "ENTRY_POINT_TO",
            "trigger": "Pemeriksaan Penunjang menuju Laboratorium Klinik dimulai dari Dashboard Pelayanan IGD.",
            "input_context": "Registrasi aktif pasien IGD.",
        },
        {
            "source": "Pelayanan (.md)/NV-171-PRD-Dashboard-Pelayanan-Rawat-Inap-Neurovi-v2-v1.2.md",
            "target": "Pelayanan (.md)/PRD-Order-Pemeriksaan-Laboratorium.md",
            "evidence": "target",
            "patterns": ("Dashboard Pelayanan Rawat Inap", "Entry point"),
            "min_line": 100,
            "type": "ENTRY_POINT_TO",
            "trigger": "Pemeriksaan Penunjang menuju Laboratorium Klinik dimulai dari Dashboard Pelayanan Rawat Inap.",
            "input_context": "Registrasi aktif pasien Rawat Inap.",
        },
        {
            "source": "Pelayanan (.md)/PRD-Dashboard-Pelayanan-IGD.md",
            "target": "Pelayanan (.md)/PRD-Order-Retur-Obat.md",
            "evidence": "target",
            "patterns": ("Dashboard Pelayanan IGD", "Entry point"),
            "min_line": 107,
            "type": "ENTRY_POINT_TO",
            "trigger": "Dashboard Pelayanan IGD menjadi entry point Order Retur Obat.",
            "input_context": "Konteks episode IGD.",
        },
        {
            "source": "Pelayanan (.md)/NV-171-PRD-Dashboard-Pelayanan-Rawat-Inap-Neurovi-v2-v1.2.md",
            "target": "Pelayanan (.md)/PRD-Order-Retur-Obat.md",
            "evidence": "target",
            "patterns": ("Dashboard Pelayanan Rawat Inap", "Entry point"),
            "min_line": 107,
            "type": "ENTRY_POINT_TO",
            "trigger": "Dashboard Pelayanan Rawat Inap menjadi entry point Order Retur Obat.",
            "input_context": "Konteks episode Rawat Inap.",
        },
        {
            "source": "Pelayanan (.md)/PRD-Dashboard-Retur-Farmasi-IGD-Rawat-Inap.md",
            "target": "inventory (.md)/prd-inventory-informasi-stok (2).md",
            "evidence": "source",
            "patterns": ("Inventory / Informasi Stok", "Menerima posting stok operasional"),
            "min_line": 120,
            "type": "HANDOFF_TO",
            "output_context": "Inventory / Informasi Stok menerima posting stok operasional dan History Stock Retur Pasien hanya untuk item Milik Pasien non-racikan.",
        },
        {
            "source": "Pelayanan (.md)/PRD-Dashboard-Pelayanan-RJ-v2.1.md",
            "target": "Pelayanan (.md)/PRD_Transfer_Internal.md",
            "evidence": "target",
            "patterns": ("Dashboard Pelayanan Poli Rawat Jalan", "Transfer Internal"),
            "min_line": 130,
            "type": "ENTRY_POINT_TO",
            "trigger": "Aksi Transfer Internal dari dashboard pelayanan rawat jalan.",
            "notes": "Relasi lintas worklist tetap dicatat tanpa menduplikasi kepemilikan PRD.",
        },
        {
            "source": "Pelayanan (.md)/PRD-Dashboard-Pelayanan-RJ-v2.1.md",
            "target": "Pelayanan (.md)/PRD-Discharge-Pasien.md",
            "evidence": "source",
            "patterns": ("Pemulangan", "Status Keluar"),
            "min_line": 155,
            "type": "ENTRY_POINT_TO",
            "trigger": "Aksi Pulangkan Pasien dari dashboard pelayanan rawat jalan.",
        },
        {
            "source": "Pelayanan (.md)/PRD-Dashboard-Pelayanan-RJ-v2.1.md",
            "target": "Pelayanan (.md)/PRD-SPRI.md",
            "evidence": "source",
            "patterns": ("Rawat Inap", "keterdaftaran Ranap"),
            "min_line": 155,
            "type": "HANDOFF_TO",
            "output_context": "Disposisi Rawat Inap memeriksa hasil admisi; status hanya ditetapkan ketika pasien sudah terdaftar Rawat Inap.",
        },
        {
            "source": "Pelayanan (.md)/PRD-SPRI.md",
            "target": "Pelayanan (.md)/NV-176-PRD-Pendaftaran-Rawat-Inap-TPPRI-Neurovi-v2-v1.6.md",
            "evidence": "source",
            "patterns": ("Waiting List", "pendaftaran rawat inap"),
            "min_line": 10,
            "type": "PRODUCES",
            "output_context": "SPRI yang tersimpan membentuk kandidat Waiting List untuk admisi rawat inap.",
            "status_transition": "SPRI tersimpan menuju Waiting List.",
        },
        {
            "source": "Pelayanan (.md)/NV-176-PRD-Pendaftaran-Rawat-Inap-TPPRI-Neurovi-v2-v1.6.md",
            "target": "Pelayanan (.md)/NV-171-PRD-Dashboard-Pelayanan-Rawat-Inap-Neurovi-v2-v1.2.md",
            "evidence": "source",
            "patterns": ("Dashboard Pelayanan Rawat Inap", "aktivasi"),
            "min_line": 20,
            "type": "ACTIVATES",
            "status_transition": "Aktivasi admisi membuat pasien masuk worklist pelayanan rawat inap.",
        },
        {
            "source": "Pelayanan (.md)/PRD_Transfer_Internal.md",
            "target": "Pelayanan (.md)/NV-176-PRD-Pendaftaran-Rawat-Inap-TPPRI-Neurovi-v2-v1.6.md",
            "evidence": "target",
            "patterns": ("Transfer Internal", "disimpan"),
            "min_line": 20,
            "type": "HANDOFF_TO",
            "condition": "Urutan dan sifat wajib Transfer Internal perlu direkonsiliasi antar-PRD.",
            "conflict": "CONFLICT_FOUND",
            "notes": "Transfer Internal menyatakan form tidak lagi memblokir admisi/perpindahan, sedangkan TPPRI mengaitkan aktivasi dengan Transfer Internal yang disimpan.",
        },
    )
    rows = []
    for rule in rules:
        source = by_suffix.get(rule["source"])
        target = by_suffix.get(rule["target"])
        if source is None or target is None:
            continue
        evidence_document = source if rule["evidence"] == "source" else target
        evidence = evidence_line_in_range(
            evidence_document,
            rule["patterns"],
            rule.get("min_line", 1),
            require_all=rule.get("require_all", True),
        )
        if evidence is None:
            continue
        rows.append(
            relation_row(
                source,
                target,
                rule["type"],
                evidence,
                evidence_class="CROSS_SOURCE_FACT",
                verification_status="SOURCE_EXPLICIT",
                conflict_status=rule.get("conflict", "NO_CONFLICT_IDENTIFIED"),
                trigger=rule.get("trigger", ""),
                input_context=rule.get("input_context", ""),
                output_context=rule.get("output_context", ""),
                status_transition=rule.get("status_transition", ""),
                condition=rule.get("condition", ""),
                notes=rule.get("notes", ""),
            )
        )
    return rows


def mechanical_relations(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    aliases = {document["content_id"]: document_aliases(document) for document in documents}
    rows = []
    seen_pairs = set()
    for source in documents:
        content = normalize(source["content"])
        matches = []
        for target in documents:
            if source["content_id"] == target["content_id"]:
                continue
            alias = next((value for value in aliases[target["content_id"]] if value in content), None)
            if alias is None:
                continue
            evidence = evidence_line(source, (alias,))
            if evidence is not None:
                matches.append((len(alias.split()), len(alias), target, alias, evidence))
        for _, _, target, alias, evidence in sorted(matches, reverse=True, key=lambda item: (item[0], item[1]))[:30]:
            pair = (source["content_id"], target["content_id"])
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            rows.append(
                relation_row(
                    source,
                    target,
                    "REFERENCES",
                    evidence,
                    evidence_class="MECHANICAL_CANDIDATE",
                    verification_status="REVIEW_REQUIRED",
                    notes=f"Nama dokumen/kapabilitas target terdeteksi secara literal: {alias}",
                )
            )
    return rows


def build(repository: Path, target: Path) -> dict[str, Any]:
    target.mkdir(parents=True, exist_ok=True)
    for filename in LEGACY_OUTPUTS:
        legacy = target / filename
        if legacy.is_file():
            legacy.unlink()

    overrides = load_overrides(target / "manual-domain-overrides.csv")
    eligible = eligible_documents(repository)
    grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for document in eligible:
        grouped[document["content_id"]].append(document)

    unique_documents = []
    for content_id, representations in grouped.items():
        representative = dict(choose_representative(representations))
        representative["content"] = representative["physical_path"].read_text(
            encoding="utf-8-sig", errors="replace"
        )
        override = overrides.get(content_id)
        if override:
            domain_code = override["owner_domain_code"]
            basis = f"USER_OVERRIDE:{override.get('decision_id') or 'UNVERSIONED'}"
            confidence = "CONFIRMED"
            assignment_status = override.get("status") or "USER_CONFIRMED"
            review_status = "CONFIRMED"
        else:
            domain_code, basis, confidence, assignment_status = classify_domain(representative)
            review_status = "REVIEW_REQUIRED" if confidence == "LOW" else "UNCONFIRMED"
        representative.update(
            {
                "owner_domain_code": domain_code,
                "owner_domain_title": DOMAIN_BY_CODE[domain_code]["title"],
                "assignment_basis": basis,
                "assignment_confidence": confidence,
                "assignment_status": assignment_status,
                "review_status": review_status,
                "worklist_stage": classify_stage(representative),
                "source_checks": source_checks(representative["content"]),
                "representations": sorted(
                    (
                        {
                            "document_id": item["document_id"],
                            "source_path": item["source_path"],
                            "title": item["title"],
                            "sha256": item["sha256"],
                        }
                        for item in representations
                    ),
                    key=lambda item: item["source_path"].casefold(),
                ),
            }
        )
        unique_documents.append(representative)

    unique_documents.sort(
        key=lambda item: (
            item["owner_domain_code"],
            STAGE_ORDER[item["worklist_stage"]],
            item["title"].casefold(),
            item["source_path"].casefold(),
        )
    )
    order_by_domain: Counter[str] = Counter()
    for document in unique_documents:
        order_by_domain[document["owner_domain_code"]] += 1
        document["worklist_order"] = order_by_domain[document["owner_domain_code"]]

    relation_map = {
        row["relation_id"]: row
        for row in mechanical_relations(unique_documents) + explicit_relations(unique_documents)
    }
    relations = sorted(
        relation_map.values(),
        key=lambda row: (
            row["source_domain_code"],
            row["source_title"].casefold(),
            row["target_title"].casefold(),
            row["relationship_type"],
        ),
    )

    incoming: Counter[str] = Counter()
    outgoing: Counter[str] = Counter()
    cross_domain: Counter[str] = Counter()
    incoming_ids: defaultdict[str, list[str]] = defaultdict(list)
    outgoing_ids: defaultdict[str, list[str]] = defaultdict(list)
    for relation in relations:
        outgoing[relation["source_content_id"]] += 1
        incoming[relation["target_content_id"]] += 1
        outgoing_ids[relation["source_content_id"]].append(relation["relation_id"])
        incoming_ids[relation["target_content_id"]].append(relation["relation_id"])
        if relation["relation_scope"] == "CROSS_DOMAIN":
            cross_domain[relation["source_content_id"]] += 1
            cross_domain[relation["target_content_id"]] += 1

    domain_documents: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    document_rows = []
    duplicate_rows = []
    for document in unique_documents:
        representations = document["representations"]
        domain_documents[document["owner_domain_code"]].append(
            {
                "worklist_order": document["worklist_order"],
                "worklist_stage": document["worklist_stage"],
                "content_id": document["content_id"],
                "document_id": document["document_id"],
                "title": document["title"],
                "source_path": document["source_path"],
                "source_representations": representations,
                "assignment_status": document["assignment_status"],
                "assignment_confidence": document["assignment_confidence"],
                "assignment_basis": document["assignment_basis"],
                "review_status": document["review_status"],
                "flow_checks": document["source_checks"],
                "incoming_relation_ids": incoming_ids[document["content_id"]],
                "outgoing_relation_ids": outgoing_ids[document["content_id"]],
            }
        )
        document_rows.append(
            {
                "content_id": document["content_id"],
                "representative_document_id": document["document_id"],
                "representative_title": document["title"],
                "representative_source_path": document["source_path"],
                "owner_domain_code": document["owner_domain_code"],
                "owner_domain_title": document["owner_domain_title"],
                "worklist_stage": document["worklist_stage"],
                "worklist_order": document["worklist_order"],
                "assignment_status": document["assignment_status"],
                "assignment_confidence": document["assignment_confidence"],
                "assignment_basis": document["assignment_basis"],
                "review_status": document["review_status"],
                "source_representation_count": len(representations),
                "source_document_ids": "|".join(item["document_id"] for item in representations),
                "source_paths": "|".join(item["source_path"] for item in representations),
                "incoming_relation_count": incoming[document["content_id"]],
                "outgoing_relation_count": outgoing[document["content_id"]],
                "cross_domain_relation_count": cross_domain[document["content_id"]],
            }
        )
        if len(representations) > 1:
            duplicate_rows.append(
                {
                    "content_id": document["content_id"],
                    "owner_domain_code": document["owner_domain_code"],
                    "representative_document_id": document["document_id"],
                    "document_ids": "|".join(item["document_id"] for item in representations),
                    "source_paths": "|".join(item["source_path"] for item in representations),
                    "representation_count": len(representations),
                }
            )

    domain_payloads = []
    for code, definition in DOMAIN_BY_CODE.items():
        documents = domain_documents.get(code, [])
        if not documents:
            continue
        relation_ids = sorted(
            relation["relation_id"]
            for relation in relations
            if relation["source_domain_code"] == code or relation["target_domain_code"] == code
        )
        domain_payloads.append(
            {
                "e2e_code": code,
                **definition,
                "status": "DOMAIN_WORKLIST_PROPOSAL",
                "origin": "ELIGIBLE_ORIGINAL_PRD",
                "document_count": len(documents),
                "duplicate_representation_count": sum(
                    len(item["source_representations"]) - 1 for item in documents
                ),
                "review_required_count": sum(
                    item["review_status"] == "REVIEW_REQUIRED" for item in documents
                ),
                "relation_count": len(relation_ids),
                "cross_domain_relation_count": sum(
                    relation["relation_scope"] == "CROSS_DOMAIN"
                    and (relation["source_domain_code"] == code or relation["target_domain_code"] == code)
                    for relation in relations
                ),
                "documents": documents,
                "relation_ids": relation_ids,
            }
        )

    domain_register_rows = [
        {
            "domain_code": domain["domain_code"],
            "title": domain["title"],
            "domain_group": domain["domain_group"],
            "status": domain["status"],
            "document_count": domain["document_count"],
            "relation_count": domain["relation_count"],
            "cross_domain_relation_count": domain["cross_domain_relation_count"],
            "review_required_count": domain["review_required_count"],
            "purpose": domain["purpose"],
        }
        for domain in domain_payloads
    ]

    assignment_counts = Counter(item["owner_domain_code"] for item in unique_documents)
    inventory_seed = "\n".join(
        f"{item['content_id']}|{item['owner_domain_code']}|{item['worklist_order']}"
        for item in unique_documents
    )
    inventory_version = hashlib.sha256(inventory_seed.encode("utf-8")).hexdigest()[:16]
    payload = {
        "schema_version": 2,
        "inventory_type": "E2E_DOMAIN_WORKLIST",
        "inventory_version": inventory_version,
        "authority": "MECHANICAL_PROPOSAL_WITH_SOURCE_TRACE",
        "source_policy": {
            "primary_source_root": "source/original/" + PRIMARY_PREFIX.rstrip("/"),
            "eligible_extension": ".md",
            "excluded_supporting_markdown": sorted(SUPPORTING_MARKDOWN_PATHS),
            "supporting_sources_role": "REASONING_ONLY",
            "mermaid_role": "REASONING_ONLY_NOT_INVENTORY",
        },
        "eligible_file_count": len(eligible),
        "unique_prd_count": len(unique_documents),
        "assigned_unique_prd_count": len(unique_documents),
        "unassigned_unique_prd_count": 0,
        "duplicate_representation_count": len(eligible) - len(unique_documents),
        "domain_count": len(domain_payloads),
        "relation_count": len(relations),
        "cross_domain_relation_count": sum(row["relation_scope"] == "CROSS_DOMAIN" for row in relations),
        "conflict_relation_count": sum(row["conflict_status"] == "CONFLICT_FOUND" for row in relations),
        "assignment_counts": dict(sorted(assignment_counts.items())),
        "domains": domain_payloads,
        "relations": relations,
    }

    if len(eligible) != 212 or len(unique_documents) != 209:
        raise SystemExit(
            "Eligible PRD invariant failed: "
            f"files={len(eligible)} expected=212, unique={len(unique_documents)} expected=209"
        )
    if sum(assignment_counts.values()) != len(unique_documents):
        raise SystemExit("Owner-domain assignment invariant failed")
    if any(row["owner_domain_code"] not in DOMAIN_BY_CODE for row in document_rows):
        raise SystemExit("Unknown owner domain detected")

    write_json(target / "domain-worklist.json", payload)
    write_csv(target / "document-domain-index.csv", DOCUMENT_INDEX_FIELDS, document_rows)
    write_csv(target / "document-relation-index.csv", RELATION_FIELDS, relations)
    write_csv(target / "duplicate-representations.csv", DUPLICATE_FIELDS, duplicate_rows)
    write_csv(
        target / "domain-register.csv",
        (
            "domain_code",
            "title",
            "domain_group",
            "status",
            "document_count",
            "relation_count",
            "cross_domain_relation_count",
            "review_required_count",
            "purpose",
        ),
        domain_register_rows,
    )

    markdown = [
        "# E2E Domain Worklist",
        "",
        "> This is a flow-checking worklist. Owner-domain assignment is unique; cross-domain context is represented by relations, not duplicate ownership.",
        "",
        f"- Eligible Markdown PRD files: `{len(eligible)}`",
        f"- Unique PRDs: `{len(unique_documents)}`",
        f"- Assigned unique PRDs: `{len(unique_documents)}`",
        "- Unassigned unique PRDs: `0`",
        f"- Domains: `{len(domain_payloads)}`",
        f"- Relations: `{len(relations)}`",
        f"- Cross-domain relations: `{payload['cross_domain_relation_count']}`",
        "",
    ]
    for domain in domain_payloads:
        markdown.extend(
            [
                f"## {domain['domain_code']} - {domain['title']}",
                "",
                domain["purpose"],
                "",
            ]
        )
        for item in domain["documents"]:
            checks = ", ".join(
                name for name, status in item["flow_checks"].items() if status == "REVIEW_REQUIRED"
            ) or "none"
            markdown.append(
                f"{item['worklist_order']}. [{item['worklist_stage']}] {item['title']} "
                f"(`{item['document_id']}`, `{item['content_id']}`) - review: {checks}"
            )
        markdown.append("")
    (target / "domain-worklist.md").write_text("\n".join(markdown).rstrip() + "\n", encoding="utf-8")

    readme = f"""# E2E Domain Worklist Inventory

Inventaris ini adalah satu-satunya inventaris E2E aktif. Tujuannya adalah menjadi worklist pemeriksaan kesinambungan flow, bukan klasifikasi folder dan bukan salinan flow Mermaid.

## Kebijakan sumber

- Sumber utama hanya file `.md` di `source/original/{PRIMARY_PREFIX.rstrip('/')}/`.
- Tiga artefak Markdown penunjang yang tercantum pada manifest tidak menjadi PRD utama.
- Mermaid, Graphify, PDF, DOCX, folder Copy, dan sumber lain hanya boleh membantu reasoning/discovery.
- Setiap `content_id` memiliki tepat satu owner domain.
- PRD yang dipakai lintas domain tetap dimiliki satu domain dan dihubungkan melalui `document-relation-index.csv`.
- Generator gagal bila jumlah PRD unik yang belum memiliki domain lebih dari nol.

## Berkas aktif

- `domain-worklist.json`: inventaris machine-readable yang authoritative.
- `domain-worklist.md`: tampilan worklist untuk manusia.
- `domain-register.csv`: ringkasan domain.
- `document-domain-index.csv`: tepat satu baris per PRD unik beserta owner domain.
- `document-relation-index.csv`: relasi dalam dan lintas domain beserta bukti.
- `duplicate-representations.csv`: representasi file identik yang berbagi satu owner.
- `manual-domain-overrides.csv`: keputusan domain eksplisit; isi hanya dengan decision ID.
- `inventory-manifest.json`: invariant, input, dan output build.

## Status bukti

Assignment tanpa decision ID adalah `MECHANICAL_PROPOSAL`. Relasi `SOURCE_EXPLICIT` memiliki kutipan dari PRD eligible, sedangkan `REVIEW_REQUIRED` adalah kandidat mekanis. Konflik tetap dicatat dan tidak diselesaikan otomatis.
"""
    (target / "README.md").write_text(readme, encoding="utf-8")

    manifest = {
        "schema_version": 2,
        "inventory_type": "E2E_DOMAIN_WORKLIST",
        "inventory_version": inventory_version,
        "inputs": [
            "catalog/document-index.json",
            "source/original/" + PRIMARY_PREFIX.rstrip("/"),
            "reconciliation/e2e-inventory/manual-domain-overrides.csv",
        ],
        "outputs": [
            "reconciliation/e2e-inventory/README.md",
            "reconciliation/e2e-inventory/domain-register.csv",
            "reconciliation/e2e-inventory/domain-worklist.json",
            "reconciliation/e2e-inventory/domain-worklist.md",
            "reconciliation/e2e-inventory/document-domain-index.csv",
            "reconciliation/e2e-inventory/document-relation-index.csv",
            "reconciliation/e2e-inventory/duplicate-representations.csv",
        ],
        "invariants": {
            "eligible_file_count": len(eligible),
            "unique_prd_count": len(unique_documents),
            "assigned_unique_prd_count": len(unique_documents),
            "unassigned_unique_prd_count": 0,
            "single_owner_per_content_id": True,
        },
        "legacy_inventory_policy": "REMOVED_NOT_GENERATED",
    }
    write_json(target / "inventory-manifest.json", manifest)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the Neurovi E2E domain worklist inventory.")
    parser.add_argument("--repo", type=Path, default=Path("neurovi-prd"))
    parser.add_argument("--target", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repository = args.repo.resolve()
    target = args.target.resolve() if args.target else repository / "reconciliation/e2e-inventory"
    payload = build(repository, target)
    print(
        json.dumps(
            {
                "status": "BUILT",
                "eligible_file_count": payload["eligible_file_count"],
                "unique_prd_count": payload["unique_prd_count"],
                "assigned_unique_prd_count": payload["assigned_unique_prd_count"],
                "unassigned_unique_prd_count": payload["unassigned_unique_prd_count"],
                "domain_count": payload["domain_count"],
                "relation_count": payload["relation_count"],
                "cross_domain_relation_count": payload["cross_domain_relation_count"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
