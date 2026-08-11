#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import html
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any


PROCESS_FIELDS = [
    "process_code",
    "title",
    "category",
    "scenario",
    "start_event",
    "end_event",
    "owner",
    "status",
    "origin",
    "source_process_id",
    "source_flow",
    "source_flow_document_id",
    "stage_count",
    "membership_count",
    "notes",
]

STAGE_FIELDS = [
    "process_code",
    "stage_order",
    "stage_code",
    "stage_title",
    "entry_condition",
    "output",
    "stage_status",
    "source_prd_id",
    "source_role",
    "origin",
    "notes",
]

MEMBERSHIP_FIELDS = [
    "process_code",
    "stage_code",
    "document_id",
    "document_title",
    "source_path",
    "source_group",
    "catalog_id",
    "membership_role",
    "membership_status",
    "basis",
    "notes",
]

FLOW_FIELDS = [
    "flow_id",
    "flow_class",
    "e2e_code",
    "title",
    "macro_group",
    "source_path",
    "document_id",
    "node_count",
    "edge_count",
    "canonical_flow_id",
    "explicit_process_ids",
]

E2E_DOMAIN_FIELDS = [
    "e2e_code",
    "title",
    "macro_group",
    "status",
    "origin",
    "flow_id",
    "flow_document_id",
    "source_path",
    "node_count",
    "edge_count",
    "explicit_process_ids",
    "explicit_membership_count",
    "manual_stage_count",
    "manual_candidate_membership_count",
    "candidate_match_count",
    "notes",
]

GROUP_PREFIXES = {
    "admisi-emr": "ADM",
    "backoffice": "BO",
    "governance": "GOV",
    "integrasi": "INT",
    "pelayanan-pendukung": "PP",
    "pelayanan-utama": "PU",
}

INVENTORY_FLOW_CODES = {
    "flowchart-inventory-distribusi-barang": ("E2E-INV-01", "Distribusi Barang"),
    "flowchart-inventory-informasi-stok (1)": ("E2E-INV-02", "Informasi Stok"),
    "flowchart-inventory-penerimaan-barang": ("E2E-INV-03", "Penerimaan Barang"),
    "flowchart-inventory-retur-pembelian": ("E2E-INV-04", "Retur Pembelian"),
    "flowchart-inventory-stok-opname": ("E2E-INV-05", "Stok Opname"),
}

