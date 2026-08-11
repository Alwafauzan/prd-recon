from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from neurovi_prd_server.capabilities import CapabilityError, CapabilityRunner
from neurovi_prd_server.config import ConfigurationError, Settings


def _params(values: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise CapabilityError(f"Parameters must use key=value: {value}")
        key, item = value.split("=", 1)
        if not key.strip():
            raise CapabilityError(f"Parameter key is empty: {value}")
        result[key.strip()] = item
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Neurovi PRD command service")
    parser.add_argument("--repo", type=Path, help="Neurovi PRD repository root")
    parser.add_argument(
        "--tools-root", type=Path, help="Neurovi document reconciliator root"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    capabilities = subparsers.add_parser(
        "capabilities", help="List available commands"
    )
    capabilities.add_argument("--json", action="store_true")

    run = subparsers.add_parser("run", help="Execute one deterministic capability")
    run.add_argument("capability")
    run.add_argument("--param", action="append", default=[], help="key=value")

    health = subparsers.add_parser("health", help="Check repository availability")
    health.add_argument("--deep", action="store_true", help="Run source validation")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        settings = Settings.from_env(args.repo, args.tools_root)
        settings.require_repository()
        settings.require_tools()
        runner = CapabilityRunner(
            settings.repo_root,
            settings.tools_root,
            settings.command_timeout_seconds,
        )
        if args.command == "capabilities":
            rows = [
                {
                    "name": spec.name,
                    "description": spec.description,
                    "access": spec.access,
                    "parameters": list(spec.parameters),
                }
                for spec in runner.list()
            ]
            if args.json:
                print(json.dumps(rows, ensure_ascii=False, indent=2))
            else:
                for row in rows:
                    params = ", ".join(row["parameters"]) or "-"
                    print(
                        f"{row['name']} | {row['access']} | {params} | "
                        f"{row['description']}"
                    )
            return 0
        if args.command == "health":
            if args.deep:
                print(runner.execute("repo.validate").output, end="")
            else:
                print(f"healthy: {settings.repo_root}")
            return 0
        print(runner.execute(args.capability, _params(args.param)).output, end="")
        return 0
    except (ConfigurationError, CapabilityError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
