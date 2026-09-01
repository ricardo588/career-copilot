from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "skills/career-copilot/scripts/pipeline.py"
SPEC = importlib.util.spec_from_file_location("pipeline_under_test", MODULE_PATH)
assert SPEC and SPEC.loader
PIPELINE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PIPELINE)

FIXTURE = Path(__file__).resolve().parents[1] / "skills/career-copilot/examples/synthetic/assessment-prep.json"


class AssessmentPrepTests(unittest.TestCase):
    def test_assessment_prep_separates_instructions_assumptions_and_required_sections(self):
        prep = json.loads(FIXTURE.read_text(encoding="utf-8"))
        markdown = PIPELINE.assessment_prep(prep)
        self.assertIn("## Known instructions", markdown)
        self.assertIn("A 20-minute case prompt was supplied.", markdown)
        self.assertIn("## Assumptions and open questions", markdown)
        self.assertIn("### Assumptions", markdown)
        self.assertIn("The audience wants concise bullets rather than a long narrative.", markdown)
        self.assertIn("### Open questions", markdown)
        self.assertIn("Will a calculator be available?", markdown)
        for heading in (
            "## Suggested structure",
            "### Problem",
            "### Evidence",
            "### Options",
            "### Recommendation",
            "### Risks",
            "### Next Steps",
            "## Rehearsal plan",
            "## Technical and logistics checks",
            "## Psychometric guidance",
            "## Declared accommodations and constraints",
            "## Risks",
            "## Next steps",
        ):
            self.assertIn(heading, markdown)
        self.assertIn("never coach falsification", markdown)
        self.assertIn("Protected attributes and accommodations stay separate", markdown)
        self.assertNotIn("%", markdown)

    def test_cli_writes_private_markdown_and_round_trips_payload(self):
        prep = json.loads(FIXTURE.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            prep_path = tmp_path / "assessment.json"
            prep_path.write_text(json.dumps(prep), encoding="utf-8")
            output_path = tmp_path / "private" / "prep.md"
            result = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    "--assessment-prep",
                    str(prep_path),
                    "--assessment-prep-md",
                    str(output_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(result.stdout)
            self.assertEqual(payload["assessment_prep"]["assessment_type"], "case")
            self.assertEqual(Path(payload["assessment_prep_markdown"]).resolve(), output_path.resolve())
            self.assertTrue(output_path.exists())
            self.assertEqual(output_path.read_text(encoding="utf-8"), payload["markdown"])
            self.assertEqual(output_path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(output_path.parent.stat().st_mode & 0o777, 0o700)
            self.assertIn("## Assessment type", payload["markdown"])
            self.assertIn("Timed numerical reasoning assessment", payload["markdown"])


if __name__ == "__main__":
    unittest.main()
