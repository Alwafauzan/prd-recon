from __future__ import annotations

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

from neurovi_prd_server.agent_gateway import AgentGateway, AgentGatewayError
from neurovi_prd_server.agent_server import ReconciliationHTTPServer
from neurovi_prd_server.capabilities import CapabilityError, CapabilityRunner
from neurovi_prd_server.config import ConfigurationError, Settings
from neurovi_prd_server.help_system import (
    answer_help,
    build_help_thread_name,
    is_help_context,
    is_help_session_thread,
    strip_bot_mention,
)
from neurovi_prd_server.llm_client import LLMResult, OpenAICompatibleLLM
from neurovi_prd_server.reconciliation_agent import (
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

            workspace = repo / "reconciliation/workspaces/E2E-ADM-01"
            self.assertTrue(created)
            self.assertEqual(session["session_id"], "REC-E2E-ADM-01-001")
            self.assertTrue((workspace / "decision-register.csv").is_file())
            self.assertTrue((workspace / "interview-register.csv").is_file())
            self.assertEqual(original.read_text(encoding="utf-8"), "immutable fact\n")
            self.assertNotIn(
                "api_key", (workspace / "session.json").read_text(encoding="utf-8")
            )


class ReconciliationAgentTests(unittest.TestCase):
    def test_start_uses_repository_evidence_and_returns_a_session(self) -> None:
        class FakeLLM:
            def __init__(self):
                self.user_prompt = ""

            def complete(self, system_prompt, user_prompt):
                self.user_prompt = user_prompt
                self.assertions = "Never edit `source/original/`" in system_prompt
                return LLMResult(
                    {
                        "message": "Konfirmasi boundary E2E terlebih dahulu.",
                        "status": "AWAITING_USER",
                        "current_question": {
                            "why_needed": "Boundary mengendalikan scope dan handoff data.",
                            "question": "Apakah boundary E2E ini sudah sesuai?",
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
            for filename in (
                "e2e-domain-inventory.json",
                "document-e2e-coverage.csv",
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
                    "capability": "reconcile.start",
                    "parameters": {"e2e": "E2E-ADM-01"},
                    "actor": {
                        "discord_user_id": "123",
                        "discord_role_ids": ["456"],
                    },
                }
            )

            self.assertTrue(llm.assertions)
            self.assertIn('"e2e_code": "E2E-ADM-01"', llm.user_prompt)
            self.assertEqual(result["session_id"], "REC-E2E-ADM-01-001")
            self.assertEqual(result["status"], "AWAITING_USER")
            self.assertTrue(
                (
                    repo
                    / "reconciliation/workspaces/E2E-ADM-01/interview-register.csv"
                ).is_file()
            )


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
                gateway.invoke("reconcile.start", {"e2e": "missing"}, {})
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
            "e2e.list", {"group": "admisi-emr", "limit": "20"}
        )
        self.assertIn("E2E-ADM-01", result.output)
        self.assertNotIn("E2E-BO-18", result.output)

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

    def test_missing_parameter_is_rejected(self) -> None:
        with self.assertRaises(CapabilityError):
            self.runner.execute("e2e.show", {})

    def test_unknown_capability_is_rejected(self) -> None:
        with self.assertRaises(CapabilityError):
            self.runner.execute("unknown", {})


class HelpSystemTests(unittest.TestCase):
    def test_overview_lists_primary_commands(self) -> None:
        result = answer_help()
        self.assertIn("/prd show", result)
        self.assertIn("/reconcile", result)
        self.assertIn("/finish", result)

    def test_natural_language_maps_to_gap_help(self) -> None:
        result = answer_help("bagaimana scan gap untuk satu E2E?")
        self.assertIn("/gap e2e", result)

    def test_finish_help_requires_baseline_approval(self) -> None:
        result = answer_help("bagaimana finish dan push hasil rekonsiliasi?")
        self.assertIn("BASELINE_APPROVAL", result)
        self.assertIn("atomic push", result)

    def test_unknown_question_stays_help_only(self) -> None:
        result = answer_help("tolong kerjakan semuanya sekarang")
        self.assertIn("pertanyaan bantuan", result)

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

    def test_help_context_requires_mention_outside_session(self) -> None:
        self.assertTrue(
            is_help_context(
                is_direct_message=False,
                bot_mentioned=True,
                is_session_thread=False,
            )
        )
        self.assertFalse(
            is_help_context(
                is_direct_message=False,
                bot_mentioned=False,
                is_session_thread=False,
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


if __name__ == "__main__":
    unittest.main()
