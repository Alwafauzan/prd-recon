#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any


OVERRIDE_FIELDS = [
    "document_id",
    "manual_domain",
    "canonical_code",
    "canonical_title",
    "owner",
    "review_status",
    "include_in_reconciliation",
    "notes",
]

REGISTER_FIELDS = [
    "inventory_domain",
    "derived_domain",
    "domain_basis",
    "manual_domain",
    "manual_domain_confirmed",
    "review_status",
    "include_in_reconciliation",
    "canonical_code",
    "canonical_title",
    "owner",
    "document_id",
    "content_id",
    "title",
    "source_path",
    "source_directory",
    "source_tree",
    "extension",
    "bytes",
    "sha256",
    "catalog_id",
    "catalog_name",
    "catalog_category",
    "process_ids",
    "process_categories",
    "process_roles",
    "mermaid_flow_ids",
    "mermaid_flow_kinds",
    "exact_content_group_size",
    "normalized_text_group_size",
    "mechanical_filename_group_size",
    "generator_counterparts",
    "relation_types",
    "filename_markers",
    "notes",
]

GENERATOR_TREES = {"PRD Generator (.md)", "PRD Generator (.md) - Copy"}
DOMAIN_ALIASES = {
    "inventory": "Inventory",
    "inventory (.md)": "Inventory",
    "master data (.md)": "Master Data",
    "pelayanan (.md)": "Pelayanan",
    "pengaturan (.md)": "Pengaturan",
    "menu-flow": "Process Flow",
    "tools": "Repository Tooling",
    ".vscode": "Repository Tooling",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_domain(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value).strip()
    if not cleaned:
        return "Unclassified"
    return DOMAIN_ALIASES.get(cleaned.casefold(), cleaned)


def source_domain(source_path: str) -> tuple[str, str]:
    parts = PurePosixPath(source_path).parts
    if not parts:
        return "Unclassified", "unknown"
    if parts[0] != "PRD" or len(parts) < 2:
        return normalize_domain(parts[0]), "source-path"
    if parts[1] not in GENERATOR_TREES:
        return normalize_domain(parts[1]), "source-path"
    if len(parts) < 4:
        return "Generator Root", "source-path"
    return normalize_domain(parts[2]), "source-path"


def source_tree(source_path: str) -> str:
    parts = PurePosixPath(source_path).parts
    if len(parts) >= 2:
        return parts[1]
    return parts[0] if parts else ""


def join_values(values: list[str] | set[str]) -> str:
    return "|".join(sorted({value for value in values if value}, key=str.casefold))


def load_overrides(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=OVERRIDE_FIELDS)
            writer.writeheader()
        return {}

    overrides: dict[str, dict[str, str]] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [field for field in OVERRIDE_FIELDS if field not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(f"Kolom manual-overrides.csv hilang: {', '.join(missing)}")
        for line_number, row in enumerate(reader, 2):
            document_id = (row.get("document_id") or "").strip()
            if not document_id:
                continue
            if document_id in overrides:
                raise SystemExit(f"Override document_id duplikat pada baris {line_number}: {document_id}")
            overrides[document_id] = {field: (row.get(field) or "").strip() for field in OVERRIDE_FIELDS}
    return overrides


def validate_overrides(overrides: dict[str, dict[str, str]], known_ids: set[str]) -> None:
    unknown = sorted(set(overrides) - known_ids)
    if unknown:
        raise SystemExit("Override merujuk document_id yang tidak dikenal: " + ", ".join(unknown))

    codes: dict[str, str] = {}
    for document_id, override in overrides.items():
        code = override.get("canonical_code", "").casefold()
        if not code:
            continue
        if code in codes:
            raise SystemExit(
                f"canonical_code digunakan lebih dari sekali: {override['canonical_code']} "
                f"({codes[code]} dan {document_id})"
            )
        codes[code] = document_id


def markdown_cell(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a facts-only document inventory grouped by domain.")
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--target", type=Path, default=Path("reconciliation/inventory"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repository = args.repo.resolve()
    target = (repository / args.target).resolve() if not args.target.is_absolute() else args.target.resolve()
    try:
        target.relative_to(repository)
    except ValueError as exc:
        raise SystemExit("Target inventaris harus berada di dalam repository") from exc

    blocked_roots = [
        repository / "source/original",
        repository / "documents",
        repository / "catalog",
        repository / "indexes",
        repository / "processes",
        repository / "graph",
        repository / "graphify-out",
        repository / "docs",
    ]
    for blocked in blocked_roots:
        try:
            target.relative_to(blocked.resolve())
        except ValueError:
            continue
        raise SystemExit(f"Target inventaris tidak boleh berada di area sumber/generated: {blocked}")

    target.mkdir(parents=True, exist_ok=True)
    overrides = load_overrides(target / "manual-overrides.csv")

    document_data = read_json(repository / "catalog/document-index.json")
    catalog_data = read_json(repository / "catalog/source-domain-feature-index.json")
    process_data = read_json(repository / "catalog/process-index.json")
    correlation_data = read_json(repository / "catalog/correlation-index.json")
    documents = document_data.get("documents", [])
    known_ids = {document["document_id"] for document in documents}
    validate_overrides(overrides, known_ids)

    catalog_by_document = {
        entry["document_id"]: entry
        for entry in catalog_data.get("entries", [])
        if entry.get("document_id")
    }

    processes_by_document: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for process in process_data.get("paths", []):
        for step in process.get("steps", []):
            if step.get("document_id"):
                processes_by_document[step["document_id"]].append(
                    {
                        "id": process.get("id", ""),
                        "category": process.get("category", ""),
                        "role": step.get("role", ""),
                        "position": str(step.get("position", "")),
                    }
                )
        if process.get("source_flow_document_id"):
            processes_by_document[process["source_flow_document_id"]].append(
                {
                    "id": process.get("id", ""),
                    "category": process.get("category", ""),
                    "role": "source-flow",
                    "position": "",
                }
            )

    mermaid_by_document: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for flow in process_data.get("mermaid_flows", []):
        if flow.get("document_id"):
            mermaid_by_document[flow["document_id"]].append(
                {"id": flow.get("id", ""), "kind": flow.get("flow_kind", "")}
            )

    exact_counts = Counter(document["sha256"] for document in documents)
    normalized_counts = Counter(
        document["normalized_text_sha256"]
        for document in documents
        if not document.get("extracted_text_empty")
    )
    mechanical_counts = Counter(document["mechanical_filename_key"] for document in documents)

    relation_types: defaultdict[str, set[str]] = defaultdict(set)
    counterparts: defaultdict[str, set[str]] = defaultdict(set)
    for relation in correlation_data.get("relations", []):
        left = relation.get("from", "")
        right = relation.get("to", "")
        relation_type = relation.get("type", "")
        if left.startswith("DOC-"):
            relation_types[left].add(relation_type)
        if right.startswith("DOC-"):
            relation_types[right].add(relation_type)
        if relation_type == "generator-tree-counterpart" and left.startswith("DOC-") and right.startswith("DOC-"):
            counterparts[left].add(right)
            counterparts[right].add(left)

    rows: list[dict[str, Any]] = []
    for document in documents:
        document_id = document["document_id"]
        catalog_entry = catalog_by_document.get(document_id, {})
        path_domain, path_basis = source_domain(document["source_path"])
        if catalog_entry.get("category"):
            derived_domain = normalize_domain(catalog_entry["category"])
            domain_basis = "explicit-prd-catalog"
        else:
            derived_domain = path_domain
            domain_basis = path_basis

        override = overrides.get(document_id, {})
        manual_domain = override.get("manual_domain", "")
        inventory_domain = normalize_domain(manual_domain) if manual_domain else derived_domain
        process_items = processes_by_document.get(document_id, [])
        mermaid_items = mermaid_by_document.get(document_id, [])
        role_values = [
            f"{item['id']}:{item['position']}:{item['role']}".strip(":")
            for item in process_items
        ]
        normalized_group_size = 0
        if not document.get("extracted_text_empty"):
            normalized_group_size = normalized_counts[document["normalized_text_sha256"]]

        rows.append(
            {
                "inventory_domain": inventory_domain,
                "derived_domain": derived_domain,
                "domain_basis": domain_basis,
                "manual_domain": manual_domain,
                "manual_domain_confirmed": "YES" if manual_domain else "NO",
                "review_status": override.get("review_status") or "UNREVIEWED",
                "include_in_reconciliation": override.get("include_in_reconciliation", ""),
                "canonical_code": override.get("canonical_code", ""),
                "canonical_title": override.get("canonical_title", ""),
                "owner": override.get("owner", ""),
                "document_id": document_id,
                "content_id": document["content_id"],
                "title": document["title"],
                "source_path": document["source_path"],
                "source_directory": document["source_directory"],
                "source_tree": source_tree(document["source_path"]),
                "extension": document["extension"],
                "bytes": document["bytes"],
                "sha256": document["sha256"],
                "catalog_id": catalog_entry.get("id", ""),
                "catalog_name": catalog_entry.get("name", ""),
                "catalog_category": catalog_entry.get("category", ""),
                "process_ids": join_values([item["id"] for item in process_items]),
                "process_categories": join_values([item["category"] for item in process_items]),
                "process_roles": join_values(role_values),
                "mermaid_flow_ids": join_values([item["id"] for item in mermaid_items]),
                "mermaid_flow_kinds": join_values([item["kind"] for item in mermaid_items]),
                "exact_content_group_size": exact_counts[document["sha256"]],
                "normalized_text_group_size": normalized_group_size,
                "mechanical_filename_group_size": mechanical_counts[document["mechanical_filename_key"]],
                "generator_counterparts": join_values(counterparts.get(document_id, set())),
                "relation_types": join_values(relation_types.get(document_id, set())),
                "filename_markers": join_values(document.get("filename_markers", [])),
                "notes": override.get("notes", ""),
            }
        )

    rows.sort(key=lambda item: (item["inventory_domain"].casefold(), item["source_path"].casefold()))
    by_domain: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_domain[row["inventory_domain"]].append(row)

    summary_rows: list[dict[str, Any]] = []
    for domain, domain_rows in sorted(by_domain.items(), key=lambda item: item[0].casefold()):
        summary_rows.append(
            {
                "domain": domain,
                "source_file_count": len(domain_rows),
                "unique_content_count": len({item["content_id"] for item in domain_rows}),
                "explicit_catalog_count": sum(item["domain_basis"] == "explicit-prd-catalog" for item in domain_rows),
                "source_path_derived_count": sum(item["domain_basis"] == "source-path" for item in domain_rows),
                "manual_domain_count": sum(item["manual_domain_confirmed"] == "YES" for item in domain_rows),
                "process_linked_count": sum(bool(item["process_ids"]) for item in domain_rows),
                "canonical_code_count": sum(bool(item["canonical_code"]) for item in domain_rows),
                "unreviewed_count": sum(item["review_status"] == "UNREVIEWED" for item in domain_rows),
            }
        )

    write_csv(target / "document-register.csv", REGISTER_FIELDS, rows)
    write_csv(
        target / "domain-summary.csv",
        [
            "domain",
            "source_file_count",
            "unique_content_count",
            "explicit_catalog_count",
            "source_path_derived_count",
            "manual_domain_count",
            "process_linked_count",
            "canonical_code_count",
            "unreviewed_count",
        ],
        summary_rows,
    )

    json_value = {
        "schema_version": 1,
        "policy": {
            "source_original": "read-only-evidence",
            "domain_classification": "explicit-catalog-or-mechanical-source-path",
            "manual_values": "manual-overrides.csv",
            "canonical_codes": "not-assigned-automatically",
        },
        "document_count": len(rows),
        "domain_count": len(summary_rows),
        "documents": rows,
    }
    (target / "document-register.json").write_text(
        json.dumps(json_value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    by_domain_lines = ["# Inventaris Dokumen per Grup Sumber", "", "> Grup pada file ini bukan domain proses end-to-end.", ""]
    for domain, domain_rows in sorted(by_domain.items(), key=lambda item: item[0].casefold()):
        by_domain_lines.extend(
            [
                f"## Grup Sumber: {domain}",
                "",
                f"- File sumber: `{len(domain_rows)}`",
                f"- Konten unik: `{len({item['content_id'] for item in domain_rows})}`",
                f"- Terhubung ke proses eksplisit: `{sum(bool(item['process_ids']) for item in domain_rows)}`",
                f"- Domain dikonfirmasi manual: `{sum(item['manual_domain_confirmed'] == 'YES' for item in domain_rows)}`",
                "",
                "| Document ID | Judul | Sumber | Format | Katalog | Proses | Salinan identik | Status | Kode canonical |",
                "|---|---|---|---|---|---|---:|---|---|",
            ]
        )
        for item in domain_rows:
            card = f"../../documents/{item['document_id']}/index.md"
            title = markdown_cell(item["canonical_title"] or item["title"])
            catalog_label = item["catalog_id"] or "-"
            process_label = item["process_ids"] or "-"
            by_domain_lines.append(
                f"| [{item['document_id']}](<{card}>) | {title} | `{markdown_cell(item['source_path'])}` | "
                f"`{item['extension']}` | `{markdown_cell(catalog_label)}` | `{markdown_cell(process_label)}` | "
                f"{item['exact_content_group_size']} | `{item['review_status']}` | "
                f"`{markdown_cell(item['canonical_code'] or '-')}` |"
            )
        by_domain_lines.append("")
    (target / "by-domain.md").write_text("\n".join(by_domain_lines).rstrip() + "\n", encoding="utf-8")

    source_path_count = sum(row["domain_basis"] == "source-path" for row in rows)
    catalog_count = sum(row["domain_basis"] == "explicit-prd-catalog" for row in rows)
    readme = f"""# Inventaris Dokumen berdasarkan Grup Sumber

Inventaris ini adalah lapisan kerja turunan. `source/original/` tetap menjadi bukti read-only dan tidak diubah.

> Nilai `inventory_domain` pada register ini adalah grup sumber awal, bukan domain proses end-to-end. Domain E2E dikelola terpisah di `reconciliation/e2e-inventory/`.

## Ringkasan

- File sumber: `{len(rows)}`
- Konten biner unik: `{len({row['content_id'] for row in rows})}`
- Grup sumber awal: `{len(summary_rows)}`
- Domain dari `prd-catalog.json`: `{catalog_count}` dokumen
- Domain dari path sumber mekanis: `{source_path_count}` dokumen
- Domain yang sudah dikonfirmasi manual: `{sum(row['manual_domain_confirmed'] == 'YES' for row in rows)}` dokumen
- Kode canonical yang sudah ditetapkan manual: `{sum(bool(row['canonical_code']) for row in rows)}` dokumen

## Aturan Klasifikasi

1. Kategori `prd-catalog.json` digunakan sebagai grup sumber bila dokumen mempunyai entri katalog eksplisit.
2. Dokumen lain dikelompokkan dari path sumber tanpa inferensi semantik.
3. Semua file sumber tetap dicatat walaupun isi binernya identik.
4. `DOC-*` adalah identitas inventaris sumber; kode canonical tidak dibuat otomatis.
5. Keanggotaan proses hanya berasal dari `prd-paths-v2.json` dan dokumen Mermaid sumber.

## Berkas

- `document-register.csv`: register utama yang dapat difilter dan dianalisis.
- `document-register.json`: bentuk machine-readable dari register yang sama.
- `domain-summary.csv`: jumlah file, konten unik, dan status per domain.
- `by-domain.md`: tampilan manusia per domain.
- `manual-overrides.csv`: satu-satunya file yang diedit manual untuk domain, kode, owner, status, dan catatan.
- `inventory-manifest.json`: sumber input dan statistik build inventaris.

## Alur Review Manual

1. Cari `document_id` pada `document-register.csv` atau `by-domain.md`.
2. Tambahkan satu baris pada `manual-overrides.csv`.
3. Isi `manual_domain` untuk mengonfirmasi atau memindahkan domain.
4. Biarkan `canonical_code` kosong sampai scope dokumen sudah disepakati.
5. Jalankan ulang generator; nilai manual akan digabungkan tanpa mengubah dokumen sumber.

Nilai yang disarankan untuk `review_status`: `UNREVIEWED`, `IN_REVIEW`, `DOMAIN_CONFIRMED`, `DUPLICATE_CANDIDATE`, `EXCLUDED`, atau `READY_FOR_RECONCILIATION`.
"""
    (target / "README.md").write_text(readme, encoding="utf-8")

    manifest = {
        "schema_version": 1,
        "inputs": [
            "catalog/document-index.json",
            "catalog/source-domain-feature-index.json",
            "catalog/process-index.json",
            "catalog/correlation-index.json",
            "reconciliation/inventory/manual-overrides.csv",
        ],
        "outputs": [
            "reconciliation/inventory/README.md",
            "reconciliation/inventory/domain-summary.csv",
            "reconciliation/inventory/document-register.csv",
            "reconciliation/inventory/document-register.json",
            "reconciliation/inventory/by-domain.md",
        ],
        "source_document_count": len(rows),
        "unique_content_count": len({row["content_id"] for row in rows}),
        "domain_count": len(summary_rows),
        "manual_override_count": len(overrides),
    }
    (target / "inventory-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": "BUILT", **manifest}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
