from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "skills/career-copilot/scripts/cv_review.py"
SPEC = importlib.util.spec_from_file_location("cv_review_under_test", MODULE_PATH)
assert SPEC and SPEC.loader
CV_REVIEW = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CV_REVIEW)


class CVReviewTests(unittest.TestCase):
    matrix = {
        "requirements": [
            {"id": "r1", "requirement": "Cloud migration", "assessment": "direct", "direct_evidence": [{"ref": "profile.verified_evidence[0]"}]},
            {"id": "r2", "requirement": "Payment rails", "assessment": "transferable", "direct_evidence": [], "transferability": {"label": "analysis_not_direct_experience"}},
            {"id": "r3", "requirement": "Rust", "assessment": "gap", "direct_evidence": []},
            {"id": "r4", "requirement": "Quantum", "assessment": "unknown", "direct_evidence": []},
        ]
    }

    def test_local_review_keeps_original_unchanged_and_labels_matrix_evidence(self):
        cv_text = """Jane Candidate\n""" + "jane@" + "example.invalid" + """ | +52 55 1234 5678\n\nProfessional Experience\nProgram Director, Example Co | 2024 - Present\nLed a cloud migration program.\n\nEducation\nMBA | 2010\n\nSkills\nCloud delivery; executive communication\n"""
        with tempfile.TemporaryDirectory() as tmp:
            cv_path = Path(tmp) / "cv.txt"
            cv_path.write_text(cv_text, encoding="utf-8")
            before = cv_path.read_bytes()
            report = CV_REVIEW.review_cv(cv_path, self.matrix)
            self.assertEqual(cv_path.read_bytes(), before)
            self.assertFalse(report["original_cv"]["modified"])
            self.assertTrue(report["proposed_diff"]["requires_candidate_approval"])
            self.assertEqual(report["requirement_alignment"][1]["assessment"], "transferable")
            self.assertIn("not promise universal ATS compatibility", report["ats_safety"])
            self.assertTrue(report["privacy_findings"])

    def test_private_report_and_empty_or_poor_extraction_are_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cv_path = root / "scanned.txt"
            cv_path.write_text("", encoding="utf-8")
            report = CV_REVIEW.review_cv(cv_path, self.matrix)
            self.assertEqual(report["text_extraction"]["quality"], "empty")
            output = root / "private" / "review.json"
            CV_REVIEW.write_private_report(output, report)
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            self.assertEqual(output.parent.stat().st_mode & 0o777, 0o700)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["original_cv"]["modified"], False)


if __name__ == "__main__":
    unittest.main()
