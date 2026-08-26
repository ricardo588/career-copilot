#!/usr/bin/env python3
"""Create a private Career Copilot workspace from bundled templates."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path


TEMPLATE_MAP = {
    "candidate-profile.template.yaml": "profile.yaml",
    "rules.template.yaml": "rules.yaml",
    "tracker.template.csv": "tracker.csv",
}

PRIVATE_README = """# Private Career Copilot workspace

This directory belongs to the candidate. It may contain personal data.

- Do not commit it to the Career Copilot distribution repository.
- Keep credentials outside these files.
- Back it up only to a destination you trust.
- External actions still require the permissions recorded in profile.yaml.
"""


def bootstrap(workspace: Path, skill_dir: Path) -> tuple[list[Path], list[Path]]:
    workspace = workspace.expanduser().resolve()
    profile_root = skill_dir.resolve().parents[1]
    if workspace == profile_root or profile_root in workspace.parents:
        raise ValueError("private workspace must be outside the Career Copilot profile/distribution directory")
    templates = skill_dir / "templates"
    workspace_was_new = not workspace.exists()
    workspace.mkdir(parents=True, exist_ok=True)
    if workspace_was_new:
        os.chmod(workspace, 0o700)
    (workspace / "notes").mkdir(exist_ok=True)
    (workspace / "applications").mkdir(exist_ok=True)

    created: list[Path] = []
    skipped: list[Path] = []
    for source_name, target_name in TEMPLATE_MAP.items():
        source = templates / source_name
        target = workspace / target_name
        if target.exists():
            skipped.append(target)
            continue
        shutil.copyfile(source, target)
        os.chmod(target, 0o600)
        created.append(target)

    readme = workspace / "README_PRIVATE.md"
    if readme.exists():
        skipped.append(readme)
    else:
        readme.write_text(PRIVATE_README, encoding="utf-8")
        os.chmod(readme, 0o600)
        created.append(readme)

    return created, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, help="Private candidate workspace")
    args = parser.parse_args()

    skill_dir = Path(__file__).resolve().parents[1]
    try:
        created, skipped = bootstrap(Path(args.workspace), skill_dir)
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    for path in created:
        print(f"created: {path}")
    for path in skipped:
        print(f"preserved: {path}")
    print("workspace ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
