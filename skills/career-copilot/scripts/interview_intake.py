#!/usr/bin/env python3
"""Normalize a private interview intake without starting research or external actions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _strings(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not _text(item) for item in value):
        raise ValueError(f"{field} must be an array of non-empty strings")
    return [_text(item) for item in value]


def build_interview_intake(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("intake must be a mapping")
    company, stage, source = (_text(payload.get(field)) for field in ("company", "stage", "source"))
    if not company or not stage or not source:
        raise ValueError("company, stage and source are required confirmed logistics")
    participants = payload.get("participants", [])
    if not isinstance(participants, list):
        raise ValueError("participants must be an array")
    normalized = []
    for participant in participants:
        if not isinstance(participant, dict) or not _text(participant.get("name")) or not _text(participant.get("role")):
            raise ValueError("participants require a confirmed name and role")
        normalized.append({"name": _text(participant["name"]), "role": _text(participant["role"])})
    duration = payload.get("duration_minutes")
    if duration is not None and (isinstance(duration, bool) or not isinstance(duration, int) or duration <= 0):
        raise ValueError("duration_minutes must be a positive integer when supplied")
    logistics = {"company": company, "vacancy_title": _text(payload.get("vacancy_title")), "stage": stage, "scheduled_at": _text(payload.get("scheduled_at")), "modality": _text(payload.get("modality")), "duration_minutes": duration, "participants": normalized, "source": source}
    unknowns = [field for field in ("vacancy_title", "scheduled_at", "modality", "duration_minutes") if logistics[field] in {None, ""}]
    if not normalized:
        unknowns.append("participants")
    return {"schema_version": 1, "confirmed_logistics": logistics, "hypotheses": _strings(payload.get("hypotheses"), "hypotheses"), "unknowns": unknowns, "research_status": "not_started", "external_actions": 0, "next_step": "Confirm visible participants and then perform separate read-only interviewer research."}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Private JSON intake file; never written by this command")
    args = parser.parse_args(argv)
    try:
        payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
        print(json.dumps(build_interview_intake(payload), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
