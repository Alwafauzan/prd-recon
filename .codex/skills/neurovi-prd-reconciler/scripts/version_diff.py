#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


class VersionDiffError(RuntimeError):
    pass


def default_repo() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / ".git").exists() and (parent / "AGENTS.md").is_file():
            return parent
    return Path.cwd()


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,
    )
    if result.returncode != 0:
        error = result.stderr.decode("utf-8", errors="replace").strip()
        raise VersionDiffError(error or f"git {' '.join(args)} failed")
    return result.stdout.decode("utf-8", errors="replace")


def verify_ref(repo: Path, ref: str) -> None:
    git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}")


def list_versions(repo: Path) -> list[dict[str, str]]:
    output = git(repo, "tag", "--list", "v[0-9]*", "--sort=v:refname", "--format=%(refname:short)%09%(objectname)%09%(contents:subject)")
    versions = []
    for line in output.splitlines():
        if not line.strip():
            continue
        fields = line.split("\t", 2)
        versions.append(
            {
                "version": fields[0],
                "object": fields[1] if len(fields) > 1 else "",
                "subject": fields[2] if len(fields) > 2 else "",
            }
        )
    return versions


def parse_name_status(raw: bytes) -> list[dict[str, Any]]:
    tokens = raw.decode("utf-8", errors="replace").split("\0")
    changes = []
    index = 0
    while index < len(tokens) and tokens[index]:
        status = tokens[index]
        index += 1
        if status.startswith(("R", "C")):
            if index + 1 >= len(tokens):
                raise VersionDiffError("Unexpected rename/copy diff output")
            old_path = tokens[index]
            new_path = tokens[index + 1]
            index += 2
            changes.append(
                {
                    "git_status": status,
                    "change_type": "RENAMED" if status.startswith("R") else "COPIED",
                    "old_path": old_path,
                    "new_path": new_path,
                }
            )
            continue
        if index >= len(tokens):
            raise VersionDiffError("Unexpected diff output")
        path = tokens[index]
        index += 1
        change_type = {
            "A": "ADDED",
            "D": "REMOVED",
            "M": "MODIFIED",
            "T": "TYPE_CHANGED",
            "U": "UNMERGED",
        }.get(status[:1], "OTHER")
        changes.append(
            {
                "git_status": status,
                "change_type": change_type,
                "old_path": path if change_type == "REMOVED" else "",
                "new_path": "" if change_type == "REMOVED" else path,
            }
        )
    return changes


def compare_versions(repo: Path, from_ref: str, to_ref: str) -> dict[str, Any]:
    verify_ref(repo, from_ref)
    verify_ref(repo, to_ref)
    result = subprocess.run(
        ["git", "diff", "--find-renames", "--name-status", "-z", f"{from_ref}..{to_ref}"],
        cwd=repo,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise VersionDiffError(result.stderr.decode("utf-8", errors="replace").strip())
    changes = parse_name_status(result.stdout)
    counts: dict[str, int] = {}
    for item in changes:
        counts[item["change_type"]] = counts.get(item["change_type"], 0) + 1
    return {
        "from_version": from_ref,
        "to_version": to_ref,
        "from_commit": git(repo, "rev-list", "-n", "1", from_ref).strip(),
        "to_commit": git(repo, "rev-list", "-n", "1", to_ref).strip(),
        "changed_file_count": len(changes),
        "change_counts": dict(sorted(counts.items())),
        "changes": changes,
    }


def print_markdown(result: Any) -> None:
    if isinstance(result, list):
        if not result:
            print("No global versions found.")
            return
        print("| version | object | subject |")
        print("|---|---|---|")
        for item in result:
            print(f"| {item['version']} | {item['object']} | {item['subject'].replace('|', '\\|')} |")
        return

    print(f"# {result['from_version']} -> {result['to_version']}")
    print()
    print(f"Changed files: `{result['changed_file_count']}`")
    print()
    print("| Type | Old path | New path |")
    print("|---|---|---|")
    for item in result["changes"]:
        old_path = item["old_path"].replace("|", "\\|") or "-"
        new_path = item["new_path"].replace("|", "\\|") or "-"
        print(f"| {item['change_type']} | {old_path} | {new_path} |")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare global Neurovi PRD Git versions")
    parser.add_argument("--repo", type=Path, default=default_repo())
    parser.add_argument("--json", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list", help="List global vX.Y.Z tags")
    compare = subparsers.add_parser("compare", help="Compare two released versions")
    compare.add_argument("--from", dest="from_ref", required=True)
    compare.add_argument("--to", dest="to_ref", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo = args.repo.resolve()
    try:
        if args.command == "list":
            result = list_versions(repo)
        else:
            result = compare_versions(repo, args.from_ref, args.to_ref)
    except (OSError, VersionDiffError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_markdown(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
