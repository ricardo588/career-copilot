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
            self.assertTrue((output / "tracker.csv").is_file())
            self.assertTrue((output / "interview-brief.md").is_file())
            self.assertTrue((output / "demo-result.json").is_file())
            brief = (output / "interview-brief.md").read_text(encoding="utf-8")
            self.assertIn("## Human Path", brief)
            self.assertIn("## Interviewer intelligence", brief)


if __name__ == "__main__":
    unittest.main()
