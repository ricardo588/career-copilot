from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "skills/career-copilot/scripts/requirement_matrix.py"
SPEC = importlib.util.spec_from_file_location("requirement_matrix_under_test", MODULE_PATH)
assert SPEC and SPEC.loader
MATRIX = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MATRIX)


class RequirementMatrixTests(unittest.TestCase):
    def setUp(self):
        self.profile = {
            "profile": {
                "strengths": ["Enterprise cloud program delivery"],
                "verified_evidence": ["Led a 14-month Oracle cloud migration for 1,000 critical workloads"],
                "gaps": ["Hands-on acquiring rails"],
            }
        }
        self.vacancy = {
            "company": "Synthetic Co",
            "title": "Program Director",
            "canonical_url": "https://jobs.example.invalid/123",
            "requirements": [
                "Oracle cloud migration delivery",
                "Acquiring rails expertise",
                "Enterprise stakeholder management",
                "Quantum computing experience",
            ],
        }

    def test_matrix_labels_direct_transferable_gap_and_unknown_with_sources(self):
        matrix = MATRIX.build_matrix(self.profile, self.vacancy)
        assessments = [item["assessment"] for item in matrix["requirements"]]
        self.assertEqual(assessments, ["direct", "gap", "transferable", "unknown"])
        direct = matrix["requirements"][0]
        self.assertEqual(direct["posting_source"]["url"], self.vacancy["canonical_url"])
        self.assertEqual(direct["direct_evidence"][0]["ref"], "profile.verified_evidence[0]")
        transferable = matrix["requirements"][2]
        self.assertEqual(transferable["transferability"]["label"], "analysis_not_direct_experience")
        self.assertIsNone(transferable["gap"])
        self.assertIsNone(matrix["requirements"][3]["direct_evidence"][0:] or None)

    def test_matrix_refresh_detects_changed_canonical_source_without_losing_evidence_links(self):
        first = MATRIX.build_matrix(self.profile, self.vacancy)
        refreshed_vacancy = dict(self.vacancy)
        refreshed_vacancy["requirements"] = list(self.vacancy["requirements"])
        refreshed = MATRIX.build_matrix(self.profile, refreshed_vacancy, prior=first)
        self.assertFalse(any(item["source_changed"] for item in refreshed["requirements"]))
        moved = dict(self.vacancy, canonical_url="https://jobs.example.invalid/456")
        changed = MATRIX.build_matrix(self.profile, moved, prior=first)
        self.assertTrue(all(item["source_changed"] for item in changed["requirements"]))
        self.assertEqual(changed["requirements"][0]["direct_evidence"][0]["ref"], "profile.verified_evidence[0]")

    def test_unverified_strength_is_transferable_not_direct_evidence(self):
        profile = {"profile": {"strengths": ["Cloud migration delivery"], "verified_evidence": []}}
        vacancy = {"canonical_url": "https://jobs.example.invalid/only-strength", "requirements": ["Cloud migration delivery"]}
        matrix = MATRIX.build_matrix(profile, vacancy)
        self.assertEqual(matrix["requirements"][0]["assessment"], "transferable")
        self.assertEqual(matrix["requirements"][0]["direct_evidence"], [])

    def test_matrix_excludes_structured_non_job_relevant_requirements(self):
        vacancy = dict(self.vacancy)
        vacancy["requirements"] = [
            "Oracle cloud migration delivery",
            {"text": "women only", "category": "protected_attribute"},
        ]
        matrix = MATRIX.build_matrix(self.profile, vacancy)
        self.assertEqual([item["requirement"] for item in matrix["requirements"]], ["Oracle cloud migration delivery"])
        self.assertEqual(matrix["ignored_non_job_relevant_requirements"], ["women only"])

    def test_requires_canonical_posting_and_writes_private_permissions(self):
        with self.assertRaisesRegex(ValueError, "canonical_url"):
            MATRIX.build_matrix(self.profile, {"requirements": ["anything"]})
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "private" / "matrix.json"
            matrix = MATRIX.build_matrix(self.profile, self.vacancy)
            MATRIX.atomic_write_json(output, matrix)
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            self.assertEqual(output.parent.stat().st_mode & 0o777, 0o700)


if __name__ == "__main__":
    unittest.main()
