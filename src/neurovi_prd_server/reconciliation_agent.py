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
        "reconcile.main-flow.start",
        "reconcile.business-cases.start",
        # Backward-compatible API alias. New clients must use an explicit mode.
        "reconcile.start",
        "reconcile.answer",
        "reconcile.control",
        "reconcile.add-reference",
        "reconcile.decide",
        "reconcile.status",
        "reconcile.stop",
        "reconcile.finish",
    }
)
HELP_CAPABILITY = "help.answer"
AGENT_CAPABILITIES = RECONCILIATION_CAPABILITIES | {HELP_CAPABILITY}

RECONCILIATION_MODES = {
    "MAIN_FLOW": {
        "slug": "main-flow",
        "id_code": "MF",
        "label": "Perbaikan alur utama",
        "question_scope": "MAIN_FLOW",
    },
    "BUSINESS_CASES": {
        "slug": "business-cases",
        "id_code": "BC",
        "label": "Perbaikan detail proses",
        "question_scope": "BUSINESS_CASE",
    },
}
START_CAPABILITY_MODES = {
    "reconcile.start": "MAIN_FLOW",
    "reconcile.main-flow.start": "MAIN_FLOW",
    "reconcile.business-cases.start": "BUSINESS_CASES",
}
RECONCILIATION_ISSUE_TYPES = {
    "MAIN_FLOW": frozenset(
        {
            "MISSING_TRIGGER",
            "BROKEN_SEQUENCE",
            "BROKEN_HANDOFF",
            "MISSING_OUTPUT",
            "UNDEFINED_STATUS_TRANSITION",
            "CROSS_DOMAIN_CONTINUATION",
            "FLOW_CONFLICT",
        }
    ),
    "BUSINESS_CASES": frozenset(
        {
            "MISSING_SCENARIO",
            "MISSING_CONDITION",
            "BUSINESS_RULE_AMBIGUITY",
            "VALIDATION_GAP",
            "ERROR_HANDLING_GAP",
            "EXCEPTION_GAP",
            "ACCEPTANCE_CRITERIA_GAP",
            "CASE_CONFLICT",
        }
    ),
}

