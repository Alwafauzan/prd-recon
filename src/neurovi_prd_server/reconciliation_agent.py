from __future__ import annotations

import csv
import hashlib
import json
import logging
import re
import subprocess
import sys
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping, Protocol

from neurovi_prd_server.config import Settings
from neurovi_prd_server.help_system import (
    CONTEXTUAL_HELP_SYSTEM_PROMPT,
    render_contextual_help,
)
from neurovi_prd_server.llm_client import LLMError, LLMResult


LOGGER = logging.getLogger("neurovi_prd_server.reconciliation")


class ReconciliationAgentError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


class LLMClient(Protocol):
    def complete(self, system_prompt: str, user_prompt: str) -> LLMResult: ...


RECONCILIATION_CAPABILITIES = frozenset(
    {
        "reconcile.start",
        "reconcile.answer",
        "reconcile.control",
        "reconcile.add-reference",
        "reconcile.decide",
        "reconcile.status",
        "reconcile.finish",
    }
)
HELP_CAPABILITY = "help.answer"
AGENT_CAPABILITIES = RECONCILIATION_CAPABILITIES | {HELP_CAPABILITY}

SESSION_TERMINAL_STATUSES = frozenset({"FINISHED", "PUBLISHED"})
INTERVIEW_CONTROL_STATUSES = {
    "SKIP": "SKIPPED_BY_USER",
    "DEFER": "DEFERRED",
    "UNKNOWN": "UNKNOWN",
}
SELECTION_STATUSES = frozenset(
    {"CONFIRMED_INCLUDE", "CONTEXT_ONLY", "TAKE_OFF", "DEFERRED"}
)
RELATIONSHIP_ROLES = frozenset(
    {
        "PRIMARY_SCOPE",
        "UPSTREAM",
        "DOWNSTREAM",
        "INTEGRATION",
        "CONTEXT",
        "SHARED_CROSS_E2E",
        "EXCLUDED",
    }
)
DECISION_TYPES = frozenset(
    {
        "E2E_SELECTION",
        "DOCUMENT_INCLUDE",
        "DOCUMENT_TAKE_OFF",
        "DOCUMENT_ROLE",
        "DOCUMENT_RENAME",
        "DOCUMENT_CODE",
        "DOMAIN_PLACEMENT",
        "RELATION_CONFIRMATION",
        "INTERVIEW_ANSWER",
        "ANSWER_CORRELATION",
        "GAP_CLOSURE",
        "GAP_RESOLUTION",
        "CONFLICT_RESOLUTION",
        "BASELINE_APPROVAL",
        "USER_OVERRIDE",
    }
)
MODEL_STATUSES = frozenset(
    {"AWAITING_USER", "IN_PROGRESS", "READY_FOR_BASELINE_REVIEW", "BLOCKED"}
)

