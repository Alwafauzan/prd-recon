from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

import scripts.build_e2e_inventory as e2e_inventory

from neurovi_prd_server.agent_gateway import AgentGateway, AgentGatewayError
from neurovi_prd_server.agent_server import ReconciliationHTTPServer
from neurovi_prd_server.capabilities import CapabilityError, CapabilityRunner
from neurovi_prd_server.config import ConfigurationError, Settings
from neurovi_prd_server.discord_bot import (
    guided_gap_summary,
    guided_process_summary,
    is_allowed_bot_context,
    is_allowed_discord_context,
    is_allowed_help_message_context,
    latest_reconciliation_session_for_user,
    load_e2e_options,
    match_e2e_options,
    plain_language_agent_message,
    plain_language_gateway_error,
    plain_language_question,
    processing_state_text,
    reconciliation_question_kind,
    reconciliation_resume_request,
)
from neurovi_prd_server.help_system import (
    answer_help,
    build_help_thread_name,
    is_help_context,
    is_plain_help_request,
    is_help_session_thread,
    render_contextual_help,
    strip_bot_mention,
)
from neurovi_prd_server.llm_client import LLMResult, OpenAICompatibleLLM
from neurovi_prd_server.reconciliation_agent import (
    AGENT_CAPABILITIES,
    ReconciliationAgent,
    ReconciliationAgentError,
    SessionStore,
)


TOOLS_REPO = Path(__file__).resolve().parents[1]
DOCUMENT_REPO = TOOLS_REPO / "neurovi-prd"


class SettingsTests(unittest.TestCase):
    def test_repository_is_detected(self) -> None:
        settings = Settings.from_env(DOCUMENT_REPO, TOOLS_REPO)
        settings.require_repository()
        settings.require_tools()
        self.assertEqual(settings.repo_root, DOCUMENT_REPO)
        self.assertEqual(settings.tools_root, TOOLS_REPO)

    def test_reconciliation_is_disabled_by_default(self) -> None:
        old_reconcile = os.environ.pop(
            "NEUROVI_DISCORD_RECONCILE_ROLE_IDS", None
        )
        old_approver = os.environ.pop(
            "NEUROVI_DISCORD_APPROVER_ROLE_IDS", None
        )
        try:
            settings = Settings.from_env(DOCUMENT_REPO, TOOLS_REPO)
            self.assertEqual(settings.discord_reconcile_role_ids, frozenset())
            self.assertEqual(settings.discord_approver_role_ids, frozenset())
        finally:
            if old_reconcile is not None:
                os.environ["NEUROVI_DISCORD_RECONCILE_ROLE_IDS"] = old_reconcile
            if old_approver is not None:
                os.environ["NEUROVI_DISCORD_APPROVER_ROLE_IDS"] = old_approver


    def test_allowed_channel_scope_is_loaded(self) -> None:
        original = os.environ.get("NEUROVI_DISCORD_ALLOWED_CHANNEL_IDS")
        try:
            os.environ["NEUROVI_DISCORD_ALLOWED_CHANNEL_IDS"] = "123, 456"
            settings = Settings.from_env(DOCUMENT_REPO, TOOLS_REPO)
            self.assertEqual(
                settings.discord_allowed_channel_ids, frozenset({123, 456})
            )
        finally:
            if original is None:
                os.environ.pop("NEUROVI_DISCORD_ALLOWED_CHANNEL_IDS", None)
            else:
                os.environ["NEUROVI_DISCORD_ALLOWED_CHANNEL_IDS"] = original

    def test_reconciliation_agent_settings_are_loaded(self) -> None:
        values = {
            "NEUROVI_AGENT_GATEWAY_TOKEN": "internal-secret",
            "NEUROVI_LLM_PROVIDER": "9router",
            "NEUROVI_LLM_BASE_URL": "https://router.example/v1",
            "NEUROVI_LLM_API_KEY": "secret-value",
            "NEUROVI_LLM_MODEL": "model-name",
            "NEUROVI_LLM_REASONING_EFFORT": "high",
        }
        original = {key: os.environ.get(key) for key in values}
        try:
            os.environ.update(values)
            settings = Settings.from_env(DOCUMENT_REPO, TOOLS_REPO)
            settings.require_reconciliation_agent()
            self.assertEqual(
                settings.reconciliation_model_profile(),
                {
                    "provider": "9router",
                    "model": "model-name",
                    "reasoning_effort": "high",
                },
            )
            self.assertEqual(settings.llm_base_url, "https://router.example/v1")
            self.assertEqual(settings.llm_api_key, "secret-value")
            self.assertNotIn("api_key", settings.reconciliation_model_profile())
        finally:
            for key, value in original.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_invalid_reasoning_effort_is_rejected(self) -> None:
        original = os.environ.get("NEUROVI_LLM_REASONING_EFFORT")
        try:
            os.environ["NEUROVI_LLM_REASONING_EFFORT"] = "extreme"
            with self.assertRaises(ConfigurationError):
                Settings.from_env(DOCUMENT_REPO, TOOLS_REPO)
        finally:
            if original is None:
                os.environ.pop("NEUROVI_LLM_REASONING_EFFORT", None)
            else:
                os.environ["NEUROVI_LLM_REASONING_EFFORT"] = original


class DomainWorklistInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.inventory = json.loads(
            (
                DOCUMENT_REPO
                / "reconciliation/e2e-inventory/domain-worklist.json"
            ).read_text(encoding="utf-8")
        )

    def test_every_unique_prd_has_exactly_one_owner_domain(self) -> None:
        content_ids = [
            item["content_id"]
            for domain in self.inventory["domains"]
            for item in domain["documents"]
        ]
        self.assertEqual(self.inventory["eligible_file_count"], 212)
        self.assertEqual(self.inventory["unique_prd_count"], 209)
        self.assertEqual(self.inventory["assigned_unique_prd_count"], 209)
        self.assertEqual(self.inventory["unassigned_unique_prd_count"], 0)
        self.assertEqual(len(content_ids), 209)
        self.assertEqual(len(content_ids), len(set(content_ids)))

    def test_duplicate_representations_share_one_owner(self) -> None:
        duplicates = [
            item
            for domain in self.inventory["domains"]
            for item in domain["documents"]
            if len(item["source_representations"]) > 1
        ]
        self.assertEqual(len(duplicates), 3)
        self.assertTrue(all(item["content_id"] for item in duplicates))

    def test_rawat_jalan_to_rawat_inap_relations_are_retained(self) -> None:
        relations = self.inventory["relations"]
        dashboard = "DOC-68FE75DBEC8D1F4A"
        targets = {
            (row["target_document_id"], row["relationship_type"])
            for row in relations
            if row["source_document_id"] == dashboard
            and row["evidence_class"] == "CROSS_SOURCE_FACT"
        }
        self.assertIn(("DOC-EB811D1305DA5C1F", "ENTRY_POINT_TO"), targets)
        self.assertIn(("DOC-CE0AC26D467B9B2B", "HANDOFF_TO"), targets)
        self.assertTrue(
            any(
                row["conflict_status"] == "CONFLICT_FOUND"
                and row["source_document_id"] == "DOC-EB811D1305DA5C1F"
                and row["target_document_id"] == "DOC-7DBDDA3A09C703D1"
                for row in relations
            )
        )

    def test_safe_operational_cross_domain_relations_are_source_explicit(self) -> None:
        active = {
            (row["source_title"], row["target_title"], row["relationship_type"])
            for row in self.inventory["relations"]
            if row["evidence_class"] == "CROSS_SOURCE_FACT"
            and row["verification_status"] == "SOURCE_EXPLICIT"
            and row["conflict_status"] == "NO_CONFLICT_IDENTIFIED"
        }
        expected = {
            ("Dashboard Pelayanan IGD", "PRD — Transfer Internal", "ENTRY_POINT_TO"),
            ("Dashboard Pelayanan IGD", "PRD — Order Hemodialisa", "ENTRY_POINT_TO"),
            (
                "PRD — Dashboard Pelayanan Rawat Inap Neurovi v2",
                "PRD — Order Hemodialisa",
                "ENTRY_POINT_TO",
            ),
            (
                "PRD — Pendaftaran Rawat Jalan",
                "PRD — Order Hemodialisa",
                "ENTRY_POINT_TO",
            ),
            (
                "Dashboard Pelayanan IGD",
                "PRD — Order Pemeriksaan Laboratorium",
                "ENTRY_POINT_TO",
            ),
            (
                "PRD — Dashboard Pelayanan Rawat Inap Neurovi v2",
                "PRD — Order Pemeriksaan Laboratorium",
                "ENTRY_POINT_TO",
            ),
            (
                "Dashboard Pelayanan IGD",
                "PRD — Order Retur Obat dan Alat Kesehatan",
                "ENTRY_POINT_TO",
            ),
            (
                "PRD — Dashboard Pelayanan Rawat Inap Neurovi v2",
                "PRD — Order Retur Obat dan Alat Kesehatan",
                "ENTRY_POINT_TO",
            ),
            (
                "PRD — Dashboard Retur Farmasi IGD dan Rawat Inap",
                "PRD — Inventory: Informasi Stok",
                "HANDOFF_TO",
            ),
        }
        self.assertTrue(expected.issubset(active))

    def test_hemodialysis_entry_points_use_current_source_context(self) -> None:
        relations = [
            row
            for row in self.inventory["relations"]
            if row["target_title"] == "PRD — Order Hemodialisa"
            and row["relationship_type"] == "ENTRY_POINT_TO"
            and row["evidence_class"] == "CROSS_SOURCE_FACT"
        ]
        self.assertEqual(
            {row["source_title"] for row in relations},
            {
                "Dashboard Pelayanan IGD",
                "PRD — Dashboard Pelayanan Rawat Inap Neurovi v2",
                "PRD — Pendaftaran Rawat Jalan",
            },
        )
        self.assertTrue(
            all(
                row["output_context"]
                == "Order HD yang berhasil dibuat menyebabkan pasien masuk/tersedia pada Dashboard Pelayanan Hemodialisa."
                for row in relations
            )
        )
        self.assertTrue(
            all("Menunggu Konfirmasi" not in row["output_context"] for row in relations)
        )
        self.assertEqual(
            {row["evidence_reference"].rsplit(":", 1)[-1] for row in relations},
            {"56", "57", "58"},
        )

    def test_ambiguous_billing_and_registration_targets_remain_review_only(self) -> None:
        ambiguous_sources = {
            "Order Tindakan VK",
            "PRD — Order Retur Obat dan Alat Kesehatan",
            "Product Requirement Document (PRD) — Jadwal Praktik",
        }
        ambiguous_targets = {
            "PRD — Billing: Tagihan Pasien (G2)",
            "PRD — Pendaftaran Rawat Jalan",
        }
        matching = [
            row
            for row in self.inventory["relations"]
            if row["source_title"] in ambiguous_sources
            and row["target_title"] in ambiguous_targets
        ]
        self.assertTrue(matching)
        self.assertTrue(
            all(row["verification_status"] == "REVIEW_REQUIRED" for row in matching)
        )

    def test_supporting_sources_and_legacy_outputs_are_excluded(self) -> None:
        paths = {
            item["source_path"]
            for domain in self.inventory["domains"]
            for item in domain["documents"]
        }
        self.assertTrue(paths.isdisjoint(e2e_inventory.SUPPORTING_MARKDOWN_PATHS))
        inventory_dir = DOCUMENT_REPO / "reconciliation/e2e-inventory"
        self.assertTrue(
            all(
                not (inventory_dir / filename).exists()
                for filename in e2e_inventory.LEGACY_OUTPUTS
            )
        )
        self.assertFalse((DOCUMENT_REPO / "reconciliation/inventory").exists())

    def test_generated_inventory_csv_uses_lf_line_endings(self) -> None:
        inventory_dir = DOCUMENT_REPO / "reconciliation/e2e-inventory"
        generated = (
            "document-domain-index.csv",
            "document-relation-index.csv",
            "domain-register.csv",
            "duplicate-representations.csv",
        )
        for filename in generated:
            path = inventory_dir / filename
            self.assertNotIn(b"\r\n", path.read_bytes(), path.name)


