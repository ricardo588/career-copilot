from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "skills/career-copilot/scripts/vacancy_discovery.py"
SPEC = importlib.util.spec_from_file_location("vacancy_discovery_under_test", MODULE_PATH)
assert SPEC and SPEC.loader
DISCOVERY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DISCOVERY)


class VacancyDiscoveryTests(unittest.TestCase):
    profile = {
        "profile": {
            "target_roles": ["Program Director"],
            "target_seniority": ["Director"],
            "target_industries": ["Cloud services"],
        },
        "constraints": {
            "countries": ["Mexico"],
            "locations": [],
            "work_modes": ["Remote"],
            "employment_types": ["Full-time"],
        },
    }
    rules = {
        "search": {
            "selected_job_portals": ["linkedin", "official_company_sites"],
            "target_companies": ["Synthetic Holdings"],
            "freshness_days": 14,
        }
    }

    def test_private_import_shortlists_selected_fresh_sources_without_tracker_mutation(self):
        payload = {"vacancies": [
            {
                "source": "linkedin",
                "company": "Synthetic Holdings",
                "role": "Program Director",
                "location": "Mexico City, Mexico",
                "work_mode": "Remote",
                "employment_type": "Full-time",
                "canonical_url": "https://jobs.example.invalid/roles/123",
                "date_posted": "2026-09-01",
            },
            {
                "source": "occ_mundial",
                "company": "Other Co",
                "role": "Program Director",
                "location": "Mexico City, Mexico",
                "canonical_url": "https://jobs.example.invalid/roles/456",
                "date_posted": "2026-09-01",
            },
            {
                "source": "linkedin",
                "company": "Old Co",
                "role": "Program Director",
                "location": "Mexico City, Mexico",
                "canonical_url": "https://jobs.example.invalid/roles/789",
                "date_posted": "2026-08-01",
            },
        ]}
        report = DISCOVERY.discover_vacancies(self.profile, self.rules, payload, date(2026, 9, 7))
        self.assertEqual(report["mode"], "private_import_read_only")
        self.assertEqual(report["external_actions"], 0)
        self.assertEqual([item["canonical_url"] for item in report["shortlist"]], ["https://jobs.example.invalid/roles/123"])
        self.assertTrue(report["shortlist"][0]["target_company"])
        self.assertEqual(report["candidate_filters"], {
            "target_roles": ["Program Director"],
            "target_seniority": ["Director"],
            "target_industries": ["Cloud services"],
            "countries": ["Mexico"],
            "locations": [],
            "work_modes": ["Remote"],
            "employment_types": ["Full-time"],
        })
        self.assertEqual(report["discarded"][0]["reason"], "source_not_selected")
        self.assertEqual(report["discarded"][1]["reason"], "stale_posting")

    def test_import_deduplicates_equivalent_canonical_urls(self):
        payload = {"vacancies": [
            {
                "source": "linkedin", "company": "Synthetic Holdings", "role": "Program Director",
                "location": "Mexico", "canonical_url": "HTTPS://Jobs.Example.Invalid/roles/123/?utm_source=portal#details",
                "date_posted": "2026-09-01",
            },
            {
                "source": "linkedin", "company": "Synthetic Holdings", "role": "Program Director",
                "location": "Mexico", "canonical_url": "https://jobs.example.invalid/roles/123",
                "date_posted": "2026-09-01",
            },
        ]}
        report = DISCOVERY.discover_vacancies(self.profile, self.rules, payload, date(2026, 9, 7))
        self.assertEqual([item["canonical_url"] for item in report["shortlist"]], ["https://jobs.example.invalid/roles/123"])
        self.assertEqual(report["discarded"], [{
            "canonical_url": "https://jobs.example.invalid/roles/123",
            "reason": "duplicate_canonical_url",
        }])

    def test_csv_import_normalizes_linkedin_export_headers_and_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            export = Path(tmp) / "linkedin-export.csv"
            export.write_text(
                "Company Name,Job Title,Job Location,Job URL,Date Posted,Work Mode,Employment Type,Source\n"
                "Synthetic Holdings,Program Director,Mexico City,https://jobs.example.invalid/roles/123?utm_source=linkedin,2026-09-01,Remote,Full-time,LinkedIn Jobs\n",
                encoding="utf-8",
            )
            payload = DISCOVERY.load_vacancy_export(export)
        self.assertEqual(payload, {"vacancies": [{
            "source": "linkedin",
            "company": "Synthetic Holdings",
            "role": "Program Director",
            "location": "Mexico City",
            "canonical_url": "https://jobs.example.invalid/roles/123?utm_source=linkedin",
            "date_posted": "2026-09-01",
            "work_mode": "Remote",
            "employment_type": "Full-time",
            "external_job_id": "",
        }]})

    def test_cli_rejects_private_inputs_inside_a_git_repository_without_writing_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repository = root / "repository"
            (repository / ".git").mkdir(parents=True)
            profile = repository / "profile.json"
            rules = repository / "rules.json"
            export = repository / "export.json"
            profile.write_text(json.dumps(self.profile), encoding="utf-8")
            rules.write_text(json.dumps(self.rules), encoding="utf-8")
            export.write_text(json.dumps({"vacancies": []}), encoding="utf-8")
            output = root / "private" / "shortlist.json"
            completed = subprocess.run([
                sys.executable, str(MODULE_PATH), "--profile", str(profile), "--rules", str(rules),
                "--import-file", str(export), "--output", str(output), "--as-of", "2026-09-07",
            ], capture_output=True, text=True)
            self.assertEqual(completed.returncode, 2)
            self.assertIn("must be outside a Git repository", completed.stderr)
            self.assertFalse(output.exists())

    def test_import_rejects_invalid_or_unselected_data_without_writing_a_report(self):
        invalid = {"vacancies": [{
            "source": "linkedin", "company": "Synthetic Holdings", "role": "Program Director",
            "location": "Mexico", "canonical_url": "not-a-url", "date_posted": "2026-09-01",
        }]}
        with self.assertRaisesRegex(ValueError, "canonical_url"):
            DISCOVERY.discover_vacancies(self.profile, self.rules, invalid, date(2026, 9, 7))
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "private" / "shortlist.json"
            report = DISCOVERY.discover_vacancies(self.profile, self.rules, {"vacancies": []}, date(2026, 9, 7))
            DISCOVERY.write_private_report(output, report)
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            self.assertEqual(output.parent.stat().st_mode & 0o777, 0o700)


if __name__ == "__main__":
    unittest.main()
