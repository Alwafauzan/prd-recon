from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping


class CapabilityError(RuntimeError):
    pass


class CapabilityExecutionError(CapabilityError):
    def __init__(self, capability: str, exit_code: int, message: str):
        super().__init__(message)
        self.capability = capability
        self.exit_code = exit_code


Builder = Callable[[Path, Path, Mapping[str, str]], list[str]]


@dataclass(frozen=True)
class CapabilitySpec:
    name: str
    description: str
    access: str
    parameters: tuple[str, ...]
    builder: Builder


@dataclass(frozen=True)
class ExecutionResult:
    capability: str
    output: str
    command: tuple[str, ...]


def _required(params: Mapping[str, str], key: str) -> str:
    value = params.get(key, "").strip()
    if not value:
        raise CapabilityError(f"Missing required parameter: {key}")
    return value


def _positive_int(params: Mapping[str, str], key: str, default: int) -> str:
    value = params.get(key, str(default)).strip()
    try:
        parsed = int(value)
    except ValueError as error:
        raise CapabilityError(f"Parameter {key} must be an integer.") from error
    if parsed < 1:
        raise CapabilityError(f"Parameter {key} must be positive.")
    return str(parsed)


def _script(repo: Path, relative: str) -> str:
    path = repo / relative
    if not path.is_file():
        raise CapabilityError(f"Capability script not found: {path}")
    return str(path)


def _show_prd(
    repo: Path, tools: Path, params: Mapping[str, str], document: bool
) -> list[str]:
    command = [
        sys.executable,
        _script(tools, ".codex/skills/neurovi-show-prd/scripts/show_prd.py"),
        "--repo",
        str(repo),
    ]
    if document:
        command.extend(["--document", _required(params, "document")])
        if params.get("section", "").strip():
            command.extend(["--section", params["section"].strip()])
    else:
        command.extend(["--limit", _positive_int(params, "limit", 50)])
        if params.get("query", "").strip():
            command.extend(["--query", params["query"].strip()])
    return command


def _show_e2e(
    repo: Path, tools: Path, params: Mapping[str, str], detail: bool
) -> list[str]:
    command = [
        sys.executable,
        _script(tools, ".codex/skills/neurovi-show-e2e/scripts/show_e2e.py"),
        "--repo",
        str(repo),
    ]
    if detail:
        command.extend(["--e2e", _required(params, "e2e")])
    else:
        command.extend(["--limit", _positive_int(params, "limit", 100)])
        for key, flag in (
            ("query", "--query"),
            ("group", "--group"),
            ("status", "--status"),
        ):
            if params.get(key, "").strip():
                command.extend([flag, params[key].strip()])
    return command


def _gap(
    repo: Path, tools: Path, params: Mapping[str, str], mode: str
) -> list[str]:
    command = [
        sys.executable,
        _script(tools, ".codex/skills/neurovi-gap-scanner/scripts/scan_gaps.py"),
        "--repo",
        str(repo),
    ]
    if mode == "e2e":
        command.extend(["--e2e", _required(params, "e2e")])
    elif mode == "prd":
        command.extend(["--document", _required(params, "document")])
    return command


def _inspect(
    repo: Path, tools: Path, params: Mapping[str, str], command_name: str
) -> list[str]:
    command = [
        sys.executable,
        _script(
            tools,
            ".codex/skills/neurovi-prd-reconciler/scripts/inspect_inventory.py",
        ),
        "--repo",
        str(repo),
        command_name,
    ]
    if command_name == "find-document":
        command.extend(["--query", _required(params, "query")])
    elif command_name == "scan-format":
        command.extend(["--document", _required(params, "document")])
    return command


def _version(
    repo: Path, tools: Path, params: Mapping[str, str], compare: bool
) -> list[str]:
    command = [
        sys.executable,
        _script(
            tools,
            ".codex/skills/neurovi-prd-reconciler/scripts/version_diff.py",
        ),
        "--repo",
        str(repo),
    ]
    if compare:
        command.extend(
            [
                "compare",
                "--from",
                _required(params, "from"),
                "--to",
                _required(params, "to"),
            ]
        )
    else:
        command.append("list")
    return command


