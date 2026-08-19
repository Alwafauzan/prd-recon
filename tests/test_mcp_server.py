from __future__ import annotations

import asyncio
import ast
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from neurovi_prd_server import mcp_server


TOOLS_REPO = Path(__file__).resolve().parents[1]
DOCUMENT_REPO = TOOLS_REPO / "neurovi-prd"


class PrdMcpReaderTests(unittest.TestCase):
    def reader(self, *, max_response_chars: int = 64_000) -> mcp_server.PrdReader:
        return mcp_server.PrdReader(
            mcp_server.Config(
                root=DOCUMENT_REPO.resolve(),
                max_response_chars=max_response_chars,
            )
        )

    def test_status_exposes_only_immutable_read_context(self) -> None:
        result = self.reader().prd_status()

        self.assertEqual(result["status"], "OK")
        self.assertTrue(result["readOnly"])
        self.assertFalse(result["writeTools"])
        self.assertFalse(result["arbitraryPathAccess"])
        self.assertFalse(result["shellAccess"])
        self.assertFalse(result["gitMutation"])
        self.assertFalse(result["outboundNetworkTools"])
        self.assertEqual(result["sourceChecksumVerification"], "EVERY_PRD_READ")
        self.assertEqual(result["counts"]["uniquePrds"], 209)
        self.assertEqual(result["counts"]["e2eDomains"], 23)

    def test_search_and_get_prd_return_literal_checksum_verified_content(self) -> None:
        reader = self.reader()
        search = reader.search_prds("check-in mandiri", e2e="E2E-RJ", limit=2)
        document_code = search["results"][0]["documentCode"]
        result = reader.get_prd(
            document_code,
            section="8. Business Rules",
            max_chars=800,
        )

        self.assertEqual(search["status"], "MATCHED")
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["representation"], "direct-original-markdown")
        self.assertEqual(result["document"]["documentCode"], "PRD-RJ-001")
        self.assertEqual(result["section"]["heading"], "8. Business Rules")
        self.assertIn("Business Rules", result["content"])
        self.assertTrue(result["document"]["sha256"])

    def test_search_rejects_queries_without_searchable_characters(self) -> None:
        with self.assertRaisesRegex(mcp_server.PrdMcpError, "letters or numbers"):
            self.reader().search_prds("---")

    def test_prd_can_be_read_to_completion_by_offset(self) -> None:
        reader = self.reader()
        first = reader.get_prd("PRD-RJ-001", max_chars=500)
        second = reader.get_prd(
            "PRD-RJ-001", offset=first["nextOffset"], max_chars=500
        )

        self.assertTrue(first["truncated"])
        self.assertEqual(second["offset"], 500)
        self.assertNotEqual(first["content"], second["content"])
        self.assertEqual(first["totalChars"], second["totalChars"])

    def test_prd_accepts_a_100000_character_request(self) -> None:
        result = self.reader(max_response_chars=128_000).get_prd(
            "PRD-HD-001", max_chars=100_000
        )

        self.assertEqual(result["status"], "OK")
        self.assertLessEqual(result["returnedChars"], 100_000)

    def test_task_context_combines_literal_sections_e2e_and_relations(self) -> None:
        result = self.reader(max_response_chars=32_000).get_task_context(
            "check-in mandiri",
            e2e="E2E-RJ",
            document_limit=1,
            section_families=["scope", "flow_scenarios", "business_rules"],
        )

        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["documents"][0]["document"]["documentCode"], "PRD-RJ-001")
        self.assertEqual(result["inferredE2eCandidates"][0]["e2eCode"], "E2E-RJ")
        families = {
            section["family"]: section
            for section in result["documents"][0]["sectionContext"]
        }
        self.assertIn("3. In Scope", families["scope"]["sections"][0]["content"])
        self.assertIn("source/original/", families["scope"]["sections"][0]["sourceReference"])
        self.assertIn("REVIEW_REQUIRED", result["evidenceNotice"])

    def test_e2e_worklist_is_paginated_without_losing_context(self) -> None:
        reader = self.reader()
        first = reader.get_e2e_context(
            "E2E-MASTER",
            include_relations=False,
            document_limit=2,
        )
        second = reader.get_e2e_context(
            "E2E-MASTER",
            include_relations=False,
            document_offset=first["nextDocumentOffset"],
            document_limit=2,
        )

        self.assertEqual(len(first["worklist"]), 2)
        self.assertTrue(first["worklistTruncated"])
        self.assertEqual(first["nextDocumentOffset"], 2)
        self.assertNotEqual(
            first["worklist"][0]["document"]["documentId"],
            second["worklist"][0]["document"]["documentId"],
        )
        self.assertEqual(first["relations"], [])

    def test_source_explicit_relation_filter_never_returns_review_candidates(self) -> None:
        result = self.reader().trace_prd_relations(
            "DOC-68FE75DBEC8D1F4A",
            evidence="source-explicit",
            limit=20,
        )

        self.assertEqual(result["status"], "OK")
        self.assertTrue(result["relations"])
        self.assertTrue(
            all(
                relation["verificationStatus"] == "SOURCE_EXPLICIT"
                for relation in result["relations"]
            )
        )

    def test_symlinked_repository_files_are_not_exposed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outside = root.parent / f"{root.name}-outside.txt"
            outside.write_text("secret", encoding="utf-8")
            link = root / "link.txt"
            link.symlink_to(outside)
            reader = mcp_server.PrdReader(mcp_server.Config(root=root.resolve()))
            try:
                with self.assertRaisesRegex(mcp_server.PrdMcpError, "escapes"):
                    reader._safe_file(Path("link.txt"))
            finally:
                outside.unlink()