SESSION_TERMINAL_STATUSES = frozenset(
    {"START_FAILED", "STOPPED_BY_USER", "FINISHED", "PUBLISHED"}
)
INTERVIEW_CONTROL_STATUSES = {
    "SKIP": "SKIPPED_BY_USER",
    "DEFER": "DEFERRED",
    "UNKNOWN": "UNKNOWN",
}
DECISION_TYPES = frozenset(
    {
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


def _reconciliation_mode(value: Any) -> str:
    mode = str(value or "MAIN_FLOW").upper().replace("-", "_")
    if mode not in RECONCILIATION_MODES:
        raise ReconciliationAgentError(f"Unsupported reconciliation mode: {value}")
    return mode


def _mode_config(value: Any) -> Mapping[str, str]:
    return RECONCILIATION_MODES[_reconciliation_mode(value)]


def _single_enum_value(value: Any) -> str:
    """Normalize a model enum while tolerating a one-item JSON array."""
    if isinstance(value, (list, tuple)):
        if len(value) != 1:
            return ""
        value = value[0]
    return str(value or "").strip().upper()


ORIGINAL_SOURCE_ROOT = Path("source/original")
PRIMARY_PRD_SOURCE_PREFIX = Path("PRD/PRD Generator (.md)")
CANONICAL_ROOT = Path("reconciliation/canonical")
CANONICAL_MANIFEST = CANONICAL_ROOT / "manifest.json"
CANONICAL_BOOTSTRAP_VERSION = "v0.0.0"
AUTO_SOURCE_FACT_STATUS = "RESOLVED_BY_SOURCE_FACT"
HUMAN_DECISION_STATUS = "HUMAN_DECISION_REQUIRED"
DISCOVERY_ONLY_SOURCE_DIRECTORIES = frozenset({"menu-flow"})
SUPPORTING_MARKDOWN_SOURCE_PATHS = frozenset(
    {
        "PRD/PRD Generator (.md)/Integrasi/Api Doc/APLICARES-KETERSEDIAAN KAMAR.md",
        "PRD/PRD Generator (.md)/KONTEKS-SESI.md",
        "PRD/PRD Generator (.md)/Pelayanan (.md)/ringkasan-merge-prd-rj.md",
    }
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
        self._document_catalog: dict[str, dict[str, Any]] | None = None
        self._canonical_cache_key: tuple[int, int, int, int] | None = None
        self._canonical_by_document_id: dict[str, dict[str, Any]] | None = None

    @contextmanager
    def lock(self, e2e_code: str, mode: str | None = None) -> Iterator[None]:
        lock_key = f"{e2e_code}:{_reconciliation_mode(mode)}" if mode else e2e_code
        with self._locks_guard:
            lock = self._locks.setdefault(lock_key, threading.RLock())
        with lock:
            yield

    def open_or_create(
        self,
        e2e: Mapping[str, Any],
        actor: Mapping[str, Any],
        model_profile: Mapping[str, str],
        reconciliation_mode: str = "MAIN_FLOW",
    ) -> tuple[dict[str, Any], bool]:
        mode = _reconciliation_mode(reconciliation_mode)
        mode_config = _mode_config(mode)
        e2e_code = str(e2e.get("e2e_code", ""))
        workspace = self._session_workspace(e2e_code, mode)
        workspace.mkdir(parents=True, exist_ok=True)
        session_path = workspace / "session.json"
        previous = self._read_json_optional(session_path)
        if previous and previous.get("status") not in SESSION_TERMINAL_STATUSES:
            if self._is_abandoned_start(workspace, previous):
                self.mark_start_failed(
                    workspace,
                    previous,
                    ReconciliationAgentError(
                        "Previous start ended before the agent returned a response."
                    ),
                )
            else:
                return previous, False
        if mode == "MAIN_FLOW":
            legacy_path = self._workspace(e2e_code) / "session.json"
            legacy = self._read_json_optional(legacy_path)
            if legacy and legacy.get("status") not in SESSION_TERMINAL_STATUSES:
                legacy.setdefault("reconciliation_mode", "MAIN_FLOW")
                legacy.setdefault(
                    "reconciliation_mode_label", mode_config["label"]
                )
                return legacy, False

        sequence = 1
        if previous:
            match = re.search(r"-(\d+)$", str(previous.get("session_id", "")))
            if match:
                sequence = int(match.group(1)) + 1
        session_id = f"REC-{e2e_code}-{mode_config['id_code']}-{sequence:03d}"
        created_at = _now()
        session = {
            "session_id": session_id,
            "e2e_code": e2e_code,
            "e2e_title": str(e2e.get("title", "")),
            "e2e_selection_status": "AUTO_WORKLIST",
            "reconciliation_mode": mode,
            "reconciliation_mode_label": mode_config["label"],
            "started_at": created_at,
            "updated_at": created_at,
            "source_inventory_version": self._inventory_version(),
            "canonical_baseline_manifest_sha256": self._canonical_baseline_version(),
            "base_canonical_version": self._canonical_version(),
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
            mode_config["label"],
        )
        self._write_json(session_path, session)
        return session, True

    def _is_abandoned_start(
        self, workspace: Path, session: Mapping[str, Any]
    ) -> bool:
        if session.get("status") != "SELECTED_FOR_REVIEW":
            return False
        if isinstance(session.get("current_question"), Mapping):
            return False
        return not any(
            event.get("event_type") == "MODEL_RESPONSE"
            for event in self.recent_events(workspace)
        )

    def find(self, session_id: str) -> tuple[Path, dict[str, Any]]:
        if not re.fullmatch(
            r"REC-E2E-[A-Z0-9-]+-(?:(?:MF|BC)-)?\d{3,}", session_id
        ):
            raise ReconciliationAgentError("Invalid reconciliation session ID.")
        if not self.workspace_root.is_dir():
            raise ReconciliationAgentError(f"Session not found: {session_id}", 404)
        for session_path in self._session_paths():
            session = self._read_json_optional(session_path)
            if session and session.get("session_id") == session_id:
                session.setdefault("reconciliation_mode", "MAIN_FLOW")
                session.setdefault(
                    "reconciliation_mode_label",
                    _mode_config(session["reconciliation_mode"])["label"],
                )
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

    def mark_start_failed(
        self,
        workspace: Path,
        session: dict[str, Any],
        error: Exception,
    ) -> None:
        session["status"] = "START_FAILED"
        session["start_failed_at"] = _now()
        self.append_event(
            workspace,
            session,
            "SESSION_START_FAILED",
            {},
            {"reason": str(error)[:1000]},
        )

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
                rows, "question_id", f"QST-{session['e2e_code']}-{_mode_config(session.get('reconciliation_mode', 'MAIN_FLOW'))['id_code']}-"
            )
        current = {
            "question_id": question_id,
            "defect_ids": self._pipe_value(value.get("defect_ids")),
            "document_ids": self._pipe_value(value.get("document_ids")),
            "flow_or_handoff": str(value.get("flow_or_handoff", "")),
            "question": question,
            "why_needed": str(value.get("why_needed", "")),
            "question_type": str(value.get("question_type", "")).upper(),
            "question_scope": str(value.get("question_scope", "")).upper(),
            "issue_type": str(value.get("issue_type", "")).upper(),
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
            rows, "reference_id", f"REF-{session['e2e_code']}-{_mode_config(session.get('reconciliation_mode', 'MAIN_FLOW'))['id_code']}-"
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
                    "Existing repository reference; supporting evidence only and "
                    "not selectable as a reconciliation source document."
                    if exists
                    else "Reference recorded as supporting evidence only; file is not "
                    "present in the repository mount."
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
            rows, "decision_id", f"DEC-{session['e2e_code']}-{_mode_config(session.get('reconciliation_mode', 'MAIN_FLOW'))['id_code']}-"
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
                self.eligible_document_ids(model_payload.get("affected_documents"))
            )
            row["affected_traces"] = self._pipe_value(
                model_payload.get("affected_traces")
            )
            break
        self._write_csv(path, REGISTER_HEADERS[path.name], rows)

    def worklist_document_context(
        self, e2e: Mapping[str, Any]
    ) -> list[dict[str, Any]]:
        worklist = e2e.get("worklist", [])
        if not isinstance(worklist, list):
            return []
        eligible = [item for item in worklist if isinstance(item, Mapping)]
        excerpt_limit = min(18_000, max(2_000, 180_000 // max(1, len(eligible))))
        result = []
        for item in eligible:
            document_id = str(item.get("document_id", ""))
            canonical = self.verified_canonical_baseline(document_id)
            if canonical is None:
                continue
            original = canonical["original_document"]
            excerpt = canonical["preserved_source_content"][:excerpt_limit]
            result.append(
                {
                    "document_id": document_id,
                    "document_code": canonical["document_code"],
                    "original_title": original.get("title", ""),
                    "original_path": original["source_path"],
                    "content_id": original.get("content_id", ""),
                    "canonical_path": canonical["canonical_path"],
                    "canonical_sha256": canonical["canonical_sha256"],
                    "canonical_version": canonical["canonical_version"],
                    "original_sha256": canonical["original_sha256"],
                    "worklist_status": "OWNER_WORKLIST",
                    "relationship_role": "PRIMARY_SCOPE",
                    "worklist_stage": item.get("worklist_stage", ""),
                    "worklist_order": item.get("worklist_order"),
                    "assignment_basis": item.get("assignment_basis", ""),
                    "assignment_confidence": item.get("assignment_confidence", ""),
                    "source_representation": "VERIFIED_LOSSLESS_CANONICAL_V0",
                    "source_authority": "IMMUTABLE_ORIGINAL_MARKDOWN",
                    "standard_section_map": canonical["standard_section_map"],
                    "preserved_content_excerpt": excerpt,
                }
            )
        return result

    def related_source_document_context(
        self, e2e: Mapping[str, Any]
    ) -> list[dict[str, Any]]:
        worklist = e2e.get("worklist", [])
        owner_ids = {
            str(item.get("document_id", ""))
            for item in worklist
            if isinstance(item, Mapping)
        }
        related: dict[str, dict[str, Any]] = {}
        for relation in e2e.get("relations", []):
            if not isinstance(relation, Mapping):
                continue
            if (
                str(relation.get("verification_status", "")) != "SOURCE_EXPLICIT"
                and str(relation.get("evidence_class", ""))
                not in {"SOURCE_FACT", "CROSS_SOURCE_FACT"}
            ):
                continue
            for side in ("source", "target"):
                document_id = str(relation.get(f"{side}_document_id", ""))
                if not document_id or document_id in owner_ids:
                    continue
                row = related.setdefault(
                    document_id,
                    {
                        "document_id": document_id,
                        "relationship_ids": [],
                        "relationship_roles": [],
                        "evidence_references": [],
                    },
                )
                row["relationship_ids"].append(
                    str(relation.get("relation_id", ""))
                )
                row["relationship_roles"].append(
                    str(relation.get("relationship_type", ""))
                )
                row["evidence_references"].append(
                    str(relation.get("evidence_reference", ""))
                )

        excerpt_limit = min(18_000, max(4_000, 80_000 // max(1, len(related))))
        result = []
        for document_id, row in related.items():
            canonical = self.verified_canonical_baseline(document_id)
            if canonical is None:
                continue
            original = canonical["original_document"]
            result.append(
                {
                    **row,
                    "document_code": canonical["document_code"],
                    "original_title": original.get("title", ""),
                    "original_path": original["source_path"],
                    "content_id": original.get("content_id", ""),
                    "canonical_path": canonical["canonical_path"],
                    "canonical_sha256": canonical["canonical_sha256"],
                    "canonical_version": canonical["canonical_version"],
                    "original_sha256": canonical["original_sha256"],
                    "worklist_status": "RELATED_SOURCE_CONTEXT",
                    "relationship_role": "CONTEXT",
                    "source_representation": "VERIFIED_LOSSLESS_CANONICAL_V0",
                    "source_authority": "IMMUTABLE_ORIGINAL_MARKDOWN",
                    "standard_section_map": canonical["standard_section_map"],
                    "preserved_content_excerpt": canonical[
                        "preserved_source_content"
                    ][:excerpt_limit],
                }
            )
        return result

    def verified_canonical_e2e(self, e2e_code: str) -> dict[str, Any]:
        # Loading the document index first applies the shared manifest and
        # active-inventory checks before this E2E artifact is trusted.
        self._canonical_index()
        manifest_path = self.repo_root / CANONICAL_MANIFEST
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        contexts = manifest.get("e2e_contexts", [])
        if not isinstance(contexts, list) or int(
            manifest.get("generated_e2e_count", -1)
        ) != len(contexts):
            raise ReconciliationAgentError(
                "Verified canonical E2E manifest has inconsistent counts.", 409
            )
        context = next(
            (
                item
                for item in contexts
                if isinstance(item, Mapping)
                and str(item.get("e2e_code", "")) == e2e_code
            ),
            None,
        )
        if context is None:
            raise ReconciliationAgentError(
                f"Verified canonical E2E is missing: {e2e_code}", 409
            )
        relative = Path(str(context.get("path", "")))
        path = self._verified_relative_path(
            relative, CANONICAL_ROOT / "e2e", "canonical E2E"
        )
        generated = path.read_bytes()
        generated_sha256 = hashlib.sha256(generated).hexdigest()
        if generated_sha256 != str(context.get("generated_sha256", "")):
            raise ReconciliationAgentError(
                f"Generated canonical E2E checksum is invalid: {e2e_code}", 409
            )
        try:
            content = generated.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ReconciliationAgentError(
                f"Canonical E2E is not valid UTF-8 Markdown: {e2e_code}", 409
            ) from error
        return {
            "e2e_code": e2e_code,
            "canonical_version": str(manifest.get("canonical_version", "")),
            "canonical_path": relative.as_posix(),
            "canonical_sha256": generated_sha256,
            "content_excerpt": content[:40_000],
            "content_truncated": len(content) > 40_000,
        }

    def verified_automatic_reconciliation(
        self, e2e_code: str = "", reconciliation_mode: str = ""
    ) -> dict[str, Any]:
        self._canonical_index()
        manifest_path = self.repo_root / CANONICAL_MANIFEST
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        metadata = manifest.get("automatic_candidate_reconciliation", {})
        if not isinstance(metadata, Mapping) or metadata.get("status") != "COMPLETED":
            raise ReconciliationAgentError(
                "Automatic source-fact reconciliation register is unavailable.", 409
            )
        relative = Path(str(metadata.get("register_path", "")))
        path = self._verified_relative_path(
            relative, CANONICAL_ROOT, "automatic reconciliation register"
        )
        generated = path.read_bytes()
        digest = hashlib.sha256(generated).hexdigest()
        if digest != str(metadata.get("register_sha256", "")):
            raise ReconciliationAgentError(
                "Automatic reconciliation register checksum is invalid.", 409
            )
        try:
            register = json.loads(generated.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ReconciliationAgentError(
                "Automatic reconciliation register is not valid JSON.", 409
            ) from error
        if register.get("source_inventory_sha256") != manifest.get(
            "source_inventory_sha256"
        ):
            raise ReconciliationAgentError(
                "Automatic reconciliation register was built from a different inventory.",
                409,
            )
        items = [item for item in register.get("items", []) if isinstance(item, Mapping)]
        if e2e_code:
            items = [item for item in items if item.get("e2e_code") == e2e_code]
        if reconciliation_mode:
            items = [
                item
                for item in items
                if item.get("reconciliation_mode") == reconciliation_mode
            ]
        return {
            "status": "COMPLETED",
            "path": relative.as_posix(),
            "sha256": digest,
            "summary": register.get("summary", {}),
            "items": items,
        }

    def verified_canonical_baseline(
        self, document_id: str
    ) -> dict[str, Any] | None:
        original = self.original_markdown_prd(document_id)
        if original is None:
            return None
        canonical = self._canonical_index().get(document_id)
        if canonical is None:
            raise ReconciliationAgentError(
                f"Verified canonical v0 is missing for eligible PRD: {document_id}",
                409,
            )
        if str(canonical.get("content_id", "")) != str(
            original.get("content_id", "")
        ):
            raise ReconciliationAgentError(
                f"Canonical v0 content ID does not match original PRD: {document_id}",
                409,
            )

        representation = next(
            (
                item
                for item in canonical.get("source_representations", [])
                if isinstance(item, Mapping)
                and str(item.get("document_id", "")) == document_id
            ),
            None,
        )
        if representation is None:
            raise ReconciliationAgentError(
                f"Canonical v0 provenance is missing original PRD: {document_id}",
                409,
            )
        source_path = str(original.get("source_path", ""))
        if str(representation.get("source_path", "")) != source_path:
            raise ReconciliationAgentError(
                f"Canonical v0 provenance path does not match original PRD: {document_id}",
                409,
            )

        original_path = self._verified_relative_path(
            ORIGINAL_SOURCE_ROOT / source_path,
            ORIGINAL_SOURCE_ROOT / PRIMARY_PRD_SOURCE_PREFIX,
            "original PRD",
        )
        original_bytes = original_path.read_bytes()
        original_sha256 = hashlib.sha256(original_bytes).hexdigest()
        expected_hashes = {
            str(original.get("sha256", "")),
            str(representation.get("sha256", "")),
            str(canonical.get("source_sha256", "")),
        }
        expected_hashes.discard("")
        if not expected_hashes or expected_hashes != {original_sha256}:
            raise ReconciliationAgentError(
                f"Canonical v0 checksum does not match original PRD: {document_id}",
                409,
            )

        canonical_relative = Path(str(canonical.get("path", "")))
        canonical_path = self._verified_relative_path(
            canonical_relative,
            CANONICAL_ROOT / "prds",
            "canonical v0",
        )
        generated_bytes = canonical_path.read_bytes()
        generated_sha256 = hashlib.sha256(generated_bytes).hexdigest()
        if generated_sha256 != str(canonical.get("generated_sha256", "")):
            raise ReconciliationAgentError(
                f"Generated canonical v0 checksum is invalid: {document_id}",
                409,
            )
        payload_offset = canonical.get("payload_offset")
        payload_length = canonical.get("payload_length")
        if (
            not isinstance(payload_offset, int)
            or not isinstance(payload_length, int)
            or payload_offset < 0
            or payload_offset > len(generated_bytes)
            or payload_length != len(original_bytes)
            or generated_bytes[payload_offset : payload_offset + payload_length]
            != original_bytes
            or len(generated_bytes) != payload_offset + payload_length
        ):
            raise ReconciliationAgentError(
                f"Canonical v0 no longer preserves the complete original PRD payload: {document_id}",
                409,
            )
        try:
            wrapper = generated_bytes[:payload_offset].decode("utf-8")
            preserved_content = generated_bytes[payload_offset:].decode("utf-8")
        except UnicodeDecodeError as error:
            raise ReconciliationAgentError(
                f"Canonical v0 is not valid UTF-8 Markdown: {document_id}",
                409,
            ) from error
        return {
            "document_code": str(canonical.get("document_code", "")),
            "content_id": str(canonical.get("content_id", "")),
            "canonical_path": canonical_relative.as_posix(),
            "canonical_sha256": generated_sha256,
            "canonical_version": str(canonical.get("canonical_version", "")),
            "canonical_wrapper": wrapper,
            "preserved_source_content": preserved_content,
            "original_sha256": original_sha256,
            "standard_section_map": canonical.get("standard_section_map", []),
            "original_document": original,
        }

    def original_markdown_prd(self, document_id: str) -> dict[str, Any] | None:
        document = self._document_catalog_by_id().get(document_id)
        if document is None or not self._is_original_markdown_prd(document):
            return None
        return dict(document)

    def eligible_document_ids(self, value: Any) -> list[str]:
        return [
            document_id
            for document_id in self._value_items(value)
            if self.original_markdown_prd(document_id) is not None
        ]

    def _document_catalog_by_id(self) -> dict[str, dict[str, Any]]:
        if self._document_catalog is None:
            catalog = self._read_json_optional(
                self.repo_root / "catalog/document-index.json"
            )
            documents = catalog.get("documents", []) if catalog else []
            self._document_catalog = {
                str(item.get("document_id", "")): dict(item)
                for item in documents
                if isinstance(item, Mapping) and item.get("document_id")
            }
        return self._document_catalog

    def _canonical_index(self) -> dict[str, dict[str, Any]]:
        manifest_path = self.repo_root / CANONICAL_MANIFEST
        inventory_path = (
            self.repo_root / "reconciliation/e2e-inventory/domain-worklist.json"
        )
        if not manifest_path.is_file() or not inventory_path.is_file():
            raise ReconciliationAgentError(
                "Verified canonical v0 or active E2E inventory is missing.", 409
            )
        manifest_stat = manifest_path.stat()
        inventory_stat = inventory_path.stat()
        cache_key = (
            manifest_stat.st_mtime_ns,
            manifest_stat.st_size,
            inventory_stat.st_mtime_ns,
            inventory_stat.st_size,
        )
        if (
            self._canonical_cache_key == cache_key
            and self._canonical_by_document_id is not None
        ):
            return self._canonical_by_document_id
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ReconciliationAgentError(
                f"Verified canonical manifest cannot be read: {error}", 409
            ) from error
        if (
            not isinstance(manifest, Mapping)
            or manifest.get("artifact_type")
            != "CANONICAL_BASELINE_MANIFEST"
        ):
            raise ReconciliationAgentError(
                "Verified canonical manifest has an invalid artifact type.", 409
            )
        canonical_version = str(manifest.get("canonical_version", ""))
        if canonical_version != CANONICAL_BOOTSTRAP_VERSION:
            raise ReconciliationAgentError(
                "Reconciliation currently requires canonical bootstrap v0.0.0.",
                409,
            )
        inventory_sha256 = hashlib.sha256(inventory_path.read_bytes()).hexdigest()
        if str(manifest.get("source_inventory_sha256", "")) != inventory_sha256:
            raise ReconciliationAgentError(
                "Verified canonical v0 is stale against the active E2E inventory. "
                "Regenerate it before reconciliation.",
                409,
            )
        documents = manifest.get("documents", [])
        if not isinstance(documents, list) or int(
            manifest.get("generated_prd_count", -1)
        ) != len(documents):
            raise ReconciliationAgentError(
                "Verified canonical manifest has inconsistent document counts.",
                409,
            )
        index: dict[str, dict[str, Any]] = {}
        for item in documents:
            if not isinstance(item, Mapping):
                raise ReconciliationAgentError(
                    "Verified canonical manifest contains an invalid document.",
                    409,
                )
            baseline = dict(item)
            representations = baseline.get("source_representations", [])
            if not isinstance(representations, list):
                raise ReconciliationAgentError(
                    "Verified canonical provenance is invalid.", 409
                )
            for representation in representations:
                if not isinstance(representation, Mapping):
                    continue
                source_document_id = str(representation.get("document_id", ""))
                if not source_document_id:
                    continue
                previous = index.get(source_document_id)
                if previous and previous.get("content_id") != baseline.get("content_id"):
                    raise ReconciliationAgentError(
                        f"Canonical v0 maps one document ID to multiple payloads: {source_document_id}",
                        409,
                    )
                index[source_document_id] = baseline
        self._canonical_cache_key = cache_key
        self._canonical_by_document_id = index
        return index

    def _verified_relative_path(
        self, relative: Path, expected_root: Path, label: str
    ) -> Path:
        if relative.is_absolute() or ".." in relative.parts:
            raise ReconciliationAgentError(f"Invalid {label} path: {relative}", 409)
        root = (self.repo_root / expected_root).resolve()
        candidate = (self.repo_root / relative).resolve()
        if not candidate.is_relative_to(root) or not candidate.is_file():
            raise ReconciliationAgentError(f"Missing or invalid {label}: {relative}", 409)
        return candidate

    def _is_original_markdown_prd(self, document: Mapping[str, Any]) -> bool:
        source_path = str(document.get("source_path", ""))
        relative = Path(source_path)
        prefix_parts = PRIMARY_PRD_SOURCE_PREFIX.parts
        if (
            not source_path
            or relative.is_absolute()
            or relative.suffix != ".md"
            or str(document.get("extension", "")) != ".md"
            or ".." in relative.parts
            or len(relative.parts) <= len(prefix_parts)
            or relative.parts[: len(prefix_parts)] != prefix_parts
            or relative.as_posix() in SUPPORTING_MARKDOWN_SOURCE_PATHS
            or DISCOVERY_ONLY_SOURCE_DIRECTORIES.intersection(
                part.casefold() for part in relative.parts
            )
        ):
            return False
        source_root = (self.repo_root / ORIGINAL_SOURCE_ROOT).resolve()
        primary_source_root = (source_root / PRIMARY_PRD_SOURCE_PREFIX).resolve()
        candidate = (source_root / relative).resolve()
        return candidate.is_relative_to(primary_source_root) and candidate.is_file()

    @staticmethod
    def _value_items(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return [item.strip() for item in str(value or "").split("|") if item.strip()]

    def _workspace(self, e2e_code: str) -> Path:
        if not re.fullmatch(r"E2E-[A-Z0-9-]+", e2e_code):
            raise ReconciliationAgentError("Resolved E2E code is invalid.")
        return self.workspace_root / e2e_code

    def _session_workspace(self, e2e_code: str, mode: str) -> Path:
        return self._workspace(e2e_code) / "sessions" / _mode_config(mode)["slug"]

    def _session_paths(self) -> tuple[Path, ...]:
        if not self.workspace_root.is_dir():
            return ()
        legacy = self.workspace_root.glob("*/session.json")
        scoped = self.workspace_root.glob("*/sessions/*/session.json")
        return tuple(sorted((*legacy, *scoped)))

    def _inventory_version(self) -> str:
        path = self.repo_root / "reconciliation/e2e-inventory/inventory-manifest.json"
        if not path.is_file():
            return "UNKNOWN"
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _canonical_baseline_version(self) -> str:
        path = self.repo_root / CANONICAL_MANIFEST
        if not path.is_file():
            raise ReconciliationAgentError(
                "Verified canonical baseline manifest is missing.", 409
            )
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _canonical_version(self) -> str:
        path = self.repo_root / CANONICAL_MANIFEST
        if not path.is_file():
            raise ReconciliationAgentError(
                "Verified canonical baseline manifest is missing.", 409
            )
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ReconciliationAgentError(
                f"Verified canonical manifest cannot be read: {error}", 409
            ) from error
        version = str(manifest.get("canonical_version", ""))
        if version != CANONICAL_BOOTSTRAP_VERSION:
            raise ReconciliationAgentError(
                "Reconciliation currently requires canonical bootstrap v0.0.0.",
                409,
            )
        return version

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
        destination: Path,
        source: Path,
        e2e_code: str,
        session_id: str,
        reconciliation_mode_label: str,
    ) -> None:
        if destination.exists():
            return
        if source.is_file():
            content = source.read_text(encoding="utf-8")
            content = content.replace("<E2E Code>", e2e_code)
            content = content.replace("<REC_ID>", session_id)
            content = content.replace(
                "<RECONCILIATION_MODE>", reconciliation_mode_label
            )
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

        if capability in START_CAPABILITY_MODES:
            return self._start(
                parameters, actor, START_CAPABILITY_MODES[capability], capability
            )
        session_id = self._required(parameters, "session_id")
        workspace, session = self.store.find(session_id)
        with self.store.lock(
            str(session["e2e_code"]),
            str(session.get("reconciliation_mode", "MAIN_FLOW")),
        ):
            if capability != "reconcile.finish":
                self._authorize_session_owner(session, actor)
            if capability == "reconcile.status":
                return self._status(workspace, session)
            if capability == "reconcile.stop":
                return self._stop(workspace, session, actor)
            if capability == "reconcile.finish":
                return self._finish_blocked(workspace, session, parameters, actor)
            if session.get("status") in SESSION_TERMINAL_STATUSES:
                raise ReconciliationAgentError(
                    "Sesi ini sudah diakhiri. Mulai sesi baru untuk melanjutkan peninjauan.",
                    409,
                )
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
        self,
        parameters: Mapping[str, Any],
        actor: Mapping[str, Any],
        reconciliation_mode: str,
        capability: str,
    ) -> dict[str, Any]:
        mode = _reconciliation_mode(reconciliation_mode)
        query = self._required(parameters, "e2e")
        e2e = self._run_inventory_json(query)
        e2e_code = str(e2e["e2e_code"])
        # Verify the flow map and every owner PRD before creating or resuming a
        # writable session.
        self.store.verified_canonical_e2e(e2e_code)
        self.store.worklist_document_context(e2e)
        with self.store.lock(e2e_code, mode):
            session, created = self.store.open_or_create(
                e2e, actor, self.model_profile, mode
            )
            started_by = session.get("started_by", {})
            session_owner = (
                str(started_by.get("discord_user_id", ""))
                if isinstance(started_by, Mapping)
                else ""
            )
            requester = str(actor.get("discord_user_id", ""))
            if not created and session_owner and session_owner != requester:
                raise ReconciliationAgentError(
                    "Proses ini sedang ditinjau oleh pengguna lain. Tunggu sampai "
                    "sesi tersebut diakhiri sebelum memulai sesi baru.",
                    409,
                )
            workspace, session = self.store.find(str(session["session_id"]))
            try:
                evidence = self._collect_evidence(e2e_code, workspace, mode)
                event = {
                    "operation": "START" if created else "RESUME",
                    "requested_e2e": query,
                    "resolved_e2e": e2e_code,
                    "reconciliation_mode": mode,
                }
                self.store.append_event(
                    workspace, session, "USER_REQUEST", actor, event
                )
                result = self._ask_model(
                    capability, session, workspace, event, evidence
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
            except Exception as error:
                events = self.store.recent_events(workspace)
                has_model_response = any(
                    event.get("event_type") == "MODEL_RESPONSE" for event in events
                )
                if (
                    session.get("status") == "SELECTED_FOR_REVIEW"
                    and not isinstance(session.get("current_question"), Mapping)
                    and not has_model_response
                ):
                    self.store.mark_start_failed(workspace, session, error)
                raise

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
        evidence = self._collect_evidence(
            str(session["e2e_code"]),
            workspace,
            str(session.get("reconciliation_mode", "MAIN_FLOW")),
        )
        result = self._ask_model(capability, session, workspace, operation, evidence)
        if decision_id:
            self.store.refine_decision(workspace, decision_id, result.payload)
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
        mode_config = _mode_config(session.get("reconciliation_mode", "MAIN_FLOW"))
        prompt = {
            "reconciliation_scope": mode_config,
            "capability": capability,
            "operation": operation,
            "session": session,
            "recent_audit_events": self.store.recent_events(workspace),
            "repository_evidence": evidence,
            "owner_worklist_content": self.store.worklist_document_context(
                evidence.get("e2e", {})
            ),
            "related_source_content": self.store.related_source_document_context(
                evidence.get("e2e", {})
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
                    "defect_ids": (
                        "One or more cited defect IDs when available; do not invent IDs"
                    ),
                    "document_ids": (
                        "One or more eligible affected document IDs from repository "
                        "evidence; required when the issue concerns documents"
                    ),
                    "flow_or_handoff": (
                        "Required plain-language name of the affected stage, flow, "
                        "or handoff"
                    ),
                    "why_needed": (
                        "Required short plain Indonesian explanation of the concrete "
                        "flow or business consequence"
                    ),
                    "question": (
                        "One neutral plain Indonesian question that names the affected "
                        "document titles or handoff and asks only for a functional or "
                        "semantic decision"
                    ),
                    "question_type": "CONFIRMATION or OPEN_ANSWER",
                    "question_scope": mode_config["question_scope"],
                    "issue_type": (
                        "Exactly one string selected from: "
                        + ", ".join(
                            sorted(
                                RECONCILIATION_ISSUE_TYPES[
                                    _reconciliation_mode(
                                        session.get("reconciliation_mode")
                                    )
                                ]
                            )
                        )
                    ),
                },
                "decision_type": "Only for USER_DECISION and only one allowed policy type",
                "decision_rationale": "Evidence-based explanation, never an invented fact",
                "affected_documents": ["document IDs"],
                "affected_traces": ["trace IDs"],
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
            normalized_question = dict(current_question)
            mode = _reconciliation_mode(
                session.get("reconciliation_mode", "MAIN_FLOW")
            )
            expected_scope = _mode_config(mode)["question_scope"]
            question_scope = _single_enum_value(
                current_question.get("question_scope")
            )
            if question_scope != expected_scope:
                raise ReconciliationAgentError(
                    "Agent model question does not match the active reconciliation "
                    f"mode. Expected {expected_scope}, received "
                    f"{question_scope or 'EMPTY'}.",
                    502,
                )
            normalized_question["question_scope"] = question_scope
            issue_type = _single_enum_value(current_question.get("issue_type"))
            allowed_issue_types = RECONCILIATION_ISSUE_TYPES[mode]
            if issue_type not in allowed_issue_types:
                raise ReconciliationAgentError(
                    "Agent model issue type does not match the active reconciliation "
                    f"mode. Received {current_question.get('issue_type') or 'EMPTY'}.",
                    502,
                )
            normalized_question["issue_type"] = issue_type
            question_type = _single_enum_value(
                current_question.get("question_type")
            )
            normalized_question["question_type"] = question_type
            if question_type == "DOCUMENT_SELECTION":
                raise ReconciliationAgentError(
                    "Agent model requested document classification, but owner-domain "
                    "worklist membership is automatic.",
                    502,
                )
            document_ids = self.store._value_items(
                current_question.get("document_ids")
            )
            if any(
                self.store.original_markdown_prd(document_id) is None
                for document_id in document_ids
            ):
                raise ReconciliationAgentError(
                    "Agent model referenced a document outside the eligible original "
                    "Markdown PRD source set.",
                    502,
                )
            question = str(current_question.get("question", "")).casefold()
            forbidden = (
                "dokumen utama",
                "hanya sebagai konteks",
                "hanya pendukung",
                "tidak terkait",
                "dikeluarkan",
                "diputuskan nanti",
                "confirmed_include",
                "context_only",
                "take_off",
                "domain ini",
                "cakupan proses ini sudah sesuai",
            )
            if any(value in question for value in forbidden):
                raise ReconciliationAgentError(
                    "Agent model requested domain or document worklist confirmation, "
                    "which is not a user decision.",
                    502,
                )
            if not str(current_question.get("flow_or_handoff", "")).strip():
                raise ReconciliationAgentError(
                    "Agent model question must identify the affected flow or handoff.",
                    502,
                )
            if not str(current_question.get("why_needed", "")).strip():
                raise ReconciliationAgentError(
                    "Agent model question must explain why the business decision is needed.",
                    502,
                )
            self.store.record_question(workspace, session, normalized_question)
        else:
            status = self._model_status(payload.get("status"))
            session["status"] = status
            self.store.save(workspace, session)

    def _collect_evidence(
        self,
        e2e_code: str,
        workspace: Path,
        reconciliation_mode: str = "MAIN_FLOW",
    ) -> dict[str, Any]:
        mode = _reconciliation_mode(reconciliation_mode)
        e2e = self._run_inventory_json(e2e_code)
        scanner = str(
            self.settings.tools_root
            / ".codex/skills/neurovi-gap-scanner/scripts/scan_gaps.py"
        )
        scan_command = [
            sys.executable,
            scanner,
            "--repo",
            str(self.settings.repo_root),
            "--json",
        ]
        if mode == "MAIN_FLOW":
            scan_command.extend(["main-flow", "--e2e", e2e_code])
        else:
            scan_command.extend(["business-cases", "--e2e", e2e_code])
        scan_result = self._run_json_command(scan_command)
        main_flow_scan = scan_result if mode == "MAIN_FLOW" else {}
        business_case_scan = scan_result if mode == "BUSINESS_CASES" else {}

        selectable_documents = []
        for item in e2e.get("worklist", []):
            if not isinstance(item, Mapping):
                continue
            document_id = str(item.get("document_id", ""))
            if self.store.original_markdown_prd(document_id) is None:
                continue
            selectable_documents.append(
                {
                    key: item.get(key)
                    for key in (
                        "worklist_order",
                        "worklist_stage",
                        "document_id",
                        "content_id",
                        "title",
                        "source_path",
                        "flow_checks",
                    )
                    if key in item
                }
                | {
                    "evidence_role": "OWNER_DOMAIN_PRIMARY_SOURCE",
                    "selectable_source_document": True,
                }
            )
        selectable_ids = {
            str(item.get("document_id", "")) for item in selectable_documents
        }

        supporting_reasoning_documents = []
        supporting_ids = set()
        for relation in e2e.get("relations", []):
            if not isinstance(relation, Mapping):
                continue
            for side in ("source", "target"):
                document_id = str(relation.get(f"{side}_document_id", ""))
                if (
                    not document_id
                    or document_id in selectable_ids
                    or document_id in supporting_ids
                ):
                    continue
                supporting_ids.add(document_id)
                supporting_reasoning_documents.append(
                    {
                        "document_id": document_id,
                        "content_id": relation.get(f"{side}_content_id", ""),
                        "title": relation.get(f"{side}_title", ""),
                        "domain_code": relation.get(f"{side}_domain_code", ""),
                        "relationship_evidence": [
                            f"RELATION:{relation.get('relation_id', '')}"
                        ],
                        "evidence_role": "SUPPORTING_REASONING_ONLY",
                        "selectable_source_document": False,
                    }
                )

        main_flow = {
            "summary": main_flow_scan.get("summary", {}),
            "ordered_documents": main_flow_scan.get("ordered_documents", [])[:60],
            "flow_relations": main_flow_scan.get("flow_relations", [])[:80],
            "gap_candidates": main_flow_scan.get("gap_candidates", [])[:80],
            "warning": main_flow_scan.get("warning"),
        }
        business_case_documents = []
        for document in business_case_scan.get("documents", [])[:60]:
            if not isinstance(document, Mapping):
                continue
            family_candidates = [
                str(family.get("context_family", ""))
                for family in document.get("families", [])
                if isinstance(family, Mapping)
                and family.get("status") == "CONTEXT_GAP_CANDIDATE"
            ]
            business_case_documents.append(
                {
                    "worklist_order": document.get("worklist_order", 0),
                    "worklist_stage": document.get("worklist_stage", ""),
                    "document_id": document.get("document_id", ""),
                    "title": document.get("title", ""),
                    "source_path": document.get("source_path", ""),
                    "business_case_candidate_count": document.get(
                        "business_case_candidate_count", 0
                    ),
                    "gap_candidate_families": family_candidates,
                    "inventory_case_candidate_count": document.get(
                        "inventory_case_candidate_count", 0
                    ),
                    "explicit_gap_markers": document.get(
                        "explicit_gap_markers", []
                    )[:10],
                }
            )
        business_cases = {
            "summary": business_case_scan.get("summary", {}),
            "documents": business_case_documents,
            "warning": business_case_scan.get("warning"),
        }
        scan_evidence = (
            {"main_flow_scan": main_flow}
            if mode == "MAIN_FLOW"
            else {"business_case_scan": business_cases}
        )
        source_fact_relations = []
        human_decision_relations = []
        for relation in e2e.get("relations", []):
            if not isinstance(relation, Mapping):
                continue
            if relation.get("verification_status") != "SOURCE_EXPLICIT":
                continue
            if relation.get("evidence_class") not in {
                "SOURCE_FACT",
                "CROSS_SOURCE_FACT",
            }:
                continue
            item = dict(relation)
            if relation.get("conflict_status") == "NO_CONFLICT_IDENTIFIED":
                item["reconciliation_status"] = AUTO_SOURCE_FACT_STATUS
                item["decision_required"] = False
                source_fact_relations.append(item)
            else:
                item["reconciliation_status"] = HUMAN_DECISION_STATUS
                item["decision_required"] = True
                human_decision_relations.append(item)
        automatic_register = self.store.verified_automatic_reconciliation(
            e2e_code, mode
        )
        return {
            "reconciliation_scope": _mode_config(mode),
            "canonical_e2e_context": self.store.verified_canonical_e2e(e2e_code),
            "e2e": {
                "e2e_code": e2e.get("e2e_code", ""),
                "title": e2e.get("title", ""),
                "status": e2e.get("status", ""),
                "origin": e2e.get("origin", ""),
                "routing_note": e2e.get(
                    "routing_note", e2e.get("boundary_warning", "")
                ),
                "purpose": e2e.get("purpose", ""),
                "document_count": e2e.get("document_count", 0),
                "relation_count": e2e.get("relation_count", 0),
                "cross_domain_relation_count": e2e.get(
                    "cross_domain_relation_count", 0
                ),
                "worklist": selectable_documents,
                "relations": self._prioritized_relations(e2e.get("relations", [])),
            },
            **scan_evidence,
            "automatic_source_fact_reconciliation": {
                "status": "COMPLETED",
                "policy": (
                    "Relations listed as RESOLVED_BY_SOURCE_FACT are settled from "
                    "eligible source-explicit evidence and must not be presented as "
                    "user questions. Relations listed as HUMAN_DECISION_REQUIRED "
                    "remain open because they contain a conflict or semantic choice."
                ),
                "resolved_relations": source_fact_relations,
                "human_decision_required_relations": human_decision_relations,
                "global_candidate_register": automatic_register,
            },
            "supporting_reasoning": {
                "documents": supporting_reasoning_documents[:60],
                "usage": (
                    "Use only to understand possible relationships, gaps, and user "
                    "questions. Never treat these documents as source facts or select "
                    "their document IDs."
                ),
            },
            "source_policy": {
                "selectable_source_documents": (
                    "Reconciliation consumes the verified lossless canonical v0 PRDs. "
                    "Each canonical document must match an eligible exact .md original beneath "
                    "source/original/PRD/PRD Generator (.md)/ by inventory checksum, "
                    "document/content identity, provenance path, checksum, and payload. "
                    "The matched original remains the source-fact authority."
                ),
                "supporting_reasoning_only": (
                    "All other files and repositories, including the Copy folder, "
                    "supporting Markdown artifacts, Mermaid, PDF, DOCX, Graphify, "
                    "unverified generated documents, and user-added references, may "
                    "support reasoning and discovery only. They cannot establish source "
                    "facts, enter selection, or be reconciled as primary documents."
                ),
            },
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

    @staticmethod
    def _prioritized_relations(value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        relations = [dict(item) for item in value if isinstance(item, Mapping)]
        relations.sort(
            key=lambda item: (
                str(item.get("conflict_status", "")) != "CONFLICT_FOUND",
                str(item.get("verification_status", "")) != "SOURCE_EXPLICIT",
                str(item.get("relation_id", "")),
            )
        )
        return relations[:80]

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
            "Jenis peninjauan: "
            f"`{session.get('reconciliation_mode_label', _mode_config('MAIN_FLOW')['label'])}`.",
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
                "reconciliation_mode": session.get("reconciliation_mode", "MAIN_FLOW"),
                "model_profile": self.model_profile,
                "event_count": session.get("event_count", 0),
                "current_question": current if isinstance(current, Mapping) else None,
            },
        }

    def _stop(
        self,
        workspace: Path,
        session: dict[str, Any],
        actor: Mapping[str, Any],
    ) -> dict[str, Any]:
        if session.get("status") == "STOPPED_BY_USER":
            return {
                "message": (
                    "Sesi ini sudah diakhiri. Semua jawaban dan pertanyaan yang "
                    "belum selesai tetap tersimpan untuk audit."
                ),
                "status": "STOPPED_BY_USER",
                "session_id": session["session_id"],
                "result": {"published": False},
            }
        if session.get("status") in SESSION_TERMINAL_STATUSES:
            raise ReconciliationAgentError("Sesi ini sudah selesai.", 409)

        session["status"] = "STOPPED_BY_USER"
        session["stopped_at"] = _now()
        session["stopped_by"] = _safe_actor(actor)
        self.store.append_event(
            workspace,
            session,
            "SESSION_STOPPED_BY_USER",
            actor,
            {
                "reason": "User ended the guided reconciliation session.",
                "current_question_preserved": isinstance(
                    session.get("current_question"), Mapping
                ),
                "published": False,
            },
        )
        return {
            "message": (
                "Sesi telah diakhiri. Semua jawaban tersimpan dan pertanyaan yang "
                "belum selesai tetap terbuka dalam catatan audit. Tidak ada dokumen "
                "yang diterbitkan, di-commit, atau di-push."
            ),
            "status": "STOPPED_BY_USER",
            "session_id": session["session_id"],
            "result": {"published": False},
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
            "result": {
                "model_profile": self.model_profile,
                "reconciliation_mode": session.get(
                    "reconciliation_mode", "MAIN_FLOW"
                ),
                "current_question": (
                    session.get("current_question")
                    if isinstance(session.get("current_question"), Mapping)
                    else None
                ),
            },
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

    @staticmethod
    def _authorize_session_owner(
        session: Mapping[str, Any], actor: Mapping[str, Any]
    ) -> None:
        started_by = session.get("started_by", {})
        owner = (
            str(started_by.get("discord_user_id", ""))
            if isinstance(started_by, Mapping)
            else ""
        )
        requester = str(actor.get("discord_user_id", ""))
        if owner and owner != requester:
            raise ReconciliationAgentError(
                "Proses ini sedang ditinjau oleh pengguna lain.", 409
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
            content = path.read_text(encoding="utf-8")
            sections.append(f"# Loaded instruction: {path.name}\n\n{content}")
        sections.append(
            """
# Runtime Response Rules

- Return exactly one JSON object following the response contract in the user message.
- Owner-domain routing and owner-worklist membership are automatic inventory context. They are not user-confirmed source facts and must not be presented as approval questions.
- Read selectable PRDs from the verified lossless canonical v0 baseline. Its inventory checksum, document/content identity, provenance path, original checksum, generated checksum, payload length, and preserved payload must match the eligible original `.md` beneath `source/original/PRD/PRD Generator (.md)/`; stop if verification fails.
- Canonical v0 supplies the stable PRD code, normalized wrapper, section map, provenance, and complete byte-identical source payload. The matched original remains the source-fact authority.
- `PRD Generator (.md) - Copy`, all other original-source folders, supporting Markdown artifacts, Mermaid `.mmd`, PDF, DOCX, unverified generated/canonical documents, Graphify artifacts, files under a `menu-flow` source directory, and user-added references are not selectable source documents.
- Non-primary sources may support reasoning, discovery, relationship hypotheses, gap detection, and user questions only. They cannot establish `SOURCE_FACT` or `CROSS_SOURCE_FACT`, change primary-source facts, or enter the preserved baseline unless the user records a separate explicit decision.
- Every reconciliation session has one explicit mode. `MAIN_FLOW` may use only `main_flow_scan` and may ask only about trigger, primary sequence, handoff, output, status transition, cross-domain continuation, or flow conflicts. `BUSINESS_CASES` may use only `business_case_scan` and may ask only about scenarios, conditions, business rules, validation, errors, exceptions, or acceptance criteria. Never combine the two scanner outputs or cross their question scopes.
- Treat an E2E as a domain worklist for checking the active reconciliation mode and related PRDs. It is not a Mermaid boundary.
- Each unique PRD has one owner domain. Cross-domain relations provide context and do not create duplicate ownership or expand the primary PRD scope.
- Read all eligible owner PRDs supplied in `owner_worklist_content` immediately. Do not ask whether an owner PRD is main, supporting, unrelated, included, excluded, or deferred.
- Do not ask the user to confirm the selected domain, its boundary, its worklist, or an owner-domain assignment.
- Treat `RESOLVED_BY_SOURCE_FACT` relations as closed. Do not ask the user to confirm, restate, or choose them; use them directly as source-backed E2E context.
- Ask about a source-explicit relation only when it is marked `HUMAN_DECISION_REQUIRED`, or when another cited source creates a conflict, ambiguity, or semantic choice.
- Ask a user question only when cited evidence identifies a functional gap, explicit source conflict, undefined handoff, missing business context, or semantic choice that the sources cannot settle.
- Every question must name the affected document titles or handoff, state the concrete issue, and explain why the answer matters to flow continuity or business meaning.
- Do not turn every mechanical `REFERENCES` relation or missing trace into a user question. Use it as reasoning context unless it exposes a concrete ambiguity, conflict, or broken handoff.
- If no meaningful user decision is supported by evidence, return `READY_FOR_BASELINE_REVIEW` or `IN_PROGRESS` without `current_question`; never invent a confirmation gate to keep the interview going.
- Never claim that a document, baseline, commit, tag, or push changed; this model has no direct filesystem or Git write authority.
- Ask one focused question at a time and always allow SKIP, DEFER, or UNKNOWN.
- Write for nontechnical hospital staff using short, familiar Indonesian words.
- Never tell the user to type internal values such as CONFIRM, CONFIRMED_INCLUDE, CONTEXT_ONLY, TAKE_OFF, SKIP, DEFER, UNKNOWN, PRIMARY_SCOPE, a session ID, or a slash command. The Discord interface provides those controls.
- Keep each user-facing message to at most three short sentences: what was found, why it matters, and what decision is needed.
- Replace technical terms in user-facing text: domain worklist -> daftar pemeriksaan proses; boundary -> cakupan proses; mechanical candidate -> dokumen yang mungkin terkait; baseline -> versi yang disetujui.
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
