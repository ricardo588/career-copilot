#!/usr/bin/env python3
"""Run an opt-in local CV review without modifying the original document."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

DATE_PATTERN = re.compile(r"\b(?:19|20)\d{2}\b")
PHONE_PATTERN = re.compile(r"\+?\d[\d .()\-]{7,}\d")
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_local_text(path: Path) -> str:
    """Extract locally from plain text, DOCX, or PDF with a local pdftotext binary."""
    suffix = path.suffix.casefold()
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="replace")
    if suffix == ".docx":
        with zipfile.ZipFile(path) as archive:
            xml = archive.read("word/document.xml")
        root = ElementTree.fromstring(xml)
        return "\n".join(text.text or "" for text in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"))
    if suffix == ".pdf":
        result = subprocess.run(["pdftotext", str(path), "-"], text=True, capture_output=True, check=False)
        if result.returncode:
            raise ValueError("local PDF extraction failed; install pdftotext or use a locally extracted .txt copy")
        return result.stdout
    raise ValueError("supported CV formats are .pdf, .docx, .txt and .md")


def text_quality(text: str) -> dict[str, Any]:
    printable = sum(character.isprintable() or character in "\n\t" for character in text)
    density = printable / max(1, len(text))
    words = re.findall(r"\w+", text)
    quality = "usable" if len(words) >= 80 and density >= 0.95 else "poor" if words else "empty"
    return {"quality": quality, "characters": len(text), "words": len(words), "printable_ratio": round(density, 3)}


def _line_signals(lines: list[str]) -> dict[str, Any]:
    nonempty = [line.strip() for line in lines if line.strip()]
    header_footer_repeats = sorted({line for line in nonempty if nonempty.count(line) >= 3})
    table_like = [line for line in nonempty if line.count("|") >= 2 or line.count("\t") >= 2]
    very_long = [line for line in nonempty if len(line) > 240]
    columns_likely = len(table_like) >= 3 or len(very_long) >= 3
    critical_sections = ("experience", "employment", "professional experience", "education", "skills", "experiencia", "educación", "habilidades")
    lower = "\n".join(nonempty).casefold()
    missing = [section for section in critical_sections if section in {"experience", "education", "skills"} and section not in lower and not any(alias in lower for alias in critical_sections)]
    return {
        "complexity": "high" if columns_likely else "low",
        "signals": {"table_like_lines": len(table_like), "very_long_lines": len(very_long), "repeated_header_footer_lines": header_footer_repeats[:10]},
        "critical_content_outside_headers_footers": "review_needed" if header_footer_repeats else "no_repeated_header_footer_signal",
        "missing_expected_sections": missing,
    }


def _consistency(text: str) -> dict[str, Any]:
    years = [int(value) for value in DATE_PATTERN.findall(text)]
    issues: list[str] = []
    if years and min(years) < 1950:
        issues.append("date before 1950; verify extraction or chronology")
    if any(later < earlier for earlier, later in zip(years, years[1:])):
        issues.append("non-chronological year sequence; verify whether the CV uses reverse chronology")
    title_lines = [line.strip() for line in text.splitlines() if re.search(r"\b(manager|director|lead|architect|gerente|director|líder)\b", line, re.I)]
    return {"years_found": years, "potential_date_issue": issues, "title_lines_for_candidate_review": title_lines[:20]}


def _privacy_findings(text: str) -> list[dict[str, str]]:
    findings = []
    if EMAIL_PATTERN.search(text):
        findings.append({"kind": "contact_email", "recommendation": "Keep only if the candidate wants it in this exact CV version."})
    if PHONE_PATTERN.search(text):
        findings.append({"kind": "phone_number", "recommendation": "Keep only if the candidate wants it in this exact CV version."})
    return findings


def _matrix_alignment(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    aligned = []
    for item in matrix.get("requirements", []) if isinstance(matrix, dict) else []:
        if not isinstance(item, dict):
            continue
        assessment = str(item.get("assessment", "unknown"))
        if assessment not in {"direct", "transferable", "gap", "unknown"}:
            raise ValueError("requirement matrix contains an unsupported assessment")
        aligned.append({
            "requirement_id": item.get("id"),
            "requirement": item.get("requirement"),
            "assessment": assessment,
            "evidence_refs": [evidence.get("ref") for evidence in item.get("direct_evidence", []) if isinstance(evidence, dict)],
            "transferability": item.get("transferability") if assessment == "transferable" else None,
            "review_action": {
                "direct": "Candidate may choose a truthful, already-supported CV example.",
                "transferable": "Do not claim direct experience; candidate must approve any contextual wording.",
                "gap": "Do not conceal or fabricate this gap; decide whether to address it in interview preparation.",
                "unknown": "Ask for evidence before proposing any CV content.",
            }[assessment],
        })
    return aligned


def review_cv(cv_path: Path, matrix: dict[str, Any]) -> dict[str, Any]:
    path = cv_path.expanduser().resolve()
    if not path.is_file():
        raise ValueError("CV file does not exist")
    text = extract_local_text(path)
    quality = text_quality(text)
    layout = _line_signals(text.splitlines())
    alignment = _matrix_alignment(matrix)
    suggestions = [
        {
            "requirement_id": item["requirement_id"],
            "kind": "candidate_review_only",
            "before": None,
            "after": None,
            "reason": item["review_action"],
            "evidence_refs": item["evidence_refs"],
        }
        for item in alignment if item["assessment"] in {"direct", "transferable"}
    ]
    return {
        "schema_version": 1,
        "reviewed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "original_cv": {"path": str(path), "sha256": sha256_file(path), "modified": False},
        "text_extraction": quality,
        "layout": layout,
        "consistency": _consistency(text),
        "privacy_findings": _privacy_findings(text),
        "requirement_alignment": alignment,
        "proposed_diff": {
            "requires_candidate_approval": True,
            "original_modified": False,
            "unified_diff": "",
            "changes": suggestions,
            "note": "No automatic CV rewrite was made. Each proposed item is review-only and must remain grounded in the cited requirement-matrix evidence.",
        },
        "ats_safety": "This local review checks extraction and layout signals only. It does not promise universal ATS compatibility, rejection percentages, or keyword-stuffing outcomes.",
    }


def write_private_report(path: Path, report: dict[str, Any]) -> None:
    destination = path.expanduser().resolve()
    for parent in (destination.parent, *destination.parents):
        if (parent / ".git").exists():
            raise ValueError("CV review report must be outside a Git repository")
    destination.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(destination.parent, 0o700)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, destination)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cv", required=True, help="Candidate-approved local CV path")
    parser.add_argument("--matrix", required=True, help="Private requirement matrix JSON")
    parser.add_argument("--output", required=True, help="Private review report JSON")
    args = parser.parse_args()
    try:
        matrix = json.loads(Path(args.matrix).expanduser().read_text(encoding="utf-8"))
        if not isinstance(matrix, dict):
            raise ValueError("matrix must be a JSON object")
        report = review_cv(Path(args.cv), matrix)
        write_private_report(Path(args.output), report)
        print(json.dumps({"written": str(Path(args.output).expanduser()), "modified_original": False}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
