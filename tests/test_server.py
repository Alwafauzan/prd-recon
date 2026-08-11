from __future__ import annotations

import os
import unittest
from pathlib import Path

from neurovi_prd_server.capabilities import CapabilityError, CapabilityRunner
from neurovi_prd_server.config import Settings
from neurovi_prd_server.help_system import (
    answer_help,
    build_help_thread_name,
    is_help_context,
    is_help_session_thread,
    strip_bot_mention,
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
