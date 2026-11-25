#!/usr/bin/env python3
"""Create a reviewable, unconfirmed STAR story proposal from private input."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any


CONFIDENTIALITY = {"shareable", "candidate_private", "restricted", "confidential"}


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _strings(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not _text(item) for item in value):
        raise ValueError(f"{field} must be an array of non-empty strings")
    return [_text(item) for item in value]


def _metrics(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("confirmed_metrics must be an array")
    result = []
    for metric in value:
        if not isinstance(metric, dict):
            raise ValueError("confirmed_metrics entries must be mappings")
        required = ("label", "value", "unit", "source")
        if any(metric.get(field) in {None, ""} for field in required) or metric.get("confirmed_by_user") is not True:
            raise ValueError("confirmed_metrics require label, value, unit, source and confirmed_by_user=true")
        result.append({field: metric[field] for field in (*required, "confirmed_by_user")})
    return result


def build_capture_proposal(capture: dict[str, Any]) -> dict[str, Any]:
    """Normalize candidate-provided facts without confirming or inventing them."""
    if not isinstance(capture, dict):
        raise ValueError("capture must be a mapping")
    title = _text(capture.get("title"))
    if not title:
        raise ValueError("title is required")
    results = capture.get("results", {})
    if not isinstance(results, dict):
        raise ValueError("results must be a mapping")
    confidentiality = _text(capture.get("confidentiality") or "candidate_private").casefold()
    if confidentiality not in CONFIDENTIALITY:
        raise ValueError("confidentiality is not supported")
    story = {
        "id": "story-" + hashlib.sha256(title.encode("utf-8")).hexdigest()[:12],
        "title": title,
        "context": _text(capture.get("context")),
        "challenge": _text(capture.get("challenge")),
        "actions": _strings(capture.get("actions"), "actions"),
        "results": {
            "facts": _strings(results.get("facts"), "results.facts"),
            "unknowns": _strings(results.get("unknowns"), "results.unknowns"),
        },
        "confirmed_metrics": _metrics(capture.get("confirmed_metrics")),
        "evidence_sources": [],
        "tags": _strings(capture.get("tags"), "tags"),
        "recency": {},
        "confidentiality": confidentiality,
        "provenance": {"source_kind": "guided_capture", "confirmation": "pending"},
        "user_confirmed": False,
    }
    questions = []
    for field, value in (("context", story["context"]), ("challenge", story["challenge"]), ("actions", story["actions"]), ("results.facts", story["results"]["facts"])):
        if not value:
            questions.append(field)
    if not story["confirmed_metrics"]:
        questions.append("confirmed_metrics")
    questions.append("evidence_sources")
    return {
        "schema_version": 1,
        "confirmation_required": True,
        "story": story,
        "questions": questions,
        "limits": ["Do not add invented metrics or outcomes.", "This proposal does not modify the story bank.", "Only an explicit candidate confirmation may mark a story confirmed."],
    }


def confirm_capture_proposal(proposal: dict[str, Any], explicit_confirmation: bool) -> dict[str, Any]:
    """Return one candidate-confirmed story only after an explicit confirmation signal."""
    if explicit_confirmation is not True:
        raise ValueError("explicit candidate confirmation is required")
    if not isinstance(proposal, dict) or proposal.get("confirmation_required") is not True:
        raise ValueError("proposal must require confirmation")
    proposed_story = proposal.get("story")
    if not isinstance(proposed_story, dict) or proposed_story.get("user_confirmed") is not False:
        raise ValueError("proposal must contain one unconfirmed story")
    story = copy.deepcopy(proposed_story)
    provenance = story.get("provenance")
    if not isinstance(provenance, dict):
        raise ValueError("proposal story provenance is required")
    provenance["confirmation"] = "explicit_candidate_confirmation"
    story["user_confirmed"] = True
    return story


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Private JSON capture or reviewed proposal file; never written by this command")
    parser.add_argument("--confirm", action="store_true", help="Return a candidate-confirmed story from a reviewed proposal")
    args = parser.parse_args(argv)
    try:
        capture = json.loads(Path(args.input).read_text(encoding="utf-8"))
        result = confirm_capture_proposal(capture, True) if args.confirm else build_capture_proposal(capture)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
