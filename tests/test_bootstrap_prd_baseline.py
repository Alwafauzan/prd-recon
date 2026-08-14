from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import scripts.bootstrap_prd_baseline as bootstrap


class CanonicalBootstrapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.repo = Path(self.temporary.name)
        source_dir = self.repo / "source/original/PRD/PRD Generator (.md)/Pelayanan (.md)"
        source_dir.mkdir(parents=True)
        (self.repo / "reconciliation/e2e-inventory").mkdir(parents=True)
        (self.repo / "catalog").mkdir(parents=True)

        self.source_relative = "PRD/PRD Generator (.md)/Pelayanan (.md)/source.md"
        self.source = source_dir / "source.md"
        self.raw = b"# Original Title\n\n## Scope\n\nLiteral source fact.\n"
        self.source.write_bytes(self.raw)
        sha = hashlib.sha256(self.raw).hexdigest()

        inventory = {
            "inventory_type": "E2E_DOMAIN_WORKLIST",
            "inventory_version": "test",
            "eligible_file_count": 1,
            "unique_prd_count": 1,
            "domain_count": 1,
            "relations": [
                {
                    "relation_id": "REL-001",
                    "source_document_id": "DOC-001",
                    "target_document_id": "DOC-001",
                    "source_domain_code": "E2E-RJ",
                    "target_domain_code": "E2E-RJ",
                    "relationship_type": "ACTIVATES",
                    "status_transition": "Source-explicit transition.",
                    "evidence_class": "CROSS_SOURCE_FACT",
                    "verification_status": "SOURCE_EXPLICIT",
                    "conflict_status": "NO_CONFLICT_IDENTIFIED",
                    "evidence_reference": f"{self.source_relative}:1",
                }
            ],
            "domains": [
                {
                    "e2e_code": "E2E-RJ",
                    "title": "Rawat Jalan",
                    "documents": [
                        {
                            "worklist_order": 1,
                            "worklist_stage": "ENTRY",
                            "content_id": "CONTENT-001",
                            "document_id": "DOC-001",
                            "title": "Original Title",
                            "source_path": self.source_relative,
                            "source_representations": [
                                {
                                    "document_id": "DOC-001",
                                    "source_path": self.source_relative,
                                    "title": "Original Title",
                                    "sha256": sha,
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        catalog = {
            "schema_version": 1,
            "documents": [
                {
                    "document_id": "DOC-001",
                    "content_id": "CONTENT-001",
                    "source_path": self.source_relative,
                    "title": "Original Title",
                    "sha256": sha,
                    "headings": [
                        {"level": 1, "text": "Original Title", "line": 1},
                        {"level": 2, "text": "Scope", "line": 3},
                    ],
                }
            ],
        }
        (self.repo / bootstrap.INVENTORY_PATH).write_text(json.dumps(inventory), encoding="utf-8")
        (self.repo / bootstrap.CATALOG_PATH).write_text(json.dumps(catalog), encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def add_rawat_inap_document(self) -> None:
        source_relative = "PRD/PRD Generator (.md)/Pelayanan (.md)/rawat-inap.md"
        source = self.repo / "source/original" / source_relative
        raw = b"# Rawat Inap\n\n## Main Flow\n\nReceives the explicit handoff.\n"
        source.write_bytes(raw)
        sha = hashlib.sha256(raw).hexdigest()

        inventory_path = self.repo / bootstrap.INVENTORY_PATH
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        inventory["eligible_file_count"] = 2
        inventory["unique_prd_count"] = 2
        inventory["domain_count"] = 2
        inventory["relations"][0].update(
            {
                "target_document_id": "DOC-002",
                "target_domain_code": "E2E-RI",
            }
        )
        inventory["domains"].append(
            {
                "e2e_code": "E2E-RI",
                "title": "Rawat Inap",
                "documents": [
                    {
                        "worklist_order": 1,
                        "worklist_stage": "ENTRY",
                        "content_id": "CONTENT-002",
                        "document_id": "DOC-002",
                        "title": "Rawat Inap",
                        "source_path": source_relative,
                        "source_representations": [
                            {
                                "document_id": "DOC-002",
                                "source_path": source_relative,
                                "title": "Rawat Inap",
                                "sha256": sha,
                            }
                        ],
                    }
                ],
            }
        )
        inventory_path.write_text(json.dumps(inventory), encoding="utf-8")

        catalog_path = self.repo / bootstrap.CATALOG_PATH
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        catalog["documents"].append(
            {
                "document_id": "DOC-002",
                "content_id": "CONTENT-002",
                "source_path": source_relative,
                "title": "Rawat Inap",
                "sha256": sha,
                "headings": [
                    {"level": 1, "text": "Rawat Inap", "line": 1},
                    {"level": 2, "text": "Main Flow", "line": 3},
                ],
            }
        )
        catalog_path.write_text(json.dumps(catalog), encoding="utf-8")

    def test_build_is_lossless_and_deterministic(self) -> None:
        self.assertTrue(bootstrap.build(self.repo)["valid"])
        manifest_path = self.repo / bootstrap.MANIFEST_PATH
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        document = manifest["documents"][0]
        generated_path = self.repo / document["path"]
        generated = generated_path.read_bytes()

        self.assertEqual(document["document_code"], "PRD-RJ-001")
        self.assertEqual(manifest["canonical_version"], "v0.0.0")
        self.assertEqual(manifest["generator_version"], 2)
        self.assertEqual(manifest["artifact_type"], "CANONICAL_BASELINE_MANIFEST")
        self.assertEqual(document["path"], "reconciliation/canonical/prds/PRD-RJ-001.md")
        self.assertEqual(document["payload_length"], len(self.raw))
        self.assertEqual(generated[document["payload_offset"] :], self.raw)
        self.assertEqual(manifest["generated_e2e_count"], 1)
        e2e = manifest["e2e_contexts"][0]
        self.assertEqual(e2e["path"], "reconciliation/canonical/e2e/E2E-RJ.md")
        e2e_text = (self.repo / e2e["path"]).read_text(encoding="utf-8")
        self.assertIn("[PRD-RJ-001](../prds/PRD-RJ-001.md)", e2e_text)
        self.assertIn("not automatically a confirmed end-to-end sequence", e2e_text)
        self.assertIn("Automatic Source-Fact Reconciliation", e2e_text)
        self.assertIn("RESOLVED_BY_SOURCE_FACT", e2e_text)
        self.assertEqual(manifest["automatically_reconciled_source_fact_count"], 1)
        self.assertEqual(e2e["automatically_reconciled_source_fact_count"], 1)
        automatic = json.loads(
            (self.repo / bootstrap.AUTOMATIC_REGISTER_PATH).read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(automatic["summary"]["scanned_document_count"], 1)
        self.assertEqual(
            manifest["automatic_candidate_reconciliation"]["candidate_count"],
            automatic["summary"]["candidate_count"],
        )

        manifest_bytes = manifest_path.read_bytes()
        self.assertTrue(bootstrap.build(self.repo)["valid"])
        self.assertEqual(manifest_path.read_bytes(), manifest_bytes)
        self.assertEqual(generated_path.read_bytes(), generated)

    def test_verified_cross_domain_relation_materializes_direct_graph_links(self) -> None:
        self.add_rawat_inap_document()

        self.assertTrue(bootstrap.build(self.repo)["valid"])
        manifest = json.loads(
            (self.repo / bootstrap.MANIFEST_PATH).read_text(encoding="utf-8")
        )
        documents = {
            item["document_code"]: item for item in manifest["documents"]
        }
        rawat_jalan = (
            self.repo / documents["PRD-RJ-001"]["path"]
        ).read_text(encoding="utf-8")
        rawat_inap = (
            self.repo / documents["PRD-RI-001"]["path"]
        ).read_text(encoding="utf-8")
        e2e_rawat_jalan = (
            self.repo / "reconciliation/canonical/e2e/E2E-RJ.md"
        ).read_text(encoding="utf-8")

        self.assertIn("## Verified Document Relationships", rawat_jalan)
        self.assertIn("[PRD-RI-001](<PRD-RI-001.md>)", rawat_jalan)
        self.assertIn("[E2E-RI](<../e2e/E2E-RI.md>)", rawat_jalan)
        self.assertIn("[PRD-RJ-001](<PRD-RJ-001.md>)", rawat_inap)
        self.assertIn("## Verified Cross-Domain Flow", e2e_rawat_jalan)
        self.assertIn("[E2E-RI](<E2E-RI.md>)", e2e_rawat_jalan)
        self.assertEqual(
            manifest["relationship_graph"]["verified_cross_domain_relation_count"],
            1,
        )
        self.assertEqual(
            documents["PRD-RJ-001"]["verified_cross_domain_relation_count"],
            1,
        )
        self.assertEqual(manifest["semantic_changes"], "NONE")

    def test_mechanical_relation_does_not_materialize_as_graph_fact(self) -> None:
        self.add_rawat_inap_document()
        inventory_path = self.repo / bootstrap.INVENTORY_PATH
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        inventory["relations"][0].update(
            {
                "relationship_type": "REFERENCES",
                "evidence_class": "MECHANICAL_CANDIDATE",
                "verification_status": "REVIEW_REQUIRED",
            }
        )
        inventory_path.write_text(json.dumps(inventory), encoding="utf-8")

        self.assertTrue(bootstrap.build(self.repo)["valid"])
        manifest = json.loads(
            (self.repo / bootstrap.MANIFEST_PATH).read_text(encoding="utf-8")
        )
        rawat_jalan = (
            self.repo / "reconciliation/canonical/prds/PRD-RJ-001.md"
        ).read_text(encoding="utf-8")
        e2e_rawat_jalan = (
            self.repo / "reconciliation/canonical/e2e/E2E-RJ.md"
        ).read_text(encoding="utf-8")

        self.assertNotIn("## Verified Document Relationships", rawat_jalan)
        self.assertNotIn("[PRD-RI-001](<PRD-RI-001.md>)", rawat_jalan)
        self.assertNotIn("## Verified Cross-Domain Flow", e2e_rawat_jalan)
        self.assertEqual(
            manifest["relationship_graph"]["verified_relation_count"], 0
        )
        self.assertEqual(
            manifest["relationship_graph"]["mechanical_candidate_relation_count"],
            1,
        )

    def test_validate_detects_modified_payload(self) -> None:
        bootstrap.build(self.repo)
        manifest = json.loads((self.repo / bootstrap.MANIFEST_PATH).read_text(encoding="utf-8"))
        document = manifest["documents"][0]
        generated_path = self.repo / document["path"]
        generated_path.write_bytes(generated_path.read_bytes() + b"changed")

        result = bootstrap.validate(self.repo)
        self.assertFalse(result["valid"])
        self.assertTrue(any("Generated checksum changed" in item for item in result["errors"]))

    def test_source_conflict_is_never_closed_automatically(self) -> None:
        inventory_path = self.repo / bootstrap.INVENTORY_PATH
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        inventory["relations"][0]["conflict_status"] = "CONFLICT_FOUND"
        inventory["relations"][0]["notes"] = "Two eligible sources disagree."
        inventory_path.write_text(json.dumps(inventory), encoding="utf-8")

        self.assertTrue(bootstrap.build(self.repo)["valid"])
        manifest = json.loads(
            (self.repo / bootstrap.MANIFEST_PATH).read_text(encoding="utf-8")
        )
        e2e = manifest["e2e_contexts"][0]
        e2e_text = (self.repo / e2e["path"]).read_text(encoding="utf-8")

        self.assertEqual(manifest["automatically_reconciled_source_fact_count"], 0)
        self.assertEqual(manifest["human_decision_required_count"], 1)
        self.assertIn("HUMAN_DECISION_REQUIRED", e2e_text)
        self.assertNotIn("RESOLVED_BY_SOURCE_FACT", e2e_text)

    def test_assumption_revision_history_and_unresolved_text_never_close(self) -> None:
        self.raw = (
            b"# Original Title\n\n"
            b"## Overview\n\nNo structured error section.\n\n"
            b"## Revision History\n\n"
            b"| Date | Version | Description |\n|---|---|---|\n"
            b"| 2026-01-01 | 1.0 | If invalid, the system shows an error. |\n\n"
            b"## Assumptions\n\n"
            b"[ASUMSI] Jika gagal, sistem menampilkan error.\n\n"
            b"## Open Questions\n\nTBD: error handling belum didefinisikan.\n"
        )
        self.source.write_bytes(self.raw)
        sha = hashlib.sha256(self.raw).hexdigest()
        inventory_path = self.repo / bootstrap.INVENTORY_PATH
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        membership = inventory["domains"][0]["documents"][0]
        membership["flow_checks"] = {
            "trigger_input": "SOURCE_CONTEXT_PRESENT",
            "sequence": "SOURCE_CONTEXT_PRESENT",
            "handoff": "SOURCE_CONTEXT_PRESENT",
            "output": "SOURCE_CONTEXT_PRESENT",
            "status_transition": "SOURCE_CONTEXT_PRESENT",
            "alternate_cases": "SOURCE_CONTEXT_PRESENT",
        }
        membership["source_representations"][0]["sha256"] = sha
        inventory["relations"] = []
        inventory_path.write_text(json.dumps(inventory), encoding="utf-8")
        catalog_path = self.repo / bootstrap.CATALOG_PATH
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        catalog["documents"][0]["sha256"] = sha
        catalog["documents"][0]["headings"] = [
            {"level": 1, "text": "Original Title", "line": 1},
            {"level": 2, "text": "Overview", "line": 3},
            {"level": 2, "text": "Revision History", "line": 7},
            {"level": 2, "text": "Assumptions", "line": 13},
            {"level": 2, "text": "Open Questions", "line": 17},
        ]
        catalog_path.write_text(json.dumps(catalog), encoding="utf-8")

        self.assertTrue(bootstrap.build(self.repo)["valid"])
        automatic = json.loads(
            (self.repo / bootstrap.AUTOMATIC_REGISTER_PATH).read_text(
                encoding="utf-8"
            )
        )
        resolved = [
            item
            for item in automatic["items"]
            if item["reconciliation_status"] == "RESOLVED_BY_SOURCE_FACT"
        ]
        self.assertEqual(resolved, [])
        self.assertTrue(
            all(
                item["reconciliation_status"] != "RESOLVED_BY_SOURCE_FACT"
                for item in automatic["items"]
                if "TBD" in item.get("evidence_excerpt", "")
                or "[ASUMSI]" in item.get("evidence_excerpt", "")
            )
        )


if __name__ == "__main__":
    unittest.main()