class PrdMcpUpdaterTests(unittest.TestCase):
    def config(self) -> mcp_server.Config:
        return mcp_server.Config(
            root=DOCUMENT_REPO.resolve(),
            agent_gateway_url="http://127.0.0.1:8080/invoke",
            agent_gateway_token="g" * 48,
            actor_id="mcp-operator",
            actor_name="MCP Operator",
            actor_role_ids=("456",),
        )

    def test_updater_forwards_only_whitelisted_capabilities_and_static_actor(self) -> None:
        class Gateway:
            def __init__(self):
                self.calls = []

            def invoke(self, capability, parameters, actor):
                self.calls.append((capability, parameters, actor))
                return SimpleNamespace(
                    message="ok",
                    status="AWAITING_USER",
                    raw={
                        "message": "ok",
                        "status": "AWAITING_USER",
                        "session_id": "REC-E2E-RJ-BC-001",
                    },
                )

        gateway = Gateway()
        updater = mcp_server.PrdReconciliationUpdater(self.config(), gateway)
        result = updater.start("E2E-RJ", "business_cases")

        self.assertEqual(result["session_id"], "REC-E2E-RJ-BC-001")
        capability, parameters, actor = gateway.calls[0]
        self.assertEqual(capability, "reconcile.business-cases.start")
        self.assertEqual(parameters, {"e2e": "E2E-RJ"})
        self.assertEqual(actor["discord_user_id"], "mcp-operator")
        self.assertEqual(actor["discord_role_ids"], ["456"])
        self.assertIsNone(actor["guild_id"])
        self.assertNotIn("repository_root", parameters)

    def test_decision_and_stop_require_explicit_confirmation_literals(self) -> None:
        class Gateway:
            def invoke(self, capability, parameters, actor):
                del capability, parameters, actor
                return SimpleNamespace(message="ok", status="OK", raw={"status": "OK"})

        updater = mcp_server.PrdReconciliationUpdater(self.config(), Gateway())
        with self.assertRaisesRegex(mcp_server.PrdMcpError, "USER_CONFIRMED"):
            updater.decide("REC-E2E-RJ-MF-001", "Pilih opsi A", "yes")
        with self.assertRaisesRegex(mcp_server.PrdMcpError, "STOP_SESSION"):
            updater.stop("REC-E2E-RJ-MF-001", "yes")

    def test_updater_rejects_invalid_session_and_control_values_locally(self) -> None:
        class Gateway:
            def invoke(self, capability, parameters, actor):
                raise AssertionError("gateway must not be called")

        updater = mcp_server.PrdReconciliationUpdater(self.config(), Gateway())
        with self.assertRaisesRegex(mcp_server.PrdMcpError, "invalid"):
            updater.status("../../session.json")
        with self.assertRaisesRegex(mcp_server.PrdMcpError, "SKIP"):
            updater.control("REC-E2E-RJ-MF-001", "ANSWER")

    def test_updater_accepts_legacy_main_flow_session_ids(self) -> None:
        class Gateway:
            def invoke(self, capability, parameters, actor):
                del actor
                return SimpleNamespace(
                    message="ok",
                    status="AWAITING_USER",
                    raw={"capability": capability, "parameters": parameters},
                )

        updater = mcp_server.PrdReconciliationUpdater(self.config(), Gateway())
        result = updater.status("REC-E2E-RJ-001")

        self.assertEqual(result["capability"], "reconcile.status")
        self.assertEqual(
            result["parameters"], {"session_id": "REC-E2E-RJ-001"}
        )


