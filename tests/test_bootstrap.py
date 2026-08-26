from __future__ import annotations

import importlib.util
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
            original = (workspace / "profile.yaml").read_text(encoding="utf-8")

            created_again, skipped_again = bootstrap_module.bootstrap(workspace, SKILL_DIR)
            self.assertEqual([], created_again)
            self.assertEqual(4, len(skipped_again))
            self.assertEqual(original, (workspace / "profile.yaml").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
