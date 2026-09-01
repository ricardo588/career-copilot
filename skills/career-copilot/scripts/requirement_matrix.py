#!/usr/bin/env python3
"""Build a private, traceable requirement-to-evidence matrix for one vacancy."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

STOPWORDS = {"and", "or", "the", "a", "an", "of", "for", "to", "in", "with", "de", "la", "el", "y", "para", "con"}
VALID_ASSESSMENTS = {"direct", "transferable", "gap", "unknown"}


def tokens(value: Any) -> set[str]:
    if isinstance(value, list):
        value = " ".join(str(item) for item in value)
    return {item for item in re.findall(r"[A-Za-zÀ-ÿ0-9+#.-]+", str(value).casefold()) if len(item) > 1 and item not in STOPWORDS}


def load_document(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise ValueError(f"{path} is not JSON-compatible YAML; install PyYAML for YAML input") from exc
        value = yaml.safe_load(text)
    if not isinstance(value, dict):
        raise ValueError(f"expected a mapping in {path}")
    return value


def private_path(path: Path) -> Path:
    path = path.expanduser().resolve()
    for parent in (path.parent, *path.parents):
        if (parent / ".git").exists():
            raise ValueError("matrix artifacts must be outside a Git repository")
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    return path


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path = private_path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def requirement_text(requirement: Any) -> str:
    if isinstance(requirement, dict):
        return str(requirement.get("text", "")).strip()
    return str(requirement).strip()


def is_non_job_relevant_requirement(requirement: Any) -> bool:
    if not isinstance(requirement, dict):
        return False
    return str(requirement.get("category", "job_requirement")).strip().casefold() in {
        "protected_attribute", "protected_proxy", "non_job_relevant",
    }


def cited_posting(vacancy: dict[str, Any]) -> dict[str, str]:
    url = str(vacancy.get("canonical_url", "")).strip()
    if not url.startswith(("https://", "http://")):
        raise ValueError("requirement matrix requires vacancy.canonical_url from the canonical posting")
    return {"kind": "canonical_posting", "url": url}


def _private_evidence(profile: dict[str, Any], stories: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    candidate = profile.get("profile", {}) if isinstance(profile, dict) else {}
    evidence: list[dict[str, Any]] = []
    for field in ("verified_evidence", "strengths"):
        for index, value in enumerate(candidate.get(field, []) if isinstance(candidate, dict) else []):
            text = str(value).strip()
            if text:
                evidence.append({"kind": "private_profile", "ref": f"profile.{field}[{index}]", "text": text, "verified": field == "verified_evidence"})
    for story in stories:
        if not isinstance(story, dict) or story.get("user_confirmed") is not True:
            continue
        story_id = str(story.get("id", "")).strip()
        confidentiality = str(story.get("confidentiality", "candidate_private")).strip()
        for index, value in enumerate(story.get("results", {}).get("facts", []) if isinstance(story.get("results"), dict) else []):
            text = str(value).strip()
            if text and story_id:
                evidence.append({"kind": "private_story", "ref": f"stories.jsonl#{story_id}:results.facts[{index}]", "text": text, "confidentiality": confidentiality, "verified": True})
    return evidence


def _source_hash(requirement: str, posting_url: str) -> str:
    return hashlib.sha256(f"{posting_url}\n{requirement}".encode("utf-8")).hexdigest()


def _prior_indexes(prior: dict[str, Any] | None) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    if not isinstance(prior, dict):
        return {}, {}
    entries = [item for item in prior.get("requirements", []) if isinstance(item, dict)]
    by_id = {str(item.get("id")): item for item in entries if item.get("id")}
    # Requirement text keeps refresh provenance connected even if a canonical URL changes.
    by_requirement = {str(item.get("requirement")): item for item in entries if item.get("requirement")}
    return by_id, by_requirement


def build_matrix(profile: dict[str, Any], vacancy: dict[str, Any], *, stories: Iterable[dict[str, Any]] = (), prior: dict[str, Any] | None = None) -> dict[str, Any]:
    posting = cited_posting(vacancy)
    raw_requirements = list(vacancy.get("requirements", []))
    ignored_requirements = [requirement_text(item) for item in raw_requirements if is_non_job_relevant_requirement(item) and requirement_text(item)]
    requirements = [requirement_text(item) for item in raw_requirements if not is_non_job_relevant_requirement(item)]
    requirements = [item for item in requirements if item]
    if not requirements:
        raise ValueError("requirement matrix requires at least one cited vacancy requirement")
    evidence = _private_evidence(profile, stories)
    gap_texts = [str(item).strip() for item in profile.get("profile", {}).get("gaps", []) if str(item).strip()]
    prior_entries, prior_by_requirement = _prior_indexes(prior)
    entries: list[dict[str, Any]] = []
    for index, requirement in enumerate(requirements, start=1):
        req_tokens = tokens(requirement)
        requirement_id = "req-" + hashlib.sha256(f"{posting['url']}\n{requirement}".encode("utf-8")).hexdigest()[:12]
        supporting = [item for item in evidence if item.get("verified") is True and req_tokens and len(req_tokens & tokens(item["text"])) >= (1 if len(req_tokens) == 1 else 2)]
        partial = [item for item in evidence if item not in supporting and req_tokens & tokens(item["text"])]
        explicit_gap = any(req_tokens & tokens(item) for item in gap_texts)
        if supporting:
            assessment = "direct"
            transferability = None
            follow_up = "Validate relevance and recency before presenting this evidence."
        elif partial:
            assessment = "transferable"
            transferability = {
                "label": "analysis_not_direct_experience",
                "reason": "Partial terminology overlap may be transferable; it is not proof of direct experience.",
                "evidence_refs": [item["ref"] for item in partial],
            }
            follow_up = "Ask the candidate whether the cited adjacent experience transfers to this requirement."
        elif explicit_gap:
            assessment = "gap"
            transferability = None
            follow_up = "Decide whether this declared gap is material or can be addressed with a truthful learning plan."
        else:
            assessment = "unknown"
            transferability = None
            follow_up = "Ask for verified evidence or confirm that no evidence exists."
        source_hash = _source_hash(requirement, posting["url"])
        previous = prior_entries.get(requirement_id) or prior_by_requirement.get(requirement, {})
        source_changed = bool(previous) and previous.get("source_sha256") != source_hash
        entry = {
            "id": requirement_id,
            "requirement": requirement,
            "posting_source": posting,
            "source_sha256": source_hash,
            "source_changed": source_changed,
            "assessment": assessment,
            "direct_evidence": [
                {"kind": item["kind"], "ref": item["ref"], "text": item["text"]}
                for item in supporting
            ],
            "transferability": transferability,
            "gap": requirement if assessment == "gap" else None,
            "unknown": requirement if assessment == "unknown" else None,
            "follow_up": follow_up,
        }
        entries.append(entry)
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "vacancy": {"company": str(vacancy.get("company", "")), "title": str(vacancy.get("title", "")), "canonical_url": posting["url"]},
        "requirements": entries,
        "ignored_non_job_relevant_requirements": ignored_requirements,
        "summary": {assessment: sum(1 for item in entries if item["assessment"] == assessment) for assessment in sorted(VALID_ASSESSMENTS)},
        "privacy": "Private candidate evidence references only. Do not commit this artifact or copy its facts into a tracker without authorization.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--vacancy", required=True)
    parser.add_argument("--stories", help="Optional private story bank JSONL")
    parser.add_argument("--prior", help="Optional prior matrix for source-change detection")
    parser.add_argument("--output", required=True, help="Private JSON artifact path outside Git")
    args = parser.parse_args()
    try:
        stories: list[dict[str, Any]] = []
        if args.stories:
            for line in Path(args.stories).expanduser().read_text(encoding="utf-8").splitlines():
                if line.strip():
                    stories.append(json.loads(line))
        prior = load_document(Path(args.prior).expanduser()) if args.prior else None
        result = build_matrix(load_document(Path(args.profile).expanduser()), load_document(Path(args.vacancy).expanduser()), stories=stories, prior=prior)
        atomic_write_json(Path(args.output), result)
        print(json.dumps({"written": str(Path(args.output).expanduser()), "summary": result["summary"]}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
