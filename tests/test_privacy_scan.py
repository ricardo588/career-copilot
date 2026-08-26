from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "skills/career-copilot/scripts/privacy_scan.py"
SPEC = importlib.util.spec_from_file_location("privacy_scan_under_test", MODULE_PATH)
assert SPEC and SPEC.loader
privacy_scan = importlib.util.module_from_spec(SPEC)
import sys
sys.modules[SPEC.name] = privacy_scan
SPEC.loader.exec_module(privacy_scan)


class PrivacyScanTests(unittest.TestCase):
    def test_clean_synthetic_content_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.md"
            path.write_text("Synthetic candidate; contact demo@example.com", encoding="utf-8")
            self.assertEqual([], privacy_scan.scan(Path(tmp), markers=[]))

    def test_personal_email_is_detected(self):
        leaked_email = "person@" + "private.invalid"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.md"
            path.write_text(f"contact: {leaked_email}", encoding="utf-8")
            findings = privacy_scan.scan(Path(tmp), markers=[])
            self.assertTrue(any(item.kind == "personal email" for item in findings))

    def test_custom_private_marker_is_detected(self):
        marker = "private" + "-candidate-marker"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.md"
            path.write_text(f"candidate: {marker}", encoding="utf-8")
            findings = privacy_scan.scan(Path(tmp), markers=[marker])
            self.assertTrue(any(item.kind == "private marker" for item in findings))


if __name__ == "__main__":
    unittest.main()
