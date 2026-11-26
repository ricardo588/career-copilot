from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "plugin.json"
SCHEMA_URL = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
FORBIDDEN_PORTABLE_FILES = ("mcp.json", "plugin.yaml", "__init__.py")
FORBIDDEN_MANIFEST_KEYS = {
    "capabilities",
    "config_schema",
    "requires_env",
    "telemetry",
    "tools",
    "hooks",
    "middleware",
    "mcp",
    "lifecycle",
    "cron",
}


class PluginManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_portable_manifest_identity(self) -> None:
        self.assertEqual(SCHEMA_URL, self.manifest["$schema"])
        self.assertEqual("career-copilot", self.manifest["name"])
        self.assertEqual("0.16.0", self.manifest["version"])
        self.assertEqual("Apache-2.0", self.manifest["license"])
        self.assertTrue(self.manifest["description"])

    def test_skill_tree_is_reused_directly(self) -> None:
        self.assertTrue((ROOT / "skills/career-copilot/SKILL.md").is_file())
        self.assertFalse((ROOT / "plugin/skills").exists())

    def test_no_declared_capabilities_or_runtime_entrypoints(self) -> None:
        self.assertTrue(FORBIDDEN_MANIFEST_KEYS.isdisjoint(self.manifest))
        for relative in FORBIDDEN_PORTABLE_FILES:
            self.assertFalse((ROOT / relative).exists(), relative)


if __name__ == "__main__":
    unittest.main()
