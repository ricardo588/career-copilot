#!/usr/bin/env python3
"""Checkpointed, privacy-first onboarding for Career Copilot."""

from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


QUESTIONS = [
    {"phase": "goals", "field": "profile.target_roles", "prompt": "Which roles are you targeting?", "required": True},
    {"phase": "goals", "field": "profile.target_seniority", "prompt": "Which seniority levels are appropriate?", "required": True},
    {"phase": "evidence", "field": "profile.strengths", "prompt": "Which verified strengths should drive matching?", "required": True},
    {"phase": "evidence", "field": "profile.verified_evidence", "prompt": "Which real achievements or examples support those strengths?", "required": True},
    {"phase": "constraints", "field": "constraints.countries", "prompt": "Which countries are eligible?", "required": False},
    {"phase": "constraints", "field": "constraints.locations", "prompt": "Which locations are eligible?", "required": False},
    {"phase": "constraints", "field": "constraints.work_modes", "prompt": "Which work modes are acceptable?", "required": False},
    {"phase": "constraints", "field": "constraints.excluded_roles", "prompt": "Which roles must be excluded?", "required": False},
    {"phase": "preferences", "field": "search.freshness_days", "prompt": "How many days should a vacancy remain fresh?", "required": False},
    {"phase": "documents", "field": "documents.primary_cv", "prompt": "Where is the private primary CV stored?", "required": False},
    {"phase": "permissions", "field": "permissions.tracker_updates", "prompt": "May the copilot update the private tracker?", "required": True},
    {"phase": "permissions", "field": "permissions.external_actions", "prompt": "What approval is required for external actions?", "required": True},
]

DEFAULT_ANSWERS: dict[str, Any] = {
    "profile": {
        "display_name": "",
        "language": "auto",
        "target_roles": [],
        "target_seniority": [],
        "target_industries": [],
        "strengths": [],
        "verified_evidence": [],
        "gaps": [],
    },
    "constraints": {
        "countries": [],
        "locations": [],
        "work_modes": [],
        "employment_types": [],
        "excluded_roles": [],
        "excluded_industries": [],
    },
    "compensation": {"enabled": False, "currency": "", "target": None, "floor": None},
    "permissions": {
        "tracker_updates": "ask",
        "draft_messages": "allow",
        "external_actions": "explicit_confirmation",
        "public_profile_changes": "explicit_confirmation",
    },
    "documents": {"primary_cv": "", "alternate_cvs": []},
    "search": {
        "source_priority": [
            "official_company_sites",
            "official_ats",
            "recruiters_and_headhunters",
            "professional_networks",
            "aggregators",
        ],
        "freshness_days": 14,
        "require_current_source": True,
    },
    "integrations": {
        "google_sheets": {"enabled": False, "spreadsheet_id_env": "CAREER_COPILOT_SHEET_ID", "range": "Applications!A:P"},
        "gmail": {"enabled": False, "user_id": "me"},
        "obsidian": {"enabled": False, "vault_env": "OBSIDIAN_VAULT_PATH", "folder": "CareerCopilot"},
    },
}

REQUIRED_FIELDS = [
    "profile.target_roles",
    "profile.target_seniority",
    "profile.strengths",
    "profile.verified_evidence",
    "permissions.tracker_updates",
    "permissions.external_actions",
]

LIST_FIELDS = {
    "profile.target_roles", "profile.target_seniority", "profile.target_industries",
    "profile.strengths", "profile.verified_evidence", "profile.gaps",
    "constraints.countries", "constraints.locations", "constraints.work_modes",
    "constraints.employment_types", "constraints.excluded_roles", "constraints.excluded_industries",
    "documents.alternate_cvs", "search.source_priority",
}
BOOLEAN_FIELDS = {
    "compensation.enabled", "search.require_current_source",
    "integrations.google_sheets.enabled", "integrations.gmail.enabled", "integrations.obsidian.enabled",
}
CHOICE_FIELDS = {
    "permissions.tracker_updates": {"ask", "allow", "deny"},
    "permissions.draft_messages": {"ask", "allow", "deny"},
    "permissions.external_actions": {"explicit_confirmation", "deny"},
    "permissions.public_profile_changes": {"explicit_confirmation", "deny"},
}
NUMBER_OR_NULL_FIELDS = {"compensation.target", "compensation.floor"}


