import csv
import importlib.util
import json
import stat
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "career-copilot" / "scripts" / "pipeline.py"
DEMO = ROOT / "skills" / "career-copilot" / "scripts" / "run_synthetic_demo.py"
FIXTURES = ROOT / "skills" / "career-copilot" / "examples" / "synthetic"
SPEC = importlib.util.spec_from_file_location("career_pipeline", SCRIPT)
PIPELINE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(PIPELINE)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.profile = PIPELINE.load_document(FIXTURES / "profile.json")
        self.rules = PIPELINE.load_document(FIXTURES / "rules.json")
        self.vacancy = PIPELINE.load_document(FIXTURES / "vacancy.json")
        self.as_of = date(2026, 8, 26)

    def test_high_fit_uses_only_meaningful_requirement_overlap(self):
        result = PIPELINE.evaluate(self.profile, self.rules, self.vacancy, self.as_of)
        self.assertEqual(result["recommendation"], "High")
        self.assertEqual(len(result["matched_requirements"]), 3)
        self.assertNotIn("Vendor commercial management", result["matched_requirements"])

    def test_tracker_deduplicates_and_verifies(self):
        result = PIPELINE.evaluate(self.profile, self.rules, self.vacancy, self.as_of)
        human_path = {
            "retrieved_at": "2026-08-25",
            "contacts": [{
                "name": "Synthetic Contact",
                "path_type": "trusted_contact",
                "current_company": "Acme Cloud Services",
                "current_role": "Transformation Leader",
                "source_url": "https://example.test/people/synthetic-contact",
                "confidence": "confirmed",
            }],
            "recruiter": None,
            "hiring_manager": None,
        }
        with tempfile.TemporaryDirectory() as tmp:
            tracker = Path(tmp) / "tracker.csv"
            interviewer_research = {
                "interviewers": [
                    {"name": "Verified Interviewer", "source_url": "https://example.test/interviewer"},
                    {"name": "Unsourced Interviewer"},
                ]
            }
            first = PIPELINE.track(
                tracker, self.vacancy, result, self.as_of, human_path, interviewer_research,
            )
            second = PIPELINE.track(
                tracker, self.vacancy, result, self.as_of, human_path, interviewer_research,
            )
            self.assertEqual(first["action"], "added")
            self.assertEqual(second["action"], "updated_existing")
            with tracker.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["canonical_url"], "https://jobs.example.test/acme/TPD-001")
            self.assertEqual(rows[0]["human_path_status"], "confirmed")
            self.assertEqual(rows[0]["contact"], "Synthetic Contact")
            self.assertEqual(rows[0]["interviewer"], "Verified Interviewer")
            self.assertEqual(rows[0]["fit_recommendation"], "High")
            self.assertEqual(rows[0]["vacancy_last_verified"], "2026-08-26")
            self.assertEqual(rows[0]["human_path_last_verified"], "2026-08-25")

    def test_duplicate_refreshes_fit_fields_without_regressing_process_status(self):
        initial = PIPELINE.evaluate(self.profile, self.rules, self.vacancy, self.as_of)
        with tempfile.TemporaryDirectory() as tmp:
            tracker = Path(tmp) / "tracker.csv"
            PIPELINE.track(tracker, self.vacancy, initial, self.as_of)
            rows = PIPELINE.read_tracker(tracker)
            rows[0]["status"] = "interview"
            rows[0]["next_action"] = "obsolete action"
            PIPELINE.atomic_write_tracker(tracker, rows)

            stale = dict(self.vacancy)
            stale["date_posted"] = "2026-07-01"
            reevaluation = PIPELINE.evaluate(self.profile, self.rules, stale, self.as_of)
            update = PIPELINE.track(tracker, stale, reevaluation, self.as_of)
            refreshed = PIPELINE.read_tracker(tracker)[0]

            self.assertEqual(update["action"], "updated_existing")
            self.assertEqual(refreshed["fit_recommendation"], "Discard")
            self.assertEqual(refreshed["priority"], "discard")
            self.assertEqual(refreshed["next_action"], reevaluation["next_action"])
            self.assertEqual(refreshed["date_posted"], "2026-07-01")
            self.assertEqual(refreshed["status"], "interview")
            self.assertEqual(refreshed["vacancy_last_verified"], "2026-08-26")
            self.assertEqual(refreshed["human_path_last_verified"], "")
            self.assertEqual(refreshed["human_path_status"], "")

    def test_vacancy_only_refresh_preserves_human_path_and_interviewer(self):
        initial = PIPELINE.evaluate(self.profile, self.rules, self.vacancy, self.as_of)
        human_path = {
            "retrieved_at": "2026-08-25",
            "contacts": [{
                "name": "Current Contact",
                "path_type": "trusted_contact",
                "current_company": "Acme Cloud Services",
                "current_role": "Director",
                "source_url": "https://example.test/current-contact",
                "confidence": "confirmed",
            }],
            "recruiter": {
                "name": "Current Recruiter",
                "source_url": "https://example.test/current-recruiter",
                "confidence": "confirmed",
            },
            "hiring_manager": {
                "name": "Current Manager",
                "current_company": "Acme Cloud Services",
                "source_url": "https://example.test/current-manager",
                "confidence": "confirmed",
            },
        }
        interviewer = {
            "interviewers": [{
                "name": "Current Interviewer",
                "source_url": "https://example.test/current-interviewer",
            }]
        }
        with tempfile.TemporaryDirectory() as tmp:
            tracker = Path(tmp) / "tracker.csv"
            PIPELINE.track(tracker, self.vacancy, initial, self.as_of, human_path, interviewer)

            later = date(2026, 8, 28)
            refreshed_vacancy = dict(self.vacancy)
            refreshed_vacancy["location"] = "Mexico City, Mexico"
            reevaluation = PIPELINE.evaluate(self.profile, self.rules, refreshed_vacancy, later)
            PIPELINE.track(tracker, refreshed_vacancy, reevaluation, later)
            row = PIPELINE.read_tracker(tracker)[0]

            self.assertEqual(row["contact"], "Current Contact")
            self.assertEqual(row["recruiter"], "Current Recruiter")
            self.assertEqual(row["hiring_manager"], "Current Manager")
            self.assertEqual(row["interviewer"], "Current Interviewer")
            self.assertEqual(row["human_path_status"], "confirmed")
            self.assertEqual(row["human_path_last_verified"], "2026-08-25")
            self.assertEqual(row["vacancy_last_verified"], "2026-08-28")

    def test_explicit_none_found_human_path_refresh_uses_artifact_date(self):
        initial = PIPELINE.evaluate(self.profile, self.rules, self.vacancy, self.as_of)
        initial_human_path = {
            "retrieved_at": "2026-08-25",
            "contacts": [{
                "name": "Former Contact",
                "path_type": "trusted_contact",
                "current_company": "Acme Cloud Services",
                "current_role": "Director",
                "source_url": "https://example.test/former-contact",
                "confidence": "confirmed",
            }],
        }
        interviewer = {
            "interviewers": [{
                "name": "Preserved Interviewer",
                "source_url": "https://example.test/preserved-interviewer",
            }]
        }
        with tempfile.TemporaryDirectory() as tmp:
            tracker = Path(tmp) / "tracker.csv"
            PIPELINE.track(tracker, self.vacancy, initial, self.as_of, initial_human_path, interviewer)

            none_found = {"retrieved_at": "2026-08-27", "contacts": []}
            PIPELINE.track(tracker, self.vacancy, initial, date(2026, 8, 28), none_found)
            row = PIPELINE.read_tracker(tracker)[0]

            self.assertEqual(row["contact"], "")
            self.assertEqual(row["recruiter"], "")
            self.assertEqual(row["hiring_manager"], "")
            self.assertEqual(row["human_path_status"], "none_found")
            self.assertEqual(row["human_path_last_verified"], "2026-08-27")
            self.assertEqual(row["interviewer"], "Preserved Interviewer")

    def test_explicit_human_path_requires_valid_retrieved_at(self):
        result = PIPELINE.evaluate(self.profile, self.rules, self.vacancy, self.as_of)
        with tempfile.TemporaryDirectory() as tmp:
            tracker = Path(tmp) / "tracker.csv"
            with self.assertRaisesRegex(ValueError, "retrieved_at"):
                PIPELINE.track(tracker, self.vacancy, result, self.as_of, {"contacts": []})
            with self.assertRaisesRegex(ValueError, "future"):
                PIPELINE.track(
                    tracker, self.vacancy, result, self.as_of,
                    {"retrieved_at": "2026-08-27", "contacts": []},
                )

    def test_invalid_human_path_shape_cannot_erase_existing_evidence(self):
        result = PIPELINE.evaluate(self.profile, self.rules, self.vacancy, self.as_of)
        initial_human_path = {
            "retrieved_at": "2026-08-25",
            "contacts": [{
                "name": "Preserved Contact",
                "path_type": "trusted_contact",
                "current_company": "Acme Cloud Services",
                "current_role": "Director",
                "source_url": "https://example.test/preserved-contact",
                "confidence": "confirmed",
            }],
        }
        with tempfile.TemporaryDirectory() as tmp:
            tracker = Path(tmp) / "tracker.csv"
            PIPELINE.track(tracker, self.vacancy, result, self.as_of, initial_human_path)
            before = tracker.read_text(encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "contacts"):
                PIPELINE.track(
                    tracker,
                    self.vacancy,
                    result,
                    date(2026, 8, 28),
                    {"retrieved_at": "2026-08-27", "contacts": "malformed"},
                )

            self.assertEqual(tracker.read_text(encoding="utf-8"), before)
            self.assertEqual(PIPELINE.read_tracker(tracker)[0]["contact"], "Preserved Contact")

    def test_human_path_summary_rejects_malformed_shape(self):
        with self.assertRaisesRegex(ValueError, "contacts"):
            PIPELINE.summarize_human_path(self.vacancy, {"contacts": "malformed"})

    def test_legacy_tracker_migration_splits_clock_conservatively(self):
        legacy_fields = [
            "id", "company", "role", "location", "source", "canonical_url", "external_job_id",
            "date_posted", "date_discovered", "status", "fit_recommendation", "priority", "next_action",
            "next_action_date", "contact", "human_path_status", "recruiter", "hiring_manager",
            "interviewer", "notes", "last_verified",
        ]
        legacy_rows = [{
            "id": "legacy-1",
            "company": "Legacy Co",
            "role": "Legacy Role",
            "status": "interview",
            "next_action": "prepare panel",
            "contact": "Known Person",
            "human_path_status": "confirmed",
            "last_verified": "2026-08-20",
        }, {
            "id": "legacy-2",
            "company": "Second Co",
            "role": "Second Role",
            "status": "applied",
            "next_action": "wait for response",
            "last_verified": "2026-08-21",
        }]
        with tempfile.TemporaryDirectory() as tmp:
            tracker = Path(tmp) / "tracker.csv"
            with tracker.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=legacy_fields)
                writer.writeheader()
                writer.writerows(legacy_rows)

            self.assertTrue(PIPELINE.migrate_tracker_schema(tracker))
            rows = PIPELINE.read_tracker(tracker)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["id"], "legacy-1")
            self.assertEqual(rows[0]["status"], "interview")
            self.assertEqual(rows[0]["next_action"], "prepare panel")
            self.assertEqual(rows[0]["vacancy_last_verified"], "2026-08-20")
            self.assertEqual(rows[0]["human_path_last_verified"], "")
            self.assertEqual(rows[0]["contact"], "Known Person")
            self.assertEqual(rows[1]["id"], "legacy-2")
            self.assertNotIn("last_verified", rows[0])
            with tracker.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                persisted = list(reader)
                self.assertEqual(persisted[0]["id"], "legacy-1")
                self.assertNotIn("last_verified", reader.fieldnames or [])

    def test_track_automatically_migrates_legacy_tracker_without_erasing_human_evidence(self):
        legacy_fields = [
            "id", "company", "role", "location", "source", "canonical_url", "external_job_id",
            "date_posted", "date_discovered", "status", "fit_recommendation", "priority", "next_action",
            "next_action_date", "contact", "human_path_status", "recruiter", "hiring_manager",
            "interviewer", "notes", "last_verified",
        ]
        legacy_row = {
            "id": "legacy-stable-id",
            "company": self.vacancy["company"],
            "role": self.vacancy["title"],
            "canonical_url": PIPELINE.canonicalize_url(self.vacancy["canonical_url"]),
            "status": "interview",
            "next_action": "prepare panel",
            "contact": "Known Contact",
            "human_path_status": "confirmed",
            "recruiter": "Known Recruiter",
            "hiring_manager": "Known Manager",
            "interviewer": "Known Interviewer",
            "last_verified": "2026-08-20",
        }
        evaluation = PIPELINE.evaluate(self.profile, self.rules, self.vacancy, self.as_of)
        with tempfile.TemporaryDirectory() as tmp:
            tracker = Path(tmp) / "tracker.csv"
            with tracker.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=legacy_fields)
                writer.writeheader()
                writer.writerow(legacy_row)

            result = PIPELINE.track(tracker, self.vacancy, evaluation, self.as_of)
            row = PIPELINE.read_tracker(tracker)[0]

            self.assertEqual(result["action"], "updated_existing")
            self.assertEqual(result["id"], "legacy-stable-id")
            self.assertEqual(len(PIPELINE.read_tracker(tracker)), 1)
            self.assertEqual(row["status"], "interview")
            self.assertEqual(row["contact"], "Known Contact")
            self.assertEqual(row["human_path_status"], "confirmed")
            self.assertEqual(row["recruiter"], "Known Recruiter")
            self.assertEqual(row["hiring_manager"], "Known Manager")
            self.assertEqual(row["interviewer"], "Known Interviewer")
            self.assertEqual(row["vacancy_last_verified"], "2026-08-26")
            self.assertEqual(row["human_path_last_verified"], "")

    def test_reordered_current_schema_is_normalized_without_losing_rows(self):
        reordered = list(reversed(PIPELINE.TRACKER_FIELDS))
        with tempfile.TemporaryDirectory() as tmp:
            tracker = Path(tmp) / "tracker.csv"
            with tracker.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=reordered)
                writer.writeheader()
                writer.writerow({"id": "current-1", "company": "Current Co", "status": "applied"})

            self.assertTrue(PIPELINE.migrate_tracker_schema(tracker))
            with tracker.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                rows = list(reader)
            self.assertEqual(reader.fieldnames, PIPELINE.TRACKER_FIELDS)
            self.assertEqual(rows[0]["id"], "current-1")
            self.assertEqual(rows[0]["status"], "applied")

    def test_schema_with_extra_columns_is_rejected_without_data_loss(self):
        fields = PIPELINE.TRACKER_FIELDS + ["custom_private_note"]
        with tempfile.TemporaryDirectory() as tmp:
            tracker = Path(tmp) / "tracker.csv"
            with tracker.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerow({"id": "custom-1", "custom_private_note": "preserve me"})
            before = tracker.read_text(encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "unsupported extra fields"):
                PIPELINE.migrate_tracker_schema(tracker)
            self.assertEqual(tracker.read_text(encoding="utf-8"), before)

    def test_human_path_requires_sources_and_separates_unknowns(self):
        research = {
            "contacts": [
                {
                    "name": "Confirmed Person",
                    "path_type": "trusted_contact",
                    "current_company": "Acme Cloud Services",
                    "current_role": "Director",
                    "source_url": "https://example.test/confirmed",
                    "confidence": "confirmed",
                },
                {
                    "name": "Unsourced Person",
                    "path_type": "possible_contact",
                    "current_company": "Acme Cloud Services",
                    "current_role": "Manager",
                    "confidence": "possible",
                },
            ],
            "recruiter": None,
            "hiring_manager": None,
        }
        result = PIPELINE.summarize_human_path(self.vacancy, research)
        self.assertEqual(result["status"], "confirmed")
        self.assertEqual(len(result["confirmed_paths"]), 1)
        self.assertEqual(len(result["unverified_paths"]), 1)
        self.assertIn("recruiter/poster", result["unknowns"])

    def test_interviewer_research_is_rendered_as_facts_and_hypotheses(self):
        evaluation = PIPELINE.evaluate(self.profile, self.rules, self.vacancy, self.as_of)
        interviewer = {
            "interviewers": [{
                "name": "Alex Example",
                "current_role": "VP Transformation",
                "source_url": "https://example.test/alex",
                "confirmed_facts": ["Leads enterprise transformation"],
                "hypotheses": ["May focus on value realization"],
            }]
        }
        brief = PIPELINE.interview_brief(self.profile, self.vacancy, evaluation, interviewer_research=interviewer)
        self.assertIn("## Interviewer intelligence", brief)
        self.assertIn("Confirmed fact: Leads enterprise transformation", brief)
        self.assertIn("Interview hypothesis: May focus on value realization", brief)
        self.assertIn("https://example.test/alex", brief)

    def test_stale_or_ineligible_vacancy_is_discarded(self):
        stale = dict(self.vacancy)
        stale["date_posted"] = "2026-07-01"
        self.assertEqual(PIPELINE.evaluate(self.profile, self.rules, stale, self.as_of)["recommendation"], "Discard")
        elsewhere = dict(self.vacancy)
        elsewhere["location"] = "Example City"
        self.assertEqual(PIPELINE.evaluate(self.profile, self.rules, elsewhere, self.as_of)["recommendation"], "Discard")

    def test_cli_without_human_path_reports_not_supplied(self):
        fixtures = FIXTURES
        with tempfile.TemporaryDirectory() as tmp:
            tracker = Path(tmp) / "tracker.csv"
            completed = subprocess.run(
                [
                    sys.executable, str(SCRIPT),
                    "--profile", str(fixtures / "profile.json"),
                    "--rules", str(fixtures / "rules.json"),
                    "--vacancy", str(fixtures / "vacancy.json"),
                    "--tracker", str(tracker),
                    "--as-of", "2026-08-26",
                ],
                check=True, capture_output=True, text=True,
            )
            result = json.loads(completed.stdout)
            row = PIPELINE.read_tracker(tracker)[0]
            self.assertEqual(result["human_path"]["status"], "not_supplied")
            self.assertEqual(row["human_path_status"], "")
            self.assertEqual(row["human_path_last_verified"], "")
            self.assertEqual(row["vacancy_last_verified"], "2026-08-26")

    def test_cli_rejects_unvalidated_human_path_without_tracker(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp) / "human-path.json"
            artifact.write_text(json.dumps({"contacts": []}), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable, str(SCRIPT),
                    "--profile", str(FIXTURES / "profile.json"),
                    "--rules", str(FIXTURES / "rules.json"),
                    "--vacancy", str(FIXTURES / "vacancy.json"),
                    "--human-path", str(artifact),
                    "--as-of", "2026-08-26",
                ],
                check=False, capture_output=True, text=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("retrieved_at", completed.stderr)

    def test_full_synthetic_demo_generates_all_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "demo"
            completed = subprocess.run(
                [sys.executable, str(DEMO), "--output-dir", str(output)],
                check=True, capture_output=True, text=True,
            )
            result = json.loads(completed.stdout)
            self.assertEqual(result["evaluation"]["recommendation"], "High")
            self.assertEqual(result["external_actions"], 0)
            self.assertEqual(result["human_path"]["status"], "confirmed")
            self.assertEqual(result["tracker_rows"], 1)
            tracker_row = PIPELINE.read_tracker(output / "tracker.csv")[0]
            self.assertEqual(tracker_row["vacancy_last_verified"], "2026-08-26")
            self.assertEqual(tracker_row["human_path_last_verified"], "2026-08-26")
            self.assertTrue((output / "tracker.csv").is_file())
            self.assertTrue((output / "interview-brief.md").is_file())
            self.assertTrue((output / "demo-result.json").is_file())
            brief = (output / "interview-brief.md").read_text(encoding="utf-8")
            self.assertIn("## Human Path", brief)
            self.assertIn("## Interviewer intelligence", brief)


if __name__ == "__main__":
    unittest.main()
