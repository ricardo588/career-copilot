from __future__ import annotations

import importlib.util
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "skills/career-copilot/scripts/workspace_backup.py"
SPEC = importlib.util.spec_from_file_location("workspace_backup_under_test", MODULE_PATH)
assert SPEC and SPEC.loader
backup = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = backup
SPEC.loader.exec_module(backup)
SKILL_DIR = MODULE_PATH.parents[1]


@unittest.skipUnless(__import__("shutil").which("age") and __import__("shutil").which("age-keygen"), "age is required")
class WorkspaceBackupTests(unittest.TestCase):
    def keypair(self, root: Path) -> tuple[Path, str]:
        identity = root / "identity.txt"
        subprocess.run(["age-keygen", "-o", str(identity)], check=True, capture_output=True, text=True)
        recipient = subprocess.run(["age-keygen", "-y", str(identity)], check=True, capture_output=True, text=True).stdout.strip()
        identity.chmod(0o600)
        return identity, recipient

    def test_real_age_round_trip_verify_restore_and_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            (source / "notes").mkdir(parents=True)
            (source / "profile.yaml").write_text("synthetic: true\n", encoding="utf-8")
            (source / "notes" / "draft.md").write_text("synthetic draft\n", encoding="utf-8")
            identity, recipient = self.keypair(root)
            archive = root / "backup.age"
            created = backup.backup_create(source=source, output=archive, skill_dir=SKILL_DIR, age_bin="age", recipient=recipient, passphrase_mode=False, overwrite=False)
            self.assertEqual(2, created["files"])
            verified = backup.backup_verify(archive=archive, age_bin="age", identities=[identity], passphrase_mode=False)
            self.assertEqual(2, verified["files"])
            target = root / "restored"
            restored = backup.backup_restore(archive=archive, target=target, skill_dir=SKILL_DIR, age_bin="age", identities=[identity], passphrase_mode=False)
            self.assertEqual(2, restored["files"])
            self.assertEqual("synthetic draft\n", (target / "notes" / "draft.md").read_text(encoding="utf-8"))
            self.assertEqual(0o700, stat.S_IMODE(target.stat().st_mode))
            self.assertEqual(0o700, stat.S_IMODE((target / "notes").stat().st_mode))
            self.assertEqual(0o600, stat.S_IMODE((target / "profile.yaml").stat().st_mode))

    def test_rejects_workspace_symlink_and_nonempty_restore_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            (source / "link").symlink_to(root)
            identity, recipient = self.keypair(root)
            with self.assertRaisesRegex(backup.BackupError, "symlinks"):
                backup.backup_create(source=source, output=root / "backup.age", skill_dir=SKILL_DIR, age_bin="age", recipient=recipient, passphrase_mode=False, overwrite=False)
            (source / "link").unlink()
            (source / "file.txt").write_text("x", encoding="utf-8")
            archive = root / "backup.age"
            backup.backup_create(source=source, output=archive, skill_dir=SKILL_DIR, age_bin="age", recipient=recipient, passphrase_mode=False, overwrite=False)
            target = root / "target"
            target.mkdir()
            (target / "keep.txt").write_text("keep", encoding="utf-8")
            with self.assertRaisesRegex(backup.BackupError, "new or empty"):
                backup.backup_restore(archive=archive, target=target, skill_dir=SKILL_DIR, age_bin="age", identities=[identity], passphrase_mode=False)


if __name__ == "__main__":
    unittest.main()
