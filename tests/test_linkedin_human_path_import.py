import csv
import importlib.util
import json
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "career-copilot" / "scripts" / "linkedin_human_path_import.py"


def load_module():
    spec = importlib.util.spec_from_file_location("linkedin_human_path_import_under_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class LinkedInHumanPathImportTests(unittest.TestCase):
    def test_stdout_artifact_is_local_read_only_and_keeps_evidence_states_separate(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "workspace"; workspace.mkdir()
            export, vacancy = workspace / "connections.csv", workspace / "vacancy.json"
            with export.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["First Name", "Last Name", "Company"])
                writer.writeheader(); writer.writerow({"First Name": "Ada", "Last Name": "Example", "Company": "Example Co"})
            vacancy.write_text(json.dumps({"company": "Example Co", "recruiter": {"name": "Ada Example"}}), encoding="utf-8")
            before = export.read_bytes()
            guarded = mock.Mock(side_effect=AssertionError("network forbidden"))
            with mock.patch.object(socket, "socket", guarded):
                result = module.run(["--workspace", str(workspace), "--export", str(export), "--vacancy", str(vacancy)])
            self.assertEqual(export.read_bytes(), before)
            self.assertFalse(guarded.called)
            artifact = json.loads(result)
            match = artifact["matches"][0]
            self.assertEqual(match["discovery_state"], "export_match_found")
            self.assertEqual(match["identity_state"], "needs_identity_review")
            self.assertEqual(match["current_employment"], "unverified")
            self.assertEqual(match["authorization"], "not_granted")

    def test_rejects_output_option_and_input_outside_workspace(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root, workspace = Path(temporary), Path(temporary) / "workspace"; workspace.mkdir()
            export, vacancy = root / "connections.csv", workspace / "vacancy.json"
            export.write_text("First Name,Last Name,Company\nAda,Example,Example Co\n", encoding="utf-8")
            vacancy.write_text(json.dumps({"company": "Example Co"}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "within the private workspace"):
                module.run(["--workspace", str(workspace), "--export", str(export), "--vacancy", str(vacancy)])
            with self.assertRaises(SystemExit):
                module.run(["--workspace", str(workspace), "--export", str(vacancy), "--vacancy", str(vacancy), "--output", "nope.json"])

    def test_rejects_git_workspace_and_symlinked_export_without_writing(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root, workspace = Path(temporary), Path(temporary) / "workspace"; workspace.mkdir()
            export, vacancy = workspace / "connections.csv", workspace / "vacancy.json"
            export.write_text("First Name,Last Name,Company\nAda,Example,Example Co\n", encoding="utf-8")
            vacancy.write_text(json.dumps({"company": "Example Co"}), encoding="utf-8")
            outside = root / "outside.csv"; outside.write_bytes(export.read_bytes())
            export.unlink(); export.symlink_to(outside)
            with self.assertRaisesRegex(ValueError, "symlink"):
                module.run(["--workspace", str(workspace), "--export", str(export), "--vacancy", str(vacancy)])
            export.unlink(); export.write_bytes(outside.read_bytes()); (workspace / ".git").mkdir()
            with self.assertRaisesRegex(ValueError, "Git"):
                module.run(["--workspace", str(workspace), "--export", str(export), "--vacancy", str(vacancy)])

    def test_rejects_non_mapping_vacancy_and_extra_csv_fields_without_processes(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "workspace"; workspace.mkdir()
            export, vacancy = workspace / "connections.csv", workspace / "vacancy.json"
            export.write_text("First Name,Last Name,Company\nAda,Example,Example Co,extra\n", encoding="utf-8")
            vacancy.write_text("[]", encoding="utf-8")
            guarded = mock.Mock(side_effect=AssertionError("process forbidden"))
            with mock.patch.object(subprocess, "run", guarded):
                with self.assertRaisesRegex(ValueError, "extra fields"):
                    module.run(["--workspace", str(workspace), "--export", str(export), "--vacancy", str(vacancy)])
            self.assertFalse(guarded.called)
            export.write_text("First Name,Last Name,Company\nAda,Example,Example Co\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "mapping"):
                module.run(["--workspace", str(workspace), "--export", str(export), "--vacancy", str(vacancy)])

    def test_company_only_and_duplicate_matches_remain_manual_review_ambiguities(self):
        module = load_module()
        artifact = module.artifact(b"First Name,Last Name,Company\nAda,Example,Example Co\nAda,Example,Example Co\n", b'{"company":"Example Co"}')
        self.assertEqual(len(artifact["matches"]), 2)
        self.assertEqual(artifact["ambiguities"], ["manual_review_required"])
        self.assertTrue(all(item["identity_state"] == "needs_identity_review" for item in artifact["matches"]))

    def test_rejects_malformed_recruiter_evidence(self):
        module = load_module()
        for vacancy in (b'{"company":"Example Co","recruiter":"invalid"}', b'{"company":"Example Co","recruiter":{"name":4}}'):
            with self.assertRaisesRegex(ValueError, "recruiter"):
                module.artifact(b"First Name,Last Name,Company\nAda,Example,Example Co\n", vacancy)

    def test_rejects_row_missing_required_company_field(self):
        module = load_module()
        with self.assertRaisesRegex(ValueError, "required fields"):
            module.artifact(b"First Name,Last Name,Company\nAda,Example\n", b'{"company":"Example Co"}')


if __name__ == "__main__":
    unittest.main()
