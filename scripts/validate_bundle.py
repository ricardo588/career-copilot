#!/usr/bin/env python3
"""Validate the Career Copilot distribution before commit or release."""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "distribution.yaml",
    "SOUL.md",
    "config.yaml",
    ".gitignore",
    "README.md",
    "skills/career-copilot/SKILL.md",
    "skills/career-copilot/references/onboarding.md",
    "skills/career-copilot/references/workflow.md",
    "skills/career-copilot/references/evaluation.md",
    "skills/career-copilot/references/requirement-matrix-and-cv-review.md",
    "skills/career-copilot/references/tracker-schema.md",
    "skills/career-copilot/references/privacy-and-actions.md",
    "skills/career-copilot/references/adapters.md",
    "skills/career-copilot/references/demo.md",
    "skills/career-copilot/templates/candidate-profile.template.yaml",
    "skills/career-copilot/templates/rules.template.yaml",
    "skills/career-copilot/templates/tracker.template.csv",
    "skills/career-copilot/scripts/bootstrap_workspace.py",
    "skills/career-copilot/scripts/onboarding.py",
    "skills/career-copilot/scripts/pipeline.py",
    "skills/career-copilot/scripts/run_synthetic_demo.py",
    "skills/career-copilot/scripts/adapters.py",
    "skills/career-copilot/scripts/requirement_matrix.py",
    "skills/career-copilot/scripts/cv_review.py",
    "skills/career-copilot/scripts/privacy_scan.py",
    "skills/career-copilot/examples/synthetic/profile.json",
    "skills/career-copilot/examples/synthetic/rules.json",
    "skills/career-copilot/examples/synthetic/vacancy.json",
    "docs/INSTALL.md",
    "docs/QUICKSTART.md",
    "docs/DEMO.md",
    "docs/ADAPTERS.md",
    "docs/PRIVACY.md",
    "docs/TROUBLESHOOTING.md",
]
FORBIDDEN = [".env", "auth.json", "memories", "sessions", "state.db", "local"]


def load_privacy_module():
    module_path = ROOT / "skills/career-copilot/scripts/privacy_scan.py"
    spec = importlib.util.spec_from_file_location("career_privacy_scan", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load privacy scanner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_frontmatter(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        return [f"missing YAML frontmatter: {path}"]
    frontmatter = text.split("---", 2)[1]
    for field in ("name", "description", "version"):
        if not re.search(rf"(?m)^{field}:\s*\S", frontmatter):
            errors.append(f"missing {field} in {path}")
    match = re.search(r"(?m)^description:\s*(.+)$", frontmatter)
    if match and len(match.group(1).strip().strip('"')) > 60:
        errors.append("skill description must be 60 characters or fewer")
    return errors


def main() -> int:
    errors: list[str] = []
    for relative in REQUIRED:
        if not (ROOT / relative).is_file():
            errors.append(f"missing required file: {relative}")

    for name in FORBIDDEN:
        if (ROOT / name).exists():
            errors.append(f"forbidden runtime/private path in repository: {name}")

    distribution = (ROOT / "distribution.yaml").read_text(encoding="utf-8")
    for key in ("name", "version", "description", "hermes_requires"):
        if not re.search(rf"(?m)^{key}:\s*\S", distribution):
            errors.append(f"distribution.yaml missing {key}")

    errors.extend(validate_frontmatter(ROOT / "skills/career-copilot/SKILL.md"))

    privacy = load_privacy_module()
    for finding in privacy.scan(ROOT):
        relative = finding.path.relative_to(ROOT)
        errors.append(f"privacy: {relative}:{finding.line}: {finding.kind}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"bundle validation failed: {len(errors)} error(s)")
        return 1

    print("bundle validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
