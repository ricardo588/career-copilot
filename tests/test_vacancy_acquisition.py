from __future__ import annotations

import importlib.util
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from datetime import date
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "skills/career-copilot/scripts/vacancy_acquisition.py"
SPEC = importlib.util.spec_from_file_location("vacancy_acquisition_under_test", MODULE_PATH)
assert SPEC and SPEC.loader
ACQUISITION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ACQUISITION)


class VacancyAcquisitionTests(unittest.TestCase):
    def test_greenhouse_public_board_normalizes_explicit_read_only_feed(self):
        requested = []

        def fetch_json(url: str) -> object:
            requested.append(url)
            return {"jobs": [{
                "id": 42,
                "title": "Program Director",
                "absolute_url": "https://boards.greenhouse.io/example/jobs/42?gh_src=widget",
                "location": {"name": "Mexico City"},
                "updated_at": "2026-09-07T12:00:00Z",
            }]}

        report = ACQUISITION.acquire_public_feed(
            "greenhouse_public_board", "example", "Synthetic Holdings", date(2026, 9, 8), fetch_json,
        )

        self.assertEqual(requested, ["https://boards-api.greenhouse.io/v1/boards/example/jobs"])
        self.assertEqual(report["mode"], "explicit_public_read_only_acquisition")
        self.assertEqual(report["external_actions"], 1)
        self.assertEqual(report["external_action_type"], "read_only_get")
        self.assertEqual(report["vacancies"], [{
            "source": "greenhouse_public_board",
            "company": "Synthetic Holdings",
            "role": "Program Director",
            "location": "Mexico City",
            "canonical_url": "https://boards.greenhouse.io/example/jobs/42?gh_src=widget",
            "source_updated_on": "2026-09-07",
            "work_mode": "",
            "employment_type": "",
            "external_job_id": "42",
        }])

    def test_lever_public_postings_normalizes_epoch_timestamp_without_application_url(self):
        def fetch_json(url: str) -> object:
            self.assertEqual(url, "https://api.lever.co/v0/postings/example?mode=json")
            return [{
                "id": "posting-1",
                "text": "Engineering Director",
                "hostedUrl": "https://jobs.lever.co/example/posting-1",
                "applyUrl": "https://jobs.lever.co/example/posting-1/apply",
                "categories": {"location": "Remote", "commitment": "Full-time"},
                "createdAt": 1788739200000,
                "workplaceType": "remote",
            }]

        report = ACQUISITION.acquire_public_feed(
            "lever_public_postings", "example", "Synthetic Holdings", date(2026, 9, 8), fetch_json,
        )

        vacancy = report["vacancies"][0]
        self.assertEqual(vacancy["canonical_url"], "https://jobs.lever.co/example/posting-1")
        self.assertEqual(vacancy["date_posted"], "2026-09-07")
        self.assertEqual(vacancy["work_mode"], "remote")
        self.assertEqual(vacancy["employment_type"], "Full-time")
        self.assertNotIn("applyUrl", vacancy)

    def test_invalid_source_identifier_blocks_before_external_read(self):
        def must_not_fetch(_: str) -> object:
            raise AssertionError("fetch must not run")

        with self.assertRaisesRegex(ValueError, "source identifier"):
            ACQUISITION.acquire_public_feed(
                "greenhouse_public_board", "example/../other", "Synthetic Holdings", date(2026, 9, 8), must_not_fetch,
            )

    def test_normalizers_reject_vacancy_urls_outside_the_provider_contract(self):
        greenhouse = {"jobs": [{
            "id": 42,
            "title": "Program Director",
            "absolute_url": "javascript:alert(1)",
            "location": {"name": "Mexico City"},
            "updated_at": "2026-09-07T12:00:00Z",
        }]}
        lever = [{
            "id": "posting-1",
            "text": "Engineering Director",
            "hostedUrl": "https://unexpected.example.invalid/example/posting-1",
            "categories": {"location": "Remote"},
            "createdAt": 1788739200000,
        }]

        with self.assertRaisesRegex(ValueError, "Greenhouse job 0.absolute_url"):
            ACQUISITION.normalize_greenhouse_jobs(greenhouse, "Synthetic Holdings")
        with self.assertRaisesRegex(ValueError, "Lever posting 0.hostedUrl"):
            ACQUISITION.normalize_lever_postings(lever, "Synthetic Holdings")

    def test_invalid_private_output_blocks_before_external_read(self):
        fetches = []

        def fetch_json(url: str) -> object:
            fetches.append(url)
            return {"jobs": []}

        with tempfile.TemporaryDirectory() as temporary:
            git_dir = Path(temporary) / ".git"
            git_dir.mkdir()
            with patch.object(ACQUISITION, "_fetch_json", fetch_json), patch.object(
                sys, "argv", [
                    "vacancy_acquisition.py", "--adapter", "greenhouse_public_board",
                    "--source-identifier", "example", "--company", "Synthetic Holdings",
                    "--as-of", "2026-09-08", "--output", str(git_dir / "report.json"),
                ],
            ), redirect_stderr(io.StringIO()):
                self.assertEqual(ACQUISITION.main(), 2)

        self.assertEqual(fetches, [])

    def test_http_client_disables_redirects_before_reading_response(self):
        handler = ACQUISITION._NoRedirect()
        self.assertIsNone(handler.redirect_request(None, None, 302, "Found", {}, "https://unexpected.example.invalid"))

    def test_catalog_audit_marks_dated_evidence_for_review_without_network(self):
        catalog = {
            "example": {
                "evidence_url": "https://example.invalid/evidence",
                "evidence_scope": "Declared coverage only; not a ranking.",
                "evidence_checked_on": "2026-08-01",
            }
        }
        audit = ACQUISITION.audit_catalog(catalog, date(2026, 9, 8), max_age_days=30)

        self.assertEqual(audit["external_actions"], 0)
        self.assertEqual(audit["review_required"], ["example"])
        self.assertEqual(audit["valid_entries"], 1)

    def test_external_action_plan_is_a_draft_bound_to_target_and_payload(self):
        plan = ACQUISITION.propose_external_action(
            "application", "https://jobs.example.invalid/roles/123", {"vacancy_ref": "private-shortlist#1"},
        )

        self.assertEqual(plan["status"], "draft_only")
        self.assertEqual(plan["external_actions"], 0)
        self.assertRegex(plan["approval_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(plan["action"], "application")
        self.assertEqual(plan["target"], "https://jobs.example.invalid/roles/123")


if __name__ == "__main__":
    unittest.main()
