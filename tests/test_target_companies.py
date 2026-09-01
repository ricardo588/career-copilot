from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "skills/career-copilot/scripts/target_companies.py"
SPEC = importlib.util.spec_from_file_location("target_companies_under_test", MODULE_PATH)
assert SPEC and SPEC.loader
TARGETS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TARGETS)


class TargetCompanyTests(unittest.TestCase):
    def setUp(self):
        self.as_of = date(2026, 9, 1)
        self.record = {
            "company": "Synthetic Holdings",
            "role_families": ["Program Delivery", "PMO"],
            "candidate_preference": {
                "statement": "I want to explore enterprise transformation roles here.",
                "declared_at": "2026-08-30",
            },
            "current_signals": [{
                "summary": "Canonical careers page lists transformation leadership roles.",
                "source_url": "https://careers.example.invalid/synthetic",
                "checked_at": "2026-08-31",
            }],
            "human_paths": [{
                "summary": "No trusted contact was found in the candidate-owned network.",
                "source_url": "https://network.example.invalid/search",
                "checked_at": "2026-08-20",
                "status": "none_found",
            }],
            "relevant_units": ["Enterprise Technology"],
            "risks": ["Current hiring need is unconfirmed."],
            "questions": ["Which business unit owns the transformation portfolio?"],
            "next_research_action": "Verify current role families from the official careers site.",
        }

    def test_add_keeps_preference_separate_from_current_signals_and_contact_authorization(self):
        registry, result = TARGETS.upsert_registry({"schema_version": 1, "companies": []}, self.record, self.as_of)
        self.assertEqual(result["action"], "added")
        company = registry["companies"][0]
        self.assertEqual(company["candidate_preference"]["kind"], "candidate_preference")
        self.assertEqual(company["candidate_preference"]["statement"], self.record["candidate_preference"]["statement"])
        self.assertEqual(company["contact_authorization"], "not_granted_by_research")
        self.assertEqual(company["company_last_verified"], "2026-08-31")
        self.assertEqual(company["human_path_last_verified"], "2026-08-20")
        self.assertEqual(company["status"], "active")
        self.assertEqual(company["client_identity"]["status"], "confirmed")

    def test_refresh_appends_provenance_and_preserves_prior_signal(self):
        first, _ = TARGETS.upsert_registry({"schema_version": 1, "companies": []}, self.record, self.as_of)
        refreshed = dict(self.record)
        refreshed["current_signals"] = [{
            "summary": "Official press release announces a new transformation unit.",
            "source_url": "https://news.example.invalid/synthetic-unit",
            "checked_at": "2026-09-01",
        }]
        refreshed["human_paths"] = []
        second, result = TARGETS.upsert_registry(first, refreshed, self.as_of)
        company = second["companies"][0]
        self.assertEqual(result["action"], "refreshed")
        self.assertEqual(len(company["current_signals"]), 2)
        self.assertEqual(company["current_signals"][0]["source_url"], self.record["current_signals"][0]["source_url"])
        self.assertEqual(company["company_last_verified"], "2026-09-01")
        self.assertEqual(company["human_path_last_verified"], "2026-08-20")
        self.assertEqual(len(company["history"]), 2)

    def test_unknown_and_confidential_client_identity_are_explicit(self):
        unknown = dict(self.record)
        unknown["company"] = ""
        unknown["client_identity"] = {"status": "unknown"}
        registry, _ = TARGETS.upsert_registry({"schema_version": 1, "companies": []}, unknown, self.as_of)
        self.assertEqual(registry["companies"][0]["company"], "Unknown client")
        self.assertEqual(registry["companies"][0]["client_identity"], {"status": "unknown"})

        confidential = dict(self.record)
        confidential["company"] = ""
        confidential["client_identity"] = {"status": "confidential", "reason": "Recruiter withheld client identity."}
        registry, _ = TARGETS.upsert_registry(registry, confidential, self.as_of)
        self.assertEqual(registry["companies"][1]["client_identity"]["status"], "confidential")

    def test_rejects_unsourced_signal_and_company_assertions_disguised_as_preference(self):
        unsourced = dict(self.record)
        unsourced["current_signals"] = [{"summary": "They are definitely hiring.", "checked_at": "2026-08-31"}]
        with self.assertRaisesRegex(ValueError, "source_url"):
            TARGETS.upsert_registry({"schema_version": 1, "companies": []}, unsourced, self.as_of)
        bad_preference = dict(self.record)
        bad_preference["candidate_preference"] = {"statement": "This is a great company.", "declared_at": "2026-08-30"}
        with self.assertRaisesRegex(ValueError, "preference"):
            TARGETS.upsert_registry({"schema_version": 1, "companies": []}, bad_preference, self.as_of)

    def test_review_uses_independent_company_and_human_path_clocks_without_mutation(self):
        registry, _ = TARGETS.upsert_registry({"schema_version": 1, "companies": []}, self.record, self.as_of)
        original = json.dumps(registry, sort_keys=True)
        review = TARGETS.review_registry(registry, date(2026, 9, 10), company_stale_after_days=14, human_path_stale_after_days=7)
        self.assertEqual(review["active_count"], 1)
        self.assertEqual(review["company_evidence_stale"], [])
        self.assertEqual(review["human_path_evidence_stale"], [registry["companies"][0]["id"]])
        self.assertEqual(json.dumps(registry, sort_keys=True), original)

    def test_archive_preserves_artifact_and_blocks_unrecognized_identity(self):
        registry, result = TARGETS.upsert_registry({"schema_version": 1, "companies": []}, self.record, self.as_of)
        company_id = result["id"]
        archived, archive_result = TARGETS.archive_company(registry, company_id, date(2026, 9, 2), "Candidate reprioritized focus.")
        company = archived["companies"][0]
        self.assertEqual(archive_result["action"], "archived")
        self.assertEqual(company["status"], "archived")
        self.assertEqual(company["archived_at"], "2026-09-02")
        self.assertEqual(company["current_signals"][0]["source_url"], self.record["current_signals"][0]["source_url"])
        with self.assertRaisesRegex(ValueError, "identity"):
            TARGETS.archive_company(archived, "company-not-present", self.as_of, "Nope")

    def test_private_registry_rejects_git_and_symlinks_and_uses_private_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = {"schema_version": 1, "companies": []}
            output = root / "private" / "targets.json"
            TARGETS.write_registry(output, registry)
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            self.assertEqual(output.parent.stat().st_mode & 0o777, 0o700)
            link = root / "linked.json"
            link.symlink_to(output)
            with self.assertRaisesRegex(ValueError, "symlink"):
                TARGETS.write_registry(link, registry)


if __name__ == "__main__":
    unittest.main()