TOKEN_STOPWORDS = {
    "a",
    "and",
    "atau",
    "buka",
    "buat",
    "cek",
    "dan",
    "data",
    "dari",
    "di",
    "dokumen",
    "form",
    "input",
    "ke",
    "klik",
    "management",
    "manajemen",
    "menu",
    "neurovi",
    "of",
    "pasien",
    "pengelolaan",
    "prd",
    "process",
    "product",
    "proses",
    "requirement",
    "review",
    "simpan",
    "status",
    "the",
    "untuk",
    "v1",
    "v2",
    "ya",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path, required_fields: list[str]) -> list[dict[str, str]]:
    if not path.is_file():
        raise SystemExit(f"Input manual tidak ditemukan: {path}")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [field for field in required_fields if field not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(f"Kolom hilang pada {path}: {', '.join(missing)}")
        return [
            {field: (row.get(field) or "").strip() for field in required_fields}
            for row in reader
            if any((row.get(field) or "").strip() for field in required_fields)
        ]


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def markdown_cell(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")


def parse_order(value: str, context: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise SystemExit(f"stage_order tidak valid pada {context}: {value}") from exc


def mechanical_title(value: str) -> str:
    cleaned = re.sub(r"^\d+[-_ ]*", "", value)
    cleaned = re.sub(r"[-_]+", " ", cleaned).strip().title()
    for source, target in {
        "Bpjs": "BPJS",
        "Bhp": "BHP",
        "Cpo": "CPO",
        "Dpjp": "DPJP",
        "Emr": "EMR",
        "Igd": "IGD",
        "Mcu": "MCU",
        "Ppi": "PPI",
    }.items():
        cleaned = cleaned.replace(source, target)
    return cleaned


def e2e_code_for_flow(source_path: str) -> tuple[str, str, str] | None:
    grouped = re.search(r"/menu-flow/entities-grouped/([^/]+)/([^/]+)\.mmd$", source_path)
    if grouped:
        macro_group = grouped.group(1)
        filename = grouped.group(2)
        number = re.match(r"(\d+)", filename)
        prefix = GROUP_PREFIXES.get(macro_group)
        if not number or not prefix:
            return None
        return f"E2E-{prefix}-{int(number.group(1)):02d}", mechanical_title(filename), macro_group

    inventory = re.search(r"/inventory \(\.md\)/flowchart inventory/([^/]+)\.mmd$", source_path)
    if inventory and "PRD Generator (.md) - Copy/" in source_path:
        code_title = INVENTORY_FLOW_CODES.get(inventory.group(1))
        if code_title:
            return code_title[0], code_title[1], "inventory-detail"
    return None


def flow_class(source_path: str) -> str:
    if "/menu-flow/entities-grouped/" in source_path:
        return "E2E_CANDIDATE"
    if "/inventory (.md)/flowchart inventory/" in source_path:
        if "PRD Generator (.md) - Copy/" in source_path:
            return "E2E_CANDIDATE"
        return "DUPLICATE_FLOW"
    if "/menu-flow/entities/" in source_path:
        return "REFERENCE_MAP"
    if source_path.endswith("/menu-flow/overall-menu-flow.mmd"):
        return "REFERENCE_MAP"
    if source_path.endswith("/menu-flow/business-process-flows.mmd"):
        return "REFERENCE_MAP"
    return "REFERENCE_MAP"


def parse_node_declarations(line: str) -> list[dict[str, Any]]:
    openers = [
        ("([", "])", "terminal"),
        ("[(", ")]", "database"),
        ("[[", "]]", "subroutine"),
        ("{{", "}}", "hexagon"),
        ("[", "]", "process"),
        ("(", ")", "rounded"),
        ("{", "}", "decision"),
    ]
    declarations: list[dict[str, Any]] = []
    for match in re.finditer(r"\b([A-Za-z][A-Za-z0-9_]*)\s*", line):
        node_id = match.group(1)
        start = match.end()
        for opener, closer, shape in openers:
            if not line.startswith(opener, start):
                continue
            label_start = start + len(opener)
            label_end = line.find(closer, label_start)
            if label_end < 0:
                continue
            label = html.unescape(line[label_start:label_end])
            label = re.sub(r"<br\s*/?>", " ", label, flags=re.I)
            label = re.sub(r"\s+", " ", label).strip()
            declarations.append(
                {
                    "node_id": node_id,
                    "label": label or node_id,
                    "shape": shape,
                    "start": match.start(),
                    "end": label_end + len(closer),
                }
            )
            break
    return declarations


def parse_mermaid(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []

    def ensure_node(node_id: str, line_number: int) -> None:
        if node_id not in nodes:
            nodes[node_id] = {
                "node_id": node_id,
                "node_label": node_id,
                "node_shape": "reference",
                "node_order": len(nodes) + 1,
                "first_line": line_number,
            }

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8-sig", errors="replace").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("%%"):
            continue
        declarations = parse_node_declarations(line)
        for declaration in declarations:
            ensure_node(declaration["node_id"], line_number)
            nodes[declaration["node_id"]].update(
                {
                    "node_label": declaration["label"],
                    "node_shape": declaration["shape"],
                }
            )
        arrows = list(re.finditer(r"-->|==>|\.->", line))
        if not arrows:
            continue
        source_match = re.match(r"([A-Za-z][A-Za-z0-9_]*)", line)
        if not source_match:
            continue
        source_id = source_match.group(1)
        arrow = arrows[-1]
        target_text = line[arrow.end() :]
        target_match = re.match(r"\s*(?:\|[^|]*\|\s*)?([A-Za-z][A-Za-z0-9_]*)", target_text)
        if not target_match:
            continue
        target_id = target_match.group(1)
        ensure_node(source_id, line_number)
        ensure_node(target_id, line_number)
        edge_label = ""
        pipe_label = re.search(r"-->\|([^|]+)\|", line)
        text_label = re.search(r"--\s+(.+?)\s+-->", line)
        dotted_label = re.search(r"-\.\s*(.+?)\s*\.->", line)
        if pipe_label:
            edge_label = pipe_label.group(1).strip()
        elif text_label:
            edge_label = text_label.group(1).strip().strip('"')
        elif dotted_label:
            edge_label = dotted_label.group(1).strip().strip('"')
        edges.append(
            {
                "edge_order": len(edges) + 1,
                "from_node": source_id,
                "to_node": target_id,
                "edge_label": edge_label,
                "source_line_number": line_number,
                "source_line": raw_line.strip(),
            }
        )
    return sorted(nodes.values(), key=lambda item: item["node_order"]), edges


def tokenize(value: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").casefold()
    tokens = set(re.findall(r"[a-z0-9]+", ascii_value))
    return {
        token
        for token in tokens
        if len(token) >= 3 and token not in TOKEN_STOPWORDS and not re.fullmatch(r"v?\d+(?:\d+)?", token)
    }


def artifact_type(document: dict[str, Any]) -> str:
    source_path = document.get("source_path", "").casefold()
    extension = document.get("extension", "").casefold()
    if extension == ".mmd":
        return "PROCESS_FLOW"
    if extension == ".html" or "preview" in source_path or "wireframe" in source_path:
        return "UI_PREVIEW"
    if extension in {".csv", ".xlsx"} or "data referensi" in source_path:
        return "DATA_REFERENCE"
    if extension == ".json":
        return "CATALOG_OR_CONFIG"
    if extension == ".ps1" or "/tools/" in source_path or "/.vscode/" in source_path:
        return "TOOLING"
    return "REQUIREMENT_DOCUMENT"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a controlled end-to-end process inventory.")
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--target", type=Path, default=Path("reconciliation/e2e-inventory"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repository = args.repo.resolve()
    target = (repository / args.target).resolve() if not args.target.is_absolute() else args.target.resolve()
    try:
        target.relative_to(repository)
    except ValueError as exc:
        raise SystemExit("Target inventaris E2E harus berada di dalam repository") from exc

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
        raise SystemExit(f"Target inventaris E2E tidak boleh berada di area sumber/generated: {blocked}")

    target.mkdir(parents=True, exist_ok=True)
    manual_processes = read_csv(
        target / "manual-processes.csv",
        ["process_code", "title", "start_event", "end_event", "owner", "status", "source_basis", "notes"],
    )
    manual_stages = read_csv(
        target / "manual-stages.csv",
        [
            "process_code",
            "stage_order",
            "stage_code",
            "stage_title",
            "entry_condition",
            "output",
            "stage_status",
            "notes",
        ],
    )
    manual_memberships = read_csv(
        target / "manual-memberships.csv",
        [
            "process_code",
            "stage_code",
            "document_id",
            "membership_role",
            "membership_status",
            "basis",
            "notes",
        ],
    )

    document_data = read_json(repository / "catalog/document-index.json")
    process_data = read_json(repository / "catalog/process-index.json")
    catalog_data = read_json(repository / "catalog/source-domain-feature-index.json")
    correlation_data = read_json(repository / "catalog/correlation-index.json")
    source_inventory = read_json(repository / "reconciliation/inventory/document-register.json")

    documents = {document["document_id"]: document for document in document_data.get("documents", [])}
    source_rows = {row["document_id"]: row for row in source_inventory.get("documents", [])}
    catalog_by_document = {
        entry["document_id"]: entry
        for entry in catalog_data.get("entries", [])
        if entry.get("document_id")
    }

    explicit_processes_by_flow: defaultdict[str, list[str]] = defaultdict(list)
    for source_process in process_data.get("paths", []):
        if source_process.get("source_flow_source_path"):
            explicit_processes_by_flow[source_process["source_flow_source_path"]].append(source_process["id"])

    flow_rows: list[dict[str, Any]] = []
    flow_nodes: list[dict[str, Any]] = []
    flow_edges: list[dict[str, Any]] = []
    flow_structures: dict[str, dict[str, Any]] = {}
    copy_inventory_flow_by_sha: dict[str, str] = {}

    for flow in process_data.get("mermaid_flows", []):
        source_path = flow["source_path"]
        classification = flow_class(source_path)
        code_data = e2e_code_for_flow(source_path)
        e2e_code = code_data[0] if code_data else ""
        title = code_data[1] if code_data else mechanical_title(Path(source_path).stem)
        macro_group = code_data[2] if code_data else ""
        source_file = repository / "source/original" / source_path
        nodes, edges = parse_mermaid(source_file)
        flow_structures[flow["id"]] = {"nodes": nodes, "edges": edges}
        document = documents.get(flow.get("document_id", ""), {})
        if classification == "E2E_CANDIDATE" and "/inventory (.md)/flowchart inventory/" in source_path:
            copy_inventory_flow_by_sha[document.get("sha256", "")] = flow["id"]
        flow_rows.append(
            {
                "flow_id": flow["id"],
                "flow_class": classification,
                "e2e_code": e2e_code,
                "title": title,
                "macro_group": macro_group,
                "source_path": source_path,
                "document_id": flow.get("document_id", ""),
                "node_count": len(nodes),
                "edge_count": len(edges),
                "canonical_flow_id": "",
                "explicit_process_ids": "|".join(sorted(explicit_processes_by_flow.get(source_path, []))),
            }
        )

    for flow_row in flow_rows:
        if flow_row["flow_class"] != "DUPLICATE_FLOW":
            continue
        document = documents.get(flow_row["document_id"], {})
        flow_row["canonical_flow_id"] = copy_inventory_flow_by_sha.get(document.get("sha256", ""), "")

    for flow_row in flow_rows:
        structure = flow_structures[flow_row["flow_id"]]
        for node in structure["nodes"]:
            flow_nodes.append(
                {
                    "flow_id": flow_row["flow_id"],
                    "e2e_code": flow_row["e2e_code"],
                    "flow_class": flow_row["flow_class"],
                    **node,
                }
            )
        for edge in structure["edges"]:
            flow_edges.append(
                {
                    "flow_id": flow_row["flow_id"],
                    "e2e_code": flow_row["e2e_code"],
                    "flow_class": flow_row["flow_class"],
                    **edge,
                }
            )

    processes: dict[str, dict[str, Any]] = {}
    stages: dict[tuple[str, str], dict[str, Any]] = {}
    memberships: dict[tuple[str, str, str], dict[str, Any]] = {}

    for source_process in process_data.get("paths", []):
        process_code = source_process["id"]
        if process_code in processes:
            raise SystemExit(f"Process code sumber duplikat: {process_code}")
        processes[process_code] = {
            "process_code": process_code,
            "title": source_process.get("name", process_code),
            "category": source_process.get("category", ""),
            "scenario": source_process.get("scenario", ""),
            "start_event": "",
            "end_event": "",
            "owner": "",
            "status": "SOURCE_EXPLICIT",
            "origin": "prd-paths-v2.json",
            "source_process_id": process_code,
            "source_flow": source_process.get("source_flow", ""),
            "source_flow_document_id": source_process.get("source_flow_document_id", ""),
            "notes": "",
        }
        for step in source_process.get("steps", []):
            position = int(step.get("position", 0))
            stage_code = f"S{position:02d}"
            stage_key = (process_code, stage_code)
            if stage_key in stages:
                raise SystemExit(f"Tahap sumber duplikat: {process_code}/{stage_code}")
            stages[stage_key] = {
                "process_code": process_code,
                "stage_order": position * 10,
                "stage_code": stage_code,
                "stage_title": step.get("catalog_name") or step.get("prd_id") or stage_code,
                "entry_condition": "",
                "output": "",
                "stage_status": "SOURCE_EXPLICIT",
                "source_prd_id": step.get("prd_id", ""),
                "source_role": step.get("role", ""),
                "origin": "prd-paths-v2.json",
                "notes": step.get("note", ""),
            }
            if step.get("document_id"):
                membership_key = (process_code, stage_code, step["document_id"])
                memberships[membership_key] = {
                    "process_code": process_code,
                    "stage_code": stage_code,
                    "document_id": step["document_id"],
                    "membership_role": (step.get("role") or "UNSPECIFIED").upper(),
                    "membership_status": "SOURCE_EXPLICIT",
                    "basis": "prd-paths-v2.json",
                    "notes": step.get("note", ""),
                }

    for row_number, item in enumerate(manual_processes, 2):
        process_code = item["process_code"]
        if not process_code:
            raise SystemExit(f"manual-processes.csv baris {row_number}: process_code wajib")
        if process_code in processes:
            raise SystemExit(f"manual-processes.csv tidak boleh menimpa proses sumber: {process_code}")
        processes[process_code] = {
            "process_code": process_code,
            "title": item["title"],
            "category": "",
            "scenario": "",
            "start_event": item["start_event"],
            "end_event": item["end_event"],
            "owner": item["owner"],
            "status": item["status"] or "DRAFT",
            "origin": item["source_basis"] or "manual",
            "source_process_id": "",
            "source_flow": "",
            "source_flow_document_id": "",
            "notes": item["notes"],
        }

    for row_number, item in enumerate(manual_stages, 2):
        process_code = item["process_code"]
        stage_code = item["stage_code"]
        if process_code not in processes:
            raise SystemExit(f"manual-stages.csv baris {row_number}: proses tidak dikenal {process_code}")
        stage_key = (process_code, stage_code)
        if stage_key in stages:
            raise SystemExit(f"manual-stages.csv tidak boleh menimpa tahap sumber: {process_code}/{stage_code}")
        stages[stage_key] = {
            "process_code": process_code,
            "stage_order": parse_order(item["stage_order"], f"manual-stages.csv baris {row_number}"),
            "stage_code": stage_code,
            "stage_title": item["stage_title"],
            "entry_condition": item["entry_condition"],
            "output": item["output"],
            "stage_status": item["stage_status"] or "DRAFT",
            "source_prd_id": "",
            "source_role": "",
            "origin": "manual",
            "notes": item["notes"],
        }

    manual_membership_keys: set[tuple[str, str, str]] = set()
    for row_number, item in enumerate(manual_memberships, 2):
        process_code = item["process_code"]
        stage_code = item["stage_code"]
        document_id = item["document_id"]
        if (process_code, stage_code) not in stages:
            raise SystemExit(
                f"manual-memberships.csv baris {row_number}: tahap tidak dikenal {process_code}/{stage_code}"
            )
        if document_id not in documents:
            raise SystemExit(f"manual-memberships.csv baris {row_number}: document_id tidak dikenal {document_id}")
        membership_key = (process_code, stage_code, document_id)
        if membership_key in memberships:
            raise SystemExit(
                f"manual-memberships.csv tidak boleh menimpa membership sumber: {process_code}/{stage_code}/{document_id}"
            )
        memberships[membership_key] = {
            "process_code": process_code,
            "stage_code": stage_code,
            "document_id": document_id,
            "membership_role": item["membership_role"] or "UNCONFIRMED",
            "membership_status": item["membership_status"] or "CANDIDATE",
            "basis": item["basis"] or "manual",
            "notes": item["notes"],
        }
        manual_membership_keys.add(membership_key)

    memberships_by_stage: defaultdict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    membership_rows: list[dict[str, Any]] = []
    for membership in memberships.values():
        document = documents[membership["document_id"]]
        source_row = source_rows.get(membership["document_id"], {})
        catalog_entry = catalog_by_document.get(membership["document_id"], {})
        row = {
            **membership,
            "document_title": document.get("title", ""),
            "source_path": document.get("source_path", ""),
            "source_group": source_row.get("inventory_domain", ""),
            "catalog_id": catalog_entry.get("id", ""),
        }
        membership_rows.append(row)
        memberships_by_stage[(membership["process_code"], membership["stage_code"])].append(row)

    membership_rows.sort(key=lambda item: (item["process_code"], item["stage_code"], item["source_path"]))
    stage_rows = sorted(stages.values(), key=lambda item: (item["process_code"], item["stage_order"], item["stage_code"]))

    stage_count_by_process: defaultdict[str, int] = defaultdict(int)
    membership_count_by_process: defaultdict[str, int] = defaultdict(int)
    for stage in stage_rows:
        stage_count_by_process[stage["process_code"]] += 1
    for membership in membership_rows:
        membership_count_by_process[membership["process_code"]] += 1

    process_rows: list[dict[str, Any]] = []
    for process in sorted(processes.values(), key=lambda item: item["process_code"]):
        process_rows.append(
            {
                **process,
                "stage_count": stage_count_by_process[process["process_code"]],
                "membership_count": membership_count_by_process[process["process_code"]],
            }
        )

    exact_groups: defaultdict[str, set[str]] = defaultdict(set)
    for document in documents.values():
        exact_groups[document["sha256"]].add(document["document_id"])
    counterparts: defaultdict[str, set[str]] = defaultdict(set)
    for relation in correlation_data.get("relations", []):
        if relation.get("type") != "generator-tree-counterpart":
            continue
        left = relation.get("from", "")
        right = relation.get("to", "")
        if left.startswith("DOC-") and right.startswith("DOC-"):
            counterparts[left].add(right)
            counterparts[right].add(left)

    variant_rows: list[dict[str, Any]] = []
    for membership_key in sorted(manual_membership_keys):
        membership = memberships[membership_key]
        selected_id = membership["document_id"]
        selected = documents[selected_id]
        variant_ids = set(exact_groups[selected["sha256"]]) | counterparts.get(selected_id, set()) | {selected_id}
        for variant_id in sorted(variant_ids):
            variant = documents[variant_id]
            bases = []
            if variant_id == selected_id:
                bases.append("selected-candidate")
            if variant["sha256"] == selected["sha256"] and variant_id != selected_id:
                bases.append("same-binary-content")
            if variant_id in counterparts.get(selected_id, set()):
                bases.append("generator-tree-counterpart")
            variant_rows.append(
                {
                    "process_code": membership["process_code"],
                    "stage_code": membership["stage_code"],
                    "selected_document_id": selected_id,
                    "candidate_document_id": variant_id,
                    "candidate_title": variant.get("title", ""),
                    "source_path": variant.get("source_path", ""),
                    "candidate_basis": "|".join(bases),
                    "selected_candidate": "YES" if variant_id == selected_id else "NO",
                }
            )

    document_search: dict[str, dict[str, Any]] = {}
    for document_id, document in documents.items():
        catalog_entry = catalog_by_document.get(document_id, {})
        search_text = " ".join(
            [
                document.get("title", ""),
                document.get("source_path", ""),
                catalog_entry.get("name", ""),
                catalog_entry.get("id", ""),
            ]
        )
        document_search[document_id] = {
            "tokens": tokenize(search_text),
            "artifact_type": artifact_type(document),
        }

    flow_candidate_rows: list[dict[str, Any]] = []
    candidate_count_by_e2e: defaultdict[str, int] = defaultdict(int)
    for flow_row in flow_rows:
        if flow_row["flow_class"] != "E2E_CANDIDATE" or not flow_row["e2e_code"]:
            continue
        queries = [
            {
                "node_id": "__FLOW__",
                "node_label": flow_row["title"],
                "query_type": "flow-title",
            }
        ]
        queries.extend(
            {
                "node_id": node["node_id"],
                "node_label": node["node_label"],
                "query_type": "flow-node",
            }
            for node in flow_structures[flow_row["flow_id"]]["nodes"]
        )
        for query in queries:
            query_tokens = tokenize(query["node_label"])
            if not query_tokens:
                continue
            matches = []
            for document_id, search in document_search.items():
                if search["artifact_type"] in {"PROCESS_FLOW", "TOOLING", "CATALOG_OR_CONFIG"}:
                    continue
                common = query_tokens & search["tokens"]
                if not common:
                    continue
                coverage = len(common) / len(query_tokens)
                candidate_status = "MECHANICAL_CANDIDATE"
                if len(common) >= 2 and coverage >= 0.66:
                    score = 100 if query_tokens <= search["tokens"] else round(50 + coverage * 50)
                else:
                    longest_common = max(len(token) for token in common)
                    if len(query_tokens) == 1 and longest_common >= 5:
                        score = 65
                    elif len(query_tokens) <= 3 and longest_common >= 7:
                        score = 55
                    else:
                        continue
                    candidate_status = "WEAK_MECHANICAL_CANDIDATE"
                document = documents[document_id]
                matches.append(
                    {
                        "e2e_code": flow_row["e2e_code"],
                        "flow_id": flow_row["flow_id"],
                        "query_type": query["query_type"],
                        "node_id": query["node_id"],
                        "node_label": query["node_label"],
                        "candidate_document_id": document_id,
                        "candidate_title": document.get("title", ""),
                        "source_path": document.get("source_path", ""),
                        "artifact_type": search["artifact_type"],
                        "match_score": score,
                        "matched_tokens": "|".join(sorted(common)),
                        "candidate_status": candidate_status,
                    }
                )
            matches.sort(key=lambda item: (-item["match_score"], item["source_path"].casefold()))
            for match in matches[:5]:
                flow_candidate_rows.append(match)
                candidate_count_by_e2e[flow_row["e2e_code"]] += 1

    explicit_memberships_by_process: defaultdict[str, set[str]] = defaultdict(set)
    source_membership_rows_by_process: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for membership in membership_rows:
        if membership["membership_status"] == "SOURCE_EXPLICIT":
            explicit_memberships_by_process[membership["process_code"]].add(membership["document_id"])
            source_membership_rows_by_process[membership["process_code"]].append(membership)

    e2e_domain_rows: list[dict[str, Any]] = []
    explicit_membership_rows_by_e2e: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for flow_row in flow_rows:
        if flow_row["flow_class"] != "E2E_CANDIDATE" or not flow_row["e2e_code"]:
            continue
        explicit_process_ids = [value for value in flow_row["explicit_process_ids"].split("|") if value]
        explicit_document_ids: set[str] = set()
        for process_id in explicit_process_ids:
            explicit_document_ids.update(explicit_memberships_by_process.get(process_id, set()))
            explicit_membership_rows_by_e2e[flow_row["e2e_code"]].extend(
                source_membership_rows_by_process.get(process_id, [])
            )
        e2e_domain_rows.append(
            {
                "e2e_code": flow_row["e2e_code"],
                "title": flow_row["title"],
                "macro_group": flow_row["macro_group"],
                "status": "SOURCE_FLOW_WITH_EXPLICIT_PATH" if explicit_process_ids else "SOURCE_FLOW_CANDIDATE",
                "origin": "mermaid-source",
                "flow_id": flow_row["flow_id"],
                "flow_document_id": flow_row["document_id"],
                "source_path": flow_row["source_path"],
                "node_count": flow_row["node_count"],
                "edge_count": flow_row["edge_count"],
                "explicit_process_ids": flow_row["explicit_process_ids"],
                "explicit_membership_count": len(explicit_document_ids),
                "manual_stage_count": 0,
                "manual_candidate_membership_count": 0,
                "candidate_match_count": candidate_count_by_e2e[flow_row["e2e_code"]],
                "notes": "Flow dan kandidat dokumen berasal dari ekstraksi mekanis; perlu review manual.",
            }
        )

    for process in process_rows:
        if process["origin"] == "prd-paths-v2.json":
            continue
        process_code = process["process_code"]
        e2e_domain_rows.append(
            {
                "e2e_code": process_code,
                "title": process["title"],
                "macro_group": process["owner"],
                "status": process["status"],
                "origin": process["origin"],
                "flow_id": "",
                "flow_document_id": "",
                "source_path": "",
                "node_count": 0,
                "edge_count": 0,
                "explicit_process_ids": "",
                "explicit_membership_count": 0,
                "manual_stage_count": process["stage_count"],
                "manual_candidate_membership_count": process["membership_count"],
                "candidate_match_count": 0,
                "notes": process["notes"],
            }
        )
    e2e_domain_rows.sort(key=lambda item: item["e2e_code"])

    direct_mapped_document_ids = {item["document_id"] for item in membership_rows}
    direct_mapped_document_ids.update(
        process.get("source_flow_document_id", "") for process in process_rows if process.get("source_flow_document_id")
    )
    explicit_processes_by_document: defaultdict[str, set[str]] = defaultdict(set)
    manual_e2e_by_document: defaultdict[str, set[str]] = defaultdict(set)
    for membership in membership_rows:
        if membership["membership_status"] == "SOURCE_EXPLICIT":
            explicit_processes_by_document[membership["document_id"]].add(membership["process_code"])
        else:
            manual_e2e_by_document[membership["document_id"]].add(membership["process_code"])

    mechanical_e2e_by_document: defaultdict[str, set[str]] = defaultdict(set)
    for candidate in flow_candidate_rows:
        mechanical_e2e_by_document[candidate["candidate_document_id"]].add(candidate["e2e_code"])

    source_flow_e2e_by_document: defaultdict[str, set[str]] = defaultdict(set)
    flow_classes_by_document: defaultdict[str, set[str]] = defaultdict(set)
    for flow in flow_rows:
        if not flow["document_id"]:
            continue
        flow_classes_by_document[flow["document_id"]].add(flow["flow_class"])
        if flow["e2e_code"]:
            source_flow_e2e_by_document[flow["document_id"]].add(flow["e2e_code"])

    document_coverage_rows: list[dict[str, Any]] = []
    unmapped_rows = []
    for document_id, document in documents.items():
        source_row = source_rows.get(document_id, {})
        if explicit_processes_by_document.get(document_id):
            coverage_status = "SOURCE_EXPLICIT_MEMBERSHIP"
        elif manual_e2e_by_document.get(document_id):
            coverage_status = "MANUAL_CANDIDATE_MEMBERSHIP"
        elif mechanical_e2e_by_document.get(document_id):
            coverage_status = "MECHANICAL_CANDIDATE"
        elif source_flow_e2e_by_document.get(document_id):
            coverage_status = "E2E_SOURCE_FLOW"
        elif flow_classes_by_document.get(document_id):
            coverage_status = "FLOW_REFERENCE_OR_DUPLICATE"
        else:
            coverage_status = "UNMAPPED_TO_E2E_INVENTORY"
        coverage_row = {
            "document_id": document_id,
            "title": document.get("title", ""),
            "source_path": document.get("source_path", ""),
            "source_group": source_row.get("inventory_domain", ""),
            "artifact_type": artifact_type(document),
            "content_id": document.get("content_id", ""),
            "explicit_process_ids": "|".join(sorted(explicit_processes_by_document.get(document_id, set()))),
            "manual_e2e_codes": "|".join(sorted(manual_e2e_by_document.get(document_id, set()))),
            "mechanical_candidate_e2e_codes": "|".join(
                sorted(mechanical_e2e_by_document.get(document_id, set()))
            ),
            "source_flow_e2e_codes": "|".join(sorted(source_flow_e2e_by_document.get(document_id, set()))),
            "flow_classes": "|".join(sorted(flow_classes_by_document.get(document_id, set()))),
            "coverage_status": coverage_status,
        }
        document_coverage_rows.append(coverage_row)
        if coverage_status == "UNMAPPED_TO_E2E_INVENTORY":
            unmapped_rows.append(
                {
                    "document_id": document_id,
                    "title": document.get("title", ""),
                    "source_path": document.get("source_path", ""),
                    "source_group": source_row.get("inventory_domain", ""),
                    "extension": document.get("extension", ""),
                    "content_id": document.get("content_id", ""),
                    "exact_content_group_size": source_row.get("exact_content_group_size", ""),
                    "mapping_status": coverage_status,
                }
            )
    document_coverage_rows.sort(key=lambda item: (item["coverage_status"], item["source_path"].casefold()))
    unmapped_rows.sort(key=lambda item: (item["source_group"].casefold(), item["source_path"].casefold()))
    candidate_document_ids = set(mechanical_e2e_by_document)
    covered_document_ids = {
        row["document_id"]
        for row in document_coverage_rows
        if row["coverage_status"] != "UNMAPPED_TO_E2E_INVENTORY"
    }
    coverage_status_counts: defaultdict[str, int] = defaultdict(int)
    for row in document_coverage_rows:
        coverage_status_counts[row["coverage_status"]] += 1

    write_csv(target / "process-register.csv", PROCESS_FIELDS, process_rows)
    write_csv(target / "stage-register.csv", STAGE_FIELDS, stage_rows)
    write_csv(target / "membership-register.csv", MEMBERSHIP_FIELDS, membership_rows)
    write_csv(
        target / "candidate-variants.csv",
        [
            "process_code",
            "stage_code",
            "selected_document_id",
            "candidate_document_id",
            "candidate_title",
            "source_path",
            "candidate_basis",
            "selected_candidate",
        ],
        variant_rows,
    )
    write_csv(
        target / "unmapped-documents.csv",
        [
            "document_id",
            "title",
            "source_path",
            "source_group",
            "extension",
            "content_id",
            "exact_content_group_size",
            "mapping_status",
        ],
        unmapped_rows,
    )
    write_csv(
        target / "document-e2e-coverage.csv",
        [
            "document_id",
            "title",
            "source_path",
            "source_group",
            "artifact_type",
            "content_id",
            "explicit_process_ids",
            "manual_e2e_codes",
            "mechanical_candidate_e2e_codes",
            "source_flow_e2e_codes",
            "flow_classes",
            "coverage_status",
        ],
        document_coverage_rows,
    )
    write_csv(target / "flow-register.csv", FLOW_FIELDS, sorted(flow_rows, key=lambda item: item["source_path"]))
    write_csv(target / "e2e-domain-register.csv", E2E_DOMAIN_FIELDS, e2e_domain_rows)
    write_csv(
        target / "flow-node-register.csv",
        [
            "flow_id",
            "e2e_code",
            "flow_class",
            "node_order",
            "node_id",
            "node_label",
            "node_shape",
            "first_line",
        ],
        sorted(flow_nodes, key=lambda item: (item["flow_id"], item["node_order"])),
    )
    write_csv(
        target / "flow-edge-register.csv",
        [
            "flow_id",
            "e2e_code",
            "flow_class",
            "edge_order",
            "from_node",
            "to_node",
            "edge_label",
            "source_line_number",
            "source_line",
        ],
        sorted(flow_edges, key=lambda item: (item["flow_id"], item["edge_order"])),
    )
    write_csv(
        target / "flow-document-candidates.csv",
        [
            "e2e_code",
            "flow_id",
            "query_type",
            "node_id",
            "node_label",
            "candidate_document_id",
            "candidate_title",
            "source_path",
            "artifact_type",
            "match_score",
            "matched_tokens",
            "candidate_status",
        ],
        sorted(
            flow_candidate_rows,
            key=lambda item: (item["e2e_code"], item["node_id"], -item["match_score"], item["source_path"]),
        ),
    )

    nested_processes = []
    for process in process_rows:
        process_stages = []
        for stage in [item for item in stage_rows if item["process_code"] == process["process_code"]]:
            process_stages.append(
                {
                    **stage,
                    "memberships": memberships_by_stage.get((process["process_code"], stage["stage_code"]), []),
                }
            )
        nested_processes.append({**process, "stages": process_stages})
    inventory_json = {
        "schema_version": 1,
        "policy": {
            "source_processes": "preserved-from-prd-paths-v2",
            "manual_processes": "user-controlled-csv-explicit-approval-only",
            "manual_memberships": "candidate-until-user-confirmed",
            "document_relationship": "many-to-many",
        },
        "process_count": len(process_rows),
        "stage_count": len(stage_rows),
        "membership_count": len(membership_rows),
        "document_count": len(document_coverage_rows),
        "direct_mapped_document_count": len(direct_mapped_document_ids),
        "candidate_document_count": len(candidate_document_ids),
        "covered_document_count": len(covered_document_ids),
        "unmapped_document_count": len(unmapped_rows),
        "coverage_status_counts": dict(sorted(coverage_status_counts.items())),
        "processes": nested_processes,
    }
    (target / "process-inventory.json").write_text(
        json.dumps(inventory_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    candidates_by_query: defaultdict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for candidate in flow_candidate_rows:
        candidates_by_query[(candidate["e2e_code"], candidate["node_id"])].append(candidate)

    e2e_json_domains = []
    for domain in e2e_domain_rows:
        if domain["flow_id"]:
            structure = flow_structures[domain["flow_id"]]
            e2e_json_domains.append(
                {
                    **domain,
                    "explicit_memberships": explicit_membership_rows_by_e2e.get(domain["e2e_code"], []),
                    "nodes": [
                        {
                            **node,
                            "document_candidates": candidates_by_query.get(
                                (domain["e2e_code"], node["node_id"]), []
                            ),
                        }
                        for node in structure["nodes"]
                    ],
                    "flow_title_candidates": candidates_by_query.get((domain["e2e_code"], "__FLOW__"), []),
                    "edges": structure["edges"],
                }
            )
        else:
            manual_process = next(
                process for process in nested_processes if process["process_code"] == domain["e2e_code"]
            )
            e2e_json_domains.append({**domain, "stages": manual_process["stages"]})

    e2e_domain_json = {
        "schema_version": 1,
        "policy": {
            "e2e_candidates": "source-flow-or-user-defined",
            "flow_nodes_and_edges": "literal-mermaid-extraction",
            "document_candidates": "mechanical-token-overlap-only",
            "approval": "manual-required",
        },
        "source_flow_count": len(flow_rows),
        "e2e_domain_count": len(e2e_domain_rows),
        "e2e_source_flow_count": sum(row["origin"] == "mermaid-source" for row in e2e_domain_rows),
        "manual_e2e_count": sum(row["origin"] != "mermaid-source" for row in e2e_domain_rows),
        "reference_flow_count": sum(row["flow_class"] == "REFERENCE_MAP" for row in flow_rows),
        "duplicate_flow_count": sum(row["flow_class"] == "DUPLICATE_FLOW" for row in flow_rows),
        "candidate_match_count": len(flow_candidate_rows),
        "document_count": len(document_coverage_rows),
        "direct_mapped_document_count": len(direct_mapped_document_ids),
        "candidate_document_count": len(candidate_document_ids),
        "covered_document_count": len(covered_document_ids),
        "unmapped_document_count": len(unmapped_rows),
        "coverage_status_counts": dict(sorted(coverage_status_counts.items())),
        "domains": e2e_json_domains,
    }
    (target / "e2e-domain-inventory.json").write_text(
        json.dumps(e2e_domain_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    by_e2e_lines = [
        "# Inventaris Lengkap Domain End-to-End",
        "",
        "> Seluruh flow dan kandidat dokumen pada halaman ini adalah inventaris. Status kandidat tidak berarti hubungan sudah disetujui.",
        "",
    ]
    for domain in e2e_domain_rows:
        by_e2e_lines.extend(
            [
                f"## {domain['e2e_code']} - {domain['title']}",
                "",
                f"- Status: `{domain['status']}`",
                f"- Macro group: `{domain['macro_group'] or '-'}`",
                f"- Origin: `{domain['origin']}`",
                f"- Explicit process paths: `{domain['explicit_process_ids'] or '-'}`",
                f"- Kandidat dokumen mekanis: `{domain['candidate_match_count']}`",
            ]
        )
        if domain["flow_document_id"]:
            flow_link = f"../../documents/{domain['flow_document_id']}/index.md"
            by_e2e_lines.append(
                f"- Source flow: [{domain['flow_document_id']}](<{flow_link}>) - `{markdown_cell(domain['source_path'])}`"
            )
        if domain.get("notes"):
            by_e2e_lines.append(f"- Notes: {domain['notes']}")
        by_e2e_lines.append("")

        if not domain["flow_id"]:
            manual_process = next(
                process for process in nested_processes if process["process_code"] == domain["e2e_code"]
            )
            by_e2e_lines.extend(
                [
                    "| Urutan | Stage | Capability | Dokumen kandidat | Role | Status |",
                    "|---:|---|---|---|---|---|",
                ]
            )
            for stage in manual_process["stages"]:
                stage_memberships = stage.get("memberships", [])
                if not stage_memberships:
                    by_e2e_lines.append(
                        f"| {stage['stage_order']} | `{stage['stage_code']}` | {markdown_cell(stage['stage_title'])} | "
                        "- | `-` | `-` |"
                    )
                    continue
                for membership in stage_memberships:
                    doc_link = f"../../documents/{membership['document_id']}/index.md"
                    by_e2e_lines.append(
                        f"| {stage['stage_order']} | `{stage['stage_code']}` | {markdown_cell(stage['stage_title'])} | "
                        f"[{membership['document_id']}](<{doc_link}>) {markdown_cell(membership['document_title'])} | "
                        f"`{membership['membership_role']}` | `{membership['membership_status']}` |"
                    )
            by_e2e_lines.append("")
            continue

        structure = flow_structures[domain["flow_id"]]
        explicit_domain_memberships = explicit_membership_rows_by_e2e.get(domain["e2e_code"], [])
        if explicit_domain_memberships:
            by_e2e_lines.extend(
                [
                    "### Dokumen dari Path Eksplisit",
                    "",
                    "| Process path | Stage | Dokumen | Role |",
                    "|---|---|---|---|",
                ]
            )
            for membership in explicit_domain_memberships:
                doc_link = f"../../documents/{membership['document_id']}/index.md"
                by_e2e_lines.append(
                    f"| `{membership['process_code']}` | `{membership['stage_code']}` | "
                    f"[{membership['document_id']}](<{doc_link}>) {markdown_cell(membership['document_title'])} | "
                    f"`{membership['membership_role']}` |"
                )
            by_e2e_lines.append("")
        flow_title_candidates = candidates_by_query.get((domain["e2e_code"], "__FLOW__"), [])
        if flow_title_candidates:
            by_e2e_lines.extend(["### Kandidat Tingkat Proses", ""])
            for candidate in flow_title_candidates[:5]:
                doc_link = f"../../documents/{candidate['candidate_document_id']}/index.md"
                by_e2e_lines.append(
                    f"- [{candidate['candidate_document_id']}](<{doc_link}>) {markdown_cell(candidate['candidate_title'])} "
                    f"- score `{candidate['match_score']}` - `{candidate['artifact_type']}`"
                )
            by_e2e_lines.append("")

        by_e2e_lines.extend(
            [
                "### Flow Nodes",
                "",
                "| Urutan | Node | Label sumber | Bentuk | Kandidat dokumen |",
                "|---:|---|---|---|---|",
            ]
        )
        for node in structure["nodes"]:
            node_candidates = candidates_by_query.get((domain["e2e_code"], node["node_id"]), [])[:3]
            candidate_labels = []
            for candidate in node_candidates:
                doc_link = f"../../documents/{candidate['candidate_document_id']}/index.md"
                candidate_labels.append(
                    f"[{candidate['candidate_document_id']}](<{doc_link}>) ({candidate['match_score']})"
                )
            by_e2e_lines.append(
                f"| {node['node_order']} | `{node['node_id']}` | {markdown_cell(node['node_label'])} | "
                f"`{node['node_shape']}` | {'<br>'.join(candidate_labels) or '-'} |"
            )
        by_e2e_lines.extend(
            [
                "",
                "### Flow Edges",
                "",
                "| Urutan | From | Kondisi | To |",
                "|---:|---|---|---|",
            ]
        )
        for edge in structure["edges"]:
            by_e2e_lines.append(
                f"| {edge['edge_order']} | `{edge['from_node']}` | {markdown_cell(edge['edge_label'] or '-')} | "
                f"`{edge['to_node']}` |"
            )
        by_e2e_lines.append("")
    (target / "by-e2e-domain.md").write_text("\n".join(by_e2e_lines).rstrip() + "\n", encoding="utf-8")

    by_process_lines = [
        "# Inventaris Dokumen berdasarkan Proses End-to-End",
        "",
        "> Proses `SOURCE_EXPLICIT` berasal dari `prd-paths-v2.json`. Proses atau membership `DRAFT/CANDIDATE` memerlukan konfirmasi manual.",
        "",
    ]
    for process in process_rows:
        process_code = process["process_code"]
        by_process_lines.extend(
            [
                f"## {process_code} - {process['title']}",
                "",
                f"- Status: `{process['status']}`",
                f"- Origin: `{process['origin']}`",
                f"- Category/owner: `{process['category'] or process['owner'] or '-'}`",
                f"- Scenario: {process['scenario'] or '-'}",
                f"- Start event: {process['start_event'] or '(belum ditetapkan)' }",
                f"- End event: {process['end_event'] or '(belum ditetapkan)' }",
            ]
        )
        if process.get("source_flow_document_id"):
            flow_link = f"../../documents/{process['source_flow_document_id']}/index.md"
            by_process_lines.append(
                f"- Source flow: [{process['source_flow_document_id']}](<{flow_link}>) - `{markdown_cell(process['source_flow'])}`"
            )
        if process.get("notes"):
            by_process_lines.append(f"- Notes: {process['notes']}")
        by_process_lines.extend(
            [
                "",
                "| Urutan | Stage | Capability | Dokumen | Role | Membership | Entry condition | Output |",
                "|---:|---|---|---|---|---|---|---|",
            ]
        )
        process_stage_rows = [item for item in stage_rows if item["process_code"] == process_code]
        for stage in process_stage_rows:
            stage_memberships = memberships_by_stage.get((process_code, stage["stage_code"]), [])
            if not stage_memberships:
                by_process_lines.append(
                    f"| {stage['stage_order']} | `{stage['stage_code']}` | {markdown_cell(stage['stage_title'])} | "
                    f"(belum dipetakan) | `-` | `-` | {markdown_cell(stage['entry_condition'] or '-')} | "
                    f"{markdown_cell(stage['output'] or '-')} |"
                )
                continue
            for membership in stage_memberships:
                doc_link = f"../../documents/{membership['document_id']}/index.md"
                by_process_lines.append(
                    f"| {stage['stage_order']} | `{stage['stage_code']}` | {markdown_cell(stage['stage_title'])} | "
                    f"[{membership['document_id']}](<{doc_link}>) {markdown_cell(membership['document_title'])} | "
                    f"`{membership['membership_role']}` | `{membership['membership_status']}` | "
                    f"{markdown_cell(stage['entry_condition'] or '-')} | {markdown_cell(stage['output'] or '-')} |"
                )
        by_process_lines.append("")

        process_variants = [item for item in variant_rows if item["process_code"] == process_code]
        if process_variants:
            by_process_lines.extend(
                [
                    "### Kandidat/Varian Sumber",
                    "",
                    "| Stage | Kandidat | Basis | Dipilih sementara |",
                    "|---|---|---|---|",
                ]
            )
            for variant in process_variants:
                doc_link = f"../../documents/{variant['candidate_document_id']}/index.md"
                by_process_lines.append(
                    f"| `{variant['stage_code']}` | [{variant['candidate_document_id']}](<{doc_link}>) "
                    f"{markdown_cell(variant['candidate_title'])} | `{variant['candidate_basis']}` | "
                    f"`{variant['selected_candidate']}` |"
                )
            by_process_lines.append("")
    (target / "by-process.md").write_text("\n".join(by_process_lines).rstrip() + "\n", encoding="utf-8")

    readme = f"""# Inventaris Proses End-to-End

Inventaris ini mengelompokkan dokumen berdasarkan proses bisnis end-to-end, bukan berdasarkan folder atau modul sumber.

## Ringkasan

- Flow sumber yang diinventaris: `{len(flow_rows)}`
- Domain E2E kandidat dari flow unik: `{sum(domain['origin'] == 'mermaid-source' for domain in e2e_domain_rows)}`
- Domain E2E manual/draft: `{sum(domain['origin'] != 'mermaid-source' for domain in e2e_domain_rows)}`
- Total domain E2E kandidat: `{len(e2e_domain_rows)}`
- Flow referensi tingkat agregat: `{sum(flow['flow_class'] == 'REFERENCE_MAP' for flow in flow_rows)}`
- Flow duplikat yang diarahkan ke counterpart: `{sum(flow['flow_class'] == 'DUPLICATE_FLOW' for flow in flow_rows)}`
- Kandidat dokumen hasil pencocokan mekanis: `{len(flow_candidate_rows)}`
- Proses sumber eksplisit: `{sum(process['status'] == 'SOURCE_EXPLICIT' for process in process_rows)}`
- Proses manual/draft: `{sum(process['status'] != 'SOURCE_EXPLICIT' for process in process_rows)}`
- Total proses: `{len(process_rows)}`
- Total tahap: `{len(stage_rows)}`
- Membership dokumen: `{len(membership_rows)}`
- Total dokumen dalam matriks coverage: `{len(document_coverage_rows)}`
- Dokumen dengan hubungan langsung (membership atau source flow eksplisit): `{len(direct_mapped_document_ids)}`
- Dokumen dengan kandidat hubungan mekanis: `{len(candidate_document_ids)}`
- Dokumen tercakup oleh hubungan langsung, kandidat, atau artefak flow: `{len(covered_document_ids)}`
- Dokumen belum dipetakan ke proses E2E: `{len(unmapped_rows)}`

## Status Coverage Dokumen

- Source explicit membership: `{coverage_status_counts['SOURCE_EXPLICIT_MEMBERSHIP']}`
- Manual candidate membership: `{coverage_status_counts['MANUAL_CANDIDATE_MEMBERSHIP']}`
- Mechanical candidate: `{coverage_status_counts['MECHANICAL_CANDIDATE']}`
- E2E source flow: `{coverage_status_counts['E2E_SOURCE_FLOW']}`
- Flow reference atau duplicate: `{coverage_status_counts['FLOW_REFERENCE_OR_DUPLICATE']}`
- Belum terpetakan ke inventaris E2E: `{coverage_status_counts['UNMAPPED_TO_E2E_INVENTORY']}`

## Model

- Satu proses mempunyai tahap terurut.
- Satu tahap dapat menunjuk satu atau lebih dokumen.
- Satu dokumen dapat digunakan oleh beberapa proses tanpa disalin.
- Membership `CANDIDATE` atau role `UNCONFIRMED` belum menjadi keputusan final.
- Proses `SOURCE_EXPLICIT` mempertahankan isi `prd-paths-v2.json` dan tetap perlu direview sebagai calon E2E final.
- Flow node dan edge diekstrak literal dari Mermaid; urutan node adalah urutan kemunculan, bukan keputusan urutan implementasi.
- Pencocokan dokumen memakai token literal/mekanis dan selalu berstatus `MECHANICAL_CANDIDATE`.

## Input Manual

- `manual-processes.csv`: definisi proses E2E yang dibuat user.
- `manual-stages.csv`: urutan tahap di dalam proses manual.
- `manual-memberships.csv`: pemetaan dokumen ke tahap dan role-nya.

Ketiga file tersebut tidak ditulis ulang oleh generator. File lainnya adalah keluaran turunan.
Contoh alur, hipotesis, atau ilustrasi percakapan tidak boleh dimasukkan sebagai proses manual tanpa persetujuan eksplisit user.

## Keluaran

- `e2e-domain-register.csv`: seluruh kandidat domain E2E unik.
- `by-e2e-domain.md`: tampilan lengkap node, edge, dan kandidat dokumen per domain E2E.
- `e2e-domain-inventory.json`: bentuk nested domain E2E lengkap.
- `flow-register.csv`: klasifikasi seluruh flow sumber.
- `flow-node-register.csv`: node literal dari Mermaid.
- `flow-edge-register.csv`: edge literal dari Mermaid.
- `flow-document-candidates.csv`: kandidat dokumen berdasarkan kecocokan token mekanis.
- `document-e2e-coverage.csv`: matriks lengkap satu baris per dokumen beserta status dan seluruh kode E2E kandidatnya.
- `process-register.csv`: daftar proses dan statusnya.
- `stage-register.csv`: seluruh tahap terurut.
- `membership-register.csv`: hubungan many-to-many proses, tahap, dan dokumen.
- `by-process.md`: tampilan manusia per proses.
- `candidate-variants.csv`: varian exact duplicate atau generator counterpart untuk kandidat manual.
- `unmapped-documents.csv`: dokumen yang belum terhubung ke proses E2E.
- `process-inventory.json`: bentuk nested machine-readable.

## Status Manual yang Disarankan

Proses: `DRAFT`, `IN_REVIEW`, `CONFIRMED`, `BASELINED`.

Tahap: `DRAFT`, `CONFIRMED`, `NEEDS_DETAIL`.

Membership: `CANDIDATE`, `CONFIRMED`, `CONTEXT`, `EXCLUDED`.

Role: `MAIN`, `SHARED`, `INTEGRATION`, `CONTEXT`, `REFERENCE`, atau `UNCONFIRMED`.
"""
    (target / "README.md").write_text(readme, encoding="utf-8")

    manifest = {
        "schema_version": 1,
        "inputs": [
            "catalog/document-index.json",
            "catalog/process-index.json",
            "catalog/source-domain-feature-index.json",
            "catalog/correlation-index.json",
            "reconciliation/inventory/document-register.json",
            "reconciliation/e2e-inventory/manual-processes.csv",
            "reconciliation/e2e-inventory/manual-stages.csv",
            "reconciliation/e2e-inventory/manual-memberships.csv",
        ],
        "outputs": [
            "reconciliation/e2e-inventory/README.md",
            "reconciliation/e2e-inventory/e2e-domain-register.csv",
            "reconciliation/e2e-inventory/by-e2e-domain.md",
            "reconciliation/e2e-inventory/e2e-domain-inventory.json",
            "reconciliation/e2e-inventory/flow-register.csv",
            "reconciliation/e2e-inventory/flow-node-register.csv",
            "reconciliation/e2e-inventory/flow-edge-register.csv",
            "reconciliation/e2e-inventory/flow-document-candidates.csv",
            "reconciliation/e2e-inventory/document-e2e-coverage.csv",
            "reconciliation/e2e-inventory/process-register.csv",
            "reconciliation/e2e-inventory/stage-register.csv",
            "reconciliation/e2e-inventory/membership-register.csv",
            "reconciliation/e2e-inventory/candidate-variants.csv",
            "reconciliation/e2e-inventory/unmapped-documents.csv",
            "reconciliation/e2e-inventory/process-inventory.json",
            "reconciliation/e2e-inventory/by-process.md",
        ],
        "process_count": len(process_rows),
        "source_flow_count": len(flow_rows),
        "e2e_domain_count": len(e2e_domain_rows),
        "reference_flow_count": sum(flow["flow_class"] == "REFERENCE_MAP" for flow in flow_rows),
        "duplicate_flow_count": sum(flow["flow_class"] == "DUPLICATE_FLOW" for flow in flow_rows),
        "candidate_match_count": len(flow_candidate_rows),
        "stage_count": len(stage_rows),
        "membership_count": len(membership_rows),
        "document_count": len(document_coverage_rows),
        "direct_mapped_document_count": len(direct_mapped_document_ids),
        "candidate_document_count": len(candidate_document_ids),
        "covered_document_count": len(covered_document_ids),
        "unmapped_document_count": len(unmapped_rows),
        "coverage_status_counts": dict(sorted(coverage_status_counts.items())),
    }
    (target / "inventory-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": "BUILT", **manifest}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