def _validate(repo: Path, tools: Path, params: Mapping[str, str]) -> list[str]:
    del params
    return [
        sys.executable,
        _script(tools, "scripts/build_structure.py"),
        "validate",
        "--source",
        str(repo / "source/original"),
        "--target",
        str(repo),
    ]


CAPABILITIES: dict[str, CapabilitySpec] = {
    "prd.list": CapabilitySpec(
        "prd.list",
        "List original PRD records",
        "read",
        ("query", "limit"),
        lambda repo, tools, params: _show_prd(repo, tools, params, False),
    ),
    "prd.show": CapabilitySpec(
        "prd.show",
        "Display an immutable original PRD",
        "read",
        ("document", "section"),
        lambda repo, tools, params: _show_prd(repo, tools, params, True),
    ),
    "e2e.list": CapabilitySpec(
        "e2e.list",
        "List E2E inventory candidates",
        "read",
        ("query", "group", "status", "limit"),
        lambda repo, tools, params: _show_e2e(repo, tools, params, False),
    ),
    "e2e.show": CapabilitySpec(
        "e2e.show",
        "Display one E2E flow",
        "read",
        ("e2e",),
        lambda repo, tools, params: _show_e2e(repo, tools, params, True),
    ),
    "gap.list": CapabilitySpec(
        "gap.list",
        "List E2E flows with gap candidates",
        "read",
        (),
        lambda repo, tools, params: _gap(repo, tools, params, "list"),
    ),
    "gap.e2e": CapabilitySpec(
        "gap.e2e",
        "Scan cross-document gaps in one E2E",
        "read",
        ("e2e",),
        lambda repo, tools, params: _gap(repo, tools, params, "e2e"),
    ),
    "gap.prd": CapabilitySpec(
        "gap.prd",
        "Scan internal context gaps in one PRD",
        "read",
        ("document",),
        lambda repo, tools, params: _gap(repo, tools, params, "prd"),
    ),
    "inventory.find-prd": CapabilitySpec(
        "inventory.find-prd",
        "Find documents and E2E coverage",
        "read",
        ("query",),
        lambda repo, tools, params: _inspect(
            repo, tools, params, "find-document"
        ),
    ),
    "inventory.scan-format": CapabilitySpec(
        "inventory.scan-format",
        "Scan source PRD heading families",
        "read",
        ("document",),
        lambda repo, tools, params: _inspect(repo, tools, params, "scan-format"),
    ),
    "version.list": CapabilitySpec(
        "version.list",
        "List global repository versions",
        "read",
        (),
        lambda repo, tools, params: _version(repo, tools, params, False),
    ),
    "version.compare": CapabilitySpec(
        "version.compare",
        "Compare two global repository versions",
        "read",
        ("from", "to"),
        lambda repo, tools, params: _version(repo, tools, params, True),
    ),
    "repo.validate": CapabilitySpec(
        "repo.validate",
        "Validate original source preservation",
        "read",
        (),
        _validate,
    ),
}


class CapabilityRunner:
    def __init__(
        self, repo_root: Path, tools_root: Path, timeout_seconds: int = 120
    ):
        self.repo_root = repo_root.resolve()
        self.tools_root = tools_root.resolve()
        self.timeout_seconds = timeout_seconds

    def list(self) -> tuple[CapabilitySpec, ...]:
        return tuple(CAPABILITIES[name] for name in sorted(CAPABILITIES))

    def execute(
        self, name: str, params: Mapping[str, str] | None = None
    ) -> ExecutionResult:
        if name not in CAPABILITIES:
            raise CapabilityError(f"Unknown capability: {name}")
        spec = CAPABILITIES[name]
        command = spec.builder(self.repo_root, self.tools_root, params or {})
        try:
            completed = subprocess.run(
                command,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise CapabilityExecutionError(
                name,
                124,
                f"Capability timed out after {self.timeout_seconds} seconds.",
            ) from error
        if completed.returncode != 0:
            message = (completed.stderr or completed.stdout).strip()
            raise CapabilityExecutionError(name, completed.returncode, message)
        return ExecutionResult(name, completed.stdout, tuple(command))