class PrdMcpConfigurationTests(unittest.TestCase):
    def environment(self) -> dict[str, str]:
        return {
            "NEUROVI_PRD_MCP_REPOSITORY": str(DOCUMENT_REPO),
            "NEUROVI_PRD_MCP_BIND_HOST": "192.168.1.20",
            "NEUROVI_PRD_MCP_PORT": "8767",
            "NEUROVI_PRD_MCP_PUBLIC_URL": "http://192.168.1.20:8767/mcp",
            "NEUROVI_PRD_MCP_TOKEN": "x" * 48,
        }

    def update_environment(self) -> dict[str, str]:
        return self.environment() | {
            "NEUROVI_PRD_MCP_AGENT_GATEWAY_URL": "http://127.0.0.1:8080/invoke",
            "NEUROVI_PRD_MCP_AGENT_GATEWAY_TOKEN": "g" * 48,
            "NEUROVI_PRD_MCP_ACTOR_ID": "mcp-operator",
            "NEUROVI_PRD_MCP_ACTOR_NAME": "MCP Operator",
            "NEUROVI_PRD_MCP_ACTOR_ROLE_IDS": "456,789",
        }

    def test_update_config_requires_complete_private_gateway_and_actor(self) -> None:
        with mock.patch.dict(os.environ, self.update_environment(), clear=True):
            config = mcp_server.Config.from_environment(require_http=True)

        self.assertTrue(config.reconciliation_updates_enabled)
        self.assertEqual(config.actor_role_ids, ("456", "789"))

        incomplete = self.environment() | {
            "NEUROVI_PRD_MCP_AGENT_GATEWAY_URL": "http://127.0.0.1:8080/invoke"
        }
        with mock.patch.dict(os.environ, incomplete, clear=True):
            with self.assertRaisesRegex(mcp_server.PrdMcpError, "partially configured"):
                mcp_server.Config.from_environment(require_http=True)

    def test_update_config_rejects_public_or_arbitrary_gateway(self) -> None:
        environment = self.update_environment() | {
            "NEUROVI_PRD_MCP_AGENT_GATEWAY_URL": "https://8.8.8.8/invoke"
        }
        with mock.patch.dict(os.environ, environment, clear=True):
            with self.assertRaisesRegex(mcp_server.PrdMcpError, "private IPv4"):
                mcp_server.Config.from_environment(require_http=True)

    def test_remote_config_requires_private_ipv4_bind_and_token(self) -> None:
        with mock.patch.dict(os.environ, self.environment(), clear=True):
            config = mcp_server.Config.from_environment(require_http=True)

        self.assertEqual(config.bind_host, "192.168.1.20")
        self.assertEqual(config.port, 8767)

    def test_https_reverse_proxy_url_can_differ_from_private_bind(self) -> None:
        environment = self.environment() | {
            "NEUROVI_PRD_MCP_BIND_HOST": "127.0.0.1",
            "NEUROVI_PRD_MCP_PUBLIC_URL": "https://prd.internal.example/mcp",
        }
        with mock.patch.dict(os.environ, environment, clear=True):
            config = mcp_server.Config.from_environment(require_http=True)

        self.assertEqual(config.bind_host, "127.0.0.1")
        self.assertEqual(config.public_url, "https://prd.internal.example/mcp")

    def test_unspecified_or_public_bind_is_rejected(self) -> None:
        for bind_host, public_url in (
            ("0.0.0.0", "http://0.0.0.0:8767/mcp"),
            ("8.8.8.8", "http://8.8.8.8:8767/mcp"),
        ):
            environment = self.environment() | {
                "NEUROVI_PRD_MCP_BIND_HOST": bind_host,
                "NEUROVI_PRD_MCP_PUBLIC_URL": public_url,
            }
            with self.subTest(bind_host=bind_host):
                with mock.patch.dict(os.environ, environment, clear=True):
                    with self.assertRaisesRegex(mcp_server.PrdMcpError, "private IPv4"):
                        mcp_server.Config.from_environment(require_http=True)

    def test_invalid_static_token_is_rejected_without_importing_sdk(self) -> None:
        verifier = mcp_server.StaticTokenVerifier(
            "a" * 48, "http://127.0.0.1:8767/mcp"
        )
        result = asyncio.run(verifier.verify_token("b" * 48))
        self.assertIsNone(result)

    def test_mcp_surface_has_bounded_read_and_workspace_update_tools(self) -> None:
        source_path = TOOLS_REPO / "src/neurovi_prd_server/mcp_server.py"
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        tools = set()
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                function = decorator.func if isinstance(decorator, ast.Call) else decorator
                if isinstance(function, ast.Attribute) and function.attr == "tool":
                    tools.add(node.name)

        self.assertEqual(
            tools,
            {
                "prd_status",
                "search_prds",
                "get_prd",
                "get_e2e_context",
                "get_task_context",
                "trace_prd_relations",
                "start_prd_reconciliation",
                "get_prd_reconciliation_status",
                "answer_prd_reconciliation",
                "control_prd_reconciliation",
                "add_prd_reconciliation_reference",
                "confirm_prd_reconciliation_decision",
                "stop_prd_reconciliation",
            },
        )
        source = source_path.read_text(encoding="utf-8")
        self.assertNotIn("subprocess", source)
        self.assertNotIn("os.system", source)
        self.assertNotIn("def write_", source)
        self.assertNotIn("def read_path", source)
        self.assertNotIn('"reconcile.finish"', source)
        self.assertIn('run(transport="streamable-http")', source)
        self.assertNotIn('run(transport="stdio")', source)


if __name__ == "__main__":
    unittest.main()