def leaf_paths(data: dict[str, Any], prefix: str = "") -> set[str]:
    paths: set[str] = set()
    for key, value in data.items():
        dotted = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            paths.update(leaf_paths(value, dotted))
        else:
            paths.add(dotted)
    return paths


ALLOWED_FIELDS = leaf_paths(DEFAULT_ANSWERS)


def validate_answer(field: str, value: Any) -> None:
    if field not in ALLOWED_FIELDS:
        raise ValueError(f"unknown onboarding field: {field}")
    if field in LIST_FIELDS:
        if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
            raise ValueError(f"{field} must be a JSON array of non-empty strings")
        return
    if field in BOOLEAN_FIELDS:
        if not isinstance(value, bool):
            raise ValueError(f"{field} must be a JSON boolean")
        return
    if field in CHOICE_FIELDS:
        if value not in CHOICE_FIELDS[field]:
            allowed = ", ".join(sorted(CHOICE_FIELDS[field]))
            raise ValueError(f"{field} must be one of: {allowed}")
        return
    if field == "search.freshness_days":
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 365:
            raise ValueError("search.freshness_days must be an integer from 1 to 365")
        return
    if field in NUMBER_OR_NULL_FIELDS:
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0):
            raise ValueError(f"{field} must be null or a non-negative number")
        return
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def state_file(workspace: Path) -> Path:
    return workspace / ".career_copilot_onboarding.json"


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def ensure_private_workspace(workspace: Path) -> Path:
    resolved = workspace.expanduser().resolve()
    profile_root = Path(__file__).resolve().parents[3]
    if resolved == profile_root or profile_root in resolved.parents:
        raise ValueError("private workspace must be outside the Career Copilot profile/distribution directory")
    return resolved


def new_state() -> dict[str, Any]:
    now = utc_now()
    return {
        "schema_version": 1,
        "status": "in_progress",
        "created_at": now,
        "updated_at": now,
        "answered_fields": [],
        "answers": copy.deepcopy(DEFAULT_ANSWERS),
    }


def load_state(workspace: Path) -> dict[str, Any]:
    path = state_file(workspace)
    if not path.is_file():
        raise ValueError("onboarding has not started; run the start command first")
    return json.loads(path.read_text(encoding="utf-8"))


