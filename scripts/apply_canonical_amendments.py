#!/usr/bin/env python3
"""Apply user-confirmed reconciliation amendments to canonical PRDs.

Reads an amendment spec (default ``reconciliation/amendments/E2E-RJ.json`` in
the document repository) and rewrites the listed canonical PRD files in place:

- header note lines are switched from "preserved byte-for-byte" to
  ``DECISION_APPLIED`` provenance;
- the ``SOURCE_CONTENT_BEGIN`` marker gains ``amendment_status=DECISION_APPLIED``;
- every spec edit replaces an exact anchor that must occur exactly once in the
  payload region (between the BEGIN marker and the reconciliation footer);
- the footer disclaimer is updated and optional footer rows are appended;
- ``reconciliation/canonical/manifest.json`` is resynced (payload offset,
  payload length, generated checksum, per-document ``amendment`` block).

The script is strict: any anchor that is missing or ambiguous aborts the run
before any file is written. Rerunning after a successful apply fails loudly
because the original anchors no longer exist (amendments are not idempotent).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MANIFEST_PATH = Path("reconciliation/canonical/manifest.json")

HEADER_NOTE_FIND = (
    "> Canonical bootstrap version 0. Formatting metadata is generated without changing source meaning.\n"
    "> The complete original Markdown payload below is preserved byte-for-byte from the primary source."
)
HEADER_NOTE_REPLACE = (
    "> Canonical bootstrap version 0, amended by user-confirmed reconciliation decisions.\n"
    "> The payload below has been amended at decision-backed conflict points (status: `DECISION_APPLIED`); "
    "every change is traced to `{spec_ref}`. The unamended original payload remains preserved at the "
    "primary source path (Original SHA-256) and in Git history."
)
SEMANTIC_CHANGES_FIND = "| Semantic changes | `NONE` |"
SEMANTIC_CHANGES_REPLACE = "| Semantic changes | `DECISION_APPLIED` (`{spec_ref}`) |"
MARKER_PATTERN = re.compile(r"(<!-- SOURCE_CONTENT_BEGIN document_id=\S+ sha256=[0-9a-f]+) -->")
FOOTER_DISCLAIMER_FIND = (
    "> The following entries are reconciliation metadata layered on top of the preserved original payload "
    "above. They do not alter, remove, or reinterpret any source statement; they record user-confirmed "
    "decisions, open gaps, and deferrals with full traceability to "
    "`reconciliation/workspaces/E2E-RJ/sessions/*/decision-register.csv` and `defect-register.csv`. "
    "Global repository version: `UNRELEASED` pending `BASELINE_APPROVAL`."
)
FOOTER_DISCLAIMER_REPLACE = (
    "> The following entries record the user-confirmed reconciliation decisions for this document. Since "
    "`{target_version}`, these decisions are **applied in place** at the conflict points in the payload "
    "above (marked `[DIPUTUSKAN: ...]`, `[Dikonfirmasi: ...]`, or `[GAP TERBUKA: ...]`); the unamended "
    "original payload remains preserved at the primary source path and in Git history. Full traceability: "
    "`reconciliation/workspaces/E2E-RJ/sessions/*/decision-register.csv`, `defect-register.csv`, and "
    "`{spec_ref}`. Global repository version: `{target_version}` (`BASELINE_APPROVAL`: `DEC-GLOBAL-002`)."
)


class AmendmentError(Exception):
    """Raised when an amendment cannot be applied safely."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def atomic_write(path: Path, value: bytes) -> None:
    temporary = path.with_name(path.name + ".tmp-amend")
    temporary.write_bytes(value)
    os.replace(temporary, path)


def replace_once(region: str, find: str, replace: str, *, context: str) -> str:
    count = region.count(find)
    if count != 1:
        raise AmendmentError(
            f"{context}: anchor occurs {count} times (expected 1): {find[:120]!r}"
        )
    return region.replace(find, replace, 1)


def split_document(text: str, *, path: str) -> tuple[str, str, str]:
    """Split canonical text into (header, payload, footer) regions.

    Works on the raw decoded text so each region keeps its original line
    endings (canonical files mix a CRLF wrapper/footer with an LF or CRLF
    byte-identical payload).
    """
    marker = text.find("<!-- SOURCE_CONTENT_BEGIN")
    if marker < 0:
        raise AmendmentError(f"{path}: SOURCE_CONTENT_BEGIN marker missing")
    line_end = text.find("-->", marker) + 3
    if text[line_end : line_end + 4] == "\r\n\r\n":
        payload_start = line_end + 4
    elif text[line_end : line_end + 2] == "\n\n":
        payload_start = line_end + 2
    else:
        raise AmendmentError(f"{path}: unexpected bytes after SOURCE_CONTENT_BEGIN marker")
    heading = text.find("## Reconciliation Decisions Applied")
    if heading < 0:
        raise AmendmentError(f"{path}: reconciliation footer heading missing")
    prefix = text[:heading]
    if not prefix.rstrip().endswith("---"):
        raise AmendmentError(f"{path}: footer separator (---) missing before heading")
    cut = prefix.rfind("---")
    return text[:payload_start], text[payload_start:cut], text[cut:]


def region_eol(region: str) -> str:
    return "\r\n" if "\r\n" in region else "\n"


def encode_region(region: str) -> bytes:
    return region.encode("utf-8")