class LLMClientTests(unittest.TestCase):
    def test_9router_settings_are_sent_by_the_agent_client(self) -> None:
        captured = {}

        class Response:
            headers = {"x-request-id": "req-123"}

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self) -> bytes:
                return json.dumps(
                    {
                        "choices": [
                            {
                                "message": {
                                    "content": json.dumps(
                                        {
                                            "message": "Pertanyaan rekonsiliasi",
                                            "status": "AWAITING_USER",
                                        }
                                    )
                                }
                            }
                        ]
                    }
                ).encode()

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["body"] = json.loads(request.data.decode())
            captured["authorization"] = request.get_header("Authorization")
            captured["timeout"] = timeout
            return Response()

        client = OpenAICompatibleLLM(
            provider="9router",
            base_url="https://router.example/v1",
            api_key="secret-value",
            model="model-name",
            reasoning_effort="high",
            timeout_seconds=77,
        )
        with patch("urllib.request.urlopen", fake_urlopen):
            result = client.complete("system", "user")

        self.assertEqual(captured["url"], "https://router.example/v1/chat/completions")
        self.assertEqual(captured["body"]["model"], "model-name")
        self.assertEqual(captured["body"]["reasoning_effort"], "high")
        self.assertEqual(captured["authorization"], "Bearer secret-value")
        self.assertEqual(captured["timeout"], 77)
        self.assertEqual(result.payload["status"], "AWAITING_USER")
        self.assertEqual(result.request_id, "req-123")


