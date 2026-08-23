#!/usr/bin/env python3
"""Rename canonical PRD files to '<CODE> - <short title>.md' and resync references.

One-time, surgical migration from the bootstrap naming '<CODE>.md' to the
human-readable naming produced by canonical_prd_filename() in
bootstrap_prd_baseline.py. This is deliberately NOT a full rebuild: the
canonical files carry post-reconciliation additions (confirmed decision
sections, relation redirects) that a rebuild would destroy. Only link
targets, manifest path/checksum fields, and file names change; every
original payload stays byte-for-byte identical.

Safety checks (any failure aborts before anything is written):
  - every manifest document path resolves to an existing prds/*.md file
  - every recorded payload region matches the immutable source bytes
  - every new filename is unique
  - after edits, the payload is found exactly once per file

Use --dry-run to preview the rename map without writing anything.
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bootstrap_prd_baseline import canonical_prd_filename  # noqa: E402

CANONICAL_ROOT = Path("reconciliation/canonical")
MANIFEST_PATH = CANONICAL_ROOT / "manifest.json"
SOURCE_ROOT = Path("source/original")


def fail(message):
    sys.exit(f"ERROR: {message}")


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def load_repo(repo):
    manifest_raw = (repo / MANIFEST_PATH).read_bytes()
    manifest = json.loads(manifest_raw)
    documents = manifest.get("documents", [])
    if not documents:
        fail("manifest has no documents")

    rename_map = {}  # old basename -> new basename
    doc_info = {}
    for doc in documents:
        code = str(doc.get("document_code", ""))
        old_rel = str(doc.get("path", ""))
        old_name = Path(old_rel).name
        new_name = canonical_prd_filename(code, str(doc.get("original_title", "")))
        source_rel = str(doc.get("primary_source_path", ""))

        old_file = repo / old_rel
        source_file = repo / SOURCE_ROOT / source_rel
        if not old_file.is_file():
            fail(f"canonical file missing: {old_rel}")
        if not source_file.is_file():
            fail(f"immutable source missing: {source_rel}")

        content = old_file.read_bytes()
        payload = source_file.read_bytes()
        offset = doc.get("payload_offset")
        length = doc.get("payload_length")
        if not isinstance(offset, int) or not isinstance(length, int) or length != len(payload):
            fail(f"payload metadata invalid for {code}")
        if content[offset : offset + length] != payload:
            fail(f"recorded payload region does not match source for {code} (pre-check)")
        if content.count(payload) != 1:
            fail(f"payload occurs {content.count(payload)}x in {old_name} (must be exactly 1)")

        rename_map[old_name] = new_name
        doc_info[code] = {
            "doc": doc,
            "old_rel": old_rel,
            "old_name": old_name,
            "new_name": new_name,
            "payload": payload,
        }

    new_names = list(rename_map.values())
    if len(new_names) != len(set(new_names)):
        dupes = sorted({name for name in new_names if new_names.count(name) > 1})
        fail(f"new filenames are not unique: {dupes}")

    # every old basename must appear exactly once in the manifest (its path field)
    manifest_text = manifest_raw.decode("utf-8")
    for old_name in rename_map:
        count = manifest_text.count(old_name)
        if count != 1:
            fail(f"{old_name} appears {count}x in manifest.json (expected 1)")

    return manifest, manifest_raw, rename_map, doc_info


LINK_RE_TEMPLATE = r"\]\((<)?((?:[^()<>]*/)?){old}(#[^)>\s]*)?(>)?\)"


def rewrite_links(text, rename_map):
    """Replace link targets that end in an old basename with the new basename.
    New names contain spaces, so the angle-bracket form is always used."""
    total = 0
    for old_name, new_name in rename_map.items():
        if old_name == new_name:
            continue
        pattern = re.compile(LINK_RE_TEMPLATE.format(old=re.escape(old_name)))

        def repl(match):
            nonlocal total
            total += 1
            prefix = match.group(2) or ""
            anchor = match.group(3) or ""
            return f"](<{prefix}{new_name}{anchor}>)"

        text = pattern.sub(repl, text)
    return text, total


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", default="neurovi-prd", help="document repository path")
    parser.add_argument("--dry-run", action="store_true", help="print the rename map without writing")
    args = parser.parse_args()

    repo = Path(args.repo)
    if not repo.is_dir():
        fail(f"repository not found: {repo}")

    manifest, manifest_raw, rename_map, doc_info = load_repo(repo)
    changed = {old: new for old, new in rename_map.items() if old != new}
    print(f"documents: {len(rename_map)}, renames needed: {len(changed)}")
    for old, new in sorted(changed.items())[:10]:
        print(f"  {old}\n    -> {new}")
    if len(changed) > 10:
        print(f"  ... and {len(changed) - 10} more")
    if args.dry_run:
        print("dry-run: nothing written")
        return
    if not changed:
        print("nothing to do")
        return

    # 1. rewrite link targets in every canonical markdown file
    md_files = sorted((repo / CANONICAL_ROOT).glob("prds/*.md")) + sorted(
        (repo / CANONICAL_ROOT).glob("e2e/*.md")
    ) + [repo / CANONICAL_ROOT / "index.md"]
    total_links = 0
    payload_by_name = {info["old_name"]: info["payload"] for info in doc_info.values()}
    for md_file in md_files:
        raw = md_file.read_bytes()
        # regex substitution only rewrites link targets; every other byte
        # (including mixed LF/CRLF line endings) is preserved as-is
        text, count = rewrite_links(raw.decode("utf-8"), rename_map)
        if count:
            total_links += count
            new_raw = text.encode("utf-8")
            payload = payload_by_name.get(md_file.name)
            if payload is not None and new_raw.count(payload) != 1:
                fail(f"payload corrupted by link rewrite in {md_file.name} (abort before rename)")
            md_file.write_bytes(new_raw)
    print(f"link targets rewritten: {total_links}")

    # 2. rename prds files
    for info in doc_info.values():
        if info["old_name"] != info["new_name"]:
            (repo / info["old_rel"]).rename(repo / CANONICAL_ROOT / "prds" / info["new_name"])
    print(f"files renamed: {len(changed)}")

    # 3. resync manifest: path, payload_offset, generated_sha256 per document
    for info in doc_info.values():
        doc = info["doc"]
        new_file = repo / CANONICAL_ROOT / "prds" / info["new_name"]
        content = new_file.read_bytes()
        occurrences = content.count(info["payload"])
        if occurrences != 1:
            fail(f"payload occurs {occurrences}x in {info['new_name']} after edits")
        doc["path"] = (CANONICAL_ROOT / "prds" / info["new_name"]).as_posix()
        doc["payload_offset"] = content.find(info["payload"])
        doc["generated_sha256"] = sha256_bytes(content)

    # e2e context files were not renamed, but their prd links were rewritten,
    # so their recorded checksums must be resynced as well
    e2e_updated = 0
    for context in manifest.get("e2e_contexts", []):
        content = (repo / str(context.get("path", ""))).read_bytes()
        sha = sha256_bytes(content)
        if context.get("generated_sha256") != sha:
            context["generated_sha256"] = sha
            e2e_updated += 1

    dumped = json.dumps(manifest, indent=2, ensure_ascii=False).replace("\n", "\r\n") + "\r\n"
    (repo / MANIFEST_PATH).write_bytes(dumped.encode("utf-8"))
    print(f"manifest.json resynced (e2e checksums: {e2e_updated})")
    print("done")


if __name__ == "__main__":
    main()
