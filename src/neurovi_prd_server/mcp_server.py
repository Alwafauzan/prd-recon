#!/usr/bin/env python3
"""Expose immutable Neurovi PRD context through an authenticated remote MCP."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import hmac
import ipaddress
import json
import os
from pathlib import Path
import re
import sys
import unicodedata
from urllib.parse import urlparse
import warnings
from typing import Any, Iterable

from neurovi_prd_server.agent_gateway import AgentGateway, AgentGatewayError

DOCUMENT_INDEX_PATH = Path("catalog/document-index.json")
E2E_INVENTORY_PATH = Path("reconciliation/e2e-inventory/domain-worklist.json")
CANONICAL_MANIFEST_PATH = Path("reconciliation/canonical/manifest.json")
ORIGINAL_ROOT = Path("source/original")
DEFAULT_PORT = 8767
MAX_JSON_BYTES = 32 * 1024 * 1024
MAX_SOURCE_BYTES = 2 * 1024 * 1024
MAX_RESPONSE_CHARS = 128_000
MAX_CONTENT_CHARS = 100_000
MAX_QUERY_CHARS = 300
MAX_IDENTIFIER_CHARS = 240
MAX_RESULTS = 50
MAX_RELATIONS = 100
MAX_TASK_DOCUMENTS = 10
MAX_EXCERPT_CHARS = 1_200
MAX_RECONCILIATION_TEXT_CHARS = 8_000
MAX_REFERENCE_CHARS = 1_000
SECTION_FAMILIES = {
    "purpose_background",
    "scope",
    "actors_stakeholders",
    "flow_scenarios",
    "business_rules",
    "logical_data",
    "cases_exceptions",
    "acceptance",
}
DEFAULT_TASK_SECTION_FAMILIES = (
    "purpose_background",
    "scope",
    "flow_scenarios",
    "business_rules",
    "logical_data",
    "cases_exceptions",
    "acceptance",
)


class PrdMcpError(RuntimeError):
    pass


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.findall(r"[a-z0-9]+", value))


def checked_text(value: str, label: str, maximum: int) -> str:
    result = value.strip()
    if not result:
        raise PrdMcpError(f"{label} must not be empty")
    if len(result) > maximum:
        raise PrdMcpError(f"{label} exceeds {maximum} characters")
    return result


def checked_limit(value: int, *, maximum: int = MAX_RESULTS) -> int:
    if value < 1 or value > maximum:
        raise PrdMcpError(f"limit must be between 1 and {maximum}")
    return value


def bounded(value: str, limit: int) -> tuple[str, bool]:
    if len(value) <= limit:
        return value, False
    return value[:limit] + "\n... content truncated ...", True


def public_error(error: Exception) -> str:
    if isinstance(error, PrdMcpError):
        return str(error)
    return f"PRD reader failed ({type(error).__name__})"


@dataclass(frozen=True)
class Config:
    root: Path
    max_response_chars: int = MAX_RESPONSE_CHARS
    bind_host: str = "127.0.0.1"
    port: int = DEFAULT_PORT
    public_url: str = f"http://127.0.0.1:{DEFAULT_PORT}/mcp"
    token: str = ""
    agent_gateway_url: str = ""
    agent_gateway_token: str = ""
    agent_gateway_timeout_seconds: int = 180
    actor_id: str = ""
    actor_name: str = "Neurovi PRD MCP"
    actor_role_ids: tuple[str, ...] = ()

    @property
    def reconciliation_updates_enabled(self) -> bool:
        return bool(self.agent_gateway_url)

    @classmethod
    def from_environment(
        cls, explicit_root: str | None = None, *, require_http: bool = False
    ) -> "Config":
        configured = (
            explicit_root
            or os.environ.get("NEUROVI_PRD_MCP_REPOSITORY")
            or os.getcwd()
        )
        root = Path(configured).expanduser().resolve()
        required = (
            root / "AGENTS.md",
            root / DOCUMENT_INDEX_PATH,
            root / E2E_INVENTORY_PATH,
            root / CANONICAL_MANIFEST_PATH,
        )
        if not root.is_dir() or not all(path.is_file() for path in required):
            raise PrdMcpError(
                "PRD root must contain AGENTS.md, the document index, the E2E "
                "worklist, and the canonical manifest"
            )
        bind_host = os.environ.get("NEUROVI_PRD_MCP_BIND_HOST", "127.0.0.1").strip()
        try:
            port = int(os.environ.get("NEUROVI_PRD_MCP_PORT", str(DEFAULT_PORT)))
            max_response_chars = int(
                os.environ.get(
                    "NEUROVI_PRD_MCP_MAX_RESPONSE_CHARS", str(MAX_RESPONSE_CHARS)
                )
            )
            agent_gateway_timeout_seconds = int(
                os.environ.get(
                    "NEUROVI_PRD_MCP_AGENT_GATEWAY_TIMEOUT_SECONDS", "180"
                )
            )
        except ValueError as error:
            raise PrdMcpError(
                "MCP port, response limit, and gateway timeout must be integers"
            ) from error
        if not 1 <= port <= 65535:
            raise PrdMcpError("MCP port must be between 1 and 65535")
        if not 16_000 <= max_response_chars <= 256_000:
            raise PrdMcpError(
                "MCP response limit must be between 16000 and 256000 characters"
            )
        public_url = os.environ.get(
            "NEUROVI_PRD_MCP_PUBLIC_URL", f"http://127.0.0.1:{port}/mcp"
        ).strip()
        token = os.environ.get("NEUROVI_PRD_MCP_TOKEN", "")
        agent_gateway_url = os.environ.get(
            "NEUROVI_PRD_MCP_AGENT_GATEWAY_URL", ""
        ).strip()
        agent_gateway_token = os.environ.get(
            "NEUROVI_PRD_MCP_AGENT_GATEWAY_TOKEN", ""
        )
        actor_id = os.environ.get("NEUROVI_PRD_MCP_ACTOR_ID", "").strip()
        actor_name = os.environ.get(
            "NEUROVI_PRD_MCP_ACTOR_NAME", "Neurovi PRD MCP"
        ).strip()
        role_ids_value = os.environ.get("NEUROVI_PRD_MCP_ACTOR_ROLE_IDS", "")
        actor_role_ids = tuple(
            item.strip() for item in role_ids_value.split(",") if item.strip()
        )
        cls._validate_reconciliation_gateway(
            agent_gateway_url,
            agent_gateway_token,
            agent_gateway_timeout_seconds,
            actor_id,
            actor_name,
            actor_role_ids,
        )
        if require_http:
            cls._validate_http(bind_host, public_url, token)
        return cls(
            root=root,
            max_response_chars=max_response_chars,
            bind_host=bind_host,
            port=port,
            public_url=public_url,
            token=token,
            agent_gateway_url=agent_gateway_url,
            agent_gateway_token=agent_gateway_token,
            agent_gateway_timeout_seconds=agent_gateway_timeout_seconds,
            actor_id=actor_id,
            actor_name=actor_name,
            actor_role_ids=actor_role_ids,
        )

    @staticmethod
    def _validate_http(
        bind_host: str, public_url: str, token: str
    ) -> None:
        try:
            address = ipaddress.ip_address(bind_host)
        except ValueError as error:
            raise PrdMcpError(
                "MCP bind host must be an explicit private IPv4 or loopback address"
            ) from error
        if (
            address.version != 4
            or address.is_unspecified
            or not (address.is_private or address.is_loopback)
        ):
            raise PrdMcpError(
                "MCP bind host must be an explicit private IPv4 or loopback address"
            )
        parsed = urlparse(public_url)
        try:
            parsed.port
        except ValueError as error:
            raise PrdMcpError("public URL contains an invalid port") from error
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path.rstrip("/") != "/mcp"
        ):
            raise PrdMcpError(
                "public URL must be an http(s) URL ending in /mcp"
            )
        if len(token) < 32 or len(token) > 256 or any(char.isspace() for char in token):
            raise PrdMcpError(
                "MCP bearer token must contain 32 to 256 non-whitespace characters"
            )

    @staticmethod
    def _validate_reconciliation_gateway(
        url: str,
        token: str,
        timeout_seconds: int,
        actor_id: str,
        actor_name: str,
        actor_role_ids: tuple[str, ...],
    ) -> None:
        configured = any((url, token, actor_id, actor_role_ids))
        if not configured:
            return
        missing = []
        if not url:
            missing.append("NEUROVI_PRD_MCP_AGENT_GATEWAY_URL")
        if not token:
            missing.append("NEUROVI_PRD_MCP_AGENT_GATEWAY_TOKEN")
        if not actor_id:
            missing.append("NEUROVI_PRD_MCP_ACTOR_ID")
        if not actor_role_ids:
            missing.append("NEUROVI_PRD_MCP_ACTOR_ROLE_IDS")
        if missing:
            raise PrdMcpError(
                "MCP reconciliation updates are partially configured; missing: "
                + ", ".join(missing)
            )
        parsed = urlparse(url)
        try:
            address = ipaddress.ip_address(parsed.hostname or "")
            parsed.port
        except ValueError as error:
            raise PrdMcpError(
                "agent gateway URL must use an explicit private IPv4 or loopback address"
            ) from error
        if (
            parsed.scheme not in {"http", "https"}
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path.rstrip("/") != "/invoke"
            or address.version != 4
            or address.is_unspecified
            or not (address.is_private or address.is_loopback)
        ):
            raise PrdMcpError(
                "agent gateway URL must be an http(s) private IPv4 URL ending in /invoke"
            )
        if len(token) < 32 or len(token) > 256 or any(char.isspace() for char in token):
            raise PrdMcpError(
                "agent gateway token must contain 32 to 256 non-whitespace characters"
            )
        if not 1 <= timeout_seconds <= 600:
            raise PrdMcpError("agent gateway timeout must be between 1 and 600 seconds")
        if len(actor_id) > 128:
            raise PrdMcpError("MCP reconciliation actor ID exceeds 128 characters")
        if not actor_name or len(actor_name) > 128:
            raise PrdMcpError(
                "MCP reconciliation actor name must contain 1 to 128 characters"
            )
        if any(not role_id.isdigit() for role_id in actor_role_ids):
            raise PrdMcpError(
                "MCP reconciliation actor role IDs must be comma-separated integers"
            )


class StaticTokenVerifier:
    def __init__(
        self, expected_token: str, resource: str, scopes: tuple[str, ...] = ("prd:read",)
    ):
        self.expected_token = expected_token
        self.resource = resource
        self.scopes = scopes

    async def verify_token(self, token: str):
        if not hmac.compare_digest(token, self.expected_token):
            return None
        from mcp.server.auth.provider import AccessToken

        return AccessToken(
            token=token,
            client_id="neurovi-prd-client",
            scopes=list(self.scopes),
            resource=self.resource,
        )


class PrdReconciliationUpdater:
    """Forward only whitelisted workspace updates to the isolated agent."""

    def __init__(self, config: Config, gateway: AgentGateway | None = None):
        if not config.reconciliation_updates_enabled:
            raise PrdMcpError("MCP reconciliation updates are not configured")
        self.config = config
        self.gateway = gateway or AgentGateway(
            config.agent_gateway_url,
            token=config.agent_gateway_token,
            timeout_seconds=config.agent_gateway_timeout_seconds,
        )

    def start(self, e2e: str, mode: str) -> dict[str, Any]:
        normalized_mode = mode.strip().casefold().replace("_", "-")
        capabilities = {
            "main-flow": "reconcile.main-flow.start",
            "business-cases": "reconcile.business-cases.start",
        }
        if normalized_mode not in capabilities:
            raise PrdMcpError("mode must be main-flow or business-cases")
        return self._invoke(
            capabilities[normalized_mode],
            {"e2e": checked_text(e2e, "E2E identifier", MAX_IDENTIFIER_CHARS)},
        )

    def status(self, session_id: str) -> dict[str, Any]:
        return self._invoke("reconcile.status", self._session(session_id))

    def answer(self, session_id: str, answer: str) -> dict[str, Any]:
        return self._invoke(
            "reconcile.answer",
            {
                **self._session(session_id),
                "answer": checked_text(
                    answer, "answer", MAX_RECONCILIATION_TEXT_CHARS
                ),
            },
        )

    def control(self, session_id: str, action: str) -> dict[str, Any]:
        normalized = action.strip().upper()
        if normalized not in {"SKIP", "DEFER", "UNKNOWN"}:
            raise PrdMcpError("action must be SKIP, DEFER, or UNKNOWN")
        return self._invoke(
            "reconcile.control",
            {**self._session(session_id), "action": normalized},
        )

    def add_reference(self, session_id: str, reference: str) -> dict[str, Any]:
        return self._invoke(
            "reconcile.add-reference",
            {
                **self._session(session_id),
                "reference": checked_text(
                    reference, "reference", MAX_REFERENCE_CHARS
                ),
            },
        )

    def decide(
        self, session_id: str, decision: str, confirmation: str
    ) -> dict[str, Any]:
        if confirmation != "USER_CONFIRMED":
            raise PrdMcpError("confirmation must be exactly USER_CONFIRMED")
        return self._invoke(
            "reconcile.decide",
            {
                **self._session(session_id),
                "decision": checked_text(
                    decision, "decision", MAX_RECONCILIATION_TEXT_CHARS
                ),
            },
        )

    def stop(self, session_id: str, confirmation: str) -> dict[str, Any]:
        if confirmation != "STOP_SESSION":
            raise PrdMcpError("confirmation must be exactly STOP_SESSION")
        return self._invoke("reconcile.stop", self._session(session_id))

    def _session(self, session_id: str) -> dict[str, str]:
        value = checked_text(session_id, "session ID", MAX_IDENTIFIER_CHARS)
        if not re.fullmatch(r"REC-E2E-[A-Z0-9-]+(?:-(?:MF|BC))?-\d{3,}", value):
            raise PrdMcpError("session ID has an invalid reconciliation format")
        return {"session_id": value}

    def _invoke(self, capability: str, parameters: dict[str, Any]) -> dict[str, Any]:
        actor = {
            "discord_user_id": self.config.actor_id,
            "discord_user_name": self.config.actor_name,
            "discord_role_ids": list(self.config.actor_role_ids),
            "guild_id": None,
            "channel_id": None,
        }
        try:
            response = self.gateway.invoke(capability, parameters, actor)
        except AgentGatewayError as error:
            raise PrdMcpError(
                f"reconciliation agent rejected the update: {error}"
            ) from error
        return dict(
            response.raw or {"message": response.message, "status": response.status}
        )

@dataclass(frozen=True)
class Catalogs:
    documents: dict[str, dict[str, Any]]
    records: tuple[dict[str, Any], ...]
    domains: tuple[dict[str, Any], ...]
    relations: tuple[dict[str, Any], ...]
    manifest: dict[str, Any]
    inventory: dict[str, Any]


class PrdReader:
    def __init__(self, config: Config):
        self.config = config

    def _safe_file(self, relative: Path) -> Path:
        if relative.is_absolute() or ".." in relative.parts:
            raise PrdMcpError("repository path is outside the allowlist")
        candidate = self.config.root / relative
        try:
            resolved = candidate.resolve(strict=True)
        except (FileNotFoundError, OSError) as error:
            raise PrdMcpError(
                f"repository file is unavailable: {relative.as_posix()}"
            ) from error
        if not resolved.is_relative_to(self.config.root):
            raise PrdMcpError("repository path escapes the PRD checkout")
        if resolved != candidate.absolute():
            raise PrdMcpError("symlinked repository files are not exposed")
        if not resolved.is_file():
            raise PrdMcpError(
                f"repository file is unavailable: {relative.as_posix()}"
            )
        return resolved

    def _read_json(self, relative: Path) -> dict[str, Any]:
        path = self._safe_file(relative)
        if path.stat().st_size > MAX_JSON_BYTES:
            raise PrdMcpError(f"repository index is too large: {relative.as_posix()}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise PrdMcpError(
                f"repository index is invalid: {relative.as_posix()}"
            ) from error
        if not isinstance(payload, dict):
            raise PrdMcpError(
                f"repository index must be an object: {relative.as_posix()}"
            )
        return payload

    def _catalogs(self) -> Catalogs:
        document_index = self._read_json(DOCUMENT_INDEX_PATH)
        inventory = self._read_json(E2E_INVENTORY_PATH)
        manifest = self._read_json(CANONICAL_MANIFEST_PATH)
        indexed_documents = document_index.get("documents")
        domains = inventory.get("domains")
        relations = inventory.get("relations")
        records = manifest.get("documents")
        if not isinstance(indexed_documents, list):
            raise PrdMcpError("document index has no documents list")
        if inventory.get("inventory_type") != "E2E_DOMAIN_WORKLIST":
            raise PrdMcpError("E2E inventory has an unexpected authority type")
        if not isinstance(domains, list) or not isinstance(relations, list):
            raise PrdMcpError("E2E inventory is missing domains or relations")
        if not isinstance(records, list):
            raise PrdMcpError("canonical manifest has no documents list")
        documents = {
            str(item.get("document_id")): item
            for item in indexed_documents
            if isinstance(item, dict) and item.get("document_id")
        }
        for record in records:
            if not isinstance(record, dict):
                raise PrdMcpError("canonical manifest contains an invalid PRD record")
            document_id = str(record.get("primary_source_document_id", ""))
            indexed = documents.get(document_id)
            if not indexed:
                raise PrdMcpError(
                    f"canonical PRD source is absent from the catalog: {document_id}"
                )
            if (
                indexed.get("source_path") != record.get("primary_source_path")
                or indexed.get("sha256") != record.get("source_sha256")
                or indexed.get("extension") != ".md"
            ):
                raise PrdMcpError(
                    f"canonical PRD source identity does not match the catalog: {document_id}"
                )
        return Catalogs(
            documents=documents,
            records=tuple(records),
            domains=tuple(item for item in domains if isinstance(item, dict)),
            relations=tuple(item for item in relations if isinstance(item, dict)),
            manifest=manifest,
            inventory=inventory,
        )

    @staticmethod
    def _aliases(record: dict[str, Any]) -> list[str]:
        values = [
            str(record.get("document_code", "")),
            str(record.get("primary_source_document_id", "")),
            str(record.get("original_title", "")),
            str(record.get("primary_source_path", "")),
            Path(str(record.get("primary_source_path", ""))).name,
        ]
        for representation in record.get("source_representations", []):
            if not isinstance(representation, dict):
                continue
            values.extend(
                (
                    str(representation.get("document_id", "")),
                    str(representation.get("title", "")),
                    str(representation.get("source_path", "")),
                    Path(str(representation.get("source_path", ""))).name,
                )
            )
        return [value for value in values if value]

    @staticmethod
    def _record_summary(record: dict[str, Any]) -> dict[str, Any]:
        return {
            "documentCode": record.get("document_code"),
            "documentId": record.get("primary_source_document_id"),
            "contentId": record.get("content_id"),
            "title": record.get("original_title"),
            "ownerE2eCode": record.get("owner_e2e_code"),
            "ownerE2eTitle": record.get("owner_e2e_title"),
            "worklistOrder": record.get("worklist_order"),
            "worklistStage": record.get("worklist_stage"),
            "sourcePath": f"source/original/{record.get('primary_source_path', '')}",
            "sha256": record.get("source_sha256"),
            "canonicalVersion": record.get("canonical_version"),
            "semanticChanges": record.get("semantic_changes"),
            "sourceRepresentationCount": len(record.get("source_representations", [])),
        }

    def _resolve_record(
        self, catalogs: Catalogs, identifier: str
    ) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        identifier = checked_text(identifier, "identifier", MAX_IDENTIFIER_CHARS)
        folded = identifier.casefold()
        exact = [
            record
            for record in catalogs.records
            if any(alias.casefold() == folded for alias in self._aliases(record))
        ]
        if len(exact) == 1:
            return exact[0], []
        if len(exact) > 1:
            return None, [self._record_summary(record) for record in exact[:20]]
        target = normalize(identifier)
        if not target:
            raise PrdMcpError("identifier must contain letters or numbers")
        tokens = target.split()
        partial: list[dict[str, Any]] = []
        for record in catalogs.records:
            haystack = normalize(" ".join(self._aliases(record)))
            if target in haystack or (tokens and all(token in haystack for token in tokens)):
                partial.append(record)
        if len(partial) == 1:
            return partial[0], []
        return None, [self._record_summary(record) for record in partial[:20]]

    def _resolve_domain(
        self, catalogs: Catalogs, identifier: str
    ) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        identifier = checked_text(identifier, "E2E identifier", MAX_IDENTIFIER_CHARS)
        folded = identifier.casefold()
        exact = [
            domain
            for domain in catalogs.domains
            if str(domain.get("e2e_code", "")).casefold() == folded
            or str(domain.get("title", "")).casefold() == folded
        ]
        if len(exact) == 1:
            return exact[0], []
        target = normalize(identifier)
        if not target:
            raise PrdMcpError("E2E identifier must contain letters or numbers")
        tokens = target.split()
        partial = []
        for domain in catalogs.domains:
            haystack = normalize(
                " ".join(
                    (
                        str(domain.get("e2e_code", "")),
                        str(domain.get("title", "")),
                        str(domain.get("domain_group", "")),
                    )
                )
            )
            if target in haystack or (tokens and all(token in haystack for token in tokens)):
                partial.append(domain)
        candidates = [self._domain_summary(domain) for domain in (exact or partial)[:20]]
        if len(exact) == 1 or (not exact and len(partial) == 1):
            return (exact or partial)[0], []
        return None, candidates

    @staticmethod
    def _domain_summary(domain: dict[str, Any]) -> dict[str, Any]:
        return {
            "e2eCode": domain.get("e2e_code"),
            "title": domain.get("title"),
            "domainGroup": domain.get("domain_group"),
            "purpose": domain.get("purpose"),
            "status": domain.get("status"),
            "documentCount": domain.get("document_count"),
            "relationCount": domain.get("relation_count"),
            "crossDomainRelationCount": domain.get("cross_domain_relation_count"),
            "reviewRequiredCount": domain.get("review_required_count"),
        }

    def _read_source(
        self, catalogs: Catalogs, record: dict[str, Any]
    ) -> tuple[str, Path]:
        document_id = str(record.get("primary_source_document_id", ""))
        indexed = catalogs.documents.get(document_id)
        if not indexed:
            raise PrdMcpError(f"source document is not cataloged: {document_id}")
        relative = ORIGINAL_ROOT / str(record.get("primary_source_path", ""))
        path = self._safe_file(relative)
        if path.stat().st_size > MAX_SOURCE_BYTES:
            raise PrdMcpError(f"PRD source exceeds the read limit: {document_id}")
        payload = path.read_bytes()
        actual_sha = hashlib.sha256(payload).hexdigest()
        expected_sha = str(record.get("source_sha256", ""))
        if not expected_sha or actual_sha != expected_sha or actual_sha != indexed.get("sha256"):
            raise PrdMcpError(
                f"source checksum does not match the immutable catalog: {document_id}"
            )
        try:
            return payload.decode("utf-8-sig"), path
        except UnicodeDecodeError as error:
            raise PrdMcpError(f"PRD source is not UTF-8 text: {document_id}") from error

    @staticmethod
    def _heading_bounds(
        content: str, headings: list[dict[str, Any]], selected: dict[str, Any]
    ) -> tuple[int, int, int, int]:
        lines = content.splitlines(keepends=True)
        selected_index = headings.index(selected)
        start_line = max(int(selected.get("line", 1)) - 1, 0)
        end_line = len(lines)
        selected_level = int(selected.get("level", 1))
        for heading in headings[selected_index + 1 :]:
            if int(heading.get("level", 1)) <= selected_level:
                end_line = max(int(heading.get("line", 1)) - 1, start_line + 1)
                break
        expected = normalize(str(selected.get("text", "")))
        if start_line >= len(lines) or expected not in normalize(lines[start_line]):
            matching = [
                index
                for index, line in enumerate(lines)
                if normalize(re.sub(r"^\s*#+\s*", "", line)) == expected
            ]
            if not matching:
                raise PrdMcpError(
                    f"catalog heading cannot be found in source: {selected.get('text', '')}"
                )
            offset = matching[0] - start_line
            start_line += offset
            end_line = min(len(lines), end_line + offset)
        start_char = sum(len(line) for line in lines[:start_line])
        end_char = sum(len(line) for line in lines[:end_line])
        return start_line + 1, end_line, start_char, end_char

    def _section(
        self,
        catalogs: Catalogs,
        record: dict[str, Any],
        content: str,
        selector: str,
    ) -> tuple[str, dict[str, Any]]:
        indexed = catalogs.documents[str(record["primary_source_document_id"])]
        headings = [
            heading
            for heading in indexed.get("headings", [])
            if isinstance(heading, dict) and heading.get("text")
        ]
        if not headings:
            raise PrdMcpError("this PRD has no cataloged headings")
        target = normalize(checked_text(selector, "section", MAX_IDENTIFIER_CHARS))
        if not target:
            raise PrdMcpError("section must contain letters or numbers")
        exact = [heading for heading in headings if normalize(str(heading["text"])) == target]
        matches = exact or [
            heading for heading in headings if target in normalize(str(heading["text"]))
        ]
        if len(matches) != 1:
            candidates = ", ".join(str(item.get("text")) for item in matches[:10])
            if matches:
                raise PrdMcpError(f"section is ambiguous; candidates: {candidates}")
            raise PrdMcpError("section was not found; call get_prd without a section for headings")
        selected = matches[0]
        start_line, end_line, start_char, end_char = self._heading_bounds(
            content, headings, selected
        )
        return content[start_char:end_char], {
            "heading": selected.get("text"),
            "level": selected.get("level"),
            "startLine": start_line,
            "endLine": end_line,
        }

    def _section_by_heading(
        self,
        catalogs: Catalogs,
        record: dict[str, Any],
        content: str,
        heading_text: str,
    ) -> tuple[str, dict[str, Any]] | None:
        try:
            return self._section(catalogs, record, content, heading_text)
        except PrdMcpError:
            return None

    @staticmethod
    def _best_match(content: str, query: str) -> tuple[int, int, str, str]:
        normalized_query = normalize(query)
        query_tokens = set(normalized_query.split())
        heading = ""
        best_score = 0
        best_line = 1
        best_heading = ""
        best_excerpt = ""
        lines = content.splitlines()
        for number, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                heading = stripped.lstrip("#").strip()
            normalized_line = normalize(stripped)
            if not normalized_line:
                continue
            if normalized_line == normalized_query:
                score = 140
            elif normalized_query in normalized_line:
                score = 115
            else:
                overlap = len(query_tokens & set(normalized_line.split()))
                score = 35 + overlap * 14 if overlap else 0
                if query_tokens and query_tokens.issubset(set(normalized_line.split())):
                    score += 20
            if score > best_score:
                start = max(0, number - 2)
                end = min(len(lines), number + 2)
                excerpt, _ = bounded(
                    "\n".join(item.rstrip() for item in lines[start:end]).strip(),
                    MAX_EXCERPT_CHARS,
                )
                best_score = score
                best_line = number
                best_heading = heading
                best_excerpt = excerpt
        return best_score, best_line, best_heading, best_excerpt

    def prd_status(self) -> dict[str, Any]:
        catalogs = self._catalogs()
        return {
            "status": "OK",
            "readOnly": True,
            "writeTools": False,
            "arbitraryPathAccess": False,
            "shellAccess": False,
            "gitMutation": False,
            "outboundNetworkTools": False,
            "sourceAuthority": "source/original plus immutable catalog checksums",
            "sourceChecksumVerification": "EVERY_PRD_READ",
            "canonicalVersion": catalogs.manifest.get("canonical_version"),
            "baselineStatus": catalogs.manifest.get("baseline_status"),
            "releaseStatus": catalogs.manifest.get("release_status"),
            "counts": {
                "eligibleFiles": catalogs.manifest.get("eligible_file_count"),
                "uniquePrds": len(catalogs.records),
                "e2eDomains": len(catalogs.domains),
                "relations": len(catalogs.relations),
                "crossDomainRelations": catalogs.inventory.get(
                    "cross_domain_relation_count"
                ),
                "sourceExplicitRelations": sum(
                    1
                    for relation in catalogs.relations
                    if relation.get("verification_status") == "SOURCE_EXPLICIT"
                ),
                "reviewRequiredRelations": sum(
                    1
                    for relation in catalogs.relations
                    if relation.get("verification_status") == "REVIEW_REQUIRED"
                ),
            },
            "evidenceNotice": (
                "Original PRD text is authoritative. Canonical and E2E artifacts provide "
                "identity, worklist, coverage, and relation context without adding facts."
            ),
        }

    def validate_repository(self, *, deep: bool = False) -> dict[str, Any]:
        catalogs = self._catalogs()
        verified = 0
        if deep:
            for record in catalogs.records:
                self._read_source(catalogs, record)
                verified += 1
        return {
            **self.prd_status(),
            "validation": "DEEP" if deep else "INDEX_ONLY",
            "verifiedSourceCount": verified,
        }

    def search_prds(
        self, query: str, e2e: str = "", limit: int = 10
    ) -> dict[str, Any]:
        query = checked_text(query, "query", MAX_QUERY_CHARS)
        limit = checked_limit(limit, maximum=20)
        normalized_query = normalize(query)
        if not normalized_query:
            raise PrdMcpError("query must contain letters or numbers")
        catalogs = self._catalogs()
        domain = None
        allowed_ids: set[str] | None = None
        if e2e.strip():
            domain, candidates = self._resolve_domain(catalogs, e2e)
            if not domain:
                return {
                    "status": "AMBIGUOUS" if candidates else "NO_MATCH",
                    "query": query,
                    "e2eCandidates": candidates,
                    "results": [],
                }
            allowed_ids = {
                str(item.get("document_id")) for item in domain.get("documents", [])
            }
        query_tokens = set(normalized_query.split())
        ranked: list[tuple[int, str, dict[str, Any]]] = []
        for record in catalogs.records:
            document_id = str(record.get("primary_source_document_id", ""))
            if allowed_ids is not None and document_id not in allowed_ids:
                continue
            metadata = normalize(" ".join(self._aliases(record)))
            metadata_score = 0
            if normalized_query in {
                normalize(str(record.get("document_code", ""))),
                normalize(document_id),
            }:
                metadata_score = 180
            elif normalized_query in normalize(str(record.get("original_title", ""))):
                metadata_score = 140
            elif normalized_query in metadata:
                metadata_score = 110
            elif query_tokens and query_tokens.issubset(set(metadata.split())):
                metadata_score = 95
            content, _ = self._read_source(catalogs, record)
            content_score, line, heading, excerpt = self._best_match(content, query)
            score = max(metadata_score, content_score)
            if not score:
                continue
            result = self._record_summary(record) | {
                "score": score,
                "match": {
                    "sourceReference": (
                        f"source/original/{record.get('primary_source_path')}:{line}"
                    ),
                    "heading": heading or None,
                    "excerpt": excerpt,
                },
            }
            ranked.append((score, str(record.get("document_code", "")), result))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return {
            "status": "MATCHED" if ranked else "NO_MATCH",
            "query": query,
            "e2e": self._domain_summary(domain) if domain else None,
            "results": [result for _, _, result in ranked[:limit]],
            "truncated": len(ranked) > limit,
        }

    def get_prd(
        self,
        identifier: str,
        section: str = "",
        offset: int = 0,
        max_chars: int = 12_000,
    ) -> dict[str, Any]:
        if offset < 0:
            raise PrdMcpError("offset must be zero or positive")
        max_content_chars = min(MAX_CONTENT_CHARS, self.config.max_response_chars)
        if max_chars < 1 or max_chars > max_content_chars:
            raise PrdMcpError(
                f"max_chars must be between 1 and {max_content_chars}"
            )
        catalogs = self._catalogs()
        record, candidates = self._resolve_record(catalogs, identifier)
        if not record:
            return {
                "status": "AMBIGUOUS" if candidates else "NO_MATCH",
                "identifier": identifier,
                "candidates": candidates,
            }
        content, _ = self._read_source(catalogs, record)
        section_metadata = None
        if section.strip():
            content, section_metadata = self._section(catalogs, record, content, section)
        total_chars = len(content)
        if offset > total_chars:
            raise PrdMcpError(f"offset exceeds content length {total_chars}")
        chunk = content[offset : offset + max_chars]
        next_offset = offset + len(chunk)
        indexed = catalogs.documents[str(record["primary_source_document_id"])]
        return {
            "status": "OK",
            "document": self._record_summary(record),
            "representation": "direct-original-markdown",
            "section": section_metadata,
            "headings": [
                {
                    "level": heading.get("level"),
                    "heading": heading.get("text"),
                    "line": heading.get("line"),
                }
                for heading in indexed.get("headings", [])
                if isinstance(heading, dict)
            ],
            "content": chunk,
            "offset": offset,
            "returnedChars": len(chunk),
            "totalChars": total_chars,
            "nextOffset": next_offset if next_offset < total_chars else None,
            "truncated": next_offset < total_chars,
        }

    def get_e2e_context(
        self,
        identifier: str,
        include_relations: bool = True,
        document_offset: int = 0,
        document_limit: int = 25,
        relation_limit: int = 50,
    ) -> dict[str, Any]:
        if document_offset < 0:
            raise PrdMcpError("document_offset must be zero or positive")
        document_limit = checked_limit(document_limit, maximum=50)
        relation_limit = checked_limit(relation_limit, maximum=MAX_RELATIONS)
        catalogs = self._catalogs()
        domain, candidates = self._resolve_domain(catalogs, identifier)
        if not domain:
            return {
                "status": "AMBIGUOUS" if candidates else "NO_MATCH",
                "identifier": identifier,
                "candidates": candidates,
            }
        records_by_id = {
            str(record.get("primary_source_document_id")): record
            for record in catalogs.records
        }
        all_documents = list(domain.get("documents", []))
        if document_offset > len(all_documents):
            raise PrdMcpError(
                f"document_offset exceeds worklist length {len(all_documents)}"
            )
        visible_documents = all_documents[document_offset : document_offset + document_limit]
        worklist = []
        for item in visible_documents:
            record = records_by_id.get(str(item.get("document_id", "")))
            worklist.append(
                {
                    "document": self._record_summary(record) if record else {
                        "documentId": item.get("document_id"),
                        "title": item.get("title"),
                    },
                    "assignmentStatus": item.get("assignment_status"),
                    "assignmentConfidence": item.get("assignment_confidence"),
                    "assignmentBasis": item.get("assignment_basis"),
                    "reviewStatus": item.get("review_status"),
                    "flowChecks": item.get("flow_checks", {}),
                }
            )
        relation_ids = set(domain.get("relation_ids", []))
        relation_rows = [
            relation
            for relation in catalogs.relations
            if relation.get("relation_id") in relation_ids
        ]
        relations, relations_truncated = self._bounded_relations(
            relation_rows if include_relations else [],
            limit=relation_limit,
            char_budget=max(4_000, self.config.max_response_chars // 3),
            excerpt_limit=500,
        )
        return {
            "status": "OK",
            "evidenceNotice": (
                "This is a review worklist. Mechanical assignments and REVIEW_REQUIRED "
                "relations are context candidates, not approved business facts."
            ),
            "e2e": self._domain_summary(domain),
            "worklist": worklist,
            "documentOffset": document_offset,
            "nextDocumentOffset": (
                document_offset + len(worklist)
                if document_offset + len(worklist) < len(all_documents)
                else None
            ),
            "worklistTruncated": document_offset + len(worklist) < len(all_documents),
            "relations": relations,
            "relationsTruncated": relations_truncated,
        }

    @staticmethod
    def _relation_summary(
        relation: dict[str, Any], excerpt_limit: int = MAX_EXCERPT_CHARS
    ) -> dict[str, Any]:
        excerpt, excerpt_truncated = bounded(
            str(relation.get("evidence_excerpt", "")), excerpt_limit
        )
        return {
            "relationId": relation.get("relation_id"),
            "sourceDocumentId": relation.get("source_document_id"),
            "sourceTitle": relation.get("source_title"),
            "sourceE2eCode": relation.get("source_domain_code"),
            "relationshipType": relation.get("relationship_type"),
            "targetDocumentId": relation.get("target_document_id"),
            "targetTitle": relation.get("target_title"),
            "targetE2eCode": relation.get("target_domain_code"),
            "relationScope": relation.get("relation_scope"),
            "verificationStatus": relation.get("verification_status"),
            "evidenceClass": relation.get("evidence_class"),
            "conflictStatus": relation.get("conflict_status"),
            "condition": relation.get("condition"),
            "statusTransition": relation.get("status_transition"),
            "evidenceReference": relation.get("evidence_reference"),
            "evidenceExcerpt": excerpt,
            "evidenceExcerptTruncated": excerpt_truncated,
        }

    def _bounded_relations(
        self,
        relations: Iterable[dict[str, Any]],
        *,
        limit: int,
        char_budget: int,
        excerpt_limit: int,
    ) -> tuple[list[dict[str, Any]], bool]:
        rows = list(relations)
        selected: list[dict[str, Any]] = []
        used = 0
        for relation in rows[:limit]:
            summary = self._relation_summary(relation, excerpt_limit)
            size = len(json.dumps(summary, ensure_ascii=False))
            if selected and used + size > char_budget:
                break
            selected.append(summary)
            used += size
        return selected, len(selected) < len(rows)

    def get_task_context(
        self,
        task: str,
        e2e: str = "",
        document_limit: int = 5,
        section_families: list[str] | None = None,
    ) -> dict[str, Any]:
        task = checked_text(task, "task", MAX_QUERY_CHARS)
        document_limit = checked_limit(document_limit, maximum=MAX_TASK_DOCUMENTS)
        requested = list(
            DEFAULT_TASK_SECTION_FAMILIES
            if section_families is None
            else section_families
        )
        if not requested or len(requested) > len(SECTION_FAMILIES):
            raise PrdMcpError("section_families must contain 1 to 8 values")
        unknown = sorted(set(requested) - SECTION_FAMILIES)
        if unknown:
            raise PrdMcpError(
                f"unsupported section families: {', '.join(unknown)}"
            )
        search = self.search_prds(task, e2e=e2e, limit=document_limit)
        if search["status"] != "MATCHED":
            return search | {"task": task, "documents": []}
        catalogs = self._catalogs()
        records_by_id = {
            str(record.get("primary_source_document_id")): record
            for record in catalogs.records
        }
        # Reserve space for metadata, task evidence, and relation summaries.
        remaining = max(2_000, self.config.max_response_chars - 24_000)
        documents = []
        included_ids = []
        context_truncated = False
        section_content_truncated = False
        for search_result in search["results"]:
            record = records_by_id[str(search_result["documentId"])]
            included_ids.append(str(search_result["documentId"]))
            content, _ = self._read_source(catalogs, record)
            coverage = {
                str(item.get("section_family")): item
                for item in record.get("standard_section_map", [])
                if isinstance(item, dict) and item.get("section_family")
            }
            sections = []
            per_section_limit = min(2_400, max(600, remaining // max(1, len(requested))))
            for family in requested:
                mapping = coverage.get(family, {})
                matched_headings = [
                    str(value) for value in mapping.get("matched_headings", []) if value
                ]
                section_documents = []
                for heading in matched_headings[:2]:
                    extracted = self._section_by_heading(
                        catalogs, record, content, heading
                    )
                    if not extracted:
                        continue
                    section_content, metadata = extracted
                    excerpt, truncated = bounded(section_content, per_section_limit)
                    section_content_truncated = section_content_truncated or truncated
                    section_documents.append(
                        metadata
                        | {
                            "sourceReference": (
                                f"source/original/{record.get('primary_source_path')}:"
                                f"{metadata['startLine']}"
                            ),
                            "content": excerpt,
                            "truncated": truncated,
                        }
                    )
                    remaining -= len(excerpt)
                    if remaining <= 0:
                        context_truncated = True
                        break
                sections_truncated = len(section_documents) < len(matched_headings)
                section_content_truncated = (
                    section_content_truncated or sections_truncated
                )
                sections.append(
                    {
                        "family": family,
                        "label": mapping.get("label"),
                        "coverageStatus": mapping.get(
                            "status", "NO_MATCHING_SOURCE_HEADING_DETECTED"
                        ),
                        "matchedHeadings": matched_headings,
                        "sections": section_documents,
                        "sectionsTruncated": sections_truncated,
                    }
                )
                if context_truncated:
                    break
            documents.append(
                {
                    "document": self._record_summary(record),
                    "taskMatch": search_result["match"],
                    "sectionContext": sections,
                }
            )
            if context_truncated:
                break
        selected_set = set(included_ids)
        relation_rows = [
            relation
            for relation in catalogs.relations
            if str(relation.get("source_document_id")) in selected_set
            or str(relation.get("target_document_id")) in selected_set
        ]
        relation_rows.sort(
            key=lambda relation: (
                relation.get("verification_status") != "SOURCE_EXPLICIT",
                str(relation.get("relation_id", "")),
            )
        )
        relation_limit = min(30, len(relation_rows))
        relations, relations_truncated = self._bounded_relations(
            relation_rows,
            limit=relation_limit,
            char_budget=min(12_000, self.config.max_response_chars // 4),
            excerpt_limit=500,
        )
        owner_counts = Counter(
            str(records_by_id[document_id].get("owner_e2e_code", ""))
            for document_id in included_ids
        )
        return {
            "status": "OK",
            "task": task,
            "requestedE2e": search.get("e2e"),
            "inferredE2eCandidates": [
                {"e2eCode": code, "matchedDocumentCount": count}
                for code, count in owner_counts.most_common()
                if code
            ],
            "evidenceNotice": (
                "Every content fragment below is literal original PRD text. Section coverage "
                "and E2E ownership are generated navigation metadata. REVIEW_REQUIRED or "
                "mechanical relations must not be treated as approved requirements."
            ),
            "documents": documents,
            "relations": relations,
            "relationsTruncated": relations_truncated,
            "contextTruncated": context_truncated or section_content_truncated,
            "continuation": (
                "Call get_prd with documentCode/documentId and section or nextOffset to read "
                "the complete immutable source when a returned fragment is truncated."
            ),
        }

    def trace_prd_relations(
        self,
        identifier: str,
        direction: str = "both",
        depth: int = 1,
        evidence: str = "all",
        limit: int = 50,
    ) -> dict[str, Any]:
        direction = direction.strip().lower()
        if direction not in {"incoming", "outgoing", "both"}:
            raise PrdMcpError("direction must be incoming, outgoing, or both")
        if depth < 1 or depth > 2:
            raise PrdMcpError("depth must be 1 or 2")
        evidence = evidence.strip().lower()
        if evidence not in {"all", "source-explicit", "review-required"}:
            raise PrdMcpError(
                "evidence must be all, source-explicit, or review-required"
            )
        limit = checked_limit(limit, maximum=MAX_RELATIONS)
        catalogs = self._catalogs()
        record, candidates = self._resolve_record(catalogs, identifier)
        if not record:
            return {
                "status": "AMBIGUOUS" if candidates else "NO_MATCH",
                "identifier": identifier,
                "candidates": candidates,
                "relations": [],
            }
        root_id = str(record.get("primary_source_document_id"))
        relations = list(catalogs.relations)
        if evidence == "source-explicit":
            relations = [
                relation
                for relation in relations
                if relation.get("verification_status") == "SOURCE_EXPLICIT"
            ]
        elif evidence == "review-required":
            relations = [
                relation
                for relation in relations
                if relation.get("verification_status") == "REVIEW_REQUIRED"
            ]
        frontier = {root_id}
        visited = {root_id}
        selected = []
        seen: set[str] = set()
        truncated = False
        for _ in range(depth):
            next_frontier: set[str] = set()
            for relation in relations:
                source = str(relation.get("source_document_id", ""))
                target = str(relation.get("target_document_id", ""))
                include = (
                    direction in {"outgoing", "both"} and source in frontier
                ) or (direction in {"incoming", "both"} and target in frontier)
                if not include:
                    continue
                relation_id = str(relation.get("relation_id", ""))
                if relation_id not in seen:
                    selected.append(relation)
                    seen.add(relation_id)
                next_frontier.update((source, target))
                if len(selected) >= limit:
                    truncated = True
                    break
            visited.update(next_frontier)
            frontier = next_frontier
            if truncated or not frontier:
                break
        records_by_id = {
            str(item.get("primary_source_document_id")): item
            for item in catalogs.records
        }
        relation_summaries, response_truncated = self._bounded_relations(
            selected,
            limit=limit,
            char_budget=max(4_000, self.config.max_response_chars // 2),
            excerpt_limit=600,
        )
        return {
            "status": "OK",
            "root": self._record_summary(record),
            "direction": direction,
            "depth": depth,
            "evidenceFilter": evidence,
            "relations": relation_summaries,
            "nodes": [
                self._record_summary(records_by_id[node_id])
                if node_id in records_by_id
                else {"documentId": node_id, "eligiblePrd": False}
                for node_id in sorted(visited)
                if node_id
            ],
            "truncated": truncated or response_truncated,
        }


def build_server(config: Config):
    warnings.filterwarnings(
        "ignore",
        message="Field .* has an incomplete definition.*",
        module="pydantic_settings.sources.utils",
    )
    try:
        from mcp.server.auth.settings import AuthSettings
        from mcp.server.fastmcp import FastMCP
        from mcp.server.transport_security import TransportSecuritySettings
        from starlette.responses import JSONResponse
    except ImportError as error:
        raise PrdMcpError("MCP SDK is unavailable; install the mcp extra") from error
    reader = PrdReader(config)
    updater = (
        PrdReconciliationUpdater(config)
        if config.reconciliation_updates_enabled
        else None
    )
    auth_scopes = (
        ("prd:read", "prd:reconcile") if updater is not None else ("prd:read",)
    )
    parsed_url = urlparse(config.public_url)
    origin = f"{parsed_url.scheme}://{parsed_url.netloc}"
    server = FastMCP(
        "neurovi-prd-reconciliation" if updater is not None else "neurovi-prd-readonly",
        instructions=(
            "Neurovi PRD context for implementation and controlled reconciliation. "
            "Original PRD text is authoritative. Resolve the task and E2E context, "
            "inspect literal sections, and distinguish SOURCE_EXPLICIT evidence from "
            "REVIEW_REQUIRED mechanical candidates. When reconciliation tools are "
            "enabled, they update only audited session/register artifacts through the "
            "isolated agent. No tool edits source/original, executes shell commands, "
            "mutates Git, publishes a baseline, or reads arbitrary paths."
        ),
        log_level="WARNING",
        host=config.bind_host,
        port=config.port,
        streamable_http_path=parsed_url.path,
        json_response=True,
        stateless_http=True,
        max_request_body_size=262_144,
        token_verifier=StaticTokenVerifier(
            config.token, config.public_url, auth_scopes
        ),
        auth=AuthSettings(
            issuer_url=origin,
            resource_server_url=config.public_url,
            required_scopes=list(auth_scopes),
        ),
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[
                parsed_url.netloc,
                f"{config.bind_host}:{config.port}",
                "127.0.0.1:*",
                "localhost:*",
            ],
            allowed_origins=[origin],
        ),
    )

    @server.custom_route("/healthz", methods=["GET"], include_in_schema=False)
    async def healthz(_request):
        return JSONResponse(
            {
                "status": "OK",
                "readOnly": updater is None,
                "writeTools": updater is not None,
            }
        )

    @server.tool()
    def prd_status() -> dict[str, Any]:
        """Return PRD/E2E counts, source authority, and enforced MCP controls."""
        try:
            result = reader.prd_status()
            result.update(
                {
                    "readOnly": updater is None,
                    "writeTools": updater is not None,
                    "reconciliationWorkspaceUpdates": updater is not None,
                    "originalSourceMutation": False,
                    "canonicalPublish": False,
                    "fixedAgentGateway": updater is not None,
                }
            )
            return result
        except Exception as error:
            return {"status": "ERROR", "error": public_error(error)}

    @server.tool()
    def search_prds(query: str, e2e: str = "", limit: int = 10) -> dict[str, Any]:
        """Search eligible original PRDs and return checksum-verified literal excerpts."""
        try:
            return reader.search_prds(query, e2e, limit)
        except Exception as error:
            return {"status": "ERROR", "error": public_error(error)}

    @server.tool()
    def get_prd(
        identifier: str,
        section: str = "",
        offset: int = 0,
        max_chars: int = 12_000,
    ) -> dict[str, Any]:
        """Read an original PRD incrementally by stable ID, heading, and offset."""
        try:
            return reader.get_prd(identifier, section, offset, max_chars)
        except Exception as error:
            return {"status": "ERROR", "error": public_error(error)}

    @server.tool()
    def get_e2e_context(
        identifier: str,
        include_relations: bool = True,
        document_offset: int = 0,
        document_limit: int = 25,
        relation_limit: int = 50,
    ) -> dict[str, Any]:
        """Return one E2E owner worklist, flow coverage, and bounded relation evidence."""
        try:
            return reader.get_e2e_context(
                identifier,
                include_relations,
                document_offset,
                document_limit,
                relation_limit,
            )
        except Exception as error:
            return {"status": "ERROR", "error": public_error(error)}

    @server.tool()
    def get_task_context(
        task: str,
        e2e: str = "",
        document_limit: int = 5,
        section_families: list[str] | None = None,
    ) -> dict[str, Any]:
        """Assemble literal PRD sections, E2E ownership, and relations relevant to a task."""
        try:
            return reader.get_task_context(
                task, e2e, document_limit, section_families
            )
        except Exception as error:
            return {"status": "ERROR", "error": public_error(error)}

    @server.tool()
    def trace_prd_relations(
        identifier: str,
        direction: str = "both",
        depth: int = 1,
        evidence: str = "all",
        limit: int = 50,
    ) -> dict[str, Any]:
        """Trace bounded incoming/outgoing PRD relations with explicit evidence status."""
        try:
            return reader.trace_prd_relations(
                identifier, direction, depth, evidence, limit
            )
        except Exception as error:
            return {"status": "ERROR", "error": public_error(error)}

    if updater is not None:

        @server.tool()
        def start_prd_reconciliation(
            e2e: str, mode: str = "main-flow"
        ) -> dict[str, Any]:
            """Start or resume a mode-isolated audited reconciliation session."""
            try:
                return updater.start(e2e, mode)
            except Exception as error:
                return {"status": "ERROR", "error": public_error(error)}

        @server.tool()
        def get_prd_reconciliation_status(session_id: str) -> dict[str, Any]:
            """Return the saved state and current question for a reconciliation session."""
            try:
                return updater.status(session_id)
            except Exception as error:
                return {"status": "ERROR", "error": public_error(error)}

        @server.tool()
        def answer_prd_reconciliation(
            session_id: str, answer: str
        ) -> dict[str, Any]:
            """Save a non-final answer and ask the agent for the next controlled step."""
            try:
                return updater.answer(session_id, answer)
            except Exception as error:
                return {"status": "ERROR", "error": public_error(error)}

        @server.tool()
        def control_prd_reconciliation(
            session_id: str, action: str
        ) -> dict[str, Any]:
            """Mark the current question as SKIP, DEFER, or UNKNOWN without guessing."""
            try:
                return updater.control(session_id, action)
            except Exception as error:
                return {"status": "ERROR", "error": public_error(error)}

        @server.tool()
        def add_prd_reconciliation_reference(
            session_id: str, reference: str
        ) -> dict[str, Any]:
            """Register supporting evidence without promoting it to source authority."""
            try:
                return updater.add_reference(session_id, reference)
            except Exception as error:
                return {"status": "ERROR", "error": public_error(error)}

        @server.tool()
        def confirm_prd_reconciliation_decision(
            session_id: str, decision: str, confirmation: str
        ) -> dict[str, Any]:
            """Record a semantic decision only with confirmation=USER_CONFIRMED."""
            try:
                return updater.decide(session_id, decision, confirmation)
            except Exception as error:
                return {"status": "ERROR", "error": public_error(error)}

        @server.tool()
        def stop_prd_reconciliation(
            session_id: str, confirmation: str
        ) -> dict[str, Any]:
            """Stop the session only with confirmation=STOP_SESSION; never publish."""
            try:
                return updater.stop(session_id, confirmation)
            except Exception as error:
                return {"status": "ERROR", "error": public_error(error)}

    return server


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", help="path to the Neurovi PRD repository")
    parser.add_argument(
        "command", choices=("serve", "validate"), nargs="?", default="serve"
    )
    parser.add_argument(
        "--deep", action="store_true", help="verify every eligible original checksum"
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        config = Config.from_environment(
            args.repo, require_http=args.command == "serve"
        )
        reader = PrdReader(config)
        if args.command == "validate":
            print(
                json.dumps(
                    reader.validate_repository(deep=args.deep),
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            return 0
        reader.prd_status()
        build_server(config).run(transport="streamable-http")
        return 0
    except (OSError, PrdMcpError) as error:
        print(f"ERROR: {public_error(error)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