def apply_document(
    *,
    repo: Path,
    spec_ref: str,
    target_version: str,
    document: dict[str, Any],
) -> dict[str, Any]:
    path = repo / str(document["path"])
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    header, payload, footer = split_document(text, path=str(document["path"]))

    # Replacements are authored with "\n"; apply them on a normalized copy of
    # each region, then convert back to that region's own line endings so
    # untouched bytes (including the byte-identical source payload) survive.
    def edit_region(region: str, edits: list[tuple[str, str, str]]) -> str:
        eol = region_eol(region)
        normalized = region.replace("\r\n", "\n")
        for find, replace, context in edits:
            normalized = replace_once(normalized, find, replace, context=context)
        return normalized.replace("\n", eol)

    code = str(document["document_code"])
    header = edit_region(
        header,
        [
            (
                HEADER_NOTE_FIND,
                HEADER_NOTE_REPLACE.format(spec_ref=spec_ref),
                f"{code} header note",
            ),
            (
                SEMANTIC_CHANGES_FIND,
                SEMANTIC_CHANGES_REPLACE.format(spec_ref=spec_ref),
                f"{code} semantic changes row",
            ),
        ],
    )
    header, marker_count = MARKER_PATTERN.subn(r"\1 amendment_status=DECISION_APPLIED -->", header)
    if marker_count != 1:
        raise AmendmentError(f"{code}: SOURCE_CONTENT_BEGIN marker update matched {marker_count} times")

    payload = edit_region(
        payload,
        [
            (str(edit["find"]), str(edit["replace"]), f"{code} edit {edit.get('edit_id')}")
            for edit in document.get("edits", [])
        ],
    )
    footer = edit_region(
        footer,
        [
            (
                FOOTER_DISCLAIMER_FIND,
                FOOTER_DISCLAIMER_REPLACE.format(spec_ref=spec_ref, target_version=target_version),
                f"{code} footer disclaimer",
            ),
        ]
        + [
            (str(edit["find"]), str(edit["replace"]), f"{code} footer edit {edit.get('edit_id')}")
            for edit in document.get("footer_appends", [])
        ],
    )

    header_bytes = encode_region(header)
    payload_bytes = encode_region(payload)
    footer_bytes = encode_region(footer)
    generated = header_bytes + payload_bytes + footer_bytes
    atomic_write(path, generated)

    return {
        "payload_offset": len(header_bytes),
        "payload_length": len(payload_bytes),
        "generated_sha256": sha256_bytes(generated),
        "amended_payload_sha256": sha256_bytes(payload_bytes),
    }


def apply(repo: Path, spec_path: Path) -> dict[str, Any]:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec_ref = spec_path.relative_to(repo).as_posix()
    target_version = str(spec.get("target_repository_version", "UNRELEASED"))
    manifest_file = repo / MANIFEST_PATH
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    documents_by_code = {
        str(item.get("document_code", "")): item for item in manifest.get("documents", [])
    }

    applied: list[dict[str, Any]] = []
    staged: list[tuple[dict[str, Any], dict[str, Any]]] = []
    # Stage all document rewrites first so a failure aborts before the manifest
    # is touched; file writes happen per document but manifest is written last.
    for document in spec.get("documents", []):
        code = str(document["document_code"])
        if code not in documents_by_code:
            raise AmendmentError(f"{code}: not present in canonical manifest")
        result = apply_document(
            repo=repo, spec_ref=spec_ref, target_version=target_version, document=document
        )
        staged.append((document, result))

    applied_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for document, result in staged:
        code = str(document["document_code"])
        item = documents_by_code[code]
        item["payload_offset"] = result["payload_offset"]
        item["payload_length"] = result["payload_length"]
        item["generated_sha256"] = result["generated_sha256"]
        item["semantic_changes"] = "DECISION_APPLIED"
        item["amendment"] = {
            "status": "DECISION_APPLIED",
            "amendment_set_id": str(spec.get("amendment_set_id", "")),
            "spec_path": spec_ref,
            "decision_ids": [str(d) for d in document.get("decision_ids", [])],
            "defect_ids": [str(d) for d in document.get("defect_ids", [])],
            "amended_payload_sha256": result["amended_payload_sha256"],
            "applied_at": applied_at,
        }
        applied.append(
            {
                "document_code": code,
                "edits_applied": len(document.get("edits", []))
                + len(document.get("footer_appends", [])),
                "decision_ids": item["amendment"]["decision_ids"],
                "defect_ids": item["amendment"]["defect_ids"],
            }
        )

    manifest["semantic_changes"] = (
        f"DECISION_APPLIED ({len(applied)} documents — see {spec_ref})"
    )
    manifest_bytes = (
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    ).encode("utf-8").replace(b"\n", b"\r\n")
    atomic_write(manifest_file, manifest_bytes)

    return {
        "amendment_set_id": str(spec.get("amendment_set_id", "")),
        "applied_at": applied_at,
        "documents": applied,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="Path to the neurovi-prd repository")
    parser.add_argument(
        "--spec",
        default=None,
        help="Amendment spec path (default: <repo>/reconciliation/amendments/E2E-RJ.json)",
    )
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()
    spec_path = Path(args.spec).resolve() if args.spec else repo / "reconciliation" / "amendments" / "E2E-RJ.json"
    try:
        report = apply(repo, spec_path)
    except AmendmentError as exc:
        print(json.dumps({"applied": False, "error": str(exc)}, indent=2, ensure_ascii=False))
        return 1
    print(json.dumps({"applied": True, **report}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
