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
            self.assertEqual(initial["next_question"]["field"], "documents.has_cv")
            self.assertEqual(initial["external_action_policy"]["mode"], "draft_only")
            self.assertFalse(initial["external_action_policy"]["locked"])

            answers = {
                "documents.has_cv": False,
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
            self.assertEqual(profile["schema_version"], 4)
            self.assertEqual(profile["profile"]["target_roles"], ["Program Director"])
            self.assertEqual(profile["permissions"]["external_action_mode"], "draft_only")
            self.assertEqual(profile["documents"]["cv_import_status"], "not_applicable")
            self.assertTrue((workspace / "profile.yaml.pre-onboarding.bak").is_file())
            self.assertTrue((workspace / "rules.yaml.pre-onboarding.bak").is_file())
            self.assertEqual(final["story_count"], 1)
            story = json.loads((workspace / "stories.jsonl").read_text(encoding="utf-8").strip())
            self.assertEqual(story["results"]["facts"], ["Led a verified synthetic program"])
            self.assertEqual(profile["profile"]["verified_evidence"], ["Led a verified synthetic program"])

    def test_optional_career_direction_is_resumable_and_preserves_fact_categories(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "candidate"
            self.run_command("--workspace", str(workspace), "start")
            value = {
                "facts": [],
                "interpretations": ["A larger remit may accelerate development"],
                "preferences": ["Visible executive sponsorship"],
            }
            result = self.run_command(
                "--workspace", str(workspace), "answer",
                "--field", "profile.career_direction.success_criteria",
                "--json-value", json.dumps(value),
            )
            checkpoint = json.loads((workspace / ".career_copilot_onboarding.json").read_text(encoding="utf-8"))
            self.assertEqual(
                checkpoint["answers"]["profile"]["career_direction"]["success_criteria"],
                value,
            )
            self.assertNotIn("profile.career_direction.success_criteria", result["missing"])

    def test_cv_first_proposes_supported_fields_and_requires_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "candidate"
            cv = workspace / "synthetic-cv.txt"
            workspace.mkdir(parents=True)
            cv.write_text("Synthetic Candidate — Program Director", encoding="utf-8")

            initial = self.run_command("--workspace", str(workspace), "start")
            self.assertEqual(initial["next_question"]["field"], "documents.has_cv")
            has_cv = self.run_command(
                "--workspace", str(workspace), "answer",
                "--field", "documents.has_cv", "--json-value", "true",
            )
            self.assertEqual(has_cv["next_question"]["field"], "documents.primary_cv")
            self.assertEqual(has_cv["completed_required"], 1)
            cv_path = self.run_command(
                "--workspace", str(workspace), "answer",
                "--field", "documents.primary_cv", "--value", str(cv),
            )
            self.assertEqual(cv_path["next_question"]["field"], "documents.cv_import")

            proposal = {
                "source_file": str(cv),
                "proposals": {
                    "profile.display_name": {"value": "Synthetic Candidate", "basis": "direct", "source": "header"},
                    "profile.target_roles": {"value": ["Program Director"], "basis": "inferred", "source": "headline"},
                    "profile.target_seniority": {"value": ["Director"], "basis": "inferred", "source": "headline"},
                    "profile.strengths": {"value": ["program governance"], "basis": "direct", "source": "experience"},
                    "profile.verified_evidence": {"value": ["Led a synthetic transformation"], "basis": "direct", "source": "experience"},
                    "constraints.locations": {"value": ["Example City"], "basis": "inferred", "source": "current location in header"},
                },
            }
            proposed = self.run_command(
                "--workspace", str(workspace), "cv-propose",
                "--json-value", json.dumps(proposal),
            )
            self.assertEqual(proposed["cv_import"]["status"], "pending_confirmation")
            self.assertEqual(proposed["next_question"]["field"], "documents.cv_confirmation")
            self.assertIn("profile.target_roles", proposed["cv_import"]["proposals"])
            staged_state = json.loads((workspace / ".career_copilot_onboarding.json").read_text(encoding="utf-8"))
            self.assertEqual(staged_state["answers"]["profile"]["target_roles"], [])
            self.assertNotIn("profile.target_roles", staged_state["answered_fields"])

            confirmed = self.run_command(
                "--workspace", str(workspace), "cv-confirm",
                "--overrides-json", json.dumps({"profile.target_roles": ["Transformation Director"]}),
            )
            self.assertEqual(confirmed["cv_import"]["status"], "confirmed")
            state = json.loads((workspace / ".career_copilot_onboarding.json").read_text(encoding="utf-8"))
            self.assertEqual(state["answers"]["profile"]["target_roles"], ["Transformation Director"])
            self.assertEqual(state["answers"]["profile"]["display_name"], "Synthetic Candidate")
            self.assertNotIn("documents.cv_confirmation", confirmed["missing"])
            self.assertNotIn("profile.target_roles", confirmed["missing"])

            self.run_command(
                "--workspace", str(workspace), "answer",
                "--field", "profile.display_name", "--value", "Manually Confirmed Name",
            )

            replacement_cv = workspace / "replacement-cv.txt"
            replacement_cv.write_text("Replacement CV", encoding="utf-8")
            changed = self.run_command(
                "--workspace", str(workspace), "answer",
                "--field", "documents.primary_cv", "--value", str(replacement_cv),
            )
            changed_state = json.loads((workspace / ".career_copilot_onboarding.json").read_text(encoding="utf-8"))
            self.assertEqual(changed["next_question"]["field"], "documents.cv_import")
            self.assertEqual(changed_state["answers"]["profile"]["target_roles"], [])
            self.assertEqual(changed_state["answers"]["profile"]["display_name"], "Manually Confirmed Name")
            self.assertIn("profile.target_roles", changed["missing"])

    def test_cv_proposals_reject_unknown_fields_and_do_not_copy_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "candidate"
            cv = root / "outside-private-cv.txt"
            cv.write_text("Synthetic", encoding="utf-8")
            self.run_command("--workspace", str(workspace), "start")
            self.run_command(
                "--workspace", str(workspace), "answer",
                "--field", "documents.has_cv", "--json-value", "true",
            )
            self.run_command(
                "--workspace", str(workspace), "answer",
                "--field", "documents.primary_cv", "--value", str(cv),
            )
            invalid = {
                "source_file": str(cv),
                "proposals": {
                    "permissions.external_action_mode": {
                        "value": "confirm_each_external", "basis": "inferred", "source": "none",
                    }
                },
            }
            completed = subprocess.run(
                [
                    sys.executable, str(ONBOARDING), "--workspace", str(workspace),
                    "cv-propose", "--json-value", json.dumps(invalid),
                ],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(completed.returncode, 2)
            self.assertIn("cannot be proposed from a CV", completed.stderr)
            self.assertEqual(sorted(path.name for path in workspace.iterdir()), [".career_copilot_onboarding.json"])

            inferred_evidence = {
                "source_file": str(cv),
                "proposals": {
                    "profile.verified_evidence": {
                        "value": ["Unsupported inference"],
                        "basis": "inferred",
                        "source": "Experience",
                    }
                },
            }
            inferred = subprocess.run(
                [
                    sys.executable, str(ONBOARDING), "--workspace", str(workspace), "cv-propose",
                    "--json-value", json.dumps(inferred_evidence),
                ],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(inferred.returncode, 2)
            self.assertIn("must be direct evidence", inferred.stderr)

    def test_cv_path_inside_distribution_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "candidate"
            self.run_command("--workspace", str(workspace), "start")
            self.run_command(
                "--workspace", str(workspace), "answer",
                "--field", "documents.has_cv", "--json-value", "true",
            )
            completed = subprocess.run(
                [
                    sys.executable, str(ONBOARDING), "--workspace", str(workspace),
                    "answer", "--field", "documents.primary_cv", "--value", str(ROOT / "README.md"),
                ],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(completed.returncode, 2)
            self.assertIn("outside the Career Copilot", completed.stderr)

    def test_cv_change_after_staging_requires_new_proposal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "candidate"
            cv = root / "candidate-cv.txt"
            cv.write_text("Original CV", encoding="utf-8")
            self.run_command("--workspace", str(workspace), "start")
            self.run_command(
                "--workspace", str(workspace), "answer",
                "--field", "documents.has_cv", "--json-value", "true",
            )
            self.run_command(
                "--workspace", str(workspace), "answer",
                "--field", "documents.primary_cv", "--value", str(cv),
            )
            proposal = {
                "source_file": str(cv),
                "proposals": {
                    "profile.target_roles": {
                        "value": ["Program Director"],
                        "basis": "inferred",
                        "source": "Headline",
                    }
                },
            }
            self.run_command(
                "--workspace", str(workspace), "cv-propose",
                "--json-value", json.dumps(proposal),
            )
            cv.write_text("Changed CV", encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable, str(ONBOARDING), "--workspace", str(workspace),
                    "cv-confirm",
                ],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(completed.returncode, 2)
            self.assertIn("changed since proposals were staged", completed.stderr)
            state = json.loads((workspace / ".career_copilot_onboarding.json").read_text(encoding="utf-8"))
            self.assertEqual(state["cv_import"]["status"], "pending_confirmation")
            self.assertEqual(state["answers"]["profile"]["target_roles"], [])

    def test_existing_cv_can_fall_back_to_manual_questions(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "candidate"
            cv = Path(tmp) / "unreadable.pdf"
            cv.write_bytes(b"not a real pdf")
            self.run_command("--workspace", str(workspace), "start")
            self.run_command(
                "--workspace", str(workspace), "answer",
                "--field", "documents.has_cv", "--json-value", "true",
            )
            self.run_command(
                "--workspace", str(workspace), "answer",
                "--field", "documents.primary_cv", "--value", str(cv),
            )
            skipped = self.run_command(
                "--workspace", str(workspace), "cv-skip",
                "--reason", "local text extraction unavailable",
            )
            self.assertEqual(skipped["cv_import"]["status"], "manual")
            self.assertEqual(skipped["next_question"]["field"], "profile.target_roles")

    def test_schema_two_checkpoint_migrates_to_cv_first_without_losing_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "candidate"
            self.run_command("--workspace", str(workspace), "start", "--lock-draft-only")
            checkpoint = workspace / ".career_copilot_onboarding.json"
            state = json.loads(checkpoint.read_text(encoding="utf-8"))
            state["schema_version"] = 2
            state.pop("cv_import")
            state["answers"]["documents"].pop("has_cv")
            state["answers"]["documents"].pop("cv_import_status")
            checkpoint.write_text(json.dumps(state), encoding="utf-8")

            migrated = self.run_command("--workspace", str(workspace), "status")
            self.assertEqual(migrated["next_question"]["field"], "documents.has_cv")
            self.assertEqual(migrated["external_action_policy"], {"mode": "draft_only", "locked": True})
            resumed = json.loads(checkpoint.read_text(encoding="utf-8"))
            self.assertEqual(resumed["schema_version"], 4)

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

    def test_structured_eligibility_and_accommodations_are_checkpointed(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "candidate"
            self.run_command("--workspace", str(workspace), "start")
            self.run_command(
                "--workspace", str(workspace), "answer",
                "--field", "constraints.job_eligibility.work_authorization",
                "--json-value", '["Mexico"]',
            )
            self.run_command(
                "--workspace", str(workspace), "answer",
                "--field", "constraints.job_eligibility.travel", "--value", "up to 25 percent",
            )
            self.run_command(
                "--workspace", str(workspace), "answer",
                "--field", "constraints.accommodations", "--json-value", '["step-free interview access"]',
            )

            state = json.loads((workspace / ".career_copilot_onboarding.json").read_text(encoding="utf-8"))
            constraints = state["answers"]["constraints"]
            self.assertEqual(constraints["job_eligibility"]["work_authorization"], ["Mexico"])
            self.assertEqual(constraints["job_eligibility"]["travel"], "up to 25 percent")
            self.assertEqual(constraints["accommodations"], ["step-free interview access"])

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