REGISTER_HEADERS = {
    "document-selection.csv": (
        "selection_id",
        "e2e_code",
        "document_id",
        "original_title",
        "original_path",
        "content_id",
        "proposed_document_code",
        "proposed_title",
        "relationship_role",
        "evidence_type",
        "evidence_reference",
        "selection_status",
        "decision_id",
        "notes",
    ),
    "context-trace.csv": (
        "trace_id",
        "e2e_code",
        "stage_code",
        "from_document_id",
        "to_document_id",
        "relationship_role",
        "input_or_trigger",
        "output_or_result",
        "logical_entity",
        "identifier",
        "status_or_condition",
        "evidence_type",
        "evidence_reference",
        "approval_status",
        "decision_id",
        "notes",
    ),
    "reference-register.csv": (
        "reference_id",
        "session_id",
        "original_filename",
        "original_path",
        "stored_path",
        "sha256",
        "supplied_by",
        "added_at",
        "proposed_e2e_codes",
        "format_scan_status",
        "relationship_scan_status",
        "decision_id",
        "notes",
    ),
    "defect-register.csv": (
        "defect_id",
        "e2e_code",
        "document_ids",
        "defect_type",
        "summary",
        "evidence_references",
        "affected_flow_or_data",
        "impact",
        "decision_question",
        "status",
        "resolution_decision_id",
        "notes",
    ),
    "interview-register.csv": (
        "question_id",
        "e2e_code",
        "defect_ids",
        "document_ids",
        "flow_or_handoff",
        "question",
        "why_needed",
        "asked_at",
        "status",
        "user_answer",
        "answered_at",
        "answer_evidence",
        "notes",
    ),
    "answer-correlation.csv": (
        "correlation_id",
        "source_question_id",
        "source_answer_reference",
        "target_question_id",
        "target_defect_ids",
        "correlation_basis",
        "supporting_evidence",
        "contradicting_evidence",
        "proposed_resolution_options",
        "recommended_option",
        "recommendation_reason",
        "scope_impact",
        "data_integrity_impact",
        "user_confirmation",
        "status",
        "decision_id",
        "notes",
    ),
    "decision-register.csv": (
        "decision_id",
        "e2e_code",
        "decision_type",
        "question",
        "options",
        "user_decision",
        "rationale",
        "affected_documents",
        "affected_traces",
        "requested_at",
        "decided_at",
        "status",
    ),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_actor(actor: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "discord_user_id": str(actor.get("discord_user_id", "")),
        "discord_user_name": str(actor.get("discord_user_name", "")),
        "discord_role_ids": [str(item) for item in actor.get("discord_role_ids", [])],
        "guild_id": actor.get("guild_id"),
        "channel_id": actor.get("channel_id"),
    }


class SessionStore:
    def __init__(self, repo_root: Path, tools_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        self.tools_root = tools_root.resolve()
        self.workspace_root = self.repo_root / "reconciliation/workspaces"
        self._locks_guard = threading.Lock()
        self._locks: dict[str, threading.RLock] = {}

    @contextmanager
    def lock(self, e2e_code: str) -> Iterator[None]:
        with self._locks_guard:
            lock = self._locks.setdefault(e2e_code, threading.RLock())
        with lock:
            yield

    def open_or_create(
        self,
        e2e: Mapping[str, Any],
        actor: Mapping[str, Any],
        model_profile: Mapping[str, str],
    ) -> tuple[dict[str, Any], bool]:
        e2e_code = str(e2e.get("e2e_code", ""))
        workspace = self._workspace(e2e_code)
        workspace.mkdir(parents=True, exist_ok=True)
        session_path = workspace / "session.json"
        previous = self._read_json_optional(session_path)
        if previous and previous.get("status") not in SESSION_TERMINAL_STATUSES:
            return previous, False

        sequence = 1
        if previous:
            match = re.search(r"-(\d+)$", str(previous.get("session_id", "")))
            if match:
                sequence = int(match.group(1)) + 1
        session_id = f"REC-{e2e_code}-{sequence:03d}"
        created_at = _now()
        session = {
            "session_id": session_id,
            "e2e_code": e2e_code,
            "e2e_title": str(e2e.get("title", "")),
            "e2e_selection_status": "PENDING_USER_CONFIRMATION",
            "started_at": created_at,
            "updated_at": created_at,
            "source_inventory_version": self._inventory_version(),
            "base_global_version": self._git_output(
                ["describe", "--tags", "--abbrev=0", "--match", "v[0-9]*"]
            )
            or "UNRELEASED",
            "base_git_commit": self._git_output(["rev-parse", "HEAD"])
            or "UNCOMMITTED",
            "status": "SELECTED_FOR_REVIEW",
            "model_profile": dict(model_profile),
            "started_by": _safe_actor(actor),
            "current_question": None,
            "event_count": 0,
        }
        for filename, headers in REGISTER_HEADERS.items():
            self._ensure_csv(workspace / filename, headers)
        (workspace / "references").mkdir(exist_ok=True)
        (workspace / "promoted").mkdir(exist_ok=True)
        self._create_template(
            workspace / "review-session.md",
            self.tools_root
            / ".codex/skills/neurovi-prd-reconciler/assets/review-session-template.md",
            e2e_code,
            session_id,
        )
        self._write_json(session_path, session)
        return session, True

    def find(self, session_id: str) -> tuple[Path, dict[str, Any]]:
        if not re.fullmatch(r"REC-E2E-[A-Z0-9-]+-\d{3,}", session_id):
            raise ReconciliationAgentError("Invalid reconciliation session ID.")
        if not self.workspace_root.is_dir():
            raise ReconciliationAgentError(f"Session not found: {session_id}", 404)
        for session_path in self.workspace_root.glob("*/session.json"):
            session = self._read_json_optional(session_path)
            if session and session.get("session_id") == session_id:
                return session_path.parent, session
        raise ReconciliationAgentError(f"Session not found: {session_id}", 404)

    def save(self, workspace: Path, session: Mapping[str, Any]) -> None:
        updated = dict(session)
        updated["updated_at"] = _now()
        self._write_json(workspace / "session.json", updated)

    def append_event(
        self,
        workspace: Path,
        session: dict[str, Any],
        event_type: str,
        actor: Mapping[str, Any],
        data: Mapping[str, Any],
    ) -> None:
        event = {
            "event_id": int(session.get("event_count", 0)) + 1,
            "occurred_at": _now(),
            "event_type": event_type,
            "actor": _safe_actor(actor),
            "model_profile": session.get("model_profile", {}),
            "data": dict(data),
        }
        with (workspace / "agent-audit.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        session["event_count"] = event["event_id"]
        self.save(workspace, session)

    def recent_events(self, workspace: Path, limit: int = 30) -> list[dict[str, Any]]:
        path = workspace / "agent-audit.jsonl"
        if not path.is_file():
            return []
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines()[-limit:]:
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                rows.append(value)
        return rows

    def record_question(
        self, workspace: Path, session: dict[str, Any], value: Mapping[str, Any]
    ) -> None:
        question = str(value.get("question", "")).strip()
        if not question:
            return
        path = workspace / "interview-register.csv"
        rows = self._read_csv(path)
        question_id = str(value.get("question_id", "")).strip()
        if not question_id:
            question_id = self._next_id(
                rows, "question_id", f"QST-{session['e2e_code']}-"
            )
        current = {
            "question_id": question_id,
            "defect_ids": self._pipe_value(value.get("defect_ids")),
            "document_ids": self._pipe_value(value.get("document_ids")),
            "flow_or_handoff": str(value.get("flow_or_handoff", "")),
            "question": question,
            "why_needed": str(value.get("why_needed", "")),
            "question_type": str(value.get("question_type", "")).upper(),
        }
        if not any(row.get("question_id") == question_id for row in rows):
            rows.append(
                {
                    **current,
                    "e2e_code": session["e2e_code"],
                    "asked_at": _now(),
                    "status": "PENDING",
                    "user_answer": "",
                    "answered_at": "",
                    "answer_evidence": "",
                    "notes": "Generated as a decision question; not a source fact.",
                }
            )
            self._write_csv(path, REGISTER_HEADERS[path.name], rows)
        session["current_question"] = current
        session["status"] = "AWAITING_USER"
        self.save(workspace, session)

    def resolve_current_question(
        self,
        workspace: Path,
        session: dict[str, Any],
        status: str,
        answer: str,
    ) -> None:
        current = session.get("current_question")
        if not isinstance(current, Mapping):
            return
        question_id = str(current.get("question_id", ""))
        path = workspace / "interview-register.csv"
        rows = self._read_csv(path)
        for row in rows:
            if row.get("question_id") != question_id:
                continue
            row["status"] = status
            row["user_answer"] = answer
            row["answered_at"] = _now()
            row["answer_evidence"] = f"agent-audit.jsonl event {session.get('event_count', 0) + 1}"
            break
        self._write_csv(path, REGISTER_HEADERS[path.name], rows)
        session["current_question"] = None
        session["status"] = "IN_PROGRESS"
        self.save(workspace, session)

    def record_reference(
        self,
        workspace: Path,
        session: Mapping[str, Any],
        actor: Mapping[str, Any],
        reference: str,
    ) -> str:
        path = workspace / "reference-register.csv"
        rows = self._read_csv(path)
        reference_id = self._next_id(
            rows, "reference_id", f"REF-{session['e2e_code']}-"
        )
        candidate = (self.repo_root / reference).resolve()
        within_repo = candidate == self.repo_root or self.repo_root in candidate.parents
        exists = within_repo and candidate.is_file()
        stored_path = str(candidate.relative_to(self.repo_root)) if exists else ""
        digest = hashlib.sha256(candidate.read_bytes()).hexdigest() if exists else ""
        rows.append(
            {
                "reference_id": reference_id,
                "session_id": session["session_id"],
                "original_filename": Path(reference).name,
                "original_path": reference,
                "stored_path": stored_path,
                "sha256": digest,
                "supplied_by": str(actor.get("discord_user_id", "")),
                "added_at": _now(),
                "proposed_e2e_codes": session["e2e_code"],
                "format_scan_status": "PENDING_RESCAN",
                "relationship_scan_status": "PENDING_RESCAN",
                "decision_id": "",
                "notes": (
                    "Existing repository reference."
                    if exists
                    else "Reference recorded; file is not present in the repository mount."
                ),
            }
        )
        self._write_csv(path, REGISTER_HEADERS[path.name], rows)
        return reference_id

    def record_decision(
        self,
        workspace: Path,
        session: Mapping[str, Any],
        decision: str,
    ) -> str:
        path = workspace / "decision-register.csv"
        rows = self._read_csv(path)
        decision_id = self._next_id(
            rows, "decision_id", f"DEC-{session['e2e_code']}-"
        )
        current = session.get("current_question")
        question = str(current.get("question", "")) if isinstance(current, Mapping) else ""
        now = _now()
        rows.append(
            {
                "decision_id": decision_id,
                "e2e_code": session["e2e_code"],
                "decision_type": "GAP_RESOLUTION",
                "question": question,
                "options": "",
                "user_decision": decision,
                "rationale": "",
                "affected_documents": "",
                "affected_traces": "",
                "requested_at": now,
                "decided_at": now,
                "status": "USER_CONFIRMED",
            }
        )
        self._write_csv(path, REGISTER_HEADERS[path.name], rows)
        return decision_id

    def refine_decision(
        self,
        workspace: Path,
        decision_id: str,
        model_payload: Mapping[str, Any],
    ) -> None:
        path = workspace / "decision-register.csv"
        rows = self._read_csv(path)
        decision_type = str(model_payload.get("decision_type", "")).upper()
        if decision_type not in DECISION_TYPES:
            decision_type = "GAP_RESOLUTION"
        for row in rows:
            if row.get("decision_id") != decision_id:
                continue
            row["decision_type"] = decision_type
            row["rationale"] = str(model_payload.get("decision_rationale", ""))
            row["affected_documents"] = self._pipe_value(
                model_payload.get("affected_documents")
            )
            row["affected_traces"] = self._pipe_value(
                model_payload.get("affected_traces")
            )
            break
        self._write_csv(path, REGISTER_HEADERS[path.name], rows)

    def apply_decision_actions(
        self,
        workspace: Path,
        session: dict[str, Any],
        decision_id: str,
        actions: Any,
        evidence: Mapping[str, Any],
    ) -> None:
        if not isinstance(actions, list):
            return
        gap = evidence.get("gap_scan", {})
        mapped = gap.get("mapped_documents", []) if isinstance(gap, Mapping) else []
        documents = {
            str(item.get("document_id", "")): item
            for item in mapped
            if isinstance(item, Mapping)
        }
        source = evidence.get("e2e", {}).get("source_flow", {})
        if isinstance(source, Mapping) and source.get("document_id"):
            documents.setdefault(
                str(source["document_id"]),
                {
                    "document_id": source["document_id"],
                    "title": session.get("e2e_title", ""),
                    "source_path": source.get("source_path", ""),
                    "content_id": "",
                    "relationship_evidence": ["SOURCE_FLOW"],
                },
            )

        for action in actions:
            if not isinstance(action, Mapping):
                continue
            action_type = str(action.get("type", "")).upper()
            if action_type == "E2E_SELECTION":
                status = str(action.get("status", "")).upper()
                if status in {"USER_CONFIRMED", "DEFERRED"}:
                    session["e2e_selection_status"] = status
                continue
            if action_type != "DOCUMENT_SELECTION":
                continue
            document_id = str(action.get("document_id", "")).strip()
            status = str(action.get("selection_status", "")).upper()
            role = str(action.get("relationship_role", "CONTEXT")).upper()
            if document_id not in documents or status not in SELECTION_STATUSES:
                continue
            if role not in RELATIONSHIP_ROLES:
                role = "CONTEXT"
            document = documents[document_id]
            path = workspace / "document-selection.csv"
            rows = self._read_csv(path)
            row = next(
                (item for item in rows if item.get("document_id") == document_id),
                None,
            )
            if row is None:
                row = {
                    "selection_id": self._next_id(
                        rows, "selection_id", f"SEL-{session['e2e_code']}-"
                    ),
                    "e2e_code": session["e2e_code"],
                    "document_id": document_id,
                    "original_title": str(document.get("title", "")),
                    "original_path": str(document.get("source_path", "")),
                    "content_id": str(document.get("content_id", "")),
                    "proposed_document_code": "",
                    "proposed_title": "",
                    "relationship_role": role,
                    "evidence_type": self._pipe_value(
                        document.get("relationship_evidence")
                    ),
                    "evidence_reference": "reconciliation E2E inventory",
                    "selection_status": status,
                    "decision_id": decision_id,
                    "notes": str(action.get("reason", "")),
                }
                rows.append(row)
            else:
                row["relationship_role"] = role
                row["selection_status"] = status
                row["decision_id"] = decision_id
                row["notes"] = str(action.get("reason", ""))
            self._write_csv(path, REGISTER_HEADERS[path.name], rows)
        self.save(workspace, session)

    def selected_document_context(self, workspace: Path) -> list[dict[str, Any]]:
        selections = self._read_csv(workspace / "document-selection.csv")
        selected = [
            row
            for row in selections
            if row.get("selection_status") in {"CONFIRMED_INCLUDE", "CONTEXT_ONLY"}
        ]
        result = []
        remaining = 100_000
        for row in selected:
            if remaining <= 0:
                break
            document_id = row.get("document_id", "")
            content_path = self.repo_root / "documents" / document_id / "content.md"
            content = (
                content_path.read_text(encoding="utf-8", errors="replace")
                if content_path.is_file()
                else ""
            )
            excerpt = content[: min(20_000, remaining)]
            remaining -= len(excerpt)
            result.append({**row, "preserved_content_excerpt": excerpt})
        return result

    def _workspace(self, e2e_code: str) -> Path:
        if not re.fullmatch(r"E2E-[A-Z0-9-]+", e2e_code):
            raise ReconciliationAgentError("Resolved E2E code is invalid.")
        return self.workspace_root / e2e_code

    def _inventory_version(self) -> str:
        path = self.repo_root / "reconciliation/e2e-inventory/inventory-manifest.json"
        if not path.is_file():
            return "UNKNOWN"
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _git_output(self, args: list[str]) -> str:
        completed = subprocess.run(
            ["git", *args],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        return completed.stdout.strip() if completed.returncode == 0 else ""

    @staticmethod
    def _read_json_optional(path: Path) -> dict[str, Any] | None:
        if not path.is_file():
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None

    @staticmethod
    def _write_json(path: Path, value: Mapping[str, Any]) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)

    @staticmethod
    def _ensure_csv(path: Path, headers: tuple[str, ...]) -> None:
        if path.is_file():
            return
        SessionStore._write_csv(path, headers, [])

    @staticmethod
    def _read_csv(path: Path) -> list[dict[str, str]]:
        if not path.is_file():
            return []
        with path.open(encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))

    @staticmethod
    def _write_csv(
        path: Path, headers: tuple[str, ...], rows: list[Mapping[str, Any]]
    ) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({key: row.get(key, "") for key in headers})
        temporary.replace(path)

    @staticmethod
    def _next_id(
        rows: list[Mapping[str, str]], column: str, prefix: str
    ) -> str:
        sequence = 0
        for row in rows:
            value = row.get(column, "")
            if not value.startswith(prefix):
                continue
            suffix = value.removeprefix(prefix)
            if suffix.isdigit():
                sequence = max(sequence, int(suffix))
        return f"{prefix}{sequence + 1:03d}"

    @staticmethod
    def _pipe_value(value: Any) -> str:
        if isinstance(value, list):
            return "|".join(str(item) for item in value if str(item).strip())
        return str(value or "")

    @staticmethod
    def _create_template(
        destination: Path, source: Path, e2e_code: str, session_id: str
    ) -> None:
        if destination.exists():
            return
        if source.is_file():
            content = source.read_text(encoding="utf-8")
            content = content.replace("<E2E Code>", e2e_code)
            content = content.replace("<REC_ID>", session_id)
        else:
            content = f"# Reconciliation Review - {e2e_code}\n"
        destination.write_text(content, encoding="utf-8")


class ReconciliationAgent:
    def __init__(self, settings: Settings, llm: LLMClient) -> None:
        self.settings = settings
        self.llm = llm
        self.store = SessionStore(settings.repo_root, settings.tools_root)
        self.model_profile = settings.reconciliation_model_profile()
        self.system_prompt = self._load_system_prompt()

    def invoke(self, request: Mapping[str, Any]) -> dict[str, Any]:
        capability = str(request.get("capability", "")).strip()
        if capability not in AGENT_CAPABILITIES:
            raise ReconciliationAgentError(f"Unknown agent capability: {capability}")
        parameters = request.get("parameters", {})
        actor = request.get("actor", {})
        if not isinstance(parameters, Mapping) or not isinstance(actor, Mapping):
            raise ReconciliationAgentError("parameters and actor must be objects.")
        if capability == HELP_CAPABILITY:
            return self._answer_help(parameters)
        self._authorize(capability, actor)

        if capability == "reconcile.start":
            return self._start(parameters, actor)
        session_id = self._required(parameters, "session_id")
        workspace, session = self.store.find(session_id)
        with self.store.lock(str(session["e2e_code"])):
            if capability == "reconcile.status":
                return self._status(workspace, session)
            if capability == "reconcile.finish":
                return self._finish_blocked(workspace, session, parameters, actor)
            return self._continue(capability, workspace, session, parameters, actor)

    def _answer_help(self, parameters: Mapping[str, Any]) -> dict[str, Any]:
        query = self._required(parameters, "query")
        if len(query) > 4000:
            raise ReconciliationAgentError("Help question is too long.")
        prompt = json.dumps(
            {
                "user_question": query,
                "instruction": (
                    "Classify the need against the catalog and return the exact "
                    "JSON response contract from the system prompt."
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
        try:
            result = self.llm.complete(CONTEXTUAL_HELP_SYSTEM_PROMPT, prompt)
        except LLMError as error:
            raise ReconciliationAgentError(str(error), 502) from error
        rendered = render_contextual_help(result.payload)
        if rendered is None:
            LOGGER.warning(
                "Contextual help model output failed validation: %s",
                json.dumps(result.payload, ensure_ascii=False)[:3000],
            )
            raise ReconciliationAgentError(
                "Help advisor returned an unsafe or invalid command recommendation.",
                502,
            )
        return {
            "message": rendered,
            "status": "ADVISORY",
            "result": {"model_profile": self.model_profile},
        }

    def _start(
        self, parameters: Mapping[str, Any], actor: Mapping[str, Any]
    ) -> dict[str, Any]:
        query = self._required(parameters, "e2e")
        e2e = self._run_inventory_json(query)
        e2e_code = str(e2e["e2e_code"])
        with self.store.lock(e2e_code):
            session, created = self.store.open_or_create(
                e2e, actor, self.model_profile
            )
            workspace, session = self.store.find(str(session["session_id"]))
            evidence = self._collect_evidence(e2e_code, workspace)
            event = {
                "operation": "START" if created else "RESUME",
                "requested_e2e": query,
                "resolved_e2e": e2e_code,
            }
            self.store.append_event(workspace, session, "USER_REQUEST", actor, event)
            result = self._ask_model(
                "reconcile.start", session, workspace, event, evidence
            )
            self._apply_model_result(workspace, session, result.payload)
            self.store.append_event(
                workspace,
                session,
                "MODEL_RESPONSE",
                {},
                {
                    "request_id": result.request_id,
                    "message": str(result.payload.get("message", "")),
                    "status": str(result.payload.get("status", "")),
                },
            )
            return self._response(session, result.payload)

    def _continue(
        self,
        capability: str,
        workspace: Path,
        session: dict[str, Any],
        parameters: Mapping[str, Any],
        actor: Mapping[str, Any],
    ) -> dict[str, Any]:
        operation: dict[str, Any]
        decision_id: str | None = None
        if capability == "reconcile.answer":
            answer = self._required(parameters, "answer")
            self.store.resolve_current_question(
                workspace, session, "ANSWERED", answer
            )
            operation = {"operation": "ANSWER", "answer": answer}
        elif capability == "reconcile.control":
            action = self._required(parameters, "action").upper()
            if action not in INTERVIEW_CONTROL_STATUSES:
                raise ReconciliationAgentError("action must be SKIP, DEFER, or UNKNOWN.")
            self.store.resolve_current_question(
                workspace, session, INTERVIEW_CONTROL_STATUSES[action], action
            )
            operation = {"operation": "CONTROL", "action": action}
        elif capability == "reconcile.add-reference":
            reference = self._required(parameters, "reference")
            reference_id = self.store.record_reference(
                workspace, session, actor, reference
            )
            operation = {
                "operation": "ADD_REFERENCE",
                "reference": reference,
                "reference_id": reference_id,
            }
        elif capability == "reconcile.decide":
            decision = self._required(parameters, "decision")
            decision_id = self.store.record_decision(workspace, session, decision)
            self.store.resolve_current_question(
                workspace, session, "CONFIRMED_RESOLVED", decision
            )
            operation = {
                "operation": "USER_DECISION",
                "decision": decision,
                "decision_id": decision_id,
            }
        else:
            raise ReconciliationAgentError(f"Unsupported capability: {capability}")

        self.store.append_event(workspace, session, "USER_REQUEST", actor, operation)
        evidence = self._collect_evidence(str(session["e2e_code"]), workspace)
        result = self._ask_model(capability, session, workspace, operation, evidence)
        if decision_id:
            self.store.refine_decision(workspace, decision_id, result.payload)
            self.store.apply_decision_actions(
                workspace,
                session,
                decision_id,
                result.payload.get("actions"),
                evidence,
            )
        self._apply_model_result(workspace, session, result.payload)
        self.store.append_event(
            workspace,
            session,
            "MODEL_RESPONSE",
            {},
            {
                "request_id": result.request_id,
                "message": str(result.payload.get("message", "")),
                "status": str(result.payload.get("status", "")),
                "decision_id": decision_id,
            },
        )
        return self._response(session, result.payload)

    def _ask_model(
        self,
        capability: str,
        session: Mapping[str, Any],
        workspace: Path,
        operation: Mapping[str, Any],
        evidence: Mapping[str, Any],
    ) -> LLMResult:
        prompt = {
            "capability": capability,
            "operation": operation,
            "session": session,
            "recent_audit_events": self.store.recent_events(workspace),
            "repository_evidence": evidence,
            "selected_document_content": self.store.selected_document_context(
                workspace
            ),
            "response_contract": {
                "message": (
                    "Required plain Indonesian response for a nontechnical hospital "
                    "user. Use at most 3 short sentences, explain what was found and "
                    "what the user must decide, and do not instruct the user to type "
                    "status codes, session IDs, or slash commands."
                ),
                "status": "AWAITING_USER, IN_PROGRESS, READY_FOR_BASELINE_REVIEW, or BLOCKED",
                "current_question": {
                    "question_id": "Optional stable ID",
                    "defect_ids": ["optional"],
                    "document_ids": ["optional"],
                    "flow_or_handoff": "optional",
                    "why_needed": "short plain Indonesian reason without internal codes",
                    "question": "one neutral plain Indonesian question without internal codes",
                    "question_type": "CONFIRMATION, DOCUMENT_SELECTION, or OPEN_ANSWER",
                },
                "decision_type": "Only for USER_DECISION and only one allowed policy type",
                "decision_rationale": "Evidence-based explanation, never an invented fact",
                "affected_documents": ["document IDs"],
                "affected_traces": ["trace IDs"],
                "actions": [
                    {
                        "type": "E2E_SELECTION or DOCUMENT_SELECTION",
                        "status": "USER_CONFIRMED or DEFERRED for E2E_SELECTION",
                        "document_id": "required for DOCUMENT_SELECTION",
                        "selection_status": "CONFIRMED_INCLUDE, CONTEXT_ONLY, TAKE_OFF, or DEFERRED",
                        "relationship_role": "one allowed relationship role",
                        "reason": "evidence and exact user-decision basis",
                    }
                ],
            },
        }
        try:
            return self.llm.complete(
                self.system_prompt,
                json.dumps(prompt, ensure_ascii=False, indent=2),
            )
        except LLMError as error:
            raise ReconciliationAgentError(str(error), 502) from error

    def _apply_model_result(
        self,
        workspace: Path,
        session: dict[str, Any],
        payload: Mapping[str, Any],
    ) -> None:
        message = payload.get("message")
        if not isinstance(message, str) or not message.strip():
            raise ReconciliationAgentError(
                "Agent model response must contain a message.", 502
            )
        current_question = payload.get("current_question")
        if isinstance(current_question, Mapping):
            self.store.record_question(workspace, session, current_question)
        else:
            status = self._model_status(payload.get("status"))
            session["status"] = status
            self.store.save(workspace, session)

    def _collect_evidence(
        self, e2e_code: str, workspace: Path
    ) -> dict[str, Any]:
        e2e = self._run_inventory_json(e2e_code)
        gap = self._run_json_command(
            [
                sys.executable,
                str(
                    self.settings.tools_root
                    / ".codex/skills/neurovi-gap-scanner/scripts/scan_gaps.py"
                ),
                "--repo",
                str(self.settings.repo_root),
                "--json",
                "--e2e",
                e2e_code,
            ]
        )
        compact_gap = {
            "summary": gap.get("summary"),
            "mapped_documents": gap.get("mapped_documents", [])[:60],
            "cross_document_gaps": gap.get("cross_document_gaps", []),
            "handoff_gap_candidates": gap.get("handoff_gap_candidates", [])[:40],
            "flow_node_gaps": gap.get("flow_node_gaps", []),
            "duplicate_content_groups": gap.get("duplicate_content_groups", []),
            "open_confirmed_defects": gap.get("open_confirmed_defects", []),
            "unresolved_interview_questions": gap.get(
                "unresolved_interview_questions", []
            ),
            "warning": gap.get("warning"),
        }
        return {
            "e2e": {
                **e2e,
                "mechanical_candidates": e2e.get("mechanical_candidates", [])[:60],
            },
            "gap_scan": compact_gap,
            "workspace": str(workspace.relative_to(self.settings.repo_root)),
        }

    def _run_inventory_json(self, query: str) -> dict[str, Any]:
        return self._run_json_command(
            [
                sys.executable,
                str(
                    self.settings.tools_root
                    / ".codex/skills/neurovi-prd-reconciler/scripts/inspect_inventory.py"
                ),
                "--repo",
                str(self.settings.repo_root),
                "--json",
                "show-e2e",
                "--e2e",
                query,
            ]
        )

    def _run_json_command(self, command: list[str]) -> dict[str, Any]:
        completed = subprocess.run(
            command,
            cwd=self.settings.repo_root,
            capture_output=True,
            text=True,
            timeout=self.settings.command_timeout_seconds,
            check=False,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()
            raise ReconciliationAgentError(detail or "Repository scan failed.", 422)
        try:
            value = json.loads(completed.stdout)
        except json.JSONDecodeError as error:
            raise ReconciliationAgentError(
                "Repository scan returned invalid JSON.", 500
            ) from error
        if not isinstance(value, dict):
            raise ReconciliationAgentError(
                "Repository scan returned an unexpected payload.", 500
            )
        return value

    def _status(
        self, workspace: Path, session: Mapping[str, Any]
    ) -> dict[str, Any]:
        current = session.get("current_question")
        lines = [
            f"Session `{session['session_id']}` untuk `{session['e2e_code']}`.",
            f"Status: `{session.get('status', 'UNKNOWN')}`.",
            f"Model agent: `{self.model_profile['provider']}/{self.model_profile['model']}` dengan effort `{self.model_profile['reasoning_effort']}`.",
        ]
        if isinstance(current, Mapping) and current.get("question"):
            lines.append(f"Pertanyaan aktif: {current['question']}")
        return {
            "message": "\n".join(lines),
            "status": session.get("status"),
            "session_id": session.get("session_id"),
            "result": {
                "workspace": str(workspace.relative_to(self.settings.repo_root)),
                "model_profile": self.model_profile,
                "event_count": session.get("event_count", 0),
            },
        }

    def _finish_blocked(
        self,
        workspace: Path,
        session: dict[str, Any],
        parameters: Mapping[str, Any],
        actor: Mapping[str, Any],
    ) -> dict[str, Any]:
        approval = str(parameters.get("approval", ""))
        if approval != "BASELINE_APPROVAL":
            raise ReconciliationAgentError(
                "reconcile.finish requires BASELINE_APPROVAL."
            )
        self.store.append_event(
            workspace,
            session,
            "PUBLISH_BLOCKED",
            actor,
            {
                "reason": "The agent interview runtime does not yet implement the audited release publisher.",
                "requested_version_bump": parameters.get("version_bump", "patch"),
            },
        )
        return {
            "message": (
                "Sesi belum dipublikasikan. Runtime agent sudah menjalankan interview "
                "rekonsiliasi dengan model container, tetapi publisher Git atomik tetap "
                "dikunci sampai generator canonical, pemeriksaan UNEXPLAINED_CHANGE, dan "
                "release manifest tersedia. Tidak ada commit, tag, atau push yang dibuat."
            ),
            "status": "BLOCKED",
            "session_id": session["session_id"],
            "result": {"push_status": "NOT_ATTEMPTED"},
        }

    def _response(
        self, session: Mapping[str, Any], payload: Mapping[str, Any]
    ) -> dict[str, Any]:
        return {
            "message": str(payload["message"]),
            "status": self._model_status(session.get("status", "IN_PROGRESS")),
            "session_id": session["session_id"],
            "result": {"model_profile": self.model_profile},
        }

    def _authorize(self, capability: str, actor: Mapping[str, Any]) -> None:
        allowed = (
            self.settings.discord_approver_role_ids
            if capability == "reconcile.finish"
            else self.settings.discord_reconcile_role_ids
        )
        role_ids = set()
        for value in actor.get("discord_role_ids", []):
            try:
                role_ids.add(int(value))
            except (TypeError, ValueError):
                continue
        if not allowed or not role_ids.intersection(allowed):
            raise ReconciliationAgentError(
                "Actor is not authorized for this reconciliation capability.", 403
            )

    def _load_system_prompt(self) -> str:
        paths = (
            self.settings.tools_root / "AGENTS.md",
            self.settings.repo_root / "AGENTS.md",
            self.settings.tools_root
            / ".codex/skills/neurovi-prd-reconciler/SKILL.md",
            self.settings.tools_root
            / ".codex/skills/neurovi-prd-reconciler/references/reconciliation-policy.md",
            self.settings.tools_root
            / ".codex/skills/neurovi-prd-reconciler/references/artifact-schema.md",
            self.settings.tools_root
            / ".codex/skills/neurovi-prd-reconciler/references/git-versioning-policy.md",
        )
        sections = []
        for path in paths:
            if not path.is_file():
                raise ReconciliationAgentError(
                    f"Required reconciliation instruction is missing: {path}", 500
                )
            sections.append(f"# Loaded instruction: {path.name}\n\n{path.read_text(encoding='utf-8')}")
        sections.append(
            """
# Runtime Response Rules

- Return exactly one JSON object following the response contract in the user message.
- The repository evidence is diagnostic until the user confirms it.
- Never claim that a document, baseline, commit, tag, or push changed; this model has no direct filesystem or Git write authority.
- `actions` are allowed only when the current operation is `USER_DECISION`, and every action must be directly supported by the exact user decision.
- Ask one focused question at a time and always allow SKIP, DEFER, or UNKNOWN.
- Write for nontechnical hospital staff using short, familiar Indonesian words.
- Never tell the user to type internal values such as CONFIRM, CONFIRMED_INCLUDE, CONTEXT_ONLY, TAKE_OFF, SKIP, DEFER, UNKNOWN, PRIMARY_SCOPE, a session ID, or a slash command. The Discord interface provides those controls.
- Keep each user-facing message to at most three short sentences: what was found, why it matters, and what decision is needed.
- Replace technical terms in user-facing text: source flow Mermaid -> diagram alur; boundary -> cakupan proses; mechanical candidate -> dokumen yang mungkin terkait; baseline -> versi yang disetujui.
- Respond in Indonesian unless source wording must be quoted exactly.
""".strip()
        )
        return "\n\n".join(sections)

    @staticmethod
    def _required(parameters: Mapping[str, Any], key: str) -> str:
        value = str(parameters.get(key, "")).strip()
        if not value:
            raise ReconciliationAgentError(f"Missing required parameter: {key}")
        return value

    @staticmethod
    def _model_status(value: Any) -> str:
        normalized = str(value or "IN_PROGRESS").upper()
        return normalized if normalized in MODEL_STATUSES else "IN_PROGRESS"
