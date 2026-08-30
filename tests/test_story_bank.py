import importlib.util
import json
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "career-copilot" / "scripts" / "story_bank.py"
SPEC = importlib.util.spec_from_file_location("career_story_bank", SCRIPT)
assert SPEC and SPEC.loader
STORY_BANK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(STORY_BANK)


class StoryBankTests(unittest.TestCase):
    def profile(self):
        return {
            "profile": {
                "target_roles": ["Transformation Director"],
                "verified_evidence": ["Led a verified transformation"],
                "career_direction": {
                    "values": {"facts": [], "interpretations": [], "preferences": ["Evidence-based decisions"]},
                    "departure_narrative": {
                        "candidate_approved": True,
                        "facts": ["The prior role ended after a restructuring."],
                        "interpretations": ["It created a useful transition."],
                        "preferences": [],
                    },
                },
            }
        }

    def story(self, confidentiality="shareable", confirmed=True):
        return {
            "id": "story-one",
            "title": "Transformation governance",
            "context": "A program needed governance",
            "challenge": "Decision rights were unclear",
            "actions": ["Defined governance"],
            "results": {"facts": ["One cadence was adopted"], "unknowns": ["Financial impact is unknown"]},
            "confirmed_metrics": [
                {"label": "countries", "value": 3, "unit": "countries", "source": "program record", "confirmed_by_user": True}
            ],
            "evidence_sources": [
                {"kind": "program_record", "label": "Program record", "reference": "private reference", "confirmed_by_user": True}
            ],
            "tags": ["transformation", "governance"],
            "recency": {"last_confirmed": "2026-08-25"},
            "confidentiality": confidentiality,
            "provenance": {"source_kind": "candidate_record"},
            "user_confirmed": confirmed,
        }

    def test_round_trip_preserves_provenance_unknowns_and_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "stories.jsonl"
            STORY_BANK.save_story_bank(path, [self.story()])
            loaded = STORY_BANK.load_story_bank(path)
            self.assertEqual(loaded[0]["id"], "story-one")
            self.assertEqual(loaded[0]["results"]["unknowns"], ["Financial impact is unknown"])
            self.assertEqual(loaded[0]["provenance"]["source_kind"], "candidate_record")
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_selection_reuses_story_without_mutating_or_exposing_restricted_content(self):
        shareable = self.story()
        restricted = self.story(confidentiality="restricted")
        restricted["id"] = "story-restricted"
        before = json.dumps([shareable, restricted], sort_keys=True)
        interview = STORY_BANK.serialize_story_views(
            [shareable, restricted],
            profile=self.profile(),
            vacancy={"title": "Transformation Director", "requirements": ["governance"]},
            mode="interview",
        )
        cv = STORY_BANK.serialize_story_views([shareable, restricted], profile=self.profile(), mode="cv")
        self.assertEqual(interview["story_ids"], ["story-one"])
        self.assertEqual(cv["story_ids"], ["story-one"])
        self.assertEqual(json.dumps([shareable, restricted], sort_keys=True), before)

    def test_legacy_evidence_migration_is_non_destructive_and_does_not_infer_metrics(self):
        evidence = ["Led a verified transformation"]
        stories = STORY_BANK.load_story_bank(None, legacy_evidence=evidence)
        self.assertEqual(evidence, ["Led a verified transformation"])
        self.assertEqual(stories[0]["results"]["facts"], evidence)
        self.assertEqual(stories[0]["confirmed_metrics"], [])
        self.assertTrue(stories[0]["results"]["unknowns"])
        self.assertEqual(stories[0]["provenance"]["migrated_from"], "verified_evidence")

    def test_career_direction_keeps_preferences_subjective_and_unknowns_non_filtering(self):
        view = STORY_BANK.career_direction_view(self.profile(), {"title": "Director"})
        self.assertEqual(view["hard_filters_applied"], [])
        self.assertTrue(view["unknown_preferences_ignored"])
        self.assertIn("values", view["candidate_declared"])
        self.assertIn("objective company fact", view["interpretation"])
        self.assertEqual(
            STORY_BANK.approved_departure_statement(self.profile()),
            "The prior role ended after a restructuring.",
        )
        unapproved = self.profile()
        unapproved["profile"]["career_direction"]["departure_narrative"]["candidate_approved"] = False
        self.assertIsNone(STORY_BANK.approved_departure_statement(unapproved))

    def test_cli_migrates_only_when_requested_and_supports_all_views(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            profile = tmp_path / "profile.yaml"
            stories = tmp_path / "stories.jsonl"
            profile.write_text(json.dumps(self.profile()), encoding="utf-8")
            stories.touch()
            for mode in ("evaluation", "interview", "cv"):
                command = [
                    sys.executable,
                    str(SCRIPT),
                    "--profile",
                    str(profile),
                    "--stories",
                    str(stories),
                    "--mode",
                    mode,
                    "--migrate-verified-evidence",
                ]
                result = subprocess.run(command, capture_output=True, text=True, check=True)
                payload = json.loads(result.stdout)
                self.assertEqual(payload["mode"], mode)
                expected = 0 if mode == "cv" else 1
                self.assertEqual(payload["story_count"], expected)
            self.assertEqual(stat.S_IMODE(stories.stat().st_mode), 0o600)


if __name__ == "__main__":
    unittest.main()
