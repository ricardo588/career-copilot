import importlib.util
import json
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "career-copilot" / "scripts" / "pipeline.py"
SPEC = importlib.util.spec_from_file_location("relationship_pipeline", SCRIPT)
assert SPEC and SPEC.loader
PIPELINE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PIPELINE)


class RelationshipAndDebriefTests(unittest.TestCase):
    def vacancy(self):
        return {"company": "Acme Cloud Services", "title": "Transformation Director"}

    def relationship_artifact(self):
        return {
            "retrieved_at": "2026-08-26",
            "relationships": [
                {
                    "name": "Synthetic Connector",
                    "relationship_role": "connector",
                    "influence": "moderate",
                    "strength": "strong",
                    "current_company": "Acme Cloud Services",
                    "current_role": "Regional Director",
                    "evidence": ["candidate-owned relationship record"],
                    "freshness": "2026-08-26",
                    "source_url": "https://example.test/connector",
                    "confidence": "confirmed",
                    "authorization": {"contact": True, "reference": False, "referral": False},
                },
                {
                    "name": "Synthetic Decision Maker",
                    "relationship_role": "probable decision maker",
                    "influence": "high",
                    "strength": "unknown",
                    "current_company": "Acme Cloud Services",
                    "current_role": "VP Transformation",
                    "evidence": ["current public profile"],
                    "freshness": "2026-08-26",
                    "source_url": "https://example.test/decision-maker",
                    "confidence": "probable",
                    "authorization": {"contact": False},
                },
            ],
        }

    def test_relationship_model_keeps_role_influence_strength_and_authorization_separate(self):
        summary = PIPELINE.summarize_human_path(self.vacancy(), self.relationship_artifact())
        self.assertEqual(summary["status"], "confirmed")
        connector = summary["confirmed_paths"][0]
        self.assertEqual(connector["relationship_role"], "connector")
        self.assertEqual(connector["influence"], "moderate")
        self.assertEqual(connector["strength"], "strong")
        self.assertTrue(connector["authorization"]["contact"])
        self.assertFalse(connector["authorization"]["reference"])
        probable = summary["unverified_paths"][0]
        self.assertEqual(probable["relationship_role"], "probable decision maker")
        self.assertFalse(probable["authorization"]["contact"])
        self.assertIn("not permission", summary["guardrail"])

    def test_relationship_meeting_prep_records_outcome_and_keeps_follow_up_draft_only(self):
        artifact = self.relationship_artifact()
        meeting = {
            "company": "Acme Cloud Services",
            "topic": "Operating model",
            "objective": "Learn without asking for a referral.",
            "timebox_minutes": 20,
            "questions": ["How are decisions made?"],
            "draft_follow_up": "Draft only: thank you for the context.",
            "outcome": {"referral_confirmed": False, "commitments": []},
        }
        markdown = PIPELINE.relationship_meeting_prep(artifact, meeting)
        self.assertIn("## Recorded outcome", markdown)
        self.assertIn("referral_confirmed: False", markdown)
        self.assertIn("authorization contact", markdown)
        self.assertIn("Keep the follow-up as a draft", markdown)

    def test_debrief_separates_observation_from_reflection_for_every_outcome(self):
        for outcome in PIPELINE.DEBRIEF_OUTCOMES:
            with self.subTest(outcome=outcome):
                debrief = {
                    "company": "Acme Cloud Services",
                    "role": "Transformation Director",
                    "outcome": outcome,
                    "sentiment": "mixed",
                    "observed_facts": ["The panel asked two governance questions."],
                    "candidate_interpretation": ["The opening may have been too long."],
                    "learning": ["Prompt for a concise governance story in future briefs."],
                    "unanswered_questions": ["Who owns the final decision?"],
                    "authorized_follow_up": {"contact": False, "send": False},
                    "follow_up_draft": "Draft only: thank you for the conversation.",
                }
                markdown = PIPELINE.interview_debrief(debrief)
                facts = markdown.index("## Observed facts")
                reflection = markdown.index("## Candidate interpretation")
                self.assertLess(facts, reflection)
                self.assertIn("Sentiment never changes tracker state", markdown)
                self.assertIn("future briefs", markdown)
                self.assertIn("Draft only", markdown)

    def test_cli_special_modes_write_private_readback_artifacts_without_tracker_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            relationship_path = root / "relationship.json"
            meeting_path = root / "meeting.json"
            debrief_path = root / "debrief.json"
            tracker = root / "tracker.csv"
            tracker.write_text("sentinel\n", encoding="utf-8")
            relationship_path.write_text(json.dumps(self.relationship_artifact()), encoding="utf-8")
            meeting_path.write_text(json.dumps({
                "company": "Acme Cloud Services",
                "topic": "Operating model",
                "questions": [],
                "draft_follow_up": "Draft only.",
            }), encoding="utf-8")
            debrief_path.write_text(json.dumps({
                "company": "Acme Cloud Services",
                "role": "Transformation Director",
                "outcome": "rejected",
                "observed_facts": ["A rejection was received."],
                "candidate_interpretation": [],
                "learning": ["Prepare a shorter opening."],
                "authorized_follow_up": {"contact": False, "send": False},
                "follow_up_draft": "Draft only: thank you.",
            }), encoding="utf-8")
            prep_md = root / "private" / "prep.md"
            debrief_md = root / "private" / "debrief.md"
            subprocess.run([
                sys.executable, str(SCRIPT), "--relationship-prep", str(relationship_path),
                "--meeting", str(meeting_path), "--relationship-prep-md", str(prep_md),
            ], check=True, capture_output=True, text=True)
            subprocess.run([
                sys.executable, str(SCRIPT), "--interview-debrief", str(debrief_path),
                "--interview-debrief-md", str(debrief_md),
            ], check=True, capture_output=True, text=True)
            self.assertEqual(tracker.read_text(encoding="utf-8"), "sentinel\n")
            self.assertEqual(stat.S_IMODE(prep_md.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(debrief_md.stat().st_mode), 0o600)
            self.assertIn("Draft only", debrief_md.read_text(encoding="utf-8"))

    def test_special_mode_rejects_tracker_mutation_and_distribution_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            debrief_path = root / "debrief.json"
            tracker = root / "tracker.csv"
            debrief_path.write_text(json.dumps({
                "outcome": "positive", "observed_facts": [], "candidate_interpretation": []
            }), encoding="utf-8")
            result = subprocess.run([
                sys.executable, str(SCRIPT), "--interview-debrief", str(debrief_path),
                "--tracker", str(tracker),
            ], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(tracker.exists())
            with self.assertRaisesRegex(ValueError, "outside"):
                PIPELINE.write_private_markdown(str(ROOT / "private-debrief.md"), "private")
            self.assertFalse((ROOT / "private-debrief.md").exists())


if __name__ == "__main__":
    unittest.main()