def get_nested(data: dict[str, Any], dotted: str) -> Any:
    current: Any = data
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def set_nested(data: dict[str, Any], dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    current: dict[str, Any] = data
    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            child = {}
            current[part] = child
        current = child
    current[parts[-1]] = value


def is_populated(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def missing_fields(state: dict[str, Any]) -> list[str]:
    answers = state["answers"]
    explicitly_answered = set(state.get("answered_fields", []))
    missing = []
    for field in REQUIRED_FIELDS:
        if not is_populated(get_nested(answers, field)):
            missing.append(field)
        elif field.startswith("permissions.") and field not in explicitly_answered:
            missing.append(field)
    if not (is_populated(get_nested(answers, "constraints.countries")) or is_populated(get_nested(answers, "constraints.locations"))):
        missing.append("constraints.countries_or_locations")
    return missing


def status_payload(state: dict[str, Any]) -> dict[str, Any]:
    missing = missing_fields(state)
    required_total = len(REQUIRED_FIELDS) + 1
    completed = required_total - len(missing)
    next_question = next(
        (item for item in QUESTIONS if item["field"] in missing or item["field"].startswith("constraints.") and "constraints.countries_or_locations" in missing),
        None,
    )
    return {
        "status": state.get("status", "in_progress"),
        "completed_required": completed,
        "required_total": required_total,
        "missing": missing,
        "next_question": next_question,
        "updated_at": state.get("updated_at"),
    }


def backup_once(path: Path) -> None:
    if not path.exists():
        return
    backup = path.with_suffix(path.suffix + ".pre-onboarding.bak")
    if not backup.exists():
        shutil.copyfile(path, backup)
        os.chmod(backup, 0o600)


def finalize(workspace: Path, state: dict[str, Any]) -> dict[str, Any]:
    missing = missing_fields(state)
    if missing:
        raise ValueError("cannot finalize; missing: " + ", ".join(missing))

    answers = state["answers"]
    profile_document = {
        "schema_version": 1,
        "profile": answers["profile"],
        "constraints": answers["constraints"],
        "compensation": answers["compensation"],
        "permissions": answers["permissions"],
        "documents": answers["documents"],
        "integrations": answers["integrations"],
    }
    rules_document = {
        "schema_version": 1,
        "search": answers["search"],
        "evaluation": {"hard_exclusions": [], "preferred_signals": [], "unknown_is_not_match": True},
        "tracker": {"backend": "local_csv", "file": "tracker.csv", "update_policy": answers["permissions"]["tracker_updates"], "stable_identity": True},
        "communications": {"first_contact_style": "concise", "send_policy": answers["permissions"]["external_actions"], "application_policy": answers["permissions"]["external_actions"]},
    }

    profile_path = workspace / "profile.yaml"
    rules_path = workspace / "rules.yaml"
    backup_once(profile_path)
    backup_once(rules_path)
    atomic_write_json(profile_path, profile_document)
    atomic_write_json(rules_path, rules_document)

    state["status"] = "complete"
    state["completed_at"] = utc_now()
    state["updated_at"] = state["completed_at"]
    atomic_write_json(state_file(workspace), state)
    return {"status": "complete", "profile": str(profile_path), "rules": str(rules_path)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, help="Private candidate workspace")
    commands = parser.add_subparsers(dest="command", required=True)
    start = commands.add_parser("start", help="Start or resume onboarding")
    start.add_argument("--reset", action="store_true", help="Reset only the onboarding checkpoint")
    answer = commands.add_parser("answer", help="Store one answer and checkpoint")
    answer.add_argument("--field", required=True)
    value_group = answer.add_mutually_exclusive_group(required=True)
    value_group.add_argument("--value")
    value_group.add_argument("--json-value")
    commands.add_parser("status", help="Show progress and next question")
    commands.add_parser("questions", help="List the conversational question catalog")
    commands.add_parser("finalize", help="Validate and write profile/rules")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        workspace = ensure_private_workspace(Path(args.workspace))
        workspace_was_new = not workspace.exists()
        workspace.mkdir(parents=True, exist_ok=True)
        if workspace_was_new:
            os.chmod(workspace, 0o700)
        path = state_file(workspace)

        if args.command == "start":
            if path.exists() and not args.reset:
                state = load_state(workspace)
            else:
                state = new_state()
                atomic_write_json(path, state)
            print(json.dumps(status_payload(state), indent=2, ensure_ascii=False))
            return 0

        if args.command == "questions":
            print(json.dumps(QUESTIONS, indent=2, ensure_ascii=False))
            return 0

        state = load_state(workspace)
        if args.command == "status":
            print(json.dumps(status_payload(state), indent=2, ensure_ascii=False))
            return 0
        if args.command == "answer":
            value = json.loads(args.json_value) if args.json_value is not None else args.value
            validate_answer(args.field, value)
            set_nested(state["answers"], args.field, value)
            answered_fields = state.setdefault("answered_fields", [])
            if args.field not in answered_fields:
                answered_fields.append(args.field)
            state["updated_at"] = utc_now()
            atomic_write_json(path, state)
            print(json.dumps(status_payload(state), indent=2, ensure_ascii=False))
            return 0
        if args.command == "finalize":
            print(json.dumps(finalize(workspace, state), indent=2, ensure_ascii=False))
            return 0
        raise ValueError(f"unsupported command: {args.command}")
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
