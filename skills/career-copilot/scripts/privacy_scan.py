#!/usr/bin/env python3
"""Scan a Career Copilot bundle for likely private data and secrets."""

from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass
from pathlib import Path


TEXT_SUFFIXES = {".md", ".txt", ".yaml", ".yml", ".json", ".csv", ".py", ".toml"}
SKIP_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache"}
SELF = Path(__file__).resolve()


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    kind: str
    preview: str


def _patterns() -> list[tuple[str, re.Pattern[str]]]:
    return [
        ("personal email", re.compile(r"\b[A-Z0-9._%+-]+@(?!example\.(?:com|org|net)\b)[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)),
        ("macOS home path", re.compile(r"/Users/[A-Za-z0-9._-]+")),
        ("Linux home path", re.compile(r"/home/[A-Za-z0-9._-]+")),
        ("Windows home path", re.compile(r"[A-Za-z]:\\\\Users\\\\[A-Za-z0-9._-]+", re.I)),
        ("spreadsheet identifier", re.compile(r"docs\.google\.com/spreadsheets/d/[A-Za-z0-9_-]{20,}")),
        ("private key", re.compile("-----BEGIN" + r" [A-Z ]*PRIVATE KEY-----")),
        ("GitHub token", re.compile(r"gh" + r"[opsu]_[A-Za-z0-9]{20,}")),
        ("generic secret assignment", re.compile(r"(?i)\b(api[_-]?key|access[_-]?token|client[_-]?secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{12,}")),
    ]


def _private_markers() -> list[str]:
    raw = os.environ.get("PRIVATE_MARKERS", "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def scan(root: Path, markers: list[str] | None = None) -> list[Finding]:
    root = root.resolve()
    findings: list[Finding] = []
    marker_list = markers if markers is not None else _private_markers()

    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if path.resolve() == SELF or any(part in SKIP_DIRS for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            for kind, pattern in _patterns():
                if pattern.search(line):
                    findings.append(Finding(path, line_number, kind, line.strip()[:160]))
            folded = line.casefold()
            for marker in marker_list:
                if marker.casefold() in folded:
                    findings.append(Finding(path, line_number, "private marker", line.strip()[:160]))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=str(Path(__file__).resolve().parents[3]))
    args = parser.parse_args()

    findings = scan(Path(args.root))
    if findings:
        for finding in findings:
            print(f"{finding.path}:{finding.line}: {finding.kind}: {finding.preview}")
        print(f"privacy scan failed: {len(findings)} finding(s)")
        return 1
    print("privacy scan passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
