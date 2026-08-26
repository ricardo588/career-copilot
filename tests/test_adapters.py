import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "career-copilot" / "scripts" / "adapters.py"
SPEC = importlib.util.spec_from_file_location("career_adapters", SCRIPT)
ADAPTERS = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(ADAPTERS)


class FakeRunner:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, command):
        self.calls.append(command)
        return self.responses.pop(0)


class AdapterTests(unittest.TestCase):
    def test_sheets_update_is_dry_run_by_default(self):
        fake = FakeRunner([])
        result = ADAPTERS.sheets_update(fake, "sheet-example-1234", "Applications!A2:B2", [["Acme", "Role"]])
        self.assertEqual(result["status"], "dry_run")
        self.assertEqual(fake.calls, [])
        self.assertNotIn("sheet-example-1234", str(result))

    def test_sheets_apply_requires_matching_readback(self):
        fake = FakeRunner([{"updatedRows": 1}, {"values": [["Acme", "Role"]]}])
        result = ADAPTERS.sheets_update(fake, "sheet-example-1234", "Applications!A2:B2", [["Acme", "Role"]], apply=True)
        self.assertTrue(result["verified"])
        self.assertEqual(len(fake.calls), 2)
        self.assertIn("update", fake.calls[0])
        self.assertIn("get", fake.calls[1])

    def test_gmail_mark_read_is_dry_run_then_verified(self):
        dry_fake = FakeRunner([])
        dry = ADAPTERS.gmail_mark_read(dry_fake, "synthetic-message")
        self.assertEqual(dry["status"], "dry_run")
        self.assertEqual(dry_fake.calls, [])

        apply_fake = FakeRunner([{"id": "synthetic-message"}, {"id": "synthetic-message", "labelIds": ["INBOX"]}])
        applied = ADAPTERS.gmail_mark_read(apply_fake, "synthetic-message", apply=True)
        self.assertTrue(applied["verified"])
        self.assertEqual(len(apply_fake.calls), 2)

    def test_obsidian_write_is_scoped_dry_run_first_and_read_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            dry = ADAPTERS.obsidian_write(vault, "CareerCopilot/Brief.md", "# Brief\n")
            self.assertEqual(dry["status"], "dry_run")
            self.assertFalse((vault / "CareerCopilot" / "Brief.md").exists())

            applied = ADAPTERS.obsidian_write(vault, "CareerCopilot/Brief.md", "# Brief\n", apply=True)
            self.assertTrue(applied["verified"])
            self.assertEqual((vault / "CareerCopilot" / "Brief.md").read_text(encoding="utf-8"), "# Brief\n")

            with self.assertRaises(ValueError):
                ADAPTERS.obsidian_write(vault, "../outside.md", "blocked", apply=True)


if __name__ == "__main__":
    unittest.main()
