#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any


class ShowPrdError(RuntimeError):
    def __init__(self, message: str, candidates: list[dict[str, Any]] | None = None):
        super().__init__(message)
        self.candidates = candidates or []


TEXT_EXTENSIONS = {
    ".csv",
    ".html",
    ".htm",
    ".json",
    ".md",
    ".rst",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.findall(r"[a-z0-9]+", value))


def repo_path(value: str) -> str:
    normalized = value.replace("\\", "/").strip()
    marker = "source/original/"
    if marker in normalized:
        normalized = normalized.split(marker, 1)[1]
    return normalized.strip("/")


def load_documents(repo: Path) -> list[dict[str, Any]]:
    index_path = repo / "catalog" / "document-index.json"
    if not index_path.is_file():
        raise ShowPrdError(f"Document index not found: {index_path}")
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    documents = payload.get("documents")
    if not isinstance(documents, list):
        raise ShowPrdError(f"Invalid document index: {index_path}")
    return documents


def candidate_view(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_id": document["document_id"],
        "title": document.get("title", ""),
        "source_path": f"source/original/{document['source_path']}",
        "extension": document.get("extension", ""),
    }


def searchable_values(document: dict[str, Any]) -> list[str]:
    source_path = document.get("source_path", "")
    path = Path(source_path)
    return [
        document.get("document_id", ""),
        document.get("title", ""),
        source_path,
        path.name,
        path.stem,
    ]


def resolve_document(documents: list[dict[str, Any]], selector: str) -> dict[str, Any]:
    selector = selector.strip()
    if not selector:
        raise ShowPrdError("Document selector is empty.")

    exact_id = [
        document
        for document in documents
        if document.get("document_id", "").casefold() == selector.casefold()
    ]
    if exact_id:
        return exact_id[0]

    normalized_selector = normalize(repo_path(selector))
    exact = []
    for document in documents:
        values = searchable_values(document)
        if any(normalize(repo_path(value)) == normalized_selector for value in values if value):
            exact.append(document)
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        raise ShowPrdError(
            f"Document selector is ambiguous: {selector}",
            [candidate_view(document) for document in exact],
        )

    tokens = normalized_selector.split()
    partial = []
    for document in documents:
        haystack = normalize(" ".join(searchable_values(document)))
        if normalized_selector in haystack or (tokens and all(token in haystack for token in tokens)):
            partial.append(document)
    if len(partial) == 1:
        return partial[0]
    if len(partial) > 1:
        raise ShowPrdError(
            f"Document selector is ambiguous: {selector}",
            [candidate_view(document) for document in partial[:50]],
        )
    raise ShowPrdError(f"Original document not found: {selector}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_content(repo: Path, document: dict[str, Any]) -> tuple[str, str, Path]:
    source = repo / "source" / "original" / document["source_path"]
    if not source.is_file():
        raise ShowPrdError(f"Original source file not found: {source}")

    actual_sha = sha256(source)
    indexed_sha = document.get("sha256")
    if indexed_sha and actual_sha != indexed_sha:
        raise ShowPrdError(
            "Source checksum does not match catalog. Regenerate and validate repository "
            "artifacts before displaying generated extraction content."
        )

    extension = document.get("extension", source.suffix).casefold()
    if extension in TEXT_EXTENSIONS:
        return (
            source.read_text(encoding="utf-8-sig", errors="replace"),
            "direct-original-text",
            source,
        )

    generated = document.get("generated_paths", {}).get("content")
    if not generated:
        raise ShowPrdError(f"No literal extraction registered for {document['document_id']}")
    content_path = repo / generated
    if not content_path.is_file():
        raise ShowPrdError(f"Literal extraction not found: {content_path}")
    return (
        content_path.read_text(encoding="utf-8"),
        "literal-binary-extraction",
        content_path,
    )


def resolve_section(
    content: str, document: dict[str, Any], selector: str
) -> tuple[str, dict[str, Any]]:
    headings = document.get("headings") or []
    if not headings:
        raise ShowPrdError(
            f"No detected headings are available for {document['document_id']}; "
            "show the full literal content instead."
        )

    target = normalize(selector)
    exact = [heading for heading in headings if normalize(heading.get("text", "")) == target]
    matches = exact or [
        heading for heading in headings if target in normalize(heading.get("text", ""))
    ]
    if not matches:
        raise ShowPrdError(
            f"Section not found: {selector}",
            [
                {
                    "level": heading.get("level"),
                    "heading": heading.get("text"),
                    "line": heading.get("line"),
                }
                for heading in headings
            ],
        )
    if len(matches) > 1:
        raise ShowPrdError(
            f"Section selector is ambiguous: {selector}",
            [
                {
                    "level": heading.get("level"),
                    "heading": heading.get("text"),
                    "line": heading.get("line"),
                }
                for heading in matches
            ],
        )

    selected = matches[0]
    selected_index = headings.index(selected)
    start_line = max(int(selected.get("line", 1)) - 1, 0)
    end_line = None
    selected_level = int(selected.get("level", 1))
    for heading in headings[selected_index + 1 :]:
        if int(heading.get("level", 1)) <= selected_level:
            end_line = max(int(heading.get("line", 1)) - 1, start_line + 1)
            break

    lines = content.splitlines(keepends=True)
    expected = normalize(selected.get("text", ""))
    if start_line >= len(lines) or expected not in normalize(lines[start_line]):
        matching_lines = [
            index
            for index, line in enumerate(lines)
            if normalize(re.sub(r"^\s*#+\s*", "", line)) == expected
        ]
        if not matching_lines:
            raise ShowPrdError(
                f"Detected heading boundary could not be located in literal content: {selector}"
            )
        offset = matching_lines[0] - start_line
        start_line += offset
        if end_line is not None:
            end_line += offset

    section_content = "".join(lines[start_line:end_line]).rstrip() + "\n"
    return section_content, selected


def list_documents(
    documents: list[dict[str, Any]], query: str | None, limit: int
) -> dict[str, Any]:
    matches = documents
    if query:
        tokens = normalize(query).split()
        matches = [
            document
            for document in matches
            if all(
                token in normalize(" ".join(searchable_values(document))) for token in tokens
            )
        ]
    matches = sorted(matches, key=lambda document: document.get("source_path", "").casefold())
    visible = matches[:limit]
    return {
        "mode": "inventory",
        "query": query,
        "total_matches": len(matches),
        "shown": len(visible),
        "documents": [candidate_view(document) for document in visible],
    }


def render_inventory(payload: dict[str, Any]) -> str:
    lines = [
        "Original document inventory",
        f"Matches: {payload['total_matches']}; shown: {payload['shown']}",
    ]
    if payload.get("query"):
        lines.append(f"Query: {payload['query']}")
    lines.append("")
    for document in payload["documents"]:
        lines.append(
            f"- {document['document_id']} | {document['title']} | {document['source_path']}"
        )
    if payload["shown"] < payload["total_matches"]:
        lines.extend(
            [
                "",
                "Result truncated. Use --query or increase --limit to narrow or expand it.",
            ]
        )
    return "\n".join(lines) + "\n"


def render_document(payload: dict[str, Any]) -> str:
    metadata = payload["document"]
    lines = [
        f"Document ID: {metadata['document_id']}",
        f"Title: {metadata['title']}",
        f"Original path: {metadata['source_path']}",
        f"Format: {metadata['extension']}",
        f"SHA-256: {metadata['sha256']}",
        f"Representation: {payload['representation']}",
    ]
    if payload.get("section"):
        lines.append(f"Section: {payload['section']['heading']}")
    lines.extend(["", "--- ORIGINAL PRD CONTENT ---", "", payload["content"]])
    return "\n".join(lines)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Display immutable original Neurovi PRD content."
    )
    result.add_argument("selector", nargs="?", help="Document code, name, filename, or path")
    result.add_argument("--document", help="Document code, name, filename, or path")
    result.add_argument("--section", help="Exact or unambiguous detected heading")
    result.add_argument("--query", help="Filter no-parameter inventory")
    result.add_argument("--limit", type=int, default=50, help="Inventory result limit")
    result.add_argument("--json", action="store_true", help="Emit JSON")
    result.add_argument("--repo", type=Path, default=Path.cwd(), help="Repository root")
    return result


