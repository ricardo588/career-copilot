#!/usr/bin/env python3
"""Generate a private, read-only weekly job-search campaign plan."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import tempfile
from datetime import date, timedelta
from pathlib import Path
from typing import Any


SCRIPTS_DIR = Path(__file__).resolve().parent


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PIPELINE = _load_module("career_copilot_pipeline", "pipeline.py")
TARGETS = _load_module("career_copilot_targets", "target_companies.py")
PROHIBITED_ACTION_KINDS = {"send", "apply", "contact", "status_change", "mutate", "publish"}


def _parse_day(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("date must use YYYY-MM-DD") from exc


def _list(value: Any, field: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ValueError(f"{field} must be a list of mappings")
    return [dict(item) for item in value]


def _text_list(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")
    return [str(item).strip() for item in value if str(item).strip()]


def _validate_context(context: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(context, dict):
        raise ValueError("weekly context must be a mapping")
    result = {
        "focus": _text_list(context.get("focus", []), "focus"),
        "drafts": _list(context.get("drafts"), "drafts"),
        "authorized_actions": _list(context.get("authorized_actions"), "authorized_actions"),
        "attempts": _list(context.get("attempts"), "attempts"),
        "outcomes": _list(context.get("outcomes"), "outcomes"),
        "learning": _list(context.get("learning"), "learning"),
    }
    for action in result["authorized_actions"]:
        kind = str(action.get("kind", "")).strip().casefold()
        if not str(action.get("id", "")).strip():
            raise ValueError("authorized action requires id")
        if kind in PROHIBITED_ACTION_KINDS:
            raise ValueError("weekly plans must not send or mutate external state")
    for outcome in result["outcomes"]:
        if str(outcome.get("state", "")).strip().casefold() == "verified" and not str(outcome.get("evidence_ref", "")).strip():
            raise ValueError("verified outcome requires evidence_ref")
    return result


def _active_target_research(registry: dict[str, Any]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for company in registry.get("companies", []):
        if company.get("status") != "active":
            continue
        next_action = str(company.get("next_research_action", "")).strip()
        if next_action:
            items.append({"id": str(company.get("id", "")), "next_research_action": next_action})
    return items


def _passive_waiting(tracker_review: dict[str, Any]) -> list[dict[str, str]]:
    waiting: list[dict[str, str]] = []
    for item in tracker_review.get("items", []):
        status = str(item.get("status", "")).strip().casefold()
        if status in {"applied", "contact", "recruiter_screen", "interview"} and not item.get("next_action"):
            waiting.append({
                "id": str(item.get("id", "")),
                "company": str(item.get("company", "")),
                "role": str(item.get("role", "")),
                "status": str(item.get("status", "")),
                "recommended_action": "none",
                "reason": "passive waiting; no explicit follow-up is due",
            })
    return waiting


def build_weekly_plan(tracker_path: Path, target_registry_path: Path, context: dict[str, Any], week_start: date) -> dict[str, Any]:
    """Read existing artifacts and produce a plan; never write tracker or registry data."""
    validated_context = _validate_context(context)
    tracker_review = PIPELINE.review_tracker(tracker_path, week_start)
    registry = TARGETS.load_registry(target_registry_path)
    target_review = TARGETS.review_registry(registry, week_start, company_stale_after_days=30, human_path_stale_after_days=30)
    overdue = [item for item in tracker_review["items"] if item["follow_up_overdue"]]
    active_count = sum(1 for item in tracker_review["items"] if str(item.get("status", "")).casefold() not in {"withdrawn", "rejected", "discarded"})
    return {
        "schema_version": 1,
        "week_start": week_start.isoformat(),
        "week_end": (week_start + timedelta(days=6)).isoformat(),
        "read_only": True,
        "mutation": "none",
        "volume_context": "higher_volume" if active_count >= 10 else "low_volume",
        "focus": validated_context["focus"],
        "activity": {
            "authorized_actions": validated_context["authorized_actions"],
            "attempts": validated_context["attempts"],
            "note": "Activity is recorded separately from outputs and verified outcomes; no quota is imposed.",
        },
        "outputs": {"drafts": validated_context["drafts"]},
        "outcomes": validated_context["outcomes"],
        "learning": validated_context["learning"],
        "actionable_items": {
            "overdue_follow_ups": overdue,
            "target_research": _active_target_research(registry),
        },
        "passive_waiting": _passive_waiting(tracker_review),
        "research_gaps": {
            "company_evidence_stale": target_review["company_evidence_stale"],
            "human_path_evidence_stale": target_review["human_path_evidence_stale"],
        },
        "tracker_review": tracker_review,
        "guardrails": [
            "No universal activity quota is imposed.",
            "Passive waiting does not create artificial work or change tracker status.",
            "Drafts, approvals, attempts and verified outcomes remain separate.",
            "This plan is read-only and does not send, apply, contact or mutate external systems.",
        ],
    }


def _private_path(raw_path: Path) -> Path:
    """Reuse the workspace/symlink/Git-boundary enforcement of target artifacts."""
    return TARGETS.private_path(raw_path)


def write_private_report(raw_path: Path, report: dict[str, Any]) -> None:
    path = _private_path(raw_path)
    descriptor, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(temp_name, path)
        os.chmod(path, 0o600)
        if json.loads(path.read_text(encoding="utf-8")) != report:
            raise RuntimeError("weekly report readback verification failed")
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tracker", required=True)
    parser.add_argument("--targets", required=True)
    parser.add_argument("--context", required=True, help="private JSON weekly context")
    parser.add_argument("--week-start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--output", help="optional private JSON report path")
    args = parser.parse_args()
    try:
        context = json.loads(Path(args.context).read_text(encoding="utf-8"))
        report = build_weekly_plan(Path(args.tracker), Path(args.targets), context, _parse_day(args.week_start))
        if args.output:
            write_private_report(Path(args.output), report)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0
    except (ValueError, OSError, json.JSONDecodeError, RuntimeError, FileNotFoundError) as exc:
        print(f"error: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
