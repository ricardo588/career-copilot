import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "career-copilot" / "scripts" / "story_capture.py"


def load_module():
    spec = importlib.util.spec_from_file_location("story_capture_under_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class StoryCaptureTests(unittest.TestCase):
    def test_builds_unconfirmed_private_story_proposal_and_questions_missing_evidence(self):
        module = load_module()
        proposal = module.build_capture_proposal({
            "title": "Launch recovery",
            "context": "A release had a confirmed operational regression.",
            "challenge": "Restore service without losing the documented audit trail.",
            "actions": ["Coordinated rollback", "Recorded the decision"],
            "results": {"facts": ["Service was restored."], "unknowns": ["Impact metric is not yet confirmed."]},
            "confidentiality": "candidate_private",
        })
        self.assertTrue(proposal["confirmation_required"])
        self.assertFalse(proposal["story"]["user_confirmed"])
        self.assertEqual(proposal["story"]["results"]["facts"], ["Service was restored."])
        self.assertIn("confirmed_metrics", proposal["questions"])
        self.assertIn("evidence_sources", proposal["questions"])
        self.assertNotIn("metrics", proposal["story"])

    def test_rejects_invented_metrics_and_preserves_unknowns(self):
        module = load_module()
        with self.assertRaisesRegex(ValueError, "confirmed_metrics"):
            module.build_capture_proposal({
                "title": "Example",
                "confirmed_metrics": [{"label": "time saved", "value": 20}],
            })
        proposal = module.build_capture_proposal({"title": "Example", "results": {"unknowns": ["No outcome evidence supplied."]}})
        self.assertEqual(proposal["story"]["results"]["unknowns"], ["No outcome evidence supplied."])
        self.assertIn("context", proposal["questions"])

    def test_confirmation_requires_explicit_consent_and_marks_only_the_reviewed_proposal(self):
        module = load_module()
        proposal = module.build_capture_proposal({"title": "Example", "results": {"facts": ["Confirmed fact."]}})
        with self.assertRaisesRegex(ValueError, "explicit"):
            module.confirm_capture_proposal(proposal, explicit_confirmation=False)
        confirmed = module.confirm_capture_proposal(proposal, explicit_confirmation=True)
        self.assertTrue(confirmed["user_confirmed"])
        self.assertEqual(confirmed["provenance"]["confirmation"], "explicit_candidate_confirmation")
        self.assertFalse(proposal["story"]["user_confirmed"])


if __name__ == "__main__":
    unittest.main()