def main() -> int:
    args = parser().parse_args()
    repo = args.repo.resolve()
    try:
        if args.limit < 1:
            raise ShowPrdError("--limit must be at least 1.")
        documents = load_documents(repo)
        selector = args.document or args.selector
        if args.document and args.selector:
            raise ShowPrdError("Use either a positional selector or --document, not both.")
        if not selector:
            if args.section:
                raise ShowPrdError("--section requires a document selector.")
            payload = list_documents(documents, args.query, args.limit)
            print(
                json.dumps(payload, ensure_ascii=False, indent=2)
                if args.json
                else render_inventory(payload),
                end="",
            )
            return 0

        document = resolve_document(documents, selector)
        content, representation, content_path = read_content(repo, document)
        section = None
        if args.section:
            content, selected = resolve_section(content, document, args.section)
            section = {
                "heading": selected.get("text"),
                "level": selected.get("level"),
                "line": selected.get("line"),
            }
        payload = {
            "mode": "document",
            "document": candidate_view(document)
            | {
                "mime_type": document.get("mime_type"),
                "bytes": document.get("bytes"),
                "sha256": document.get("sha256"),
            },
            "representation": representation,
            "content_path": str(content_path.relative_to(repo)),
            "section": section,
            "content": content,
        }
        print(
            json.dumps(payload, ensure_ascii=False, indent=2)
            if args.json
            else render_document(payload),
            end="",
        )
        return 0
    except (OSError, json.JSONDecodeError, ShowPrdError) as error:
        candidates = error.candidates if isinstance(error, ShowPrdError) else []
        payload = {"error": str(error), "candidates": candidates}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"Error: {error}", file=sys.stderr)
            for candidate in candidates:
                if "document_id" in candidate:
                    print(
                        f"- {candidate['document_id']} | {candidate['title']} | "
                        f"{candidate['source_path']}",
                        file=sys.stderr,
                    )
                else:
                    print(
                        f"- level {candidate.get('level')} | {candidate.get('heading')} | "
                        f"line {candidate.get('line')}",
                        file=sys.stderr,
                    )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
