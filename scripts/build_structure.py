#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import mimetypes
import os
import posixpath
import re
import shutil
import subprocess
import sys
import unicodedata
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import unquote, urlparse
from xml.etree import ElementTree as ET


W_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
X_NS = {
    "x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
TEXT_EXTENSIONS = {".md", ".mmd", ".html", ".json", ".csv", ".ps1"}
BINARY_EXTENSIONS = {".docx", ".xlsx", ".pdf"}
SUPPORTED_EXTENSIONS = TEXT_EXTENSIONS | BINARY_EXTENSIONS


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha1_text(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8", "surrogatepass")).hexdigest()


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")
    return slug or "item"


def markdown_link(label: str, target: str) -> str:
    safe_label = label.replace("[", "\\[").replace("]", "\\]")
    return f"[{safe_label}](<{target}>)"


def json_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def text_write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def first_nonempty(lines: Iterable[str]) -> str:
    for line in lines:
        value = clean(line)
        if value:
            return value
    return ""


def mechanical_filename_key(path: Path) -> str:
    name = path.name.casefold()
    while True:
        stem, suffix = os.path.splitext(name)
        if suffix in {".docx", ".xlsx", ".pdf", ".md", ".mmd", ".html", ".json", ".csv", ".ps1"}:
            name = stem
            continue
        break
    name = re.sub(r"^copy of\s+", "", name)
    name = re.sub(r"\[(?:draft|fix|final|update)\]", " ", name)
    name = re.sub(r"\((?:copy|\d+)\)", " ", name)
    name = re.sub(r"\b(?:draft|final|fix|update|new|lengkap)\b", " ", name)
    name = re.sub(r"\brev(?:isi|ision)?[._ -]*\d+(?:[._-]\d+)*\b", " ", name)
    name = re.sub(r"\bv\d+(?:[._-]\d+)*\b", " ", name)
    return slugify(name)


def filename_markers(path: Path) -> list[str]:
    name = path.name.casefold()
    markers = []
    for marker in ("draft", "final", "fix", "update", "rev", "copy", "new"):
        if marker in name:
            markers.append(marker)
    markers.extend(sorted(set(re.findall(r"\(\d+\)", name))))
    markers.extend(sorted(set(re.findall(r"\bv\d+(?:[._-]\d+)*\b", name))))
    return markers


class VisibleHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.visible: list[str] = []
        self.headings: list[dict[str, Any]] = []
        self.links: list[str] = []
        self.tag_counts: Counter[str] = Counter()
        self.attributes: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        self.stack.append(tag)
        self.tag_counts[tag] += 1
        values = {key: value or "" for key, value in attrs}
        if values:
            self.attributes.append({"tag": tag, **values})
        href = values.get("href")
        if href:
            self.links.append(href)
        for key in ("aria-label", "placeholder", "alt", "title", "value"):
            if values.get(key):
                self.visible.append(values[key])

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data: str) -> None:
        if any(tag in {"script", "style", "svg"} for tag in self.stack):
            return
        value = clean(data)
        if not value:
            return
        self.visible.append(value)
        if self.stack and re.fullmatch(r"h[1-6]", self.stack[-1]):
            self.headings.append({"level": int(self.stack[-1][1]), "text": value, "method": "html-heading"})


@dataclass
class Extracted:
    text: str
    markdown: str
    headings: list[dict[str, Any]] = field(default_factory=list)
    structure: dict[str, Any] = field(default_factory=dict)
    raw_links: list[str] = field(default_factory=list)
    media: list[tuple[str, bytes]] = field(default_factory=list)
    render_pdf: bool = False


def extract_markdown(raw: bytes, extension: str) -> Extracted:
    value = raw.decode("utf-8-sig", "replace")
    headings: list[dict[str, Any]] = []
    links: list[str] = []
    for line_no, line in enumerate(value.splitlines(), 1):
        match = re.match(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if match:
            headings.append(
                {"level": len(match.group(1)), "text": clean(match.group(2)), "line": line_no, "method": "markdown-heading"}
            )
        links.extend(match.group(1) for match in re.finditer(r"(?<!!)\[[^\]]*\]\(([^)]+)\)", line))
    if extension == ".mmd":
        diagram_type = "unknown"
        for line in value.splitlines():
            item = line.strip()
            if not item or item.startswith("%%"):
                continue
            diagram_type = item.split()[0]
            break
        edge_lines = [line.rstrip() for line in value.splitlines() if re.search(r"-->|==>|-\.->", line)]
        markdown = "# Isi Mermaid Asli\n\n```mermaid\n" + value.rstrip() + "\n```\n"
        return Extracted(
            text=value,
            markdown=markdown,
            headings=headings,
            structure={"diagram_type_literal": diagram_type, "edge_lines": edge_lines},
            raw_links=links,
        )
    return Extracted(
        text=value,
        markdown="# Isi Markdown Asli\n\n" + value.rstrip() + "\n",
        headings=headings,
        structure={"line_count": len(value.splitlines())},
        raw_links=links,
    )


def extract_html(raw: bytes) -> Extracted:
    source = raw.decode("utf-8-sig", "replace")
    parser = VisibleHTMLParser()
    try:
        parser.feed(source)
    except Exception as exc:
        parse_error = str(exc)
    else:
        parse_error = None
    visible = "\n".join(parser.visible)
    markdown = (
        "# Teks Terlihat\n\n"
        + (visible.rstrip() or "(Tidak ada teks terlihat yang berhasil diekstrak.)")
        + "\n\n# Sumber HTML Asli\n\n````html\n"
        + source.rstrip()
        + "\n````\n"
    )
    return Extracted(
        text=visible + "\n" + source,
        markdown=markdown,
        headings=parser.headings,
        structure={
            "tag_counts": dict(sorted(parser.tag_counts.items())),
            "attributes": parser.attributes,
            "parse_error": parse_error,
        },
        raw_links=parser.links,
    )


def paragraph_text(node: ET.Element) -> str:
    pieces: list[str] = []
    for element in node.iter():
        local = element.tag.rsplit("}", 1)[-1]
        if local == "t":
            pieces.append(element.text or "")
        elif local == "tab":
            pieces.append("\t")
        elif local in {"br", "cr"}:
            pieces.append("\n")
    return re.sub(r"[ \t]+", " ", "".join(pieces)).strip()


def docx_table_markdown(table: ET.Element) -> tuple[str, list[list[str]]]:
    rows: list[list[str]] = []
    for row in table.findall("./w:tr", W_NS):
        cells = []
        for cell in row.findall("./w:tc", W_NS):
            values = [paragraph_text(p) for p in cell.findall(".//w:p", W_NS)]
            cells.append(" / ".join(value for value in values if value))
        rows.append(cells)
    width = max((len(row) for row in rows), default=0)
    if width == 0:
        return "", rows
    normalized = [row + [""] * (width - len(row)) for row in rows]
    escaped = [[cell.replace("|", "\\|").replace("\n", "<br>") for cell in row] for row in normalized]
    header = escaped[0]
    body = escaped[1:]
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(["---"] * width) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in body)
    return "\n".join(lines), rows


def extract_docx(path: Path) -> Extracted:
    sections: list[str] = []
    plain: list[str] = []
    headings: list[dict[str, Any]] = []
    tables: list[list[list[str]]] = []
    media: list[tuple[str, bytes]] = []
    parts_read: list[str] = []
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        for name in sorted(names):
            if name.startswith("word/media/") and not name.endswith("/"):
                media.append((Path(name).name, archive.read(name)))
        candidates = [
            name
            for name in names
            if name == "word/document.xml"
            or re.fullmatch(r"word/(?:header|footer)\d+\.xml", name)
            or name in {"word/footnotes.xml", "word/endnotes.xml", "word/comments.xml"}
        ]
        candidates.sort(key=lambda item: (item != "word/document.xml", item))
        for part in candidates:
            root = ET.fromstring(archive.read(part))
            parts_read.append(part)
            sections.append(f"# Bagian XML: {part}")
            if part == "word/document.xml":
                body = root.find("w:body", W_NS)
                children = list(body) if body is not None else list(root)
            else:
                children = list(root)
            for child in children:
                local = child.tag.rsplit("}", 1)[-1]
                if local == "p":
                    value = paragraph_text(child)
                    if not value:
                        continue
                    plain.append(value)
                    style_node = child.find("./w:pPr/w:pStyle", W_NS)
                    style = ""
                    if style_node is not None:
                        style = style_node.attrib.get(f"{{{W_NS['w']}}}val", "")
                    if style.casefold().startswith(("heading", "judul", "title")):
                        match = re.search(r"(\d+)$", style)
                        headings.append(
                            {
                                "level": int(match.group(1)) if match else 1,
                                "text": value,
                                "style": style,
                                "part": part,
                                "method": "docx-paragraph-style",
                            }
                        )
                    sections.append(value)
                elif local == "tbl":
                    rendered, rows = docx_table_markdown(child)
                    tables.append(rows)
                    sections.append(rendered or "(Tabel kosong)")
                else:
                    for paragraph in child.findall(".//w:p", W_NS):
                        value = paragraph_text(paragraph)
                        if value:
                            plain.append(value)
                            sections.append(value)
    return Extracted(
        text="\n".join(plain),
        markdown="\n\n".join(sections).rstrip() + "\n",
        headings=headings,
        structure={"xml_parts": parts_read, "table_count": len(tables), "tables": tables},
        media=media,
    )


def excel_column_number(reference: str) -> int:
    match = re.match(r"([A-Z]+)", reference)
    if not match:
        return 0
    value = 0
    for character in match.group(1):
        value = value * 26 + ord(character) - 64
    return value


def extract_xlsx(path: Path) -> Extracted:
    markdown_sections: list[str] = []
    plain: list[str] = []
    headings: list[dict[str, Any]] = []
    sheets: list[dict[str, Any]] = []
    media: list[tuple[str, bytes]] = []
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        for name in sorted(names):
            if name.startswith("xl/media/") and not name.endswith("/"):
                media.append((Path(name).name, archive.read(name)))
        shared: list[str] = []
        if "xl/sharedStrings.xml" in names:
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in root.findall("x:si", X_NS):
                shared.append("".join(node.text or "" for node in item.findall(".//x:t", X_NS)))
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships: dict[str, str] = {}
        if "xl/_rels/workbook.xml.rels" in names:
            rel_root = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
            for relation in rel_root:
                relationships[relation.attrib.get("Id", "")] = relation.attrib.get("Target", "")
        for sheet in workbook.findall(".//x:sheet", X_NS):
            sheet_name = sheet.attrib.get("name", "")
            relation_id = sheet.attrib.get(f"{{{X_NS['r']}}}id", "")
            target = relationships.get(relation_id, "")
            part = target.lstrip("/") if target.startswith("/") else posixpath.normpath("xl/" + target)
            headings.append({"level": 1, "text": sheet_name, "method": "xlsx-sheet-name"})
            markdown_sections.append(f"# Sheet: {sheet_name}")
            cells_output: list[str] = []
            formulas = 0
            max_row = 0
            max_col = 0
            nonempty_cells = 0
            merged: list[str] = []
            if part in names:
                root = ET.fromstring(archive.read(part))
                merged = [item.attrib.get("ref", "") for item in root.findall(".//x:mergeCell", X_NS)]
                for row in root.findall(".//x:sheetData/x:row", X_NS):
                    row_number = int(row.attrib.get("r", "0") or 0)
                    max_row = max(max_row, row_number)
                    for cell in row.findall("x:c", X_NS):
                        reference = cell.attrib.get("r", "")
                        max_col = max(max_col, excel_column_number(reference))
                        value_type = cell.attrib.get("t", "")
                        formula_node = cell.find("x:f", X_NS)
                        value_node = cell.find("x:v", X_NS)
                        if value_type == "inlineStr":
                            value = "".join(node.text or "" for node in cell.findall(".//x:t", X_NS))
                        elif value_node is not None:
                            value = value_node.text or ""
                            if value_type == "s":
                                try:
                                    value = shared[int(value)]
                                except (ValueError, IndexError):
                                    pass
                        else:
                            value = ""
                        formula = formula_node.text if formula_node is not None else ""
                        if formula:
                            formulas += 1
                        if value or formula:
                            nonempty_cells += 1
                            plain.append(value)
                            suffix = f"\tFORMULA={formula}" if formula else ""
                            cells_output.append(f"{reference}\t{value}{suffix}")
            markdown_sections.append("```text\n" + "\n".join(cells_output) + "\n```")
            sheets.append(
                {
                    "name": sheet_name,
                    "part": part,
                    "max_row": max_row,
                    "max_column": max_col,
                    "nonempty_cells": nonempty_cells,
                    "formula_count": formulas,
                    "merged_ranges": merged,
                }
            )
    return Extracted(
        text="\n".join(plain),
        markdown="\n\n".join(markdown_sections).rstrip() + "\n",
        headings=headings,
        structure={"sheets": sheets},
        media=media,
    )


def extract_pdf(path: Path) -> Extracted:
    process = subprocess.run(
        ["pdftotext", "-layout", str(path), "-"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=180,
    )
    value = process.stdout.decode("utf-8", "replace")
    info_process = subprocess.run(
        ["pdfinfo", str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=60
    )
    metadata: dict[str, str] = {}
    for line in info_process.stdout.decode("utf-8", "replace").splitlines():
        if ":" in line:
            key, item = line.split(":", 1)
            metadata[clean(key)] = clean(item)
    headings = []
    for line_number, line in enumerate(value.splitlines(), 1):
        item = clean(line)
        if item and len(item) <= 160 and item == item.upper() and re.search(r"[A-Z]", item):
            headings.append({"level": 1, "text": item, "line": line_number, "method": "pdf-uppercase-line"})
    markdown = "# Teks PDF Hasil Ekstraksi Layout\n\n```text\n" + value.rstrip() + "\n```\n"
    return Extracted(
        text=value,
        markdown=markdown,
        headings=headings,
        structure={
            "metadata": metadata,
            "pdftotext_stderr": process.stderr.decode("utf-8", "replace"),
            "pdfinfo_stderr": info_process.stderr.decode("utf-8", "replace"),
        },
        render_pdf=True,
    )


def extract_csv(raw: bytes) -> Extracted:
    value = raw.decode("utf-8-sig", "replace")
    rows: list[list[str]] = []
    delimiter = None
    try:
        dialect = csv.Sniffer().sniff(value[:8192], delimiters=",;\t|")
        delimiter = dialect.delimiter
        rows = list(csv.reader(value.splitlines(), dialect))
    except csv.Error:
        pass
    return Extracted(
        text=value,
        markdown="# Isi CSV Asli\n\n```csv\n" + value.rstrip() + "\n```\n",
        structure={"delimiter": delimiter, "row_count": len(rows), "max_columns": max(map(len, rows), default=0)},
    )


def extract_json(raw: bytes) -> Extracted:
    value = raw.decode("utf-8-sig", "replace")
    try:
        parsed = json.loads(value)
        parse_error = None
        root_type = type(parsed).__name__
        top_keys = list(parsed) if isinstance(parsed, dict) else []
    except json.JSONDecodeError as exc:
        parse_error = str(exc)
        root_type = "invalid"
        top_keys = []
    return Extracted(
        text=value,
        markdown="# Isi JSON Asli\n\n```json\n" + value.rstrip() + "\n```\n",
        structure={"root_type": root_type, "top_keys": top_keys, "parse_error": parse_error},
    )


def extract_powershell(raw: bytes) -> Extracted:
    value = raw.decode("utf-8-sig", "replace")
    functions = re.findall(r"(?mi)^function\s+([\w-]+)", value)
    return Extracted(
        text=value,
        markdown="# Isi PowerShell Asli\n\n```powershell\n" + value.rstrip() + "\n```\n",
        structure={"functions": functions},
    )


def extract_file(path: Path, raw: bytes) -> Extracted:
    extension = path.suffix.casefold()
    if extension in {".md", ".mmd"}:
        return extract_markdown(raw, extension)
    if extension == ".html":
        return extract_html(raw)
    if extension == ".docx":
        return extract_docx(path)
    if extension == ".xlsx":
        return extract_xlsx(path)
    if extension == ".pdf":
        return extract_pdf(path)
    if extension == ".csv":
        return extract_csv(raw)
    if extension == ".json":
        return extract_json(raw)
    if extension == ".ps1":
        return extract_powershell(raw)
    value = raw.decode("utf-8", "replace")
    return Extracted(text=value, markdown="# Isi Asli\n\n```text\n" + value.rstrip() + "\n```\n")


def detect_title(extracted: Extracted, source_path: Path) -> str:
    if source_path.suffix.casefold() in {".md", ".html"} and extracted.headings:
        return extracted.headings[0]["text"]
    return source_path.name


def source_directory_key(relative_path: str) -> str:
    parts = Path(relative_path).parts
    if len(parts) >= 3 and parts[0] == "PRD" and parts[1].startswith("PRD Generator"):
        return "/".join(parts[:3])
    if len(parts) >= 2:
        return "/".join(parts[:2])
    return parts[0] if parts else "[root]"


def resolve_local_link(source_rel: str, target: str, source_paths: set[str]) -> str | None:
    cleaned = target.strip().strip("<>")
    if cleaned.startswith(("http://", "https://", "mailto:", "#", "data:")):
        return None
    parsed = urlparse(cleaned)
    path_value = unquote(parsed.path)
    if not path_value:
        return None
    candidate = posixpath.normpath(posixpath.join(posixpath.dirname(source_rel), path_value))
    return candidate if candidate in source_paths else None


def relation_key(relation: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        relation["from"],
        relation["type"],
        relation["to"],
        json.dumps(relation.get("basis", {}), ensure_ascii=False, sort_keys=True),
    )


def add_relation(relations: list[dict[str, Any]], seen: set[tuple[str, str, str, str]], relation: dict[str, Any]) -> None:
    if relation["from"] == relation["to"]:
        return
    key = relation_key(relation)
    if key not in seen:
        seen.add(key)
        relations.append(relation)


def relative_from_card(target_root: Path, target: Path) -> str:
    return os.path.relpath(target, target_root).replace(os.sep, "/")


def make_document_card(
    target: Path,
    document: dict[str, Any],
    relations_by_document: dict[str, list[dict[str, Any]]],
) -> None:
    doc_dir = target / "documents" / document["document_id"]
    doc_dir.mkdir(parents=True, exist_ok=True)
    source_target = relative_from_card(doc_dir, target / "source" / "original" / document["source_path"])
    content_target = "content.md"
    structure_target = "structure.json"
    lines = [
        f"# {document['title']}",
        "",
        "## Fakta File",
        "",
        f"- Document ID: `{document['document_id']}`",
        f"- Content ID: `{document['content_id']}`",
        f"- Lokasi sumber: `{document['source_path']}`",
        f"- Format: `{document['extension']}`",
        f"- MIME: `{document['mime_type']}`",
        f"- Ukuran: `{document['bytes']}` byte",
        f"- SHA-256: `{document['sha256']}`",
        f"- SHA-256 teks ternormalisasi: `{document['normalized_text_sha256']}`",
        f"- Kunci nama mekanis: `{document['mechanical_filename_key']}`",
        f"- Penanda nama file: {', '.join(f'`{item}`' for item in document['filename_markers']) or '(tidak ada)' }",
        "",
        "## Berkas",
        "",
        f"- {markdown_link('Dokumen asli', source_target)}",
        f"- {markdown_link('Konten hasil ekstraksi literal', content_target)}",
        f"- {markdown_link('Struktur hasil deteksi', structure_target)}",
    ]
    if document.get("media_paths"):
        lines.extend(["", "## Media Terekstrak", ""])
        for media_path in document["media_paths"]:
            target_path = relative_from_card(doc_dir, target / media_path)
            lines.append(f"- {markdown_link(Path(media_path).name, target_path)}")
    if document.get("rendered_paths"):
        lines.extend(["", "## Render Halaman", ""])
        for rendered_path in document["rendered_paths"]:
            target_path = relative_from_card(doc_dir, target / rendered_path)
            lines.append(f"- {markdown_link(Path(rendered_path).name, target_path)}")
    lines.extend(["", "## Struktur Terdeteksi", ""])
    if document["headings"]:
        for heading in document["headings"]:
            lines.append(
                f"- Level `{heading.get('level', '')}` — {heading.get('text', '')} "
                f"(`{heading.get('method', 'unknown')}`)"
            )
    else:
        lines.append("- Tidak ada heading yang terdeteksi oleh extractor.")
    lines.extend(["", "## Korelasi", ""])
    relations = relations_by_document.get(document["document_id"], [])
    if relations:
        for relation in sorted(relations, key=lambda item: (item["type"], item["to"])):
            other = relation["to"] if relation["from"] == document["document_id"] else relation["from"]
            if other.startswith("PROCESS-"):
                process_id = other[len("PROCESS-") :]
                other_target = relative_from_card(
                    doc_dir, target / "processes" / "explicit" / f"{slugify(process_id)}.md"
                )
            else:
                other_target = relative_from_card(doc_dir, target / "documents" / other / "index.md")
            basis = json.dumps(relation.get("basis", {}), ensure_ascii=False, sort_keys=True)
            lines.append(f"- `{relation['type']}` → {markdown_link(other, other_target)} — basis: `{basis}`")
    else:
        lines.append("- Tidak ada korelasi dokumen yang dihasilkan oleh aturan deterministik.")
    text_write(doc_dir / "index.md", "\n".join(lines).rstrip() + "\n")


def build(source: Path, target: Path) -> None:
    if not source.is_dir():
        raise SystemExit(f"Source tidak ditemukan: {source}")
    target.mkdir(parents=True, exist_ok=True)
    for relative in ("documents", "catalog", "processes", "indexes", "graph", "docs", "source/media", "source/rendered"):
        generated = target / relative
        if generated.exists():
            shutil.rmtree(generated)
        generated.mkdir(parents=True, exist_ok=True)

    source_files = [path for path in sorted(source.rglob("*")) if path.is_file()]
    documents: list[dict[str, Any]] = []
    extracted_by_id: dict[str, Extracted] = {}
    raw_links_by_id: dict[str, list[str]] = {}
    source_to_id: dict[str, str] = {}

    for index, path in enumerate(source_files, 1):
        relative = path.relative_to(source).as_posix()
        raw = path.read_bytes()
        document_id = "DOC-" + sha1_text(relative)[:16].upper()
        content_hash = sha256_bytes(raw)
        content_id = "CONTENT-" + content_hash[:16].upper()
        extracted = extract_file(path, raw)
        normalized_hash = sha256_bytes(normalize_text(extracted.text).encode("utf-8", "replace"))
        media_paths: list[str] = []
        for media_name, media_data in extracted.media:
            media_target = target / "source" / "media" / document_id / media_name
            media_target.parent.mkdir(parents=True, exist_ok=True)
            media_target.write_bytes(media_data)
            media_paths.append(media_target.relative_to(target).as_posix())
        rendered_paths: list[str] = []
        if extracted.render_pdf:
            render_dir = target / "source" / "rendered" / document_id
            render_dir.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["pdftoppm", "-png", "-r", "110", str(path), str(render_dir / "page")],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=300,
            )
            rendered_paths = [item.relative_to(target).as_posix() for item in sorted(render_dir.glob("*.png"))]
        title = detect_title(extracted, Path(relative))
        mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        document = {
            "document_id": document_id,
            "content_id": content_id,
            "source_path": relative,
            "title": title,
            "extension": path.suffix.casefold(),
            "mime_type": mime_type,
            "bytes": len(raw),
            "sha256": content_hash,
            "normalized_text_sha256": normalized_hash,
            "extracted_text_empty": not bool(normalize_text(extracted.text)),
            "mechanical_filename_key": mechanical_filename_key(Path(relative)),
            "filename_markers": filename_markers(Path(relative)),
            "source_directory": source_directory_key(relative),
            "headings": extracted.headings,
            "media_paths": media_paths,
            "rendered_paths": rendered_paths,
            "generated_paths": {
                "card": f"documents/{document_id}/index.md",
                "content": f"documents/{document_id}/content.md",
                "structure": f"documents/{document_id}/structure.json",
            },
        }
        documents.append(document)
        source_to_id[relative] = document_id
        extracted_by_id[document_id] = extracted
        raw_links_by_id[document_id] = extracted.raw_links
        if index % 100 == 0:
            print(f"Extracted {index}/{len(source_files)}", file=sys.stderr)

    source_paths = set(source_to_id)
    by_sha: defaultdict[str, list[str]] = defaultdict(list)
    by_normalized_text: defaultdict[str, list[str]] = defaultdict(list)
    by_filename_key: defaultdict[str, list[str]] = defaultdict(list)
    by_basename: defaultdict[str, list[str]] = defaultdict(list)
    for document in documents:
        by_sha[document["sha256"]].append(document["document_id"])
        if not document["extracted_text_empty"]:
            by_normalized_text[document["normalized_text_sha256"]].append(document["document_id"])
        by_filename_key[document["mechanical_filename_key"]].append(document["document_id"])
        by_basename[Path(document["source_path"]).name.casefold()].append(document["document_id"])

    relations: list[dict[str, Any]] = []
    relation_seen: set[tuple[str, str, str, str]] = set()

    def add_star(group: list[str], relation_type: str, basis: dict[str, Any]) -> None:
        ordered = sorted(group)
        if len(ordered) < 2:
            return
        anchor = ordered[0]
        for item in ordered[1:]:
            add_relation(relations, relation_seen, {"from": anchor, "type": relation_type, "to": item, "basis": basis})

    for digest, group in sorted(by_sha.items()):
        add_star(group, "same-binary-content", {"method": "sha256", "value": digest})
    for digest, group in sorted(by_normalized_text.items()):
        if len(group) > 1:
            add_star(group, "same-normalized-extracted-text", {"method": "normalized-text-sha256", "value": digest})
    for key, group in sorted(by_filename_key.items()):
        if len(group) > 1 and len(key) >= 6 and len(group) <= 30:
            add_star(group, "same-mechanical-filename-key", {"method": "mechanical-filename-normalization", "value": key})

    original_prefix = "PRD/PRD Generator (.md)/"
    copy_prefix = "PRD/PRD Generator (.md) - Copy/"
    original_map = {
        path[len(original_prefix) :]: document_id
        for path, document_id in source_to_id.items()
        if path.startswith(original_prefix)
    }
    copy_map = {
        path[len(copy_prefix) :]: document_id
        for path, document_id in source_to_id.items()
        if path.startswith(copy_prefix)
    }
    docs_by_id = {item["document_id"]: item for item in documents}
    for relative in sorted(set(original_map) & set(copy_map)):
        left = original_map[relative]
        right = copy_map[relative]
        add_relation(
            relations,
            relation_seen,
            {
                "from": left,
                "type": "generator-tree-counterpart",
                "to": right,
                "basis": {
                    "method": "same-relative-path-under-generator-trees",
                    "relative_path": relative,
                    "same_sha256": docs_by_id[left]["sha256"] == docs_by_id[right]["sha256"],
                },
            },
        )

    for document in documents:
        document_id = document["document_id"]
        source_rel = document["source_path"]
        for raw_link in raw_links_by_id.get(document_id, []):
            resolved = resolve_local_link(source_rel, raw_link, source_paths)
            if resolved:
                add_relation(
                    relations,
                    relation_seen,
                    {
                        "from": document_id,
                        "type": "explicit-local-link",
                        "to": source_to_id[resolved],
                        "basis": {"method": "literal-link-target", "value": raw_link},
                    },
                )
        related_lines = [
            line
            for line in extracted_by_id[document_id].text.splitlines()
            if re.search(r"(?i)related document|dokumen terkait", line)
        ]
        for line in related_lines:
            for match in re.finditer(r"([^;|]+\.(?:md|docx|xlsx|pdf|html|csv|json|mmd))", line, re.I):
                basename = Path(clean(match.group(1))).name.casefold()
                for target_id in by_basename.get(basename, []):
                    add_relation(
                        relations,
                        relation_seen,
                        {
                            "from": document_id,
                            "type": "explicit-related-document-filename",
                            "to": target_id,
                            "basis": {"method": "literal-filename-in-related-document-line", "value": clean(match.group(1))},
                        },
                    )

    catalog_path = source / "PRD/PRD Generator (.md) - Copy/prd-catalog.json"
    process_path = source / "PRD/PRD Generator (.md) - Copy/prd-paths-v2.json"
    catalog_data: dict[str, Any] = {}
    process_data: dict[str, Any] = {}
    catalog_entries: list[dict[str, Any]] = []
    process_entries: list[dict[str, Any]] = []
    catalog_by_id: dict[str, dict[str, Any]] = {}
    catalog_document_ids: dict[str, str] = {}
    if catalog_path.is_file():
        catalog_data = json.loads(catalog_path.read_text(encoding="utf-8-sig"))
        for entry in catalog_data.get("prds", []):
            item = dict(entry)
            source_rel = copy_prefix + entry.get("file", "")
            item["source_path"] = source_rel
            item["document_id"] = source_to_id.get(source_rel)
            catalog_entries.append(item)
            catalog_by_id[item["id"]] = item
            if item["document_id"]:
                catalog_document_ids[item["id"]] = item["document_id"]
    if process_path.is_file():
        process_data = json.loads(process_path.read_text(encoding="utf-8-sig"))
        for process in process_data.get("paths", []):
            item = {key: value for key, value in process.items() if key != "steps"}
            item["steps"] = []
            for position, step in enumerate(process.get("steps", []), 1):
                step_item = dict(step)
                step_item["position"] = position
                catalog_entry = catalog_by_id.get(step.get("prd_id", ""))
                if catalog_entry:
                    step_item["catalog_name"] = catalog_entry.get("name")
                    step_item["catalog_file"] = catalog_entry.get("file")
                    step_item["document_id"] = catalog_entry.get("document_id")
                    if catalog_entry.get("document_id"):
                        add_relation(
                            relations,
                            relation_seen,
                            {
                                "from": catalog_entry["document_id"],
                                "type": "explicit-process-step",
                                "to": "PROCESS-" + process["id"],
                                "basis": {
                                    "method": "prd-paths-v2.json",
                                    "process_id": process["id"],
                                    "position": position,
                                    "role": step.get("role"),
                                },
                            },
                        )
                item["steps"].append(step_item)
            source_flow = process.get("source_flow")
            if source_flow:
                flow_source_rel = copy_prefix + source_flow
                item["source_flow_source_path"] = flow_source_rel
                item["source_flow_document_id"] = source_to_id.get(flow_source_rel)
                if item["source_flow_document_id"]:
                    add_relation(
                        relations,
                        relation_seen,
                        {
                            "from": item["source_flow_document_id"],
                            "type": "explicit-process-source-flow",
                            "to": "PROCESS-" + process["id"],
                            "basis": {"method": "prd-paths-v2.json", "value": source_flow},
                        },
                    )
            process_entries.append(item)

    mermaid_flows: list[dict[str, Any]] = []
    for flow_file in sorted(source.rglob("*.mmd")):
        source_rel = flow_file.relative_to(source).as_posix()
        value = flow_file.read_text(encoding="utf-8-sig", errors="replace")
        edge_lines = [line.rstrip() for line in value.splitlines() if re.search(r"-->|==>|-\.->", line)]
        if source_rel.startswith(copy_prefix + "menu-flow/"):
            flow_kind = "menu-flow"
        elif "flowchart inventory" in source_rel.casefold():
            flow_kind = "inventory-flowchart"
        else:
            flow_kind = "mermaid"
        mermaid_flows.append(
            {
                "id": "MERMAID-FLOW-" + sha1_text(source_rel)[:12].upper(),
                "source_path": source_rel,
                "document_id": source_to_id.get(source_rel),
                "flow_kind": flow_kind,
                "edge_lines": edge_lines,
                "edge_line_count": len(edge_lines),
            }
        )

    relations.sort(key=lambda item: (item["from"], item["type"], item["to"], json.dumps(item.get("basis", {}), sort_keys=True)))
    relations_by_document: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for relation in relations:
        if relation["from"].startswith("DOC-"):
            relations_by_document[relation["from"]].append(relation)
        if relation["to"].startswith("DOC-"):
            reverse = dict(relation)
            reverse["from"], reverse["to"] = relation["to"], relation["from"]
            relations_by_document[relation["to"]].append(reverse)

    for document in documents:
        doc_dir = target / "documents" / document["document_id"]
        text_write(doc_dir / "content.md", extracted_by_id[document["document_id"]].markdown)
        structure = {
            "document_id": document["document_id"],
            "source_path": document["source_path"],
            "title": document["title"],
            "headings": document["headings"],
            "raw_links": raw_links_by_id.get(document["document_id"], []),
            "extractor_structure": extracted_by_id[document["document_id"]].structure,
        }
        json_write(doc_dir / "structure.json", structure)
        make_document_card(target, document, relations_by_document)

    manifest = {
        "schema_version": 1,
        "policy": {
            "original_files": "preserved-byte-for-byte",
            "derived_content": "literal-extraction-without-correction",
            "correlation": "deterministic-or-explicit-only",
        },
        "source_root": "source/original",
        "file_count": len(documents),
        "total_bytes": sum(item["bytes"] for item in documents),
        "documents": [
            {
                "document_id": item["document_id"],
                "content_id": item["content_id"],
                "source_path": item["source_path"],
                "bytes": item["bytes"],
                "sha256": item["sha256"],
                "generated_paths": item["generated_paths"],
                "media_paths": item["media_paths"],
                "rendered_paths": item["rendered_paths"],
            }
            for item in documents
        ],
    }
    json_write(target / "source/manifest.json", manifest)
    json_write(target / "catalog/document-index.json", {"schema_version": 1, "documents": documents})
    json_write(
        target / "catalog/correlation-index.json",
        {
            "schema_version": 1,
            "policy": "relations-are-mechanical-or-explicit; no-semantic-merge",
            "relation_count": len(relations),
            "relations": relations,
        },
    )
    json_write(
        target / "catalog/process-index.json",
        {
            "schema_version": 1,
            "explicit_process_source": process_path.relative_to(source).as_posix() if process_path.is_file() else None,
            "paths": process_entries,
            "mermaid_flows": mermaid_flows,
        },
    )
    json_write(
        target / "catalog/source-domain-feature-index.json",
        {
            "schema_version": 1,
            "source": catalog_path.relative_to(source).as_posix() if catalog_path.is_file() else None,
            "schema_version_from_source": catalog_data.get("schema_version"),
            "generated_at_from_source": catalog_data.get("generated_at"),
            "note_from_source": catalog_data.get("note"),
            "entries": catalog_entries,
        },
    )

    for process in process_entries:
        page = target / "processes" / "explicit" / f"{slugify(process['id'])}.md"
        lines = [
            f"# {process.get('name', process['id'])}",
            "",
            f"- ID: `{process['id']}`",
            f"- Category: `{process.get('category', '')}`",
            f"- Scenario: {process.get('scenario', '')}",
        ]
        if process.get("exclusive_group"):
            lines.append(f"- Exclusive group: `{process['exclusive_group']}`")
        if process.get("source_flow_document_id"):
            target_link = os.path.relpath(
                target / "documents" / process["source_flow_document_id"] / "index.md", page.parent
            ).replace(os.sep, "/")
            lines.append(f"- Source flow: {markdown_link(process.get('source_flow', ''), target_link)}")
        elif process.get("source_flow"):
            lines.append(f"- Source flow: `{process['source_flow']}`")
        lines.extend(["", "## Steps", ""])
        for step in process["steps"]:
            label = step.get("catalog_name") or step.get("prd_id")
            if step.get("document_id"):
                target_link = os.path.relpath(
                    target / "documents" / step["document_id"] / "index.md", page.parent
                ).replace(os.sep, "/")
                label_value = markdown_link(label, target_link)
            else:
                label_value = f"`{label}`"
            detail = f"role=`{step.get('role', '')}`"
            if step.get("note"):
                detail += f"; note={step['note']}"
            lines.append(f"{step['position']}. {label_value} — PRD ID=`{step.get('prd_id', '')}`; {detail}")
        text_write(page, "\n".join(lines).rstrip() + "\n")

    for flow in mermaid_flows:
        source_flow = source / flow["source_path"]
        page = target / "processes" / "mermaid" / (flow["source_path"] + ".md")
        page.parent.mkdir(parents=True, exist_ok=True)
        source_link = os.path.relpath(source_flow, page.parent).replace(os.sep, "/")
        value = source_flow.read_text(encoding="utf-8-sig", errors="replace")
        text_write(
            page,
            f"# {flow['source_path']}\n\n"
            f"- Mermaid Flow ID: `{flow['id']}`\n"
            f"- Flow kind: `{flow['flow_kind']}`\n"
            f"- Document ID: `{flow.get('document_id')}`\n"
            f"- Sumber: {markdown_link(flow['source_path'], source_link)}\n\n"
            "## Mermaid Asli\n\n```mermaid\n"
            + value.rstrip()
            + "\n```\n",
        )

    extension_counts = Counter(item["extension"] for item in documents)
    directory_groups: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in documents:
        directory_groups[item["source_directory"]].append(item)
    all_lines = ["# Semua Dokumen", ""]
    for item in sorted(documents, key=lambda entry: entry["source_path"].casefold()):
        all_lines.append(
            f"- {markdown_link(item['source_path'], f'../documents/{item["document_id"]}/index.md')} "
            f"— `{item['document_id']}` — `{item['extension']}` — `{item['bytes']}` byte"
        )
    text_write(target / "indexes/all-documents.md", "\n".join(all_lines) + "\n")

    format_lines = ["# Indeks Format", ""]
    for extension, count in sorted(extension_counts.items()):
        format_lines.append(f"## {extension}")
        format_lines.append("")
        format_lines.append(f"Jumlah file: `{count}`")
        format_lines.append("")
        for item in sorted((doc for doc in documents if doc["extension"] == extension), key=lambda entry: entry["source_path"].casefold()):
            format_lines.append(f"- {markdown_link(item['source_path'], f'../documents/{item["document_id"]}/index.md')}")
        format_lines.append("")
    text_write(target / "indexes/by-format.md", "\n".join(format_lines).rstrip() + "\n")

    directory_lines = ["# Indeks Direktori Sumber", ""]
    for directory, items in sorted(directory_groups.items()):
        directory_lines.extend([f"## {directory}", "", f"Jumlah file: `{len(items)}`", ""])
        for item in sorted(items, key=lambda entry: entry["source_path"].casefold()):
            directory_lines.append(f"- {markdown_link(item['source_path'], f'../documents/{item["document_id"]}/index.md')}")
        directory_lines.append("")
    text_write(target / "indexes/by-source-directory.md", "\n".join(directory_lines).rstrip() + "\n")

    def group_index(title: str, groups: dict[str, list[str]], filename: str, label: str) -> None:
        lines = [f"# {title}", ""]
        group_number = 0
        for key, group in sorted(groups.items()):
            if len(group) < 2:
                continue
            group_number += 1
            lines.extend([f"## Group {group_number}", "", f"- {label}: `{key}`", ""])
            for doc_id in sorted(group):
                item = docs_by_id[doc_id]
                lines.append(f"- {markdown_link(item['source_path'], f'../documents/{doc_id}/index.md')}")
            lines.append("")
        text_write(target / "indexes" / filename, "\n".join(lines).rstrip() + "\n")

    group_index("Konten Biner Identik", by_sha, "exact-duplicates.md", "SHA-256")
    group_index(
        "Teks Ekstraksi Ternormalisasi Identik",
        by_normalized_text,
        "normalized-text-duplicates.md",
        "SHA-256 teks ternormalisasi",
    )
    group_index(
        "Kelompok Nama File Mekanis",
        {key: value for key, value in by_filename_key.items() if len(value) <= 30},
        "mechanical-filename-groups.md",
        "Kunci mekanis",
    )

    used_prd_ids = {step["prd_id"] for process in process_entries for step in process["steps"]}
    coverage_lines = [
        "# Cakupan Katalog terhadap Path Eksplisit",
        "",
        f"- Jumlah entri katalog: `{len(catalog_entries)}`",
        f"- Jumlah PRD ID unik yang dipakai path: `{len(used_prd_ids)}`",
        f"- Jumlah entri katalog yang tidak dipakai path eksplisit: `{len(catalog_entries) - len(used_prd_ids)}`",
        "",
        "## Tidak Dipakai oleh Path Eksplisit",
        "",
    ]
    for entry in sorted((item for item in catalog_entries if item["id"] not in used_prd_ids), key=lambda item: item["id"]):
        if entry.get("document_id"):
            link = markdown_link(entry["id"], f"../documents/{entry['document_id']}/index.md")
        else:
            link = f"`{entry['id']}`"
        coverage_lines.append(f"- {link} — `{entry.get('file', '')}`")
    text_write(target / "indexes/catalog-path-coverage.md", "\n".join(coverage_lines).rstrip() + "\n")

    process_lines = ["# Indeks Alur Proses", "", "## Path Eksplisit", ""]
    for process in process_entries:
        process_lines.append(
            f"- {markdown_link(process.get('name', process['id']), f'explicit/{slugify(process["id"])}.md')} "
            f"— `{process['id']}` — `{process.get('category', '')}`"
        )
    process_lines.extend(["", "## Dokumen Mermaid", ""])
    for flow in mermaid_flows:
        process_lines.append(
            f"- {markdown_link(flow['source_path'], 'mermaid/' + flow['source_path'] + '.md')} "
            f"— `{flow['id']}` — `{flow['flow_kind']}` — edge lines=`{flow['edge_line_count']}`"
        )
    text_write(target / "processes/index.md", "\n".join(process_lines).rstrip() + "\n")

    process_graph = ["flowchart LR"]
    for process in process_entries:
        process_node = "P_" + slugify(process["id"]).replace("-", "_")
        process_graph.append(f'  {process_node}["{process["id"]}: {process.get("name", "")}"]')
        for step in process["steps"]:
            if not step.get("document_id"):
                continue
            document_node = "D_" + step["document_id"].replace("-", "_")
            label = (step.get("catalog_name") or step.get("prd_id") or "").replace('"', "'")
            process_graph.append(f'  {document_node}["{label}"]')
            process_graph.append(f'  {process_node} -->|"{step["position"]}:{step.get("role", "")}"| {document_node}')
    text_write(target / "graph/process-relations.mmd", "\n".join(process_graph).rstrip() + "\n")

    mirror_graph = ["flowchart LR", '  ORIGINAL["PRD Generator (.md)"]', '  COPY["PRD Generator (.md) - Copy"]']
    mirror_graph.append(f'  ORIGINAL -->|"common paths: {len(set(original_map) & set(copy_map))}"| COPY')
    mirror_graph.append(f'  ORIGINAL -->|"only original: {len(set(original_map) - set(copy_map))}"| O_ONLY["Only original"]')
    mirror_graph.append(f'  COPY -->|"only copy: {len(set(copy_map) - set(original_map))}"| C_ONLY["Only copy"]')
    text_write(target / "graph/generator-trees.mmd", "\n".join(mirror_graph) + "\n")

    text_write(
        target / "docs/context-preservation.md",
        """# Aturan Preservasi Konteks

- `source/original/` adalah salinan byte-for-byte dan tidak diubah oleh builder.
- `source/manifest.json` menyimpan ukuran dan SHA-256 setiap file.
- `documents/*/content.md` adalah ekstraksi literal untuk navigasi; dokumen asli tetap menjadi acuan.
- Builder tidak memperbaiki ejaan, judul, status, struktur, atau isi dokumen.
- Grup nama file memakai normalisasi mekanis dan tidak menyatakan bahwa dua dokumen mempunyai makna yang sama.
- Korelasi semantik tidak dibuat. Relasi hanya berasal dari hash, path mirror, link literal, nama file literal pada bagian dokumen terkait, `prd-catalog.json`, atau `prd-paths-v2.json`.
""",
    )
    text_write(
        target / "docs/correlation-rules.md",
        """# Aturan Korelasi

## same-binary-content

SHA-256 file sama.

## same-normalized-extracted-text

SHA-256 dari teks hasil ekstraksi setelah whitespace dirapatkan dan huruf dibuat casefold sama.

## same-mechanical-filename-key

Nama file dikelompokkan oleh aturan mekanis yang menghapus ekstensi, marker salinan, marker draft/final/fix/update/new, marker revisi/versi, dan tanda nomor salinan. Relasi ini bukan klaim kesamaan makna.

## generator-tree-counterpart

Path relatif sama pada `PRD Generator (.md)` dan `PRD Generator (.md) - Copy`.

## explicit-local-link

Target link literal dapat diresolusikan ke file lain dalam korpus.

## explicit-related-document-filename

Nama file literal terdapat pada baris `Related Document` atau `Dokumen Terkait` dan cocok dengan basename file dalam korpus.

## explicit-process-step

Relasi berasal langsung dari langkah pada `prd-paths-v2.json` melalui ID pada `prd-catalog.json`.

## explicit-process-source-flow

Relasi berasal langsung dari field `source_flow` pada `prd-paths-v2.json`.
""",
    )
    text_write(
        target / "docs/graphify.md",
        """# Graphify

Graphify mengindeks lapisan turunan Markdown/JSON sebagai navigasi. `source/original/` tidak diindeks untuk mencegah duplikasi dan karena berisi format biner. Hasil Graphify berada di `graphify-out/` dan dapat dibangun ulang.

```bash
/home/tamtech/neurovi-v2-dev/.venv/bin/graphify update /home/tamtech/neurovi-prd --no-cluster
```

Graphify tidak menjadi sumber fakta dan tidak boleh mengubah dokumen asli.
""",
    )

    readme = f"""# Neurovi PRD — Struktur Fakta dan Korelasi

Repositori ini mempertahankan seluruh dokumen sumber tanpa perubahan dan menyediakan lapisan navigasi turunan.

## Statistik

- File sumber: `{len(documents)}`
- Total byte sumber: `{sum(item['bytes'] for item in documents)}`
- Konten biner unik: `{len(by_sha)}`
- Teks ekstraksi nonkosong ternormalisasi unik: `{len(by_normalized_text)}`
- Entri katalog PRD eksplisit: `{len(catalog_entries)}`
- Path proses eksplisit: `{len(process_entries)}`
- Dokumen Mermaid: `{len(mermaid_flows)}`
- Relasi deterministik/eksplisit: `{len(relations)}`

## Struktur

- `source/original/`: salinan seluruh file sumber, byte-for-byte.
- `source/manifest.json`: hash dan ukuran untuk verifikasi preservasi.
- `documents/`: kartu dokumen, konten ekstraksi literal, dan struktur terdeteksi.
- `catalog/`: indeks dokumen, korelasi, katalog sumber, dan proses.
- `processes/`: indeks per alur yang berasal dari JSON dan Mermaid sumber.
- `indexes/`: tampilan berdasarkan path, format, duplikasi, nama mekanis, dan cakupan katalog.
- `graph/`: proyeksi Mermaid turunan.
- `graphify-out/`: proyeksi Graphify yang dapat dibangun ulang.

## Batasan

Tidak ada isi dokumen yang diperbaiki, diringkas secara menggantikan sumber, atau diberi status implementasi baru. Lihat [aturan preservasi](docs/context-preservation.md) dan [aturan korelasi](docs/correlation-rules.md).

## Tooling

Generator, validator, scanner, skill rekonsiliasi, command service, dan adapter
Discord berada di repository terpisah `neurovi-doc-reconciliator`. Repository
ini dipasang sebagai submodule `neurovi-prd/` di dalam tools repository tersebut.

```bash
python3 ../scripts/build_structure.py validate \\
  --source source/original \\
  --target .
```

Versi global dokumen, release manifest, commit, dan annotated tag dibuat pada
repository ini. Versi aplikasi tools dikelola secara terpisah.
"""
    text_write(target / "README.md", readme)
    text_write(
        target / "AGENTS.md",
        """# Repository Rules

- Never edit files under `source/original/`.
- Preserve source facts exactly; do not correct, remove, or add document claims.
- Treat generated correlations as mechanical or explicit only.
- Treat Graphify as rebuildable navigation, never as source truth.
- Run `<tools-root>/scripts/build_structure.py validate --source source/original --target .` after regeneration.

## Repository Skills

- Skills and executable tooling live in the parent `neurovi-doc-reconciliator` repository.
- When checked out as its submodule, read skills from `../.codex/skills/`.
- Never copy application or skill implementation into this document repository.
- Keep document baselines, reconciliation artifacts, release manifests, and global document tags in this repository.
""",
    )
    text_write(
        target / ".graphifyignore",
        """/source/original/
/source/media/
/source/rendered/
/graphify-out/
/.git/
/__pycache__/
*.docx
*.xlsx
*.pdf
*.png
*.jpg
*.jpeg
*.gif
*.webp
""",
    )
    text_write(target / ".gitignore", "graphify-out/\n__pycache__/\n*.pyc\n")

    validation = validate(source, target, quiet=True)
    json_write(target / "catalog/validation-report.json", validation)
    print(json.dumps({"status": "BUILT", **validation}, ensure_ascii=False, indent=2))


def validate(source: Path, target: Path, quiet: bool = False) -> dict[str, Any]:
    errors: list[str] = []
    manifest_path = target / "source/manifest.json"
    if not manifest_path.is_file():
        errors.append("source/manifest.json tidak ditemukan")
        result = {"valid": False, "errors": errors}
        if not quiet:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return result
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    documents = manifest.get("documents", [])
    actual_files = [path for path in source.rglob("*") if path.is_file()]
    if len(actual_files) != manifest.get("file_count"):
        errors.append(f"Jumlah file berbeda: actual={len(actual_files)} manifest={manifest.get('file_count')}")
    for item in documents:
        original = source / item["source_path"]
        if not original.is_file():
            errors.append(f"File sumber hilang: {item['source_path']}")
            continue
        raw = original.read_bytes()
        if len(raw) != item["bytes"]:
            errors.append(f"Ukuran berubah: {item['source_path']}")
        if sha256_bytes(raw) != item["sha256"]:
            errors.append(f"SHA-256 berubah: {item['source_path']}")
        for generated in item.get("generated_paths", {}).values():
            if not (target / generated).is_file():
                errors.append(f"Berkas turunan hilang: {generated}")
    for relative in (
        "catalog/document-index.json",
        "catalog/correlation-index.json",
        "catalog/process-index.json",
        "catalog/source-domain-feature-index.json",
    ):
        path = target / relative
        if not path.is_file():
            errors.append(f"Indeks hilang: {relative}")
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"JSON tidak valid {relative}: {exc}")
    worklist_path = target / "reconciliation/e2e-inventory/domain-worklist.json"
    if not worklist_path.is_file():
        errors.append("Inventaris E2E domain worklist hilang: reconciliation/e2e-inventory/domain-worklist.json")
    else:
        try:
            worklist = json.loads(worklist_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"JSON tidak valid reconciliation/e2e-inventory/domain-worklist.json: {exc}")
        else:
            if worklist.get("inventory_type") != "E2E_DOMAIN_WORKLIST":
                errors.append("Tipe inventaris E2E tidak valid")
            if worklist.get("eligible_file_count") != 212:
                errors.append(
                    f"Jumlah file PRD eligible tidak valid: {worklist.get('eligible_file_count')}"
                )
            if worklist.get("unique_prd_count") != 209:
                errors.append(
                    f"Jumlah PRD unik tidak valid: {worklist.get('unique_prd_count')}"
                )
            if worklist.get("assigned_unique_prd_count") != worklist.get("unique_prd_count"):
                errors.append("Tidak semua PRD unik memiliki owner domain")
            if worklist.get("unassigned_unique_prd_count") != 0:
                errors.append("Inventaris masih memiliki PRD tanpa owner domain")
            content_ids = [
                item.get("content_id", "")
                for domain in worklist.get("domains", [])
                for item in domain.get("documents", [])
            ]
            if len(content_ids) != len(set(content_ids)):
                errors.append("Satu PRD unik tercatat pada lebih dari satu owner domain")
            if len(content_ids) != worklist.get("unique_prd_count"):
                errors.append(
                    "Jumlah item domain worklist tidak sama dengan jumlah PRD unik"
                )
            known = set(content_ids)
            for relation in worklist.get("relations", []):
                if relation.get("source_content_id") not in known:
                    errors.append(
                        f"Relasi menunjuk source PRD tidak dikenal: {relation.get('relation_id')}"
                    )
                if relation.get("target_content_id") not in known:
                    errors.append(
                        f"Relasi menunjuk target PRD tidak dikenal: {relation.get('relation_id')}"
                    )
    result = {
        "valid": not errors,
        "source_file_count": len(actual_files),
        "manifest_file_count": manifest.get("file_count"),
        "checked_documents": len(documents),
        "errors": errors,
    }
    if not quiet:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a lossless, facts-only Neurovi PRD structure.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("build", "validate"):
        item = subparsers.add_parser(command)
        item.add_argument("--source", required=True, type=Path)
        item.add_argument("--target", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source.resolve()
    target = args.target.resolve()
    if args.command == "build":
        build(source, target)
        return 0
    result = validate(source, target)
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