class SessionStoreTests(unittest.TestCase):
    @staticmethod
    def _write_document_catalog(repo: Path) -> dict[str, dict[str, str]]:
        documents = {
            "markdown": {
                "document_id": "DOC-MARKDOWN",
                "content_id": "CONTENT-MARKDOWN",
                "source_path": (
                    "PRD/PRD Generator (.md)/Pelayanan (.md)/registration.md"
                ),
                "title": "PRD Registration",
                "extension": ".md",
            },
            "copy_markdown": {
                "document_id": "DOC-COPY-MARKDOWN",
                "content_id": "CONTENT-COPY-MARKDOWN",
                "source_path": (
                    "PRD/PRD Generator (.md) - Copy/Pelayanan/registration.md"
                ),
                "title": "Copied PRD Registration",
                "extension": ".md",
            },
            "other_original_markdown": {
                "document_id": "DOC-OTHER-ORIGINAL-MARKDOWN",
                "content_id": "CONTENT-OTHER-ORIGINAL-MARKDOWN",
                "source_path": "PRD/Pelayanan Utama/registration.md",
                "title": "Other Original Registration",
                "extension": ".md",
            },
            "supporting_api_markdown": {
                "document_id": "DOC-SUPPORTING-API-MARKDOWN",
                "content_id": "CONTENT-SUPPORTING-API-MARKDOWN",
                "source_path": (
                    "PRD/PRD Generator (.md)/Integrasi/Api Doc/"
                    "APLICARES-KETERSEDIAAN KAMAR.md"
                ),
                "title": "APLICARES Ketersediaan Kamar",
                "extension": ".md",
            },
            "supporting_context_markdown": {
                "document_id": "DOC-SUPPORTING-CONTEXT-MARKDOWN",
                "content_id": "CONTENT-SUPPORTING-CONTEXT-MARKDOWN",
                "source_path": "PRD/PRD Generator (.md)/KONTEKS-SESI.md",
                "title": "Konteks Sesi",
                "extension": ".md",
            },
            "supporting_merge_markdown": {
                "document_id": "DOC-SUPPORTING-MERGE-MARKDOWN",
                "content_id": "CONTENT-SUPPORTING-MERGE-MARKDOWN",
                "source_path": (
                    "PRD/PRD Generator (.md)/Pelayanan (.md)/"
                    "ringkasan-merge-prd-rj.md"
                ),
                "title": "Ringkasan Merge PRD RJ",
                "extension": ".md",
            },
            "mermaid": {
                "document_id": "DOC-MERMAID",
                "content_id": "CONTENT-MERMAID",
                "source_path": (
                    "PRD/PRD Generator (.md)/menu-flow/registration.mmd"
                ),
                "title": "Registration Flow",
                "extension": ".mmd",
            },
            "pdf": {
                "document_id": "DOC-PDF",
                "content_id": "CONTENT-PDF",
                "source_path": "PRD/PRD Generator (.md)/registration.pdf",
                "title": "Registration PDF",
                "extension": ".pdf",
            },
            "docx": {
                "document_id": "DOC-DOCX",
                "content_id": "CONTENT-DOCX",
                "source_path": "PRD/PRD Generator (.md)/registration.docx",
                "title": "Registration DOCX",
                "extension": ".docx",
            },
            "menu_flow_markdown": {
                "document_id": "DOC-MENU-FLOW-MD",
                "content_id": "CONTENT-MENU-FLOW-MD",
                "source_path": (
                    "PRD/PRD Generator (.md)/menu-flow/registration-note.md"
                ),
                "title": "Registration Flow Note",
                "extension": ".md",
            },
            "generated": {
                "document_id": "DOC-GENERATED",
                "content_id": "CONTENT-GENERATED",
                "source_path": "PRD/PRD Generator (.md)/generated.md",
                "title": "Generated Registration",
                "extension": ".md",
            },
        }
        catalog = repo / "catalog/document-index.json"
        catalog.parent.mkdir(parents=True)
        catalog.write_text(
            json.dumps({"schema_version": 1, "documents": list(documents.values())}),
            encoding="utf-8",
        )
        source = repo / "source/original"
        for key in (
            "markdown",
            "copy_markdown",
            "other_original_markdown",
            "supporting_api_markdown",
            "supporting_context_markdown",
            "supporting_merge_markdown",
            "mermaid",
            "pdf",
            "docx",
            "menu_flow_markdown",
        ):
            document = documents[key]
            path = source / document["source_path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"original {key}\n", encoding="utf-8")
        generated = repo / "documents/DOC-GENERATED/content.md"
        generated.parent.mkdir(parents=True)
        generated.write_text("generated content\n", encoding="utf-8")
        original_document = documents["markdown"]
        original_path = source / original_document["source_path"]
        original_bytes = original_path.read_bytes()
        original_sha256 = hashlib.sha256(original_bytes).hexdigest()
        original_document["sha256"] = original_sha256
        catalog.write_text(
            json.dumps({"schema_version": 1, "documents": list(documents.values())}),
            encoding="utf-8",
        )
        inventory_path = repo / "reconciliation/e2e-inventory/domain-worklist.json"
        inventory_path.parent.mkdir(parents=True, exist_ok=True)
        inventory_path.write_text(
            json.dumps(
                {
                    "inventory_type": "E2E_DOMAIN_WORKLIST",
                    "unique_prd_count": 1,
                    "domains": [
                        {
                            "e2e_code": "E2E-RJ",
                            "documents": [original_document],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        canonical_header = (
            "---\n"
            "artifact_type: CANONICAL_PRD\n"
            "document_code: PRD-RJ-001\n"
            "canonical_version: v0.0.0\n"
            "---\n\n"
            "## Standard Section Map\n\n"
        ).encode("utf-8")
        canonical_bytes = canonical_header + original_bytes
        canonical_relative = Path(
            "reconciliation/canonical/prds/PRD-RJ-001.md"
        )
        canonical_path = repo / canonical_relative
        canonical_path.parent.mkdir(parents=True, exist_ok=True)
        canonical_path.write_bytes(canonical_bytes)
        canonical_manifest = {
            "artifact_type": "CANONICAL_BASELINE_MANIFEST",
            "canonical_version": "v0.0.0",
            "source_inventory_sha256": hashlib.sha256(
                inventory_path.read_bytes()
            ).hexdigest(),
            "generated_prd_count": 1,
            "documents": [
                {
                    "document_code": "PRD-RJ-001",
                    "content_id": original_document["content_id"],
                    "source_sha256": original_sha256,
                    "source_representations": [
                        {
                            "document_id": original_document["document_id"],
                            "source_path": original_document["source_path"],
                            "sha256": original_sha256,
                        }
                    ],
                    "standard_section_map": [
                        {
                            "section_family": "scope",
                            "status": "NO_MATCHING_SOURCE_HEADING_DETECTED",
                        }
                    ],
                    "canonical_version": "v0.0.0",
                    "path": canonical_relative.as_posix(),
                    "payload_offset": len(canonical_header),
                    "payload_length": len(original_bytes),
                    "generated_sha256": hashlib.sha256(
                        canonical_bytes
                    ).hexdigest(),
                }
            ],
        }
        manifest_path = repo / "reconciliation/canonical/manifest.json"
        manifest_path.write_text(json.dumps(canonical_manifest), encoding="utf-8")
        return documents

    def test_session_workspace_is_created_without_touching_original_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            tools = root / "tools"
            source = repo / "source/original"
            source.mkdir(parents=True)
            original = source / "original.md"
            original.write_text("immutable fact\n", encoding="utf-8")
            inventory = repo / "reconciliation/e2e-inventory"
            inventory.mkdir(parents=True)
            (inventory / "inventory-manifest.json").write_text(
                '{"schema_version": 1}\n', encoding="utf-8"
            )
            canonical = repo / "reconciliation/canonical/manifest.json"
            canonical.parent.mkdir(parents=True)
            canonical.write_text(
                '{"artifact_type":"test","canonical_version":"v0.0.0"}\n',
                encoding="utf-8",
            )
            asset = (
                tools
                / ".codex/skills/neurovi-prd-reconciler/assets/review-session-template.md"
            )
            asset.parent.mkdir(parents=True)
            asset.write_text("# Reconciliation Review - <E2E Code>\n", encoding="utf-8")

            store = SessionStore(repo, tools)
            session, created = store.open_or_create(
                {"e2e_code": "E2E-ADM-01", "title": "Registration Rajal"},
                {"discord_user_id": "123", "discord_role_ids": ["456"]},
                {
                    "provider": "9router",
                    "model": "model-name",
                    "reasoning_effort": "high",
                },
            )

            workspace = repo / "reconciliation/workspaces/E2E-ADM-01/sessions/main-flow"
            self.assertTrue(created)
            self.assertEqual(session["session_id"], "REC-E2E-ADM-01-MF-001")
            self.assertEqual(session["e2e_selection_status"], "AUTO_WORKLIST")
            self.assertEqual(len(session["canonical_baseline_manifest_sha256"]), 64)
            self.assertEqual(session["base_canonical_version"], "v0.0.0")
            self.assertTrue((workspace / "decision-register.csv").is_file())
            self.assertTrue((workspace / "interview-register.csv").is_file())
            self.assertEqual(original.read_text(encoding="utf-8"), "immutable fact\n")
            self.assertNotIn(
                "api_key", (workspace / "session.json").read_text(encoding="utf-8")
            )

    def test_main_flow_and_business_case_sessions_are_independent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            tools = root / "tools"
            inventory = repo / "reconciliation/e2e-inventory"
            inventory.mkdir(parents=True)
            (inventory / "inventory-manifest.json").write_text(
                '{"schema_version": 1}\n', encoding="utf-8"
            )
            canonical = repo / "reconciliation/canonical/manifest.json"
            canonical.parent.mkdir(parents=True)
            canonical.write_text(
                '{"artifact_type":"test","canonical_version":"v0.0.0"}\n',
                encoding="utf-8",
            )
            asset = tools / ".codex/skills/neurovi-prd-reconciler/assets/review-session-template.md"
            asset.parent.mkdir(parents=True)
            asset.write_text("# <E2E Code> - <RECONCILIATION_MODE>\n", encoding="utf-8")
            store = SessionStore(repo, tools)
            e2e = {"e2e_code": "E2E-RJ", "title": "Rawat Jalan"}
            actor = {"discord_user_id": "123"}
            profile = {"provider": "9router", "model": "model", "reasoning_effort": "high"}

            main, _ = store.open_or_create(e2e, actor, profile, "MAIN_FLOW")
            detail, _ = store.open_or_create(e2e, actor, profile, "BUSINESS_CASES")

            self.assertEqual(main["session_id"], "REC-E2E-RJ-MF-001")
            self.assertEqual(detail["session_id"], "REC-E2E-RJ-BC-001")
            main_path, _ = store.find(main["session_id"])
            detail_path, _ = store.find(detail["session_id"])
            self.assertNotEqual(main_path, detail_path)
            self.assertTrue(main_path.match("*/sessions/main-flow"))
            self.assertTrue(detail_path.match("*/sessions/business-cases"))

    def test_open_or_create_replaces_an_abandoned_start(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            store = SessionStore(repo, TOOLS_REPO)
            workspace = (
                repo
                / "reconciliation/workspaces/E2E-RI/sessions/business-cases"
            )
            workspace.mkdir(parents=True)
            abandoned = {
                "session_id": "REC-E2E-RI-BC-001",
                "e2e_code": "E2E-RI",
                "reconciliation_mode": "BUSINESS_CASES",
                "status": "SELECTED_FOR_REVIEW",
                "current_question": None,
                "event_count": 1,
            }
            (workspace / "session.json").write_text(
                json.dumps(abandoned), encoding="utf-8"
            )
            (workspace / "agent-audit.jsonl").write_text(
                json.dumps({"event_id": 1, "event_type": "USER_REQUEST"}) + "\n",
                encoding="utf-8",
            )
            store._inventory_version = lambda: "inventory"
            store._canonical_baseline_version = lambda: "manifest"
            store._canonical_version = lambda: "v0.0.0"
            store._git_output = lambda command: ""
            store._create_template = lambda *args: None

            session, created = store.open_or_create(
                {"e2e_code": "E2E-RI", "title": "Rawat Inap"},
                {"discord_user_id": "123"},
                {"provider": "9router"},
                "BUSINESS_CASES",
            )

            self.assertTrue(created)
            self.assertEqual(session["session_id"], "REC-E2E-RI-BC-002")
            events = (workspace / "agent-audit.jsonl").read_text(encoding="utf-8")
            self.assertIn("SESSION_START_FAILED", events)

    def test_active_legacy_main_flow_takes_precedence_over_stopped_scoped_session(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            tools = root / "tools"
            inventory = repo / "reconciliation/e2e-inventory"
            inventory.mkdir(parents=True)
            (inventory / "inventory-manifest.json").write_text(
                '{"schema_version": 1}\n', encoding="utf-8"
            )
            scoped = repo / "reconciliation/workspaces/E2E-RJ/sessions/main-flow"
            scoped.mkdir(parents=True)
            (scoped / "session.json").write_text(
                json.dumps(
                    {
                        "session_id": "REC-E2E-RJ-MF-001",
                        "status": "STOPPED_BY_USER",
                    }
                ),
                encoding="utf-8",
            )
            legacy = repo / "reconciliation/workspaces/E2E-RJ/session.json"
            legacy.parent.mkdir(parents=True, exist_ok=True)
            legacy.write_text(
                json.dumps(
                    {
                        "session_id": "REC-E2E-RJ-001",
                        "e2e_code": "E2E-RJ",
                        "status": "AWAITING_USER",
                    }
                ),
                encoding="utf-8",
            )

            session, created = SessionStore(repo, tools).open_or_create(
                {"e2e_code": "E2E-RJ", "title": "Rawat Jalan"},
                {"discord_user_id": "123"},
                {"provider": "9router", "model": "model"},
                "MAIN_FLOW",
            )

            self.assertFalse(created)
            self.assertEqual(session["session_id"], "REC-E2E-RJ-001")
            self.assertEqual(session["reconciliation_mode"], "MAIN_FLOW")

    def test_only_prd_generator_markdown_prds_are_selectable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            documents = self._write_document_catalog(repo)
            store = SessionStore(repo, root / "tools")

            self.assertIsNotNone(
                store.original_markdown_prd(documents["markdown"]["document_id"])
            )
            for key in (
                "copy_markdown",
                "other_original_markdown",
                "supporting_api_markdown",
                "supporting_context_markdown",
                "supporting_merge_markdown",
                "mermaid",
                "pdf",
                "docx",
                "menu_flow_markdown",
                "generated",
            ):
                self.assertIsNone(
                    store.original_markdown_prd(documents[key]["document_id"]),
                    key,
                )

    def test_owner_worklist_context_loads_eligible_sources_automatically(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            documents = self._write_document_catalog(repo)
            store = SessionStore(repo, root / "tools")
            e2e = {
                "worklist": [
                    {
                        **documents["markdown"],
                        "worklist_order": 1,
                        "assignment_basis": "TITLE_KEYWORD",
                        "assignment_confidence": "HIGH",
                    },
                    {**documents["pdf"], "worklist_order": 2},
                    {**documents["mermaid"], "worklist_order": 3},
                    {**documents["generated"], "worklist_order": 4},
                ]
            }

            context = store.worklist_document_context(e2e)
            self.assertEqual(len(context), 1)
            self.assertEqual(
                context[0]["document_id"], documents["markdown"]["document_id"]
            )
            self.assertEqual(context[0]["worklist_status"], "OWNER_WORKLIST")
            self.assertEqual(context[0]["relationship_role"], "PRIMARY_SCOPE")
            self.assertEqual(
                context[0]["preserved_content_excerpt"], "original markdown\n"
            )
            self.assertEqual(
                context[0]["source_representation"],
                "VERIFIED_LOSSLESS_CANONICAL_V0",
            )
            self.assertEqual(context[0]["document_code"], "PRD-RJ-001")
            self.assertEqual(
                context[0]["source_authority"], "IMMUTABLE_ORIGINAL_MARKDOWN"
            )
            self.assertEqual(
                context[0]["standard_section_map"][0]["section_family"],
                "scope",
            )

    def test_owner_worklist_rejects_modified_canonical(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            documents = self._write_document_catalog(repo)
            canonical = repo / "reconciliation/canonical/prds/PRD-RJ-001.md"
            canonical.write_bytes(canonical.read_bytes() + b"changed")
            store = SessionStore(repo, root / "tools")

            with self.assertRaises(ReconciliationAgentError) as captured:
                store.worklist_document_context(
                    {"worklist": [documents["markdown"]]}
                )

            self.assertEqual(captured.exception.status_code, 409)
            self.assertIn("checksum", str(captured.exception).casefold())

    def test_owner_worklist_rejects_stale_canonical_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            documents = self._write_document_catalog(repo)
            inventory = repo / "reconciliation/e2e-inventory/domain-worklist.json"
            inventory.write_text(inventory.read_text(encoding="utf-8") + "\n")
            store = SessionStore(repo, root / "tools")

            with self.assertRaises(ReconciliationAgentError) as captured:
                store.worklist_document_context(
                    {"worklist": [documents["markdown"]]}
                )

            self.assertEqual(captured.exception.status_code, 409)
            self.assertIn("stale", str(captured.exception).casefold())

    def test_related_source_context_loads_only_explicit_original_prds(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            documents = self._write_document_catalog(repo)
            store = SessionStore(repo, root / "tools")
            e2e = {
                "worklist": [documents["markdown"]],
                "relations": [
                    {
                        "relation_id": "REL-001",
                        "source_document_id": documents["markdown"]["document_id"],
                        "target_document_id": documents["copy_markdown"]["document_id"],
                        "relationship_type": "HANDOFF_TO",
                        "verification_status": "SOURCE_EXPLICIT",
                        "evidence_reference": "source.md:10",
                    },
                    {
                        "relation_id": "REL-002",
                        "source_document_id": documents["markdown"]["document_id"],
                        "target_document_id": documents["pdf"]["document_id"],
                        "relationship_type": "REFERENCES",
                        "verification_status": "REVIEW_REQUIRED",
                        "evidence_reference": "source.md:20",
                    },
                ],
            }

            self.assertEqual(store.related_source_document_context(e2e), [])

class ReconciliationAgentTests(unittest.TestCase):
    def test_model_cannot_request_document_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            documents = SessionStoreTests._write_document_catalog(repo)
            workspace = repo / "reconciliation/workspaces/E2E-ADM-01"
            workspace.mkdir(parents=True)
            agent = ReconciliationAgent.__new__(ReconciliationAgent)
            agent.store = SessionStore(repo, root / "tools")

            with self.assertRaises(ReconciliationAgentError) as captured:
                agent._apply_model_result(
                    workspace,
                    {"e2e_code": "E2E-ADM-01"},
                    {
                        "message": "Pilih dokumen ini.",
                        "status": "AWAITING_USER",
                        "current_question": {
                            "question_type": "DOCUMENT_SELECTION",
                            "question_scope": "MAIN_FLOW",
                            "issue_type": "BROKEN_HANDOFF",
                            "document_ids": [documents["markdown"]["document_id"]],
                            "flow_or_handoff": "Pendaftaran Rawat Jalan",
                            "why_needed": "Menentukan peran dokumen.",
                            "question": "Apakah dokumen ini dipilih?",
                        },
                    },
                )

            self.assertEqual(captured.exception.status_code, 502)

    def test_model_cannot_request_owner_worklist_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            documents = SessionStoreTests._write_document_catalog(repo)
            workspace = repo / "reconciliation/workspaces/E2E-RJ"
            workspace.mkdir(parents=True)
            agent = ReconciliationAgent.__new__(ReconciliationAgent)
            agent.store = SessionStore(repo, root / "tools")

            with self.assertRaises(ReconciliationAgentError) as captured:
                agent._apply_model_result(
                    workspace,
                    {"e2e_code": "E2E-RJ"},
                    {
                        "message": "Tentukan peran dokumen.",
                        "status": "AWAITING_USER",
                        "current_question": {
                            "question_type": "CONFIRMATION",
                            "question_scope": "MAIN_FLOW",
                            "issue_type": "BROKEN_HANDOFF",
                            "document_ids": [documents["markdown"]["document_id"]],
                            "flow_or_handoff": "Pendaftaran Rawat Jalan",
                            "why_needed": "Menentukan peran dokumen.",
                            "question": (
                                "Apakah dokumen ini perlu dijadikan dokumen utama, "
                                "hanya sebagai konteks, atau dikeluarkan?"
                            ),
                        },
                    },
                )

            self.assertEqual(captured.exception.status_code, 502)

    def test_model_question_must_match_active_reconciliation_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            documents = SessionStoreTests._write_document_catalog(repo)
            workspace = repo / "reconciliation/workspaces/E2E-RJ/sessions/main-flow"
            workspace.mkdir(parents=True)
            agent = ReconciliationAgent.__new__(ReconciliationAgent)
            agent.store = SessionStore(repo, root / "tools")
            question = {
                "message": "Ada detail validasi yang perlu diputuskan.",
                "status": "AWAITING_USER",
                "current_question": {
                    "question_type": "OPEN_ANSWER",
                    "question_scope": "BUSINESS_CASE",
                    "issue_type": "VALIDATION_GAP",
                    "document_ids": [documents["markdown"]["document_id"]],
                    "flow_or_handoff": "Validasi pendaftaran",
                    "why_needed": "Agar kondisi penolakan jelas.",
                    "question": "Kapan pendaftaran harus ditolak?",
                },
            }

            with self.assertRaises(ReconciliationAgentError):
                agent._apply_model_result(
                    workspace,
                    {"e2e_code": "E2E-RJ", "reconciliation_mode": "MAIN_FLOW"},
                    question,
                )

            question["current_question"]["question_scope"] = "MAIN_FLOW"
            with self.assertRaises(ReconciliationAgentError):
                agent._apply_model_result(
                    workspace,
                    {"e2e_code": "E2E-RJ", "reconciliation_mode": "MAIN_FLOW"},
                    question,
                )

    def test_business_case_issue_type_accepts_single_item_model_array(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            documents = SessionStoreTests._write_document_catalog(repo)
            workspace = repo / "reconciliation/workspaces/E2E-RJ/sessions/business-cases"
            workspace.mkdir(parents=True)
            agent = ReconciliationAgent.__new__(ReconciliationAgent)
            agent.store = SessionStore(repo, root / "tools")
            session = {
                "e2e_code": "E2E-RJ",
                "reconciliation_mode": "BUSINESS_CASES",
            }

            agent._apply_model_result(
                workspace,
                session,
                {
                    "message": "Ada aturan yang perlu diperjelas.",
                    "status": "AWAITING_USER",
                    "current_question": {
                        "question_type": ["OPEN_ANSWER"],
                        "question_scope": ["BUSINESS_CASE"],
                        "issue_type": ["BUSINESS_RULE_AMBIGUITY"],
                        "document_ids": [documents["markdown"]["document_id"]],
                        "flow_or_handoff": "Aturan pendaftaran",
                        "why_needed": "Agar perilaku pada kondisi ini jelas.",
                        "question": "Aturan mana yang harus digunakan?",
                    },
                },
            )

            self.assertEqual(
                session["current_question"]["issue_type"],
                "BUSINESS_RULE_AMBIGUITY",
            )
            self.assertEqual(
                session["current_question"]["question_scope"], "BUSINESS_CASE"
            )
            self.assertEqual(
                session["current_question"]["question_type"], "OPEN_ANSWER"
            )
            self.assertEqual(session["status"], "AWAITING_USER")

    def test_business_case_issue_type_rejects_multiple_model_values(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            documents = SessionStoreTests._write_document_catalog(repo)
            workspace = repo / "reconciliation/workspaces/E2E-RJ/sessions/business-cases"
            workspace.mkdir(parents=True)
            agent = ReconciliationAgent.__new__(ReconciliationAgent)
            agent.store = SessionStore(repo, root / "tools")

            with self.assertRaises(ReconciliationAgentError):
                agent._apply_model_result(
                    workspace,
                    {
                        "e2e_code": "E2E-RJ",
                        "reconciliation_mode": "BUSINESS_CASES",
                    },
                    {
                        "message": "Ada beberapa masalah.",
                        "status": "AWAITING_USER",
                        "current_question": {
                            "question_type": "OPEN_ANSWER",
                            "question_scope": "BUSINESS_CASE",
                            "issue_type": [
                                "BUSINESS_RULE_AMBIGUITY",
                                "CASE_CONFLICT",
                            ],
                            "document_ids": [
                                documents["markdown"]["document_id"]
                            ],
                            "flow_or_handoff": "Aturan pendaftaran",
                            "why_needed": "Agar perilaku pada kondisi ini jelas.",
                            "question": "Aturan mana yang harus digunakan?",
                        },
                    },
                )

    def test_collect_evidence_keeps_non_primary_sources_as_reasoning_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            documents = SessionStoreTests._write_document_catalog(repo)
            workspace = repo / "reconciliation/workspaces/E2E-ADM-01"
            workspace.mkdir(parents=True)
            settings = Settings(repo_root=repo, tools_root=TOOLS_REPO)
            agent = ReconciliationAgent.__new__(ReconciliationAgent)
            agent.settings = settings
            agent.store = SessionStore(repo, TOOLS_REPO)
            agent.store.verified_canonical_e2e = lambda e2e_code: {
                "e2e_code": e2e_code,
                "canonical_version": "v0.0.0",
                "canonical_path": f"reconciliation/canonical/e2e/{e2e_code}.md",
                "canonical_sha256": "0" * 64,
                "content_excerpt": "fixture",
                "content_truncated": False,
            }
            agent.store.verified_automatic_reconciliation = (
                lambda e2e_code="", reconciliation_mode="": {
                    "status": "COMPLETED",
                    "path": "reconciliation/canonical/automatic-reconciliation.json",
                    "sha256": "0" * 64,
                    "summary": {},
                    "items": [],
                }
            )
            supporting = (
                documents["copy_markdown"],
                documents["supporting_context_markdown"],
                documents["pdf"],
                documents["mermaid"],
            )
            agent._run_inventory_json = lambda query: {
                "e2e_code": query,
                "title": "Rawat Jalan",
                "status": "DOMAIN_WORKLIST_PROPOSAL",
                "origin": "ELIGIBLE_ORIGINAL_PRD",
                "purpose": "Flow-checking worklist",
                "document_count": 1,
                "relation_count": len(supporting),
                "cross_domain_relation_count": len(supporting),
                "worklist": [documents["markdown"]],
                "relations": [
                    {
                        "relation_id": f"REL-{index}",
                        "source_document_id": documents["markdown"]["document_id"],
                        "source_content_id": documents["markdown"].get("content_id", ""),
                        "source_title": documents["markdown"]["title"],
                        "source_domain_code": query,
                        "target_document_id": item["document_id"],
                        "target_content_id": item.get("content_id", ""),
                        "target_title": item["title"],
                        "target_domain_code": "SUPPORTING",
                        "relationship_type": "REFERENCES",
                        "verification_status": "REVIEW_REQUIRED",
                    }
                    for index, item in enumerate(supporting, start=1)
                ],
            }

            def scan_result(command):
                if "main-flow" in command:
                    return {
                        "summary": {"gap_candidate_count": 0},
                        "ordered_documents": [documents["markdown"]],
                        "flow_relations": [],
                        "gap_candidates": [],
                        "warning": "main-flow warning",
                    }
                return {
                    "summary": {"gap_candidate_count": 0},
                    "documents": [documents["markdown"]],
                    "warning": "business-case warning",
                }

            agent._run_json_command = scan_result
            evidence = agent._collect_evidence("E2E-ADM-01", workspace)

            self.assertEqual(
                [item["document_id"] for item in evidence["e2e"]["worklist"]],
                [documents["markdown"]["document_id"]],
            )
            self.assertEqual(
                evidence["main_flow_scan"]["ordered_documents"],
                [documents["markdown"]],
            )
            self.assertNotIn("business_case_scan", evidence)
            self.assertEqual(
                evidence["automatic_source_fact_reconciliation"]["status"],
                "COMPLETED",
            )
            self.assertEqual(
                evidence["automatic_source_fact_reconciliation"][
                    "resolved_relations"
                ],
                [],
            )

            business_evidence = agent._collect_evidence(
                "E2E-ADM-01", workspace, "BUSINESS_CASES"
            )
            self.assertNotIn("main_flow_scan", business_evidence)
            self.assertEqual(
                [
                    item["document_id"]
                    for item in business_evidence["business_case_scan"]["documents"]
                ],
                [documents["markdown"]["document_id"]],
            )
            self.assertEqual(
                [
                    item["document_id"]
                    for item in evidence["supporting_reasoning"]["documents"]
                ],
                [item["document_id"] for item in supporting],
            )
            self.assertTrue(
                all(
                    item["selectable_source_document"] is False
                    for item in evidence["supporting_reasoning"]["documents"]
                )
            )
            self.assertIn(
                "reasoning and discovery only",
                evidence["source_policy"]["supporting_reasoning_only"],
            )

    def test_collect_evidence_separates_source_facts_from_conflicts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            documents = SessionStoreTests._write_document_catalog(repo)
            workspace = repo / "reconciliation/workspaces/E2E-ADM-01"
            workspace.mkdir(parents=True)
            agent = ReconciliationAgent.__new__(ReconciliationAgent)
            agent.settings = Settings(repo_root=repo, tools_root=TOOLS_REPO)
            agent.store = SessionStore(repo, TOOLS_REPO)
            agent.store.verified_canonical_e2e = lambda e2e_code: {
                "e2e_code": e2e_code,
                "canonical_version": "v0.0.0",
                "canonical_path": f"reconciliation/canonical/e2e/{e2e_code}.md",
                "canonical_sha256": "0" * 64,
                "content_excerpt": "fixture",
                "content_truncated": False,
            }
            agent.store.verified_automatic_reconciliation = (
                lambda e2e_code="", reconciliation_mode="": {
                    "status": "COMPLETED",
                    "path": "reconciliation/canonical/automatic-reconciliation.json",
                    "sha256": "0" * 64,
                    "summary": {},
                    "items": [],
                }
            )
            base_relation = {
                "source_document_id": documents["markdown"]["document_id"],
                "source_content_id": documents["markdown"]["content_id"],
                "source_title": documents["markdown"]["title"],
                "source_domain_code": "E2E-ADM-01",
                "target_document_id": documents["markdown"]["document_id"],
                "target_content_id": documents["markdown"]["content_id"],
                "target_title": documents["markdown"]["title"],
                "target_domain_code": "E2E-ADM-01",
                "relationship_type": "HANDOFF_TO",
                "evidence_class": "CROSS_SOURCE_FACT",
                "verification_status": "SOURCE_EXPLICIT",
                "evidence_reference": "source.md:1",
            }
            agent._run_inventory_json = lambda query: {
                "e2e_code": query,
                "title": "Registration",
                "worklist": [documents["markdown"]],
                "relations": [
                    base_relation
                    | {
                        "relation_id": "REL-FACT",
                        "conflict_status": "NO_CONFLICT_IDENTIFIED",
                    },
                    base_relation
                    | {
                        "relation_id": "REL-CONFLICT",
                        "conflict_status": "CONFLICT_FOUND",
                    },
                ],
            }
            agent._run_json_command = lambda command: {
                "summary": {},
                "ordered_documents": [],
                "flow_relations": [],
                "gap_candidates": [],
            }

            evidence = agent._collect_evidence("E2E-ADM-01", workspace)
            automatic = evidence["automatic_source_fact_reconciliation"]

            self.assertEqual(
                [item["relation_id"] for item in automatic["resolved_relations"]],
                ["REL-FACT"],
            )
            self.assertFalse(automatic["resolved_relations"][0]["decision_required"])
            self.assertEqual(
                [
                    item["relation_id"]
                    for item in automatic["human_decision_required_relations"]
                ],
                ["REL-CONFLICT"],
            )
            self.assertTrue(
                automatic["human_decision_required_relations"][0][
                    "decision_required"
                ]
            )

    def test_verified_automatic_reconciliation_filters_mode_and_e2e(self) -> None:
        store = SessionStore(DOCUMENT_REPO, TOOLS_REPO)
        result = store.verified_automatic_reconciliation(
            "E2E-BILLING", "MAIN_FLOW"
        )

        self.assertEqual(result["status"], "COMPLETED")
        self.assertTrue(result["items"])
        self.assertTrue(
            all(item["e2e_code"] == "E2E-BILLING" for item in result["items"])
        )
        self.assertTrue(
            all(
                item["reconciliation_mode"] == "MAIN_FLOW"
                for item in result["items"]
            )
        )

    def test_contextual_help_is_advisory_and_does_not_require_a_role(self) -> None:
        class FakeLLM:
            def complete(self, system_prompt, user_prompt):
                self.system_prompt = system_prompt
                self.user_prompt = user_prompt
                return LLMResult(
                    {
                        "summary": "Anda ingin mulai meninjau proses rawat jalan.",
                        "next_step": "Cari nama proses, lalu pilih hasil yang sesuai.",
                        "commands": ["/reconcile alur"],
                        "requires_developer": False,
                        "limitation": "",
                        "workaround": "",
                    }
                )

        settings = Settings(
            repo_root=DOCUMENT_REPO,
            tools_root=TOOLS_REPO,
            llm_provider="9router",
            llm_model="model-name",
            llm_reasoning_effort="high",
        )
        llm = FakeLLM()
        agent = ReconciliationAgent(settings, llm)
        result = agent.invoke(
            {
                "capability": "help.answer",
                "parameters": {"query": "saya bingung mulai dari mana"},
                "actor": {"discord_user_id": "123", "discord_role_ids": []},
            }
        )

        self.assertIn("/reconcile alur", result["message"])
        self.assertIn("tidak ada dokumen yang diubah", result["message"])
        self.assertEqual(result["status"], "ADVISORY")
        self.assertIn("Never claim that you ran a command", llm.system_prompt)

    def test_start_uses_repository_evidence_and_returns_a_session(self) -> None:
        class FakeLLM:
            def __init__(self):
                self.user_prompt = ""

            def complete(self, system_prompt, user_prompt):
                self.user_prompt = user_prompt
                self.assertions = (
                    "Never edit `source/original/`" in system_prompt
                    and "verified lossless canonical v0" in system_prompt
                    and "source/original/PRD/PRD Generator (.md)/"
                    in system_prompt
                    and "RESOLVED_BY_SOURCE_FACT" in system_prompt
                    and "HUMAN_DECISION_REQUIRED" in system_prompt
                )
                return LLMResult(
                    {
                        "message": "Ada aturan pemulangan yang perlu diperjelas.",
                        "status": "AWAITING_USER",
                        "current_question": {
                            "document_ids": ["DOC-68FE75DBEC8D1F4A"],
                            "flow_or_handoff": "Pemulangan pasien dari Rawat Jalan",
                            "why_needed": "Agar status akhir kunjungan dan kelanjutan pelayanan tidak bertentangan.",
                            "question": "Kapan pasien Rawat Jalan dianggap selesai dilayani setelah tindakan pemulangan?",
                            "question_type": "OPEN_ANSWER",
                            "question_scope": "MAIN_FLOW",
                            "issue_type": "BROKEN_HANDOFF",
                        },
                    },
                    request_id="req-test",
                )

        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "repo"
            (repo / "catalog").mkdir(parents=True)
            inventory = repo / "reconciliation/e2e-inventory"
            inventory.mkdir(parents=True)
            shutil.copy2(
                DOCUMENT_REPO / "catalog/document-index.json",
                repo / "catalog/document-index.json",
            )
            shutil.copytree(
                DOCUMENT_REPO / "source/original",
                repo / "source/original",
            )
            shutil.copytree(
                DOCUMENT_REPO / "reconciliation/canonical",
                repo / "reconciliation/canonical",
            )
            for filename in (
                "domain-worklist.json",
                "document-domain-index.csv",
                "document-relation-index.csv",
                "inventory-manifest.json",
            ):
                shutil.copy2(
                    DOCUMENT_REPO / "reconciliation/e2e-inventory" / filename,
                    inventory / filename,
                )
            shutil.copy2(DOCUMENT_REPO / "AGENTS.md", repo / "AGENTS.md")

            settings = Settings(
                repo_root=repo,
                tools_root=TOOLS_REPO,
                discord_reconcile_role_ids=frozenset({456}),
                discord_approver_role_ids=frozenset({789}),
                llm_provider="9router",
                llm_model="model-name",
                llm_reasoning_effort="high",
            )
            llm = FakeLLM()
            agent = ReconciliationAgent(settings, llm)
            result = agent.invoke(
                {
                    "capability": "reconcile.main-flow.start",
                    "parameters": {"e2e": "E2E-RJ"},
                    "actor": {
                        "discord_user_id": "123",
                        "discord_role_ids": ["456"],
                    },
                }
            )

            self.assertTrue(llm.assertions)
            self.assertIn('"e2e_code": "E2E-RJ"', llm.user_prompt)
            self.assertIn('"canonical_e2e_context"', llm.user_prompt)
            self.assertIn('"canonical_version": "v0.0.0"', llm.user_prompt)
            self.assertEqual(result["session_id"], "REC-E2E-RJ-MF-001")
            self.assertEqual(result["status"], "AWAITING_USER")
            self.assertTrue(
                (
                    repo
                    / "reconciliation/workspaces/E2E-RJ/sessions/main-flow/interview-register.csv"
                ).is_file()
            )

    def test_start_rejects_stale_baseline_before_creating_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "repo"
            shutil.copytree(DOCUMENT_REPO / "catalog", repo / "catalog")
            shutil.copytree(
                DOCUMENT_REPO / "source/original", repo / "source/original"
            )
            shutil.copytree(
                DOCUMENT_REPO / "reconciliation/e2e-inventory",
                repo / "reconciliation/e2e-inventory",
            )
            shutil.copytree(
                DOCUMENT_REPO / "reconciliation/canonical",
                repo / "reconciliation/canonical",
            )
            shutil.copy2(DOCUMENT_REPO / "AGENTS.md", repo / "AGENTS.md")
            canonical = repo / "reconciliation/canonical/prds/PRD-RJ-001.md"
            canonical.write_bytes(canonical.read_bytes() + b"changed")
            settings = Settings(
                repo_root=repo,
                tools_root=TOOLS_REPO,
                discord_reconcile_role_ids=frozenset({456}),
                llm_provider="9router",
                llm_model="model-name",
            )
            agent = ReconciliationAgent.__new__(ReconciliationAgent)
            agent.settings = settings
            agent.store = SessionStore(repo, TOOLS_REPO)
            agent.model_profile = {
                "provider": "9router",
                "model": "model-name",
                "reasoning_effort": "high",
            }
            def inventory_result(query):
                del query
                domain = json.loads(
                    (
                        repo / "reconciliation/e2e-inventory/domain-worklist.json"
                    ).read_text(encoding="utf-8")
                )["domains"][0]
                return {**domain, "worklist": domain["documents"]}

            agent._run_inventory_json = inventory_result

            with self.assertRaises(ReconciliationAgentError) as captured:
                agent.invoke(
                    {
                        "capability": "reconcile.main-flow.start",
                        "parameters": {"e2e": "E2E-RJ"},
                        "actor": {
                            "discord_user_id": "123",
                            "discord_role_ids": ["456"],
                        },
                    }
                )

            self.assertEqual(captured.exception.status_code, 409)
            self.assertFalse(
                (repo / "reconciliation/workspaces/E2E-RJ").exists()
            )

    def test_start_rejects_modified_canonical_e2e_before_creating_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "repo"
            shutil.copytree(DOCUMENT_REPO / "catalog", repo / "catalog")
            shutil.copytree(
                DOCUMENT_REPO / "source/original", repo / "source/original"
            )
            shutil.copytree(
                DOCUMENT_REPO / "reconciliation/e2e-inventory",
                repo / "reconciliation/e2e-inventory",
            )
            shutil.copytree(
                DOCUMENT_REPO / "reconciliation/canonical",
                repo / "reconciliation/canonical",
            )
            shutil.copy2(DOCUMENT_REPO / "AGENTS.md", repo / "AGENTS.md")
            canonical_e2e = repo / "reconciliation/canonical/e2e/E2E-RJ.md"
            canonical_e2e.write_bytes(canonical_e2e.read_bytes() + b"changed")
            settings = Settings(
                repo_root=repo,
                tools_root=TOOLS_REPO,
                discord_reconcile_role_ids=frozenset({456}),
                llm_provider="9router",
                llm_model="model-name",
            )
            agent = ReconciliationAgent.__new__(ReconciliationAgent)
            agent.settings = settings
            agent.store = SessionStore(repo, TOOLS_REPO)
            agent.model_profile = {
                "provider": "9router",
                "model": "model-name",
                "reasoning_effort": "high",
            }

            def inventory_result(query):
                del query
                domain = json.loads(
                    (
                        repo / "reconciliation/e2e-inventory/domain-worklist.json"
                    ).read_text(encoding="utf-8")
                )["domains"][0]
                return {**domain, "worklist": domain["documents"]}

            agent._run_inventory_json = inventory_result

            with self.assertRaises(ReconciliationAgentError) as captured:
                agent.invoke(
                    {
                        "capability": "reconcile.main-flow.start",
                        "parameters": {"e2e": "E2E-RJ"},
                        "actor": {
                            "discord_user_id": "123",
                            "discord_role_ids": ["456"],
                        },
                    }
                )

            self.assertEqual(captured.exception.status_code, 409)
            self.assertIn("canonical e2e checksum", str(captured.exception).casefold())
            self.assertFalse(
                (repo / "reconciliation/workspaces/E2E-RJ").exists()
            )

    def test_stop_closes_only_the_working_session_and_preserves_open_question(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            workspace = repo / "reconciliation/workspaces/E2E-RJ"
            workspace.mkdir(parents=True)
            current_question = {
                "question_id": "QST-E2E-RJ-001",
                "question": "Apakah cakupan proses ini sudah sesuai?",
            }
            session = {
                "session_id": "REC-E2E-RJ-001",
                "e2e_code": "E2E-RJ",
                "e2e_title": "Rawat Jalan",
                "status": "AWAITING_USER",
                "started_by": {"discord_user_id": "123"},
                "current_question": current_question,
                "event_count": 0,
            }
            (workspace / "session.json").write_text(
                json.dumps(session), encoding="utf-8"
            )
            settings = Settings(
                repo_root=repo,
                tools_root=TOOLS_REPO,
                discord_reconcile_role_ids=frozenset({456}),
                llm_provider="9router",
                llm_model="model-name",
            )
            agent = ReconciliationAgent.__new__(ReconciliationAgent)
            agent.settings = settings
            agent.store = SessionStore(repo, TOOLS_REPO)
            agent.model_profile = {
                "provider": "9router",
                "model": "model-name",
                "reasoning_effort": "high",
            }

            result = agent.invoke(
                {
                    "capability": "reconcile.stop",
                    "parameters": {"session_id": "REC-E2E-RJ-001"},
                    "actor": {
                        "discord_user_id": "123",
                        "discord_role_ids": ["456"],
                    },
                }
            )

            saved = json.loads((workspace / "session.json").read_text(encoding="utf-8"))
            events = (workspace / "agent-audit.jsonl").read_text(encoding="utf-8")
            self.assertEqual(result["status"], "STOPPED_BY_USER")
            self.assertFalse(result["result"]["published"])
            self.assertEqual(saved["status"], "STOPPED_BY_USER")
            self.assertEqual(saved["current_question"], current_question)
            self.assertIn("stopped_at", saved)
            self.assertIn("SESSION_STOPPED_BY_USER", events)
            self.assertIn("Tidak ada dokumen", result["message"])

    def test_stop_is_an_agent_capability(self) -> None:
        self.assertIn("reconcile.stop", AGENT_CAPABILITIES)

    def test_start_rejects_an_active_session_owned_by_another_user(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            workspace = repo / "reconciliation/workspaces/E2E-RJ"
            workspace.mkdir(parents=True)
            (workspace / "session.json").write_text(
                json.dumps(
                    {
                        "session_id": "REC-E2E-RJ-001",
                        "e2e_code": "E2E-RJ",
                        "e2e_title": "Rawat Jalan",
                        "status": "AWAITING_USER",
                        "started_by": {"discord_user_id": "999"},
                        "event_count": 0,
                    }
                ),
                encoding="utf-8",
            )
            settings = Settings(
                repo_root=repo,
                tools_root=TOOLS_REPO,
                discord_reconcile_role_ids=frozenset({456}),
                llm_provider="9router",
                llm_model="model-name",
            )
            agent = ReconciliationAgent.__new__(ReconciliationAgent)
            agent.settings = settings
            agent.store = SessionStore(repo, TOOLS_REPO)
            agent.model_profile = {
                "provider": "9router",
                "model": "model-name",
                "reasoning_effort": "high",
            }
            agent._run_inventory_json = lambda query: {
                "e2e_code": query,
                "title": "Rawat Jalan",
            }
            agent.store.verified_canonical_e2e = lambda e2e_code: {
                "e2e_code": e2e_code
            }
            agent.store.worklist_document_context = lambda e2e: []

            with self.assertRaises(ReconciliationAgentError) as captured:
                agent.invoke(
                    {
                        "capability": "reconcile.main-flow.start",
                        "parameters": {"e2e": "E2E-RJ"},
                        "actor": {
                            "discord_user_id": "123",
                            "discord_role_ids": ["456"],
                        },
                    }
                )

            self.assertEqual(captured.exception.status_code, 409)
            self.assertIn("pengguna lain", str(captured.exception))

    def test_existing_session_rejects_updates_from_another_user(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            workspace = repo / "reconciliation/workspaces/E2E-RJ"
            workspace.mkdir(parents=True)
            (workspace / "session.json").write_text(
                json.dumps(
                    {
                        "session_id": "REC-E2E-RJ-001",
                        "e2e_code": "E2E-RJ",
                        "e2e_title": "Rawat Jalan",
                        "status": "AWAITING_USER",
                        "started_by": {"discord_user_id": "999"},
                        "event_count": 0,
                    }
                ),
                encoding="utf-8",
            )
            settings = Settings(
                repo_root=repo,
                tools_root=TOOLS_REPO,
                discord_reconcile_role_ids=frozenset({456}),
                llm_provider="9router",
                llm_model="model-name",
            )
            agent = ReconciliationAgent.__new__(ReconciliationAgent)
            agent.settings = settings
            agent.store = SessionStore(repo, TOOLS_REPO)
            agent.model_profile = {
                "provider": "9router",
                "model": "model-name",
                "reasoning_effort": "high",
            }

            with self.assertRaises(ReconciliationAgentError) as captured:
                agent.invoke(
                    {
                        "capability": "reconcile.status",
                        "parameters": {"session_id": "REC-E2E-RJ-001"},
                        "actor": {
                            "discord_user_id": "123",
                            "discord_role_ids": ["456"],
                        },
                    }
                )

            self.assertEqual(captured.exception.status_code, 409)
            self.assertIn("pengguna lain", str(captured.exception))

    def test_failed_model_start_does_not_leave_an_active_session_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            workspace = (
                repo
                / "reconciliation/workspaces/E2E-RI/sessions/business-cases"
            )
            settings = Settings(
                repo_root=repo,
                tools_root=TOOLS_REPO,
                discord_reconcile_role_ids=frozenset({456}),
                llm_provider="9router",
                llm_model="model-name",
            )
            agent = ReconciliationAgent.__new__(ReconciliationAgent)
            agent.settings = settings
            agent.store = SessionStore(repo, TOOLS_REPO)
            agent.model_profile = {
                "provider": "9router",
                "model": "model-name",
                "reasoning_effort": "high",
            }
            agent._run_inventory_json = lambda query: {
                "e2e_code": query,
                "title": "Rawat Inap",
            }
            agent.store.verified_canonical_e2e = lambda e2e_code: {
                "e2e_code": e2e_code
            }
            agent.store.worklist_document_context = lambda e2e: []

            def open_or_create(e2e, actor, model_profile, mode):
                del e2e, model_profile
                workspace.mkdir(parents=True, exist_ok=True)
                session = {
                    "session_id": "REC-E2E-RI-BC-001",
                    "e2e_code": "E2E-RI",
                    "e2e_title": "Rawat Inap",
                    "reconciliation_mode": mode,
                    "status": "SELECTED_FOR_REVIEW",
                    "started_by": actor,
                    "event_count": 0,
                }
                (workspace / "session.json").write_text(
                    json.dumps(session), encoding="utf-8"
                )
                return session, True

            agent.store.open_or_create = open_or_create
            agent._collect_evidence = lambda *args: {}
            agent._ask_model = lambda *args: LLMResult(
                {
                    "message": "Ada aturan yang perlu diperjelas.",
                    "status": "AWAITING_USER",
                    "current_question": {
                        "question_type": "OPEN_ANSWER",
                        "question_scope": "BUSINESS_CASE",
                        "issue_type": ["BUSINESS_RULE_AMBIGUITY", "CASE_CONFLICT"],
                        "flow_or_handoff": "Aturan pendaftaran",
                        "why_needed": "Agar perilakunya jelas.",
                        "question": "Aturan mana yang harus digunakan?",
                    },
                }
            )

            with self.assertRaises(ReconciliationAgentError):
                agent.invoke(
                    {
                        "capability": "reconcile.business-cases.start",
                        "parameters": {"e2e": "E2E-RI"},
                        "actor": {
                            "discord_user_id": "123",
                            "discord_role_ids": ["456"],
                        },
                    }
                )

            saved = json.loads(
                (workspace / "session.json").read_text(encoding="utf-8")
            )
            events = (workspace / "agent-audit.jsonl").read_text(encoding="utf-8")
            self.assertEqual(saved["status"], "START_FAILED")
            self.assertIn("start_failed_at", saved)
            self.assertIn("SESSION_START_FAILED", events)


class AgentHTTPTests(unittest.TestCase):
    def test_invoke_requires_the_shared_bearer_token(self) -> None:
        class Agent:
            model_profile = {
                "provider": "9router",
                "model": "model-name",
                "reasoning_effort": "high",
            }

            def invoke(self, payload):
                return {"message": payload["capability"], "status": "OK"}

        server = ReconciliationHTTPServer(("127.0.0.1", 0), Agent(), "shared-secret")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{server.server_port}/invoke"
        body = json.dumps(
            {"capability": "reconcile.status", "parameters": {}, "actor": {}}
        ).encode()
        try:
            unauthorized = urllib.request.Request(
                url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with self.assertRaises(urllib.error.HTTPError) as captured:
                urllib.request.urlopen(unauthorized, timeout=5)
            self.assertEqual(captured.exception.code, 401)

            authorized = urllib.request.Request(
                url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer shared-secret",
                },
                method="POST",
            )
            with urllib.request.urlopen(authorized, timeout=5) as response:
                result = json.loads(response.read().decode())
            self.assertEqual(result["message"], "reconcile.status")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_gateway_preserves_agent_error_message(self) -> None:
        class Agent:
            model_profile = {
                "provider": "9router",
                "model": "model-name",
                "reasoning_effort": "high",
            }

            def invoke(self, payload):
                del payload
                raise ReconciliationAgentError(
                    "E2E selector did not match the inventory.", 422
                )

        server = ReconciliationHTTPServer(("127.0.0.1", 0), Agent(), "shared-secret")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        gateway = AgentGateway(
            f"http://127.0.0.1:{server.server_port}/invoke",
            token="shared-secret",
            timeout_seconds=5,
        )
        try:
            with self.assertRaises(AgentGatewayError) as captured:
                gateway.invoke("reconcile.main-flow.start", {"e2e": "missing"}, {})
            self.assertIn("422", str(captured.exception))
            self.assertIn(
                "E2E selector did not match the inventory.",
                str(captured.exception),
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


class CapabilityRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = CapabilityRunner(
            DOCUMENT_REPO, TOOLS_REPO, timeout_seconds=120
        )

    def test_e2e_group_filter(self) -> None:
        result = self.runner.execute(
            "e2e.list", {"group": "pelayanan-utama", "limit": "20"}
        )
        self.assertIn("E2E-RJ", result.output)
        self.assertIn("E2E-RI", result.output)
        self.assertNotIn("E2E-INVENTORY", result.output)

    def test_original_prd_section(self) -> None:
        result = self.runner.execute(
            "prd.show",
            {
                "document": "DOC-4287D4C5CFF2D2E0",
                "section": "3. In Scope",
            },
        )
        self.assertIn("Representation: direct-original-text", result.output)
        self.assertIn("## 3. In Scope", result.output)

    def test_main_flow_scanner_is_separate_from_business_cases(self) -> None:
        result = self.runner.execute("gap.main-flow", {"e2e": "E2E-RI"})
        self.assertIn("Pemeriksaan Alur Utama - Rawat Inap", result.output)
        self.assertIn("Transfer Internal", result.output)
        self.assertNotIn("ALTERNATE_FLOW", result.output)

    def test_business_case_scanner_can_target_one_prd(self) -> None:
        result = self.runner.execute(
            "gap.business-cases-prd",
            {"document": "DOC-4199BA40F7A28D80"},
        )
        self.assertIn("Pemeriksaan Kasus Bisnis", result.output)
        self.assertIn("Skenario alternatif", result.output)
        self.assertIn("Kegagalan dan pengecualian", result.output)
        self.assertIn("Validasi", result.output)
        self.assertNotIn("Pemicu dan input awal", result.output)

    def test_business_case_scanner_can_aggregate_one_e2e(self) -> None:
        result = self.runner.execute(
            "gap.business-cases-e2e", {"e2e": "E2E-EMR"}
        )
        self.assertIn("Pemeriksaan Kasus Bisnis", result.output)
        self.assertIn("Input Tindakan & BHP", result.output)

    def test_document_health_can_show_one_business_flow(self) -> None:
        result = self.runner.execute(
            "health.documents-flow", {"e2e": "E2E-RJ"}
        )
        self.assertIn("Kesehatan Dokumen - Rawat Jalan", result.output)
        self.assertIn("cakupan alur", result.output)
        self.assertIn("Tinjau detail proses", result.output)
        self.assertIn("bukan defect pasti", result.output)

    def test_document_health_can_show_all_flows(self) -> None:
        result = self.runner.execute("health.documents-flow")
        self.assertIn("Kesehatan Dokumen per Flow Bisnis", result.output)
        self.assertIn("Rawat Jalan", result.output)
        self.assertIn("Rawat Inap", result.output)
        self.assertIn("Flow bisnis: **23**", result.output)

    def test_document_health_can_show_overall_repository_summary(self) -> None:
        result = self.runner.execute("health.documents-all")
        self.assertIn("Kesehatan Dokumen Keseluruhan", result.output)
        self.assertIn("PRD unik: **209**", result.output)
        self.assertIn("Flow dengan kandidat review terbanyak", result.output)
        self.assertIn("Cakupan detail proses terdeteksi", result.output)

    def test_legacy_mixed_gap_capabilities_are_removed(self) -> None:
        names = {spec.name for spec in self.runner.list()}
        self.assertNotIn("gap.list", names)
        self.assertNotIn("gap.e2e", names)
        self.assertNotIn("gap.prd", names)
        self.assertIn("health.documents-flow", names)
        self.assertIn("health.documents-all", names)

    def test_missing_parameter_is_rejected(self) -> None:
        with self.assertRaises(CapabilityError):
            self.runner.execute("e2e.show", {})

    def test_unknown_capability_is_rejected(self) -> None:
        with self.assertRaises(CapabilityError):
            self.runner.execute("unknown", {})


class HelpSystemTests(unittest.TestCase):
    def test_discord_scope_accepts_only_the_allowed_channel(self) -> None:
        allowed = frozenset({1536662604783685642})
        self.assertTrue(
            is_allowed_discord_context(
                channel_id=1536662604783685642,
                allowed_channel_ids=allowed,
            )
        )
        self.assertFalse(
            is_allowed_discord_context(
                channel_id=999,
                allowed_channel_ids=allowed,
            )
        )
        self.assertFalse(
            is_allowed_discord_context(
                channel_id=888,
                allowed_channel_ids=allowed,
            )
        )
        self.assertFalse(
            is_allowed_discord_context(
                channel_id=None,
                allowed_channel_ids=allowed,
            )
        )

    def test_only_bot_help_threads_in_allowed_channel_remain_interactive(self) -> None:
        allowed = frozenset({1536662604783685642})
        self.assertTrue(
            is_allowed_help_message_context(
                channel_id=999,
                parent_channel_id=1536662604783685642,
                is_session_thread=True,
                allowed_channel_ids=allowed,
            )
        )
        self.assertFalse(
            is_allowed_help_message_context(
                channel_id=999,
                parent_channel_id=1536662604783685642,
                is_session_thread=False,
                allowed_channel_ids=allowed,
            )
        )

    def test_commands_and_autocomplete_accept_only_bot_help_threads(self) -> None:
        allowed = frozenset({1536662604783685642})
        self.assertTrue(
            is_allowed_bot_context(
                channel_id=999,
                parent_channel_id=1536662604783685642,
                channel_name="neurovi-help-user-12345678",
                owner_id=777,
                bot_user_id=777,
                allowed_channel_ids=allowed,
            )
        )
        self.assertFalse(
            is_allowed_bot_context(
                channel_id=999,
                parent_channel_id=1536662604783685642,
                channel_name="other-thread",
                owner_id=777,
                bot_user_id=777,
                allowed_channel_ids=allowed,
            )
        )
        self.assertFalse(
            is_allowed_bot_context(
                channel_id=999,
                parent_channel_id=1536662604783685642,
                channel_name="neurovi-help-user-12345678",
                owner_id=888,
                bot_user_id=777,
                allowed_channel_ids=allowed,
            )
        )
        self.assertFalse(
            is_allowed_help_message_context(
                channel_id=999,
                parent_channel_id=888,
                is_session_thread=True,
                allowed_channel_ids=allowed,
            )
        )

    def test_overview_lists_primary_commands(self) -> None:
        result = answer_help()
        self.assertIn("/mulai", result)
        self.assertIn("Perbaiki alur utama", result)
        self.assertIn("Akhiri sesi", result)

    def test_natural_language_maps_to_gap_help(self) -> None:
        result = answer_help("bagaimana scan gap untuk satu E2E?")
        self.assertIn("/gap alur", result)
        self.assertIn("/gap kasus", result)

    def test_gap_help_explains_the_two_scanners(self) -> None:
        result = answer_help("gap")
        self.assertIn("proses tersambung", result)
        self.assertIn("skenario alternatif", result)
        self.assertIn("tidak mengubah dokumen", result)

    def test_health_help_explains_statistics_are_not_quality_scores(self) -> None:
        result = answer_help("kesehatan dokumen")
        self.assertIn("/document-health flow", result)
        self.assertIn("/document-health all", result)
        self.assertIn("bukan nilai mutu final", result)

    def test_contextual_help_accepts_document_health_commands(self) -> None:
        result = render_contextual_help(
            {
                "summary": "Anda ingin melihat statistik kesehatan dokumen.",
                "next_step": "Pilih statistik per flow atau keseluruhan.",
                "commands": ["/document-health all"],
                "requires_developer": False,
                "limitation": "",
                "workaround": "",
            }
        )
        self.assertIsNotNone(result)
        self.assertIn("tidak memerlukan parameter", result)

    def test_finish_help_explains_stop_without_publication(self) -> None:
        result = answer_help("bagaimana finish dan push hasil rekonsiliasi?")
        self.assertIn("Akhiri sesi", result)
        self.assertIn("tidak melakukan push", result)

    def test_unknown_question_stays_help_only(self) -> None:
        result = answer_help("tolong kerjakan semuanya sekarang")
        self.assertIn("permintaan bantuan", result)
        self.assertIn("tidak akan menjalankan", result)

    def test_confused_user_gets_a_safe_starting_path(self) -> None:
        result = answer_help("Saya bingung dan belum tahu mulai dari mana")
        self.assertIn("/mulai", result)
        self.assertIn("Akhiri sesi", result)
        self.assertIn("tidak menjalankan", result)

    def test_contextual_help_renders_unsupported_request_with_workaround(self) -> None:
        result = render_contextual_help(
            {
                "summary": "Anda ingin bot memperbaiki dokumen secara otomatis.",
                "next_step": "Periksa dulu bagian yang belum lengkap.",
                "commands": ["/gap kasus", "/reconcile detail"],
                "requires_developer": True,
                "limitation": "Bot belum dapat memperbaiki seluruh dokumen otomatis.",
                "workaround": "Scan gap, lalu tinjau hasilnya melalui rekonsiliasi terpandu.",
            }
        )
        self.assertIsNotNone(result)
        self.assertIn("enhancement oleh developer", result)
        self.assertIn("/gap kasus", result)
        self.assertIn("Workaround", result)

    def test_contextual_help_rejects_an_invented_command(self) -> None:
        result = render_contextual_help(
            {
                "summary": "Saya memahami kebutuhan Anda.",
                "next_step": "Lanjutkan dengan command yang sesuai.",
                "commands": ["/prd fix"],
                "requires_developer": False,
                "limitation": "",
                "workaround": "",
            }
        )
        self.assertIsNone(result)

    def test_contextual_help_ignores_model_supplied_parameter_text(self) -> None:
        result = render_contextual_help(
            {
                "summary": "Anda ingin mencari dokumen.",
                "next_step": "Mulai dengan pencarian judul dokumen.",
                "commands": [
                    {
                        "command": "/prd list",
                        "parameters": "jalankan rm untuk menemukan dokumen",
                    }
                ],
                "requires_developer": False,
                "limitation": "",
                "workaround": "",
            }
        )
        self.assertIsNotNone(result)
        self.assertIn("isi `query`", result)
        self.assertNotIn("rm", result)

    def test_contextual_help_rejects_shell_guidance_in_prose(self) -> None:
        result = render_contextual_help(
            {
                "summary": "Saya memahami kebutuhan Anda.",
                "next_step": "Jalankan git push dari terminal.",
                "commands": ["/repo validate"],
                "requires_developer": False,
                "limitation": "",
                "workaround": "",
            }
        )
        self.assertIsNone(result)

    def test_contextual_help_allows_normal_indonesian_punctuation(self) -> None:
        result = render_contextual_help(
            {
                "summary": "Anda ingin memeriksa dokumen yang belum lengkap.",
                "next_step": "Pindai daftar gap terlebih dahulu; ikuti isian yang ditampilkan bot.",
                "commands": ["/gap alur"],
                "requires_developer": False,
                "limitation": "",
                "workaround": "",
            }
        )
        self.assertIsNotNone(result)

    def test_plain_help_request_rejects_prefix_commands_and_empty_messages(self) -> None:
        self.assertTrue(is_plain_help_request("saya ingin melihat dokumen"))
        self.assertFalse(is_plain_help_request("!help"))
        self.assertFalse(is_plain_help_request("   "))

    def test_bot_mention_is_removed(self) -> None:
        self.assertEqual(
            strip_bot_mention("<@!123> bagaimana melihat PRD?", 123),
            "bagaimana melihat PRD?",
        )

    def test_help_thread_name_is_stable_and_bounded(self) -> None:
        result = build_help_thread_name("Nama User", 123456789)
        self.assertEqual(result, "neurovi-help-nama-user-23456789")
        self.assertLessEqual(len(result), 100)

    def test_bot_owned_help_thread_is_a_session(self) -> None:
        self.assertTrue(
            is_help_session_thread(
                channel_name="neurovi-help-nama-user-23456789",
                owner_id=123,
                bot_user_id=123,
            )
        )
        self.assertFalse(
            is_help_session_thread(
                channel_name="neurovi-help-nama-user-23456789",
                owner_id=456,
                bot_user_id=123,
            )
        )

    def test_help_context_accepts_unmentioned_guild_channel_message(self) -> None:
        self.assertTrue(
            is_help_context(
                is_direct_message=False,
                bot_mentioned=True,
                is_session_thread=False,
            )
        )
        self.assertTrue(
            is_help_context(
                is_direct_message=False,
                bot_mentioned=False,
                is_session_thread=False,
                is_guild_channel=True,
            )
        )

    def test_help_context_rejects_unowned_non_help_thread(self) -> None:
        self.assertFalse(
            is_help_context(
                is_direct_message=False,
                bot_mentioned=False,
                is_session_thread=False,
                is_guild_channel=False,
                is_thread=True,
            )
        )

    def test_help_context_ignores_mentions_in_unrelated_threads(self) -> None:
        self.assertFalse(
            is_help_context(
                is_direct_message=False,
                bot_mentioned=True,
                is_session_thread=False,
                is_guild_channel=False,
                is_thread=True,
            )
        )

    def test_help_context_accepts_follow_up_in_bot_session_thread(self) -> None:
        self.assertTrue(
            is_help_context(
                is_direct_message=False,
                bot_mentioned=False,
                is_session_thread=True,
            )
        )


class DiscordReconciliationUXTests(unittest.TestCase):
    def test_e2e_autocomplete_matches_names_and_codes(self) -> None:
        options = (
            ("E2E-RJ", "Rawat Jalan"),
            ("E2E-RI", "Rawat Inap"),
        )
        self.assertEqual(
            match_e2e_options(options, "jalan"),
            (("E2E-RJ", "Rawat Jalan"),),
        )
        self.assertEqual(
            match_e2e_options(options, "E2E-RI"),
            (("E2E-RI", "Rawat Inap"),),
        )

    def test_repository_e2e_options_are_available(self) -> None:
        options = load_e2e_options(DOCUMENT_REPO)
        self.assertIn(("E2E-RJ", "Rawat Jalan"), options)

    def test_guided_process_summary_hides_internal_inventory_codes(self) -> None:
        result = guided_process_summary(DOCUMENT_REPO, "E2E-RJ")
        self.assertIn("Rawat Jalan", result)
        self.assertIn("Urutan pemeriksaan", result)
        self.assertIn("Pendaftaran Rawat Jalan", result)
        self.assertNotIn("DOMAIN_WORKLIST_PROPOSAL", result)
        self.assertNotIn("MECHANICAL_PROPOSAL", result)
        self.assertNotIn("DOC-", result)

    def test_guided_gap_summary_uses_plain_operational_language(self) -> None:
        result = guided_gap_summary(DOCUMENT_REPO, "E2E-RJ")
        self.assertIn("Pemeriksaan awal", result)
        self.assertIn("hubungan ke proses lain", result)
        self.assertIn("belum mengubah dokumen", result)
        self.assertNotIn("OWNER_DOCUMENTS_UNREVIEWED", result)
        self.assertNotIn("NO_CONFIRMED_CONTEXT_TRACE", result)

    def test_processing_states_explain_action_and_wait_condition(self) -> None:
        answer_title, answer_detail = processing_state_text("answer")
        stop_title, stop_detail = processing_state_text("stop")
        self.assertIn("menyimpan jawaban", answer_title.casefold())
        self.assertIn("langkah berikutnya", answer_detail.casefold())
        self.assertIn("mengakhiri sesi", stop_title.casefold())
        self.assertIn("tombol", stop_detail.casefold())

    def test_agent_message_is_rewritten_for_nontechnical_users(self) -> None:
        message = (
            "E2E-RJ — “Rawat Jalan” ditemukan sebagai kandidat dari "
            "worklist domain. Batas ini belum dikonfirmasi dan tidak otomatis "
            "mengonfirmasi 30 kandidat dokumen mekanis yang terdeteksi. Jawab "
            "CONFIRM jika batasnya tepat, atau SKIP, DEFER, maupun UNKNOWN."
        )
        result = plain_language_agent_message(message)
        self.assertIn("Rawat Jalan", result)
        self.assertIn("dokumen yang mungkin terkait", result)
        self.assertNotIn("Mermaid", result)
        self.assertNotIn("CONFIRM", result)

    def test_legacy_document_selection_text_is_not_rendered_as_selection_ui(self) -> None:
        question = (
            "Apakah DOC-1675 — “PRD Pendaftaran Rawat Jalan” harus dipilih "
            "sebagai CONFIRMED_INCLUDE, CONTEXT_ONLY, TAKE_OFF, atau DEFERRED?"
        )
        self.assertEqual(reconciliation_question_kind(question), "CONFIRMATION")
        self.assertEqual(
            plain_language_question(question),
            "Bagaimana dokumen **PRD Pendaftaran Rawat Jalan** digunakan dalam proses ini?",
        )

    def test_document_selection_metadata_is_ignored_by_discord_ui(self) -> None:
        question = "Apakah aturan pendaftaran ini sudah sesuai?"
        self.assertEqual(
            reconciliation_question_kind(
                question,
                question_type="DOCUMENT_SELECTION",
                document_ids="DOC-1675",
            ),
            "CONFIRMATION",
        )

    def test_gateway_error_is_rewritten_for_nontechnical_users(self) -> None:
        error = AgentGatewayError(
            "Agent gateway rejected request (422): ERROR: No E2E matches: rawat"
        )
        result = plain_language_gateway_error(error)
        self.assertIn("tidak ditemukan", result)
        self.assertIn("pilih salah satu hasil", result)
        self.assertNotIn("422", result)
        self.assertNotIn("gateway", result.casefold())

    def test_latest_session_is_resolved_without_user_input(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            older = root / "reconciliation/workspaces/E2E-ONE/session.json"
            newer = root / "reconciliation/workspaces/E2E-TWO/session.json"
            older.parent.mkdir(parents=True)
            newer.parent.mkdir(parents=True)
            older.write_text(
                json.dumps(
                    {
                        "session_id": "REC-E2E-ONE-001",
                        "updated_at": "2026-01-01T00:00:00Z",
                        "status": "AWAITING_USER",
                        "started_by": {"discord_user_id": "123"},
                    }
                ),
                encoding="utf-8",
            )
            newer.write_text(
                json.dumps(
                    {
                        "session_id": "REC-E2E-TWO-001",
                        "updated_at": "2026-01-02T00:00:00Z",
                        "status": "AWAITING_USER",
                        "started_by": {"discord_user_id": "123"},
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                latest_reconciliation_session_for_user(root, 123),
                "REC-E2E-TWO-001",
            )

    def test_latest_session_ignores_user_stopped_session(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stopped = root / "reconciliation/workspaces/E2E-ONE/session.json"
            active = root / "reconciliation/workspaces/E2E-TWO/session.json"
            stopped.parent.mkdir(parents=True)
            active.parent.mkdir(parents=True)
            stopped.write_text(
                json.dumps(
                    {
                        "session_id": "REC-E2E-ONE-001",
                        "updated_at": "2026-01-03T00:00:00Z",
                        "status": "STOPPED_BY_USER",
                        "started_by": {"discord_user_id": "123"},
                    }
                ),
                encoding="utf-8",
            )
            active.write_text(
                json.dumps(
                    {
                        "session_id": "REC-E2E-TWO-001",
                        "updated_at": "2026-01-02T00:00:00Z",
                        "status": "AWAITING_USER",
                        "started_by": {"discord_user_id": "123"},
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                latest_reconciliation_session_for_user(root, 123),
                "REC-E2E-TWO-001",
            )


    def test_latest_session_can_be_selected_by_reconciliation_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            base = root / "reconciliation/workspaces/E2E-RJ/sessions"
            main = base / "main-flow/session.json"
            detail = base / "business-cases/session.json"
            main.parent.mkdir(parents=True)
            detail.parent.mkdir(parents=True)
            common = {
                "updated_at": "2026-01-02T00:00:00Z",
                "status": "AWAITING_USER",
                "started_by": {"discord_user_id": "123"},
            }
            main.write_text(
                json.dumps({**common, "session_id": "REC-E2E-RJ-MF-001", "reconciliation_mode": "MAIN_FLOW"}),
                encoding="utf-8",
            )
            detail.write_text(
                json.dumps({**common, "session_id": "REC-E2E-RJ-BC-001", "reconciliation_mode": "BUSINESS_CASES"}),
                encoding="utf-8",
            )
            self.assertEqual(
                latest_reconciliation_session_for_user(root, 123, "MAIN_FLOW"),
                "REC-E2E-RJ-MF-001",
            )
            self.assertEqual(
                latest_reconciliation_session_for_user(root, 123, "BUSINESS_CASES"),
                "REC-E2E-RJ-BC-001",
            )

    def test_resume_retries_agent_when_no_question_is_ready(self) -> None:
        capability, parameters = reconciliation_resume_request(
            {
                "session_id": "REC-E2E-RJ-MF-001",
                "e2e_code": "E2E-RJ",
                "status": "IN_PROGRESS",
                "current_question": None,
            },
            "MAIN_FLOW",
        )
        self.assertEqual(capability, "reconcile.main-flow.start")
        self.assertEqual(parameters, {"e2e": "E2E-RJ"})

    def test_resume_displays_existing_question_without_running_agent(self) -> None:
        capability, parameters = reconciliation_resume_request(
            {
                "session_id": "REC-E2E-RJ-BC-001",
                "e2e_code": "E2E-RJ",
                "status": "AWAITING_USER",
                "current_question": {"question": "Apa aturan validasinya?"},
            },
            "BUSINESS_CASES",
        )
        self.assertEqual(capability, "reconcile.status")
        self.assertEqual(parameters, {"session_id": "REC-E2E-RJ-BC-001"})

if __name__ == "__main__":
    unittest.main()
