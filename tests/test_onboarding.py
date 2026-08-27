import json
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "skills" / "career-copilot" / "scripts" / "bootstrap_workspace.py"
ONBOARDING = ROOT / "skills" / "career-copilot" / "scripts" / "onboarding.py"


class OnboardingTests(unittest.TestCase):
    def run_command(self, *args: str) -> dict:
        completed = subprocess.run([sys.executable, str(ONBOARDING), *args], check=True, capture_output=True, text=True)
        return json.loads(completed.stdout)

    def test_checkpoint_resume_and_finalize(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "candidate"
            subprocess.run([sys.executable, str(BOOTSTRAP), "--workspace", str(workspace)], check=True, capture_output=True, text=True)
            initial = self.run_command("--workspace", str(workspace), "start")
            self.assertEqual(initial["status"], "in_progress")
            self.assertEqual(initial["completed_required"], 0)
            self.assertEqual(initial["external_action_policy"]["mode"], "draft_only")
            self.assertFalse(initial["external_action_policy"]["locked"])

            answers = {
                "profile.target_roles": ["Program Director"],
                "profile.target_seniority": ["Director"],
                "profile.strengths": ["program governance"],
                "profile.verified_evidence": ["Led a verified synthetic program"],
                "constraints.countries": ["Exampleland"],
                "permissions.tracker_updates": "allow",
            }
            for field, value in answers.items():
                self.run_command(
                    "--workspace", str(workspace), "answer", "--field", field,
                    "--json-value", json.dumps(value),
                )

            resumed = self.run_command("--workspace", str(workspace), "start")
            self.assertEqual(resumed["missing"], [])
            final = self.run_command("--workspace", str(workspace), "finalize")
            self.assertEqual(final["status"], "complete")
            profile = json.loads((workspace / "profile.yaml").read_text(encoding="utf-8"))
            self.assertEqual(profile["profile"]["target_roles"], ["Program Director"])
            self.assertEqual(profile["permissions"]["external_action_mode"], "draft_only")
            self.assertTrue((workspace / "profile.yaml.pre-onboarding.bak").is_file())
            self.assertTrue((workspace / "rules.yaml.pre-onboarding.bak").is_file())

    def test_confirm_each_external_requires_explicit_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "candidate"
            self.run_command("--workspace", str(workspace), "start")
            result = self.run_command(
                "--workspace", str(workspace), "answer",
                "--field", "permissions.external_action_mode",
                "--value", "confirm_each_external",
            )
            self.assertEqual(result["external_action_policy"]["mode"], "confirm_each_external")

    def test_locked_draft_only_cannot_be_changed_or_reset(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "candidate"
            locked = self.run_command("--workspace", str(workspace), "start", "--lock-draft-only")
            self.assertEqual(locked["external_action_policy"], {"mode": "draft_only", "locked": True})

            change = subprocess.run(
                [
                    sys.executable, str(ONBOARDING), "--workspace", str(workspace),
                    "answer", "--field", "permissions.external_action_mode",
                    "--value", "confirm_each_external",
                ],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(change.returncode, 2)
            self.assertIn("locked", change.stderr)

            reset = self.run_command("--workspace", str(workspace), "start", "--reset")
            self.assertEqual(reset["external_action_policy"], {"mode": "draft_only", "locked": True})

    def test_finalize_rejects_incomplete_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "candidate"
            self.run_command("--workspace", str(workspace), "start")
            completed = subprocess.run(
                [sys.executable, str(ONBOARDING), "--workspace", str(workspace), "finalize"],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(completed.returncode, 2)
            self.assertIn("missing", completed.stderr)

    def test_invalid_field_type_and_permission_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "candidate"
            self.run_command("--workspace", str(workspace), "start")
            invalid_commands = [
                ["answer", "--field", "profile.target_roles", "--json-value", '"not-a-list"'],
                ["answer", "--field", "permissions.external_action_mode", "--value", "always_send"],
                ["answer", "--field", "permissions.external_action_mode_locked", "--json-value", "false"],
                ["answer", "--field", "unknown.private_field", "--value", "blocked"],
                ["answer", "--field", "search.freshness_days", "--json-value", "0"],
            ]
            for command in invalid_commands:
                completed = subprocess.run(
                    [sys.executable, str(ONBOARDING), "--workspace", str(workspace), *command],
                    check=False, capture_output=True, text=True,
                )
                self.assertEqual(completed.returncode, 2)
                self.assertIn("ERROR", completed.stderr)

    def test_workspace_inside_distribution_is_rejected(self):
        forbidden = ROOT / "private-candidate-test"
        completed = subprocess.run(
            [sys.executable, str(ONBOARDING), "--workspace", str(forbidden), "start"],
            check=False, capture_output=True, text=True,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("outside", completed.stderr)
        self.assertFalse(forbidden.exists())


if __name__ == "__main__":
    unittest.main()
