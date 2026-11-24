import contextlib
import hashlib
import importlib.util
import io
import json
import os
import socket
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "career-copilot" / "scripts" / "hunter_process_review.py"


HEADERS = [
    "No", "Empresa", "Puesto", "Fuente", "Estatus", "Resultado",
    "Fecha de ultimo estatus", "Notas", "URL", "Contacto en la empresa",
]
MAPPING = """schema_version: 1
fields:
  business_id: \"No\"
  company: \"Empresa\"
  role: \"Puesto\"
  source: \"Fuente\"
  status: \"Estatus\"
  result: \"Resultado\"
  status_date: \"Fecha de ultimo estatus\"
  notes: \"Notas\"
  canonical_url: \"URL\"
  contact: \"Contacto en la empresa\"
status_groups:
  terminal:
    - \"98. Rechazada\"
  active:
    - \"10. Preparar\"
  review: []
review_thresholds:
  status_age_days: 14
"""


def load_module():
    spec = importlib.util.spec_from_file_location("hunter_process_review", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def snapshot(*rows):
    return {
        "metadata": {"kind": "google_sheets_snapshot", "retrieved_at": "2026-11-22T00:00:00Z", "read_only": True},
        "headers": HEADERS,
        "rows": list(rows),
    }


def row(physical_row, **values):
    return {"physical_row": physical_row, "values": values}


class HunterProcessReviewTests(unittest.TestCase):
    def test_cli_rejects_input_outside_workspace_or_under_symlink(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root, workspace = Path(temporary), Path(temporary) / "workspace"
            workspace.mkdir()
            outside_snapshot = root / "outside.json"
            mapping = workspace / "mapping.yaml"
            outside_snapshot.write_text(json.dumps(snapshot()), encoding="utf-8")
            mapping.write_text(MAPPING, encoding="utf-8")
            arguments = ["report", "--snapshot", str(outside_snapshot), "--mapping", str(mapping), "--workspace", str(workspace), "--as-of", "2026-11-23", "--output-json", str(workspace / "report.json"), "--output-md", str(workspace / "report.md")]
            self.assertEqual(module.main(arguments), 2)
            linked = workspace / "input.json"
            linked.symlink_to(outside_snapshot)
            arguments[2] = str(linked)
            self.assertEqual(module.main(arguments), 2)
            self.assertFalse((workspace / "report.json").exists())

    def test_cli_rejects_workspace_that_becomes_git_before_output(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "workspace"; workspace.mkdir()
            snapshot_path, mapping_path = workspace / "input.json", workspace / "mapping.yaml"
            snapshot_path.write_text(json.dumps(snapshot()), encoding="utf-8"); mapping_path.write_text(MAPPING, encoding="utf-8")
            original = module._secure_parent_fd
            def create_git(*args):
                result = original(*args)
                (workspace / ".git").mkdir(exist_ok=True)
                return result
            module._secure_parent_fd = create_git
            try:
                arguments = ["report", "--snapshot", str(snapshot_path), "--mapping", str(mapping_path), "--workspace", str(workspace), "--as-of", "2026-11-23", "--output-json", str(workspace / "report.json"), "--output-md", str(workspace / "report.md")]
                self.assertEqual(module.main(arguments), 2)
                self.assertFalse((workspace / "report.json").exists())
                self.assertFalse((workspace / "report.md").exists())
            finally:
                module._secure_parent_fd = original

    def test_report_is_read_only_deterministic_and_uses_no_network_or_processes(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "private-workspace"
            workspace.mkdir()
            snapshot_path = workspace / "input.json"
            mapping_path = workspace / "mapping.yaml"
            output_json = workspace / "reports" / "review.json"
            output_md = workspace / "reports" / "review.md"
            source = snapshot(
                row(2, **{
                    "No": "1", "Empresa": "Example Co", "Puesto": "Director",
                    "Fuente": "Referral", "Estatus": "10. Preparar", "Resultado": "",
                    "Fecha de ultimo estatus": "01/nov/2026", "Notas": "Synthetic note",
                    "URL": "https://jobs.example.test/roles/1?utm_source=test", "Contacto en la empresa": "Example Person",
                }),
                row(3, **{
                    "No": "2", "Empresa": "Example Co", "Puesto": "Director",
                    "Fuente": "", "Estatus": "unknown", "Resultado": "",
                    "Fecha de ultimo estatus": "not-a-date", "Notas": "",
                    "URL": "https://jobs.example.test/roles/1?tracking=abc", "Contacto en la empresa": "",
                }),
            )
            snapshot_path.write_text(json.dumps(source), encoding="utf-8")
            mapping_path.write_text(MAPPING, encoding="utf-8")
            before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in (snapshot_path, mapping_path)}
            guarded = mock.Mock(side_effect=AssertionError("network or process use is forbidden"))
            with mock.patch.object(socket, "socket", guarded), mock.patch("subprocess.run", guarded), mock.patch("subprocess.Popen", guarded):
                result = module.main([
                    "report", "--snapshot", str(snapshot_path), "--mapping", str(mapping_path),
                    "--workspace", str(workspace), "--as-of", "2026-11-23",
                    "--output-json", str(output_json), "--output-md", str(output_md),
                ])
            self.assertEqual(result, 0)
            self.assertFalse(guarded.called)
            self.assertEqual(before, {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in (snapshot_path, mapping_path)})
            report = json.loads(output_json.read_text(encoding="utf-8"))
            self.assertEqual(report["safety"], {
                "external_actions": 0, "network_requests": 0, "input_mutated": False, "output_schema_valid": True,
            })
            self.assertEqual(report["summary"]["rows"], 2)
            self.assertEqual(report["integrity"]["unclassified_statuses"], ["unknown"])
            self.assertEqual(len(report["identity_risks"]["duplicate_canonical_urls"]), 1)
            self.assertEqual(report["evidence_quality"]["contact_signals_unverified"], 1)
            self.assertIn({"opportunity_id": "1", "reason": "status_review_due"}, report["prioritized_reviews"])
            self.assertEqual(report["snapshot_sha256"], hashlib.sha256(snapshot_path.read_bytes()).hexdigest())
            self.assertEqual(stat.S_IMODE(output_json.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(output_md.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(output_json.parent.stat().st_mode), 0o700)

    def test_packet_rejects_ambiguous_id_without_creating_outputs(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "private-workspace"
            workspace.mkdir()
            snapshot_path = workspace / "input.json"
            mapping_path = workspace / "mapping.yaml"
            output_json = workspace / "reports" / "packet.json"
            output_md = workspace / "reports" / "packet.md"
            source = snapshot(
                row(2, **{"No": "1", "Empresa": "Example One", "Puesto": "Director", "Fuente": "Direct", "Estatus": "10. Preparar", "Resultado": "", "Fecha de ultimo estatus": "2026-11-01", "Notas": "", "URL": "https://jobs.example.test/1", "Contacto en la empresa": ""}),
                row(3, **{"No": "1", "Empresa": "Example Two", "Puesto": "Director", "Fuente": "Direct", "Estatus": "10. Preparar", "Resultado": "", "Fecha de ultimo estatus": "2026-11-01", "Notas": "", "URL": "https://jobs.example.test/2", "Contacto en la empresa": ""}),
            )
            snapshot_path.write_text(json.dumps(source), encoding="utf-8")
            mapping_path.write_text(MAPPING, encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                result = module.main([
                    "packet", "--snapshot", str(snapshot_path), "--mapping", str(mapping_path),
                    "--workspace", str(workspace), "--as-of", "2026-11-23", "--opportunity-id", "1",
                    "--output-json", str(output_json), "--output-md", str(output_md),
                ])
            self.assertEqual(result, 2)
            self.assertFalse(output_json.exists())
            self.assertFalse(output_md.exists())

    def test_packet_preserves_snapshot_facts_and_keeps_human_path_authorization_separate(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "private-workspace"
            workspace.mkdir()
            snapshot_path = workspace / "input.json"
            mapping_path = workspace / "mapping.yaml"
            context_path = workspace / "context.json"
            output_json = workspace / "reports" / "packet.json"
            output_md = workspace / "reports" / "packet.md"
            source = snapshot(row(2, **{
                "No": "7", "Empresa": "Example Co", "Puesto": "Director", "Fuente": "Direct",
                "Estatus": "10. Preparar", "Resultado": "", "Fecha de ultimo estatus": "2026-11-01",
                "Notas": "Synthetic", "URL": "https://jobs.example.test/7", "Contacto en la empresa": "Example Person",
            }))
            context = {
                "schema_version": 1,
                "vacancy_evidence": {"source_url": "https://example.test/official-job", "verified_at": "2026-11-22", "state": "confirmed"},
                "requirement_matrix": {"ref": "private/opaque-ref", "state": "confirmed"},
                "human_path": {"retrieved_at": "2026-11-22", "relationships": [{"name": "Example Person", "current_company": "Example Co", "current_role": "Director", "source_url": "https://example.test/person", "confidence": "confirmed", "authorization": {"contact": False, "reference": False, "referral": False, "follow_up": False, "introduce": False}}]},
            }
            snapshot_path.write_text(json.dumps(source), encoding="utf-8")
            mapping_path.write_text(MAPPING, encoding="utf-8")
            context_path.write_text(json.dumps(context), encoding="utf-8")
            result = module.main([
                "packet", "--snapshot", str(snapshot_path), "--mapping", str(mapping_path), "--context", str(context_path),
                "--workspace", str(workspace), "--as-of", "2026-11-23", "--opportunity-id", "7",
                "--output-json", str(output_json), "--output-md", str(output_md),
            ])
            self.assertEqual(result, 0)
            packet = json.loads(output_json.read_text(encoding="utf-8"))
            self.assertEqual(packet["opportunity"]["No"], "7")
            self.assertEqual(packet["additional_evidence"]["human_path"]["state"], "confirmed")
            self.assertTrue(packet["additional_evidence"]["human_path"]["authorization_not_granted"])
            self.assertEqual(packet["recommendation"], "prepare_decision_material")
            self.assertIn("Borrador/revisión solamente", output_md.read_text(encoding="utf-8"))

    def test_rejects_symlinked_workspace_and_output_ancestor(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target"
            target.mkdir()
            workspace_link = root / "workspace-link"
            workspace_link.symlink_to(target, target_is_directory=True)
            with self.assertRaisesRegex(module.ReviewError, "symlink"):
                module.private_workspace(str(workspace_link / "new-workspace"))

            workspace = root / "workspace"
            workspace.mkdir()
            alias = workspace / "alias"
            alias.symlink_to(workspace, target_is_directory=True)
            with self.assertRaisesRegex(module.ReviewError, "symlink"):
                module.private_output(workspace, str(alias / "report.json"))

    def test_mapping_rejects_reused_headers(self):
        module = load_module()
        invalid = MAPPING.replace('  role: "Puesto"', '  role: "Empresa"')
        with self.assertRaisesRegex(module.ReviewError, "unique"):
            module.parse_mapping(invalid)

    def test_mapping_rejects_repeated_statuses_and_negative_review_age(self):
        module = load_module()
        repeated_status = MAPPING.replace('  review: []', '  review:\n    - "10. Preparar"')
        with self.assertRaisesRegex(module.ReviewError, "multiple status groups"):
            module.parse_mapping(repeated_status)
        negative_threshold = MAPPING.replace('  status_age_days: 14', '  status_age_days: -1')
        with self.assertRaisesRegex(module.ReviewError, "non-negative"):
            module.parse_mapping(negative_threshold)

    def test_mapping_rejects_duplicate_and_unknown_contract_keys(self):
        module = load_module()
        duplicate_field = MAPPING.replace('  company: "Empresa"', '  company: "Empresa"\n  business_id: "No"')
        with self.assertRaisesRegex(module.ReviewError, "duplicate mapping key"):
            module.parse_mapping(duplicate_field)
        duplicate_group = MAPPING.replace('  active:\n    - "10. Preparar"', '  active:\n    - "10. Preparar"\n  active: []')
        with self.assertRaisesRegex(module.ReviewError, "duplicate mapping key"):
            module.parse_mapping(duplicate_group)
        unknown_threshold = MAPPING.replace('  status_age_days: 14', '  status_age_days: 14\n  unexpected: 1')
        with self.assertRaisesRegex(module.ReviewError, "review_thresholds"):
            module.parse_mapping(unknown_threshold)

    def test_workspace_cannot_be_an_ancestor_of_the_distribution(self):
        module = load_module()
        with self.assertRaisesRegex(module.ReviewError, "cannot contain"):
            module.private_workspace(str(ROOT.parent))

    def test_existing_markdown_output_blocks_before_json_is_written(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "workspace"
            workspace.mkdir()
            json_path = workspace / "reports" / "review.json"
            markdown_path = workspace / "reports" / "review.md"
            markdown_path.parent.mkdir()
            markdown_path.write_text("existing", encoding="utf-8")
            with self.assertRaisesRegex(module.ReviewError, "output exists"):
                module.atomic_pair(workspace, json_path, markdown_path, {"summary": {"rows": 0}, "as_of": "2026-11-23", "snapshot_sha256": "x"}, False)
            self.assertFalse(json_path.exists())
            self.assertEqual(markdown_path.read_text(encoding="utf-8"), "existing")

    def test_open_workspace_descriptor_survives_ancestor_symlink_replacement(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            parent = root / "parent"
            workspace_path = parent / "workspace"
            workspace_path.mkdir(parents=True)
            outside = root / "outside"
            outside.mkdir()
            workspace, descriptor = module.open_private_workspace(str(workspace_path))
            moved_parent = root / "moved-parent"
            parent.rename(moved_parent)
            parent.symlink_to(outside, target_is_directory=True)
            try:
                module.atomic_pair(
                    workspace, workspace / "reports" / "review.json", workspace / "reports" / "review.md",
                    {"summary": {"rows": 0}, "as_of": "2026-11-23", "snapshot_sha256": "x"}, False, descriptor,
                )
            finally:
                os.close(descriptor)
            self.assertTrue((moved_parent / "workspace" / "reports" / "review.json").is_file())
            self.assertFalse((outside / "workspace" / "reports" / "review.json").exists())


if __name__ == "__main__":
    unittest.main()
