from __future__ import annotations

import importlib.util
import stat
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "skills/career-copilot/scripts/bootstrap_workspace.py"
SPEC = importlib.util.spec_from_file_location("bootstrap_under_test", MODULE_PATH)
assert SPEC and SPEC.loader
bootstrap_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bootstrap_module)
SKILL_DIR = MODULE_PATH.parents[1]


class BootstrapTests(unittest.TestCase):
    def test_creates_private_workspace_and_preserves_existing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "candidate"
            created, skipped = bootstrap_module.bootstrap(workspace, SKILL_DIR)
            self.assertEqual(4, len(created))
            self.assertEqual([], skipped)
            self.assertTrue((workspace / "profile.yaml").is_file())
            self.assertTrue((workspace / "rules.yaml").is_file())
            self.assertTrue((workspace / "tracker.csv").is_file())
            tracker_header = (workspace / "tracker.csv").read_text(encoding="utf-8").splitlines()[0].split(",")
            self.assertIn("vacancy_last_verified", tracker_header)
            self.assertIn("human_path_last_verified", tracker_header)
            self.assertNotIn("last_verified", tracker_header)
            self.assertEqual(stat.S_IMODE(workspace.stat().st_mode), 0o700)
            for private_file in ("profile.yaml", "rules.yaml", "tracker.csv", "README_PRIVATE.md"):
                self.assertEqual(stat.S_IMODE((workspace / private_file).stat().st_mode), 0o600)
            original = (workspace / "profile.yaml").read_text(encoding="utf-8")

            workspace.chmod(0o755)
            (workspace / "notes").chmod(0o755)
            (workspace / "applications").chmod(0o755)
            (workspace / "profile.yaml").chmod(0o644)
            nested_dir = workspace / "notes" / "private-draft"
            nested_dir.mkdir()
            nested_file = nested_dir / "draft.txt"
            nested_file.write_text("private", encoding="utf-8")
            nested_dir.chmod(0o755)
            nested_file.chmod(0o644)

            created_again, skipped_again = bootstrap_module.bootstrap(workspace, SKILL_DIR)
            self.assertEqual([], created_again)
            self.assertEqual(4, len(skipped_again))
            self.assertEqual(original, (workspace / "profile.yaml").read_text(encoding="utf-8"))
            self.assertEqual(stat.S_IMODE(workspace.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE((workspace / "notes").stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE((workspace / "applications").stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE((workspace / "profile.yaml").stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(nested_dir.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(nested_file.stat().st_mode), 0o600)

    def test_rejects_workspace_inside_distribution(self):
        forbidden = SKILL_DIR.parents[1] / "private-bootstrap-test"
        with self.assertRaises(ValueError):
            bootstrap_module.bootstrap(forbidden, SKILL_DIR)
        self.assertFalse(forbidden.exists())

    def test_rejects_workspace_inside_any_git_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            git_root = Path(tmp) / "project"
            (git_root / ".git").mkdir(parents=True)
            forbidden = git_root / "private-candidate"
            with self.assertRaisesRegex(ValueError, "Git repository"):
                bootstrap_module.bootstrap(forbidden, SKILL_DIR)
            self.assertFalse(forbidden.exists())


if __name__ == "__main__":
    unittest.main()
