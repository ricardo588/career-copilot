import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "career-copilot" / "scripts" / "interview_intake.py"


def load_module():
    spec = importlib.util.spec_from_file_location("interview_intake_under_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class InterviewIntakeTests(unittest.TestCase):
    def test_separates_confirmed_logistics_hypotheses_and_unknowns_without_research(self):
        module = load_module()
        intake = module.build_interview_intake({
            "company": "Example Co",
            "vacancy_title": "Operations Lead",
            "stage": "Hiring manager interview",
            "scheduled_at": "2026-12-01T10:00:00-06:00",
            "modality": "video",
            "participants": [{"name": "Ada Example", "role": "Hiring manager"}],
            "source": "Candidate-provided invitation",
            "hypotheses": ["The role may prioritize operating cadence."],
        })
        self.assertEqual(intake["confirmed_logistics"]["participants"][0]["name"], "Ada Example")
        self.assertEqual(intake["hypotheses"], ["The role may prioritize operating cadence."])
        self.assertIn("duration_minutes", intake["unknowns"])
        self.assertEqual(intake["external_actions"], 0)
        self.assertEqual(intake["research_status"], "not_started")

    def test_rejects_unconfirmed_participant_identity_and_missing_source(self):
        module = load_module()
        with self.assertRaisesRegex(ValueError, "source"):
            module.build_interview_intake({"company": "Example Co", "stage": "Screen"})
        with self.assertRaisesRegex(ValueError, "participants"):
            module.build_interview_intake({"company": "Example Co", "stage": "Screen", "source": "Candidate-provided invitation", "participants": [{"name": "Ada"}]})

    def test_rejects_non_positive_or_non_integer_duration(self):
        module = load_module()
        for value in (0, -1, "60", [], {}):
            with self.assertRaisesRegex(ValueError, "duration_minutes"):
                module.build_interview_intake({"company": "Example Co", "stage": "Screen", "source": "Candidate-provided invitation", "duration_minutes": value})


if __name__ == "__main__":
    unittest.main()
