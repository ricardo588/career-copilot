import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "career-copilot" / "scripts" / "provider_selection.py"


def load_module():
    spec = importlib.util.spec_from_file_location("provider_selection_under_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def profile(countries=None, modes=None, employment_types=None):
    return {
        "profile": {"target_roles": ["Software Engineering Director"], "target_seniority": ["Director"], "target_industries": ["Technology"]},
        "constraints": {"countries": countries or ["Mexico", "United States"], "locations": [], "work_modes": modes or ["Remote"], "employment_types": employment_types or ["Full time"]},
    }


class ProviderSelectionTests(unittest.TestCase):
    def test_selection_is_local_and_distinguishes_integrated_from_coverage_only(self):
        module = load_module()
        result = module.select_providers(profile(), {"search": {"selected_job_portals": []}})
        selected = {item["id"]: item for item in result["selected"]}
        self.assertEqual(result["external_actions"], 0)
        self.assertEqual(result["network_requests"], 0)
        self.assertEqual(selected["greenhouse_public_board"]["acquisition_state"], "integrated_read_only")
        self.assertEqual(selected["lever_public_postings"]["acquisition_state"], "integrated_read_only")
        self.assertEqual(selected["occ_mundial"]["acquisition_state"], "coverage_only")
        self.assertEqual(selected["we_work_remotely"]["acquisition_state"], "coverage_only")
        self.assertEqual(selected["the_ladders"]["acquisition_state"], "coverage_only")
        self.assertTrue(all(item["explicit_action_required"] for item in result["selected"]))

    def test_latin_america_employment_and_rules_change_selection_and_preserve_contract(self):
        module = load_module()
        result = module.select_providers(profile(countries=["Ecuador", "Mexico"], modes=[], employment_types=["Freelance"]), {"search": {"selected_job_portals": ["remoteok"]}})
        selected = {item["id"] for item in result["selected"]}
        self.assertIn("get_on_board", selected)
        self.assertIn("remoteok", selected)
        self.assertIn("we_work_remotely", selected)
        self.assertTrue(result["not_selected"])
        self.assertIn("unknowns", result)

    def test_cli_writes_only_inside_private_workspace_and_preserves_inputs(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "workspace"
            workspace.mkdir()
            profile_path, rules_path, output_path = workspace / "profile.json", workspace / "rules.json", workspace / "selection.json"
            profile_path.write_text(json.dumps(profile()), encoding="utf-8")
            rules_path.write_text(json.dumps({"search": {"selected_job_portals": []}}), encoding="utf-8")
            before = {path: path.read_bytes() for path in (profile_path, rules_path)}
            arguments = ["--workspace", str(workspace), "--profile", str(profile_path), "--rules", str(rules_path), "--output", str(output_path)]
            self.assertEqual(module.main(arguments), 0)
            self.assertEqual(before, {path: path.read_bytes() for path in (profile_path, rules_path)})
            self.assertEqual(module.main(arguments), 2)

    def test_cli_rejects_distribution_git_and_symlink_paths_before_writing(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root, workspace = Path(temporary), Path(temporary) / "workspace"
            workspace.mkdir()
            profile_path, rules_path = workspace / "profile.json", workspace / "rules.json"
            profile_path.write_text(json.dumps(profile()), encoding="utf-8")
            rules_path.write_text("{}", encoding="utf-8")
            external = root / "outside.json"
            args = ["--workspace", str(workspace), "--profile", str(profile_path), "--rules", str(rules_path), "--output", str(external)]
            self.assertEqual(module.main(args), 2)
            self.assertFalse(external.exists())
            git = root / "git"; git.mkdir(); (git / ".git").mkdir()
            self.assertEqual(module.main(["--workspace", str(workspace), "--profile", str(git / "profile.json"), "--rules", str(rules_path), "--output", str(workspace / "out.json")]), 2)
            outside = root / "outside"; outside.mkdir()
            (workspace / "link").symlink_to(outside, target_is_directory=True)
            self.assertEqual(module.main(["--workspace", str(workspace), "--profile", str(profile_path), "--rules", str(rules_path), "--output", str(workspace / "link" / "out.json")]), 2)
            self.assertFalse((outside / "out.json").exists())

    def test_secure_writer_rejects_preexisting_temp_symlink(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root, workspace = Path(temporary), Path(temporary) / "workspace"
            workspace.mkdir()
            profile_path, rules_path, output_path = workspace / "profile.json", workspace / "rules.json", workspace / "selection.json"
            profile_path.write_text(json.dumps(profile()), encoding="utf-8")
            rules_path.write_text("{}", encoding="utf-8")
            outside = root / "outside.json"
            original_urandom = module.os.urandom
            module.os.urandom = lambda size: b"x" * size
            temporary = workspace / f".selection.json.{'78' * 12}.tmp"
            temporary.symlink_to(outside)
            try:
                self.assertEqual(module.main(["--workspace", str(workspace), "--profile", str(profile_path), "--rules", str(rules_path), "--output", str(output_path)]), 2)
            finally:
                module.os.urandom = original_urandom
            self.assertFalse(outside.exists())
            self.assertFalse(output_path.exists())

    def test_cli_rejects_input_ancestor_replaced_after_preflight(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root, workspace = Path(temporary), Path(temporary) / "workspace"
            records, outside = workspace / "records", root / "outside"
            records.mkdir(parents=True); outside.mkdir()
            profile_path, rules_path = records / "profile.json", workspace / "rules.json"
            profile_path.write_text(json.dumps(profile()), encoding="utf-8")
            rules_path.write_text("{}", encoding="utf-8")
            (outside / "profile.json").write_text("{}", encoding="utf-8")
            original = module.private_input
            calls = 0

            def replace_after_validation(raw, selected_workspace, label):
                nonlocal calls
                result = original(raw, selected_workspace, label)
                calls += 1
                if calls == 1:
                    os.replace(records, workspace / "records-original")
                    records.symlink_to(outside, target_is_directory=True)
                return result

            module.private_input = replace_after_validation
            try:
                arguments = ["--workspace", str(workspace), "--profile", str(profile_path), "--rules", str(rules_path), "--output", str(workspace / "selection.json")]
                self.assertEqual(module.main(arguments), 2)
                self.assertFalse((workspace / "selection.json").exists())
            finally:
                module.private_input = original

    def test_cli_removes_output_when_workspace_becomes_git_during_write(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "workspace"; workspace.mkdir()
            profile_path, rules_path, output_path = workspace / "profile.json", workspace / "rules.json", workspace / "selection.json"
            profile_path.write_text(json.dumps(profile()), encoding="utf-8"); rules_path.write_text("{}", encoding="utf-8")
            original = module._secure_parent_fd
            def create_git(*args):
                result = original(*args)
                (workspace / ".git").mkdir(exist_ok=True)
                return result
            module._secure_parent_fd = create_git
            try:
                self.assertEqual(module.main(["--workspace", str(workspace), "--profile", str(profile_path), "--rules", str(rules_path), "--output", str(output_path)]), 2)
                self.assertFalse(output_path.exists())
            finally:
                module._secure_parent_fd = original


if __name__ == "__main__":
    unittest.main()
