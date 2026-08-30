#!/usr/bin/env python3
"""Checkpointed, privacy-first onboarding for Career Copilot."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from story_bank import load_story_bank, save_story_bank, story_bank_path
QUESTIONS = [
    {"phase": "documents", "field": "documents.has_cv", "prompt": "Do you already have a CV?", "required": True},
    {"phase": "documents", "field": "documents.primary_cv", "prompt": "Share or select the local CV only if you accept that its extracted text is processed by your configured Hermes model provider (unless you use a local model). I will propose onboarding facts for your confirmation.", "required": False},
    {"phase": "goals", "field": "profile.target_roles", "prompt": "Which roles are you targeting?", "required": True},
    {"phase": "goals", "field": "profile.target_seniority", "prompt": "Which seniority levels are appropriate?", "required": True},
    {"phase": "evidence", "field": "profile.strengths", "prompt": "Which verified strengths should drive matching?", "required": True},
    {"phase": "evidence", "field": "profile.verified_evidence", "prompt": "Which real achievements or examples support those strengths?", "required": True},
    {"phase": "direction", "field": "profile.career_direction.success_criteria", "prompt": "What success criteria should be captured as factual, interpretive or preference-based?", "required": False},
    {"phase": "direction", "field": "profile.career_direction.values", "prompt": "What values should be captured as factual, interpretive or preference-based?", "required": False},
    {"phase": "direction", "field": "profile.career_direction.non_negotiables", "prompt": "What non-negotiables should be captured as factual, interpretive or preference-based?", "required": False},
    {"phase": "direction", "field": "profile.career_direction.tolerable_tradeoffs", "prompt": "What tolerable tradeoffs should be captured as factual, interpretive or preference-based?", "required": False},
    {"phase": "direction", "field": "profile.career_direction.development_gaps", "prompt": "What development gaps should be captured as factual, interpretive or preference-based?", "required": False},
    {"phase": "direction", "field": "profile.career_direction.departure_narrative", "prompt": "Capture a concise candidate-approved factual departure narrative with separate facts, interpretations and preferences.", "required": False},
    {"phase": "constraints", "field": "constraints.countries", "prompt": "Which countries are eligible?", "required": False},
    {"phase": "constraints", "field": "constraints.locations", "prompt": "Which locations are eligible?", "required": False},
    {"phase": "constraints", "field": "constraints.work_modes", "prompt": "Which work modes are acceptable?", "required": False},
    {"phase": "constraints", "field": "constraints.job_eligibility.work_authorization", "prompt": "Which work authorizations or eligibility facts do you explicitly declare?", "required": False},
    {"phase": "constraints", "field": "constraints.job_eligibility.travel", "prompt": "What travel availability do you explicitly declare?", "required": False},
    {"phase": "constraints", "field": "constraints.accommodations", "prompt": "Which job-process accommodations do you explicitly request, if any?", "required": False},
    {"phase": "constraints", "field": "constraints.excluded_roles", "prompt": "Which roles must be excluded?", "required": False},
    {"phase": "preferences", "field": "search.freshness_days", "prompt": "How many days should a vacancy remain fresh?", "required": False},

    {"phase": "permissions", "field": "permissions.tracker_updates", "prompt": "May the copilot update the private tracker?", "required": True},
    {"phase": "permissions", "field": "permissions.external_action_mode", "prompt": "Keep draft-only mode, or explicitly opt in to confirmation for each external action?", "required": False},
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
        "career_direction": {
            "success_criteria": {"facts": [], "interpretations": [], "preferences": []},
            "values": {"facts": [], "interpretations": [], "preferences": []},
            "non_negotiables": {"facts": [], "interpretations": [], "preferences": []},
            "tolerable_tradeoffs": {"facts": [], "interpretations": [], "preferences": []},
            "development_gaps": {"facts": [], "interpretations": [], "preferences": []},
            "departure_narrative": {
                "candidate_approved": False,
                "facts": [],
                "interpretations": [],
                "preferences": [],
            },
        },
    },
    "constraints": {
        "countries": [],
        "locations": [],
        "work_modes": [],
        "employment_types": [],
        "job_eligibility": {"work_authorization": [], "travel": ""},
        "accommodations": [],
        "excluded_roles": [],
        "excluded_industries": [],
    },
    "compensation": {"enabled": False, "currency": "", "target": None, "floor": None},
    "permissions": {
        "tracker_updates": "ask",
        "draft_messages": "allow",
        "external_action_mode": "draft_only",
        "external_action_mode_locked": False,
    },
    "documents": {"has_cv": None, "primary_cv": "", "alternate_cvs": [], "cv_import_status": "not_started"},
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
        "google_sheets": {"enabled": False, "spreadsheet_id_env": "CAREER_COPILOT_SHEET_ID", "range": "Applications!A:U"},
        "gmail": {"enabled": False, "user_id": "me"},
        "obsidian": {"enabled": False, "vault_env": "OBSIDIAN_VAULT_PATH", "folder": "CareerCopilot"},
    },
}

REQUIRED_FIELDS = [
    "documents.has_cv",
    "profile.target_roles",
    "profile.target_seniority",
    "profile.strengths",
    "profile.verified_evidence",
    "permissions.tracker_updates",
]

LIST_FIELDS = {
    "profile.target_roles", "profile.target_seniority", "profile.target_industries",
    "profile.strengths", "profile.verified_evidence", "profile.gaps",
    "constraints.countries", "constraints.locations", "constraints.work_modes",
    "constraints.employment_types", "constraints.excluded_roles", "constraints.excluded_industries",
    "constraints.job_eligibility.work_authorization", "constraints.accommodations",
    "documents.alternate_cvs", "search.source_priority",
}
BOOLEAN_FIELDS = {
    "documents.has_cv",
    "compensation.enabled", "search.require_current_source",
    "permissions.external_action_mode_locked",
    "integrations.google_sheets.enabled", "integrations.gmail.enabled", "integrations.obsidian.enabled",
}
CHOICE_FIELDS = {
    "permissions.tracker_updates": {"ask", "allow", "deny"},
    "permissions.draft_messages": {"ask", "allow", "deny"},
    "permissions.external_action_mode": {"draft_only", "confirm_each_external"},
}
NUMBER_OR_NULL_FIELDS = {"compensation.target", "compensation.floor"}

CV_PROPOSABLE_FIELDS = {
    "profile.display_name", "profile.target_roles",
    "profile.target_seniority", "profile.target_industries", "profile.strengths",
    "profile.verified_evidence", "constraints.countries", "constraints.locations",
}
CV_DIRECT_ONLY_FIELDS = {"profile.display_name", "profile.verified_evidence"}
CV_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
CV_IMPORT_QUESTION = {
    "phase": "documents", "field": "documents.cv_import",
    "prompt": "Read the local CV, extract only supported facts and clearly labeled inferences, then stage them with cv-propose.",
    "required": True,
}
CV_CONFIRMATION_QUESTION = {
    "phase": "documents", "field": "documents.cv_confirmation",
    "prompt": "Confirm or correct the proposed onboarding information extracted from the CV.",
    "required": True,
}

CAREER_DIRECTION_FIELDS = {
    "profile.career_direction.success_criteria",
    "profile.career_direction.values",
    "profile.career_direction.non_negotiables",
    "profile.career_direction.tolerable_tradeoffs",
    "profile.career_direction.development_gaps",
    "profile.career_direction.departure_narrative",
}


def _validate_direction_map(field: str, value: Any, require_approval: bool = False) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be a JSON object")
    for category in ("facts", "interpretations", "preferences"):
        items = value.get(category, [])
        if not isinstance(items, list) or any(not isinstance(item, str) or not item.strip() for item in items):
            raise ValueError(f"{field}.{category} must be a JSON array of non-empty strings")
    if require_approval:
        approved = value.get("candidate_approved")
        if not isinstance(approved, bool):
            raise ValueError(f"{field}.candidate_approved must be a JSON boolean")



def leaf_paths(data: dict[str, Any], prefix: str = "") -> set[str]:
    paths: set[str] = set()
    for key, value in data.items():
        dotted = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            paths.update(leaf_paths(value, dotted))
        else:
            paths.add(dotted)
    return paths


ALLOWED_FIELDS = leaf_paths(DEFAULT_ANSWERS) | CAREER_DIRECTION_FIELDS


def validate_answer(field: str, value: Any) -> None:
    if field not in ALLOWED_FIELDS:
        raise ValueError(f"unknown onboarding field: {field}")
    if field == "permissions.external_action_mode_locked":
        raise ValueError("permissions.external_action_mode_locked is managed by profile policy, not onboarding answers")
    if field == "documents.cv_import_status":
        raise ValueError("documents.cv_import_status is managed by the CV onboarding workflow")
    if field in CAREER_DIRECTION_FIELDS:
        _validate_direction_map(field, value, require_approval=field == "profile.career_direction.departure_narrative")
        return
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


def containing_git_root(path: Path) -> Path | None:
    start = path if path.is_dir() else path.parent
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def ensure_private_workspace(workspace: Path) -> Path:
    resolved = workspace.expanduser().resolve()
    profile_root = Path(__file__).resolve().parents[3]
    if resolved == profile_root or profile_root in resolved.parents:
        raise ValueError("private workspace must be outside the Career Copilot profile/distribution directory")
    git_root = containing_git_root(resolved)
    if git_root is not None:
        raise ValueError(f"private workspace must be outside a Git repository: {git_root}")
    return resolved


def new_state(lock_draft_only: bool = False) -> dict[str, Any]:
    now = utc_now()
    answers = copy.deepcopy(DEFAULT_ANSWERS)
    if lock_draft_only:
        answers["permissions"]["external_action_mode"] = "draft_only"
        answers["permissions"]["external_action_mode_locked"] = True
    return {
        "schema_version": 4,
        "status": "in_progress",
        "created_at": now,
        "updated_at": now,
        "answered_fields": [],
        "answers": answers,
        "cv_import": {"status": "not_started", "proposals": {}},
    }


def load_state(workspace: Path) -> dict[str, Any]:
    path = state_file(workspace)
    if not path.is_file():
        raise ValueError("onboarding has not started; run the start command first")
    state = json.loads(path.read_text(encoding="utf-8"))
    original_state = copy.deepcopy(state)
    permissions = state.setdefault("answers", {}).setdefault("permissions", {})
    if "external_action_mode" not in permissions:
        legacy = permissions.get("external_actions")
        permissions["external_action_mode"] = "confirm_each_external" if legacy == "explicit_confirmation" else "draft_only"
    permissions.setdefault("external_action_mode_locked", False)
    documents = state["answers"].setdefault("documents", {})
    documents.setdefault("has_cv", None)
    documents.setdefault("primary_cv", "")
    documents.setdefault("alternate_cvs", [])
    documents.setdefault("cv_import_status", "not_started")
    profile = state["answers"].setdefault("profile", {})
    career_direction = profile.setdefault("career_direction", {})
    direction_defaults = DEFAULT_ANSWERS["profile"]["career_direction"]
    for field, default in direction_defaults.items():
        if not isinstance(career_direction.get(field), dict):
            career_direction[field] = copy.deepcopy(default)
            continue
        for category, category_default in default.items():
            career_direction[field].setdefault(category, copy.deepcopy(category_default))
    if not isinstance(state.get("cv_import"), dict):
        state["cv_import"] = {"status": documents["cv_import_status"], "proposals": {}}
    state["schema_version"] = 4
    if state != original_state:
        atomic_write_json(path, state)
    return state


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
    has_cv = get_nested(answers, "documents.has_cv")
    if has_cv is True:
        if not is_populated(get_nested(answers, "documents.primary_cv")):
            missing.append("documents.primary_cv")
        if state.get("cv_import", {}).get("status") not in {"confirmed", "manual"}:
            missing.append("documents.cv_confirmation")
    if not (is_populated(get_nested(answers, "constraints.countries")) or is_populated(get_nested(answers, "constraints.locations"))):
        missing.append("constraints.countries_or_locations")
    return missing


def next_question_for(state: dict[str, Any], missing: list[str]) -> dict[str, Any] | None:
    if "documents.has_cv" in missing:
        return next(item for item in QUESTIONS if item["field"] == "documents.has_cv")
    if "documents.primary_cv" in missing:
        return next(item for item in QUESTIONS if item["field"] == "documents.primary_cv")
    if "documents.cv_confirmation" in missing:
        if state.get("cv_import", {}).get("status") == "pending_confirmation":
            return CV_CONFIRMATION_QUESTION
        return CV_IMPORT_QUESTION
    required_order = [item for item in QUESTIONS if item.get("required")]
    optional_order = [item for item in QUESTIONS if not item.get("required")]
    for item in required_order:
        if item["field"] in missing:
            return item
    answers = state.get("answers", {})
    for item in optional_order:
        if not is_populated(get_nested(answers, item["field"])):
            return item
    return None


def status_payload(state: dict[str, Any]) -> dict[str, Any]:
    missing = missing_fields(state)
    has_cv = get_nested(state["answers"], "documents.has_cv")
    required_total = len(REQUIRED_FIELDS) + 1 + (2 if has_cv is True else 0)
    completed = max(0, required_total - len(missing))
    optional_missing = [item["field"] for item in QUESTIONS if not item.get("required") and not is_populated(get_nested(state["answers"], item["field"]))]
    permissions = state.get("answers", {}).get("permissions", {})
    cv_import = state.get("cv_import", {"status": "not_started", "proposals": {}})
    return {
        "status": state.get("status", "in_progress"),
        "completed_required": completed,
        "required_total": required_total,
        "missing": missing,
        "optional_missing": optional_missing,
        "next_question": next_question_for(state, missing),
        "cv_import": {
            "status": cv_import.get("status", "not_started"),
            "proposals": cv_import.get("proposals", {}) if cv_import.get("status") == "pending_confirmation" else {},
        },
        "external_action_policy": {
            "mode": permissions.get("external_action_mode", "draft_only"),
            "locked": bool(permissions.get("external_action_mode_locked", False)),
        },
        "updated_at": state.get("updated_at"),
    }


def validate_local_cv_file(raw_path: str) -> Path:
    path = Path(raw_path).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"local CV file does not exist: {path}")
    if path.suffix.lower() not in CV_EXTENSIONS:
        allowed = ", ".join(sorted(CV_EXTENSIONS))
        raise ValueError(f"unsupported CV format; use one of: {allowed}")
    profile_root = Path(__file__).resolve().parents[3]
    if path == profile_root or profile_root in path.parents:
        raise ValueError("CV file must be outside the Career Copilot profile/distribution directory")
    git_root = containing_git_root(path)
    if git_root is not None:
        raise ValueError(f"CV file must be outside a Git repository: {git_root}")
    return path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def local_cv_path(state: dict[str, Any]) -> Path:
    if get_nested(state["answers"], "documents.has_cv") is not True:
        raise ValueError("CV import requires documents.has_cv to be true")
    raw_path = get_nested(state["answers"], "documents.primary_cv")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ValueError("set documents.primary_cv before importing the CV")
    return validate_local_cv_file(raw_path)


def reset_cv_import(state: dict[str, Any], status: str = "not_started") -> None:
    state["cv_import"] = {"status": status, "proposals": {}}
    state["answers"]["documents"]["cv_import_status"] = status


def clear_cv_applied_fields(state: dict[str, Any]) -> None:
    applied = state.get("cv_import", {}).get("applied_fields", [])
    answered_fields = state.setdefault("answered_fields", [])
    for field in applied:
        if field not in CV_PROPOSABLE_FIELDS:
            continue
        set_nested(state["answers"], field, copy.deepcopy(get_nested(DEFAULT_ANSWERS, field)))
        if field in answered_fields:
            answered_fields.remove(field)


def stage_cv_proposals(state: dict[str, Any], payload: Any) -> None:
    if not isinstance(payload, dict):
        raise ValueError("CV proposal payload must be a JSON object")
    cv_path = local_cv_path(state)
    source_file = payload.get("source_file")
    if not isinstance(source_file, str) or Path(source_file).expanduser().resolve() != cv_path:
        raise ValueError("CV proposal source_file must match documents.primary_cv")
    proposals = payload.get("proposals")
    if not isinstance(proposals, dict) or not proposals:
        raise ValueError("CV proposal payload must contain non-empty proposals")
    validated: dict[str, Any] = {}
    for field, proposal in proposals.items():
        if field not in CV_PROPOSABLE_FIELDS:
            raise ValueError(f"{field} cannot be proposed from a CV")
        if not isinstance(proposal, dict):
            raise ValueError(f"CV proposal for {field} must be an object")
        basis = proposal.get("basis")
        source = proposal.get("source")
        if basis not in {"direct", "inferred"}:
            raise ValueError(f"CV proposal for {field} needs basis direct or inferred")
        if field in CV_DIRECT_ONLY_FIELDS and basis != "direct":
            raise ValueError(f"CV proposal for {field} must be direct evidence, not inferred")
        if not isinstance(source, str) or not source.strip():
            raise ValueError(f"CV proposal for {field} needs a source section")
        if "\n" in source or len(source.strip()) > 160:
            raise ValueError(f"CV proposal source for {field} must be a short section label, not extracted CV text")
        value = proposal.get("value")
        validate_answer(field, value)
        validated[field] = {"value": value, "basis": basis, "source": source.strip()}
    state["cv_import"] = {
        "status": "pending_confirmation",
        "source_file": str(cv_path),
        "source_sha256": sha256_file(cv_path),
        "proposals": validated,
        "proposed_at": utc_now(),
    }
    state["answers"]["documents"]["cv_import_status"] = "pending_confirmation"


def confirm_cv_proposals(state: dict[str, Any], overrides: Any, rejected_fields: Any) -> None:
    cv_import = state.get("cv_import", {})
    if cv_import.get("status") != "pending_confirmation":
        raise ValueError("there are no pending CV proposals to confirm")
    cv_path = local_cv_path(state)
    expected_sha256 = cv_import.get("source_sha256")
    if not isinstance(expected_sha256, str) or sha256_file(cv_path) != expected_sha256:
        raise ValueError("CV file changed since proposals were staged; run cv-propose again")
    proposals = cv_import.get("proposals", {})
    if not isinstance(overrides, dict):
        raise ValueError("CV overrides must be a JSON object")
    if not isinstance(rejected_fields, list) or any(not isinstance(item, str) for item in rejected_fields):
        raise ValueError("rejected CV fields must be a JSON array of field names")
    unknown = (set(overrides) | set(rejected_fields)) - set(proposals)
    if unknown:
        raise ValueError("CV confirmation references fields not proposed: " + ", ".join(sorted(unknown)))
    rejected = set(rejected_fields)
    applied = []
    answered_fields = state.setdefault("answered_fields", [])
    for field, proposal in proposals.items():
        if field in rejected:
            continue
        value = overrides.get(field, proposal["value"])
        validate_answer(field, value)
        set_nested(state["answers"], field, value)
        if field not in answered_fields:
            answered_fields.append(field)
        applied.append(field)
    cv_import["status"] = "confirmed"
    cv_import["confirmed_at"] = utc_now()
    cv_import["applied_fields"] = applied
    cv_import["rejected_fields"] = sorted(rejected)
    state["answers"]["documents"]["cv_import_status"] = "confirmed"


def skip_cv_import(state: dict[str, Any], reason: str) -> None:
    local_cv_path(state)
    if not reason.strip():
        raise ValueError("a short reason is required when falling back to manual onboarding")
    state["cv_import"] = {"status": "manual", "proposals": {}, "reason": reason.strip(), "updated_at": utc_now()}
    state["answers"]["documents"]["cv_import_status"] = "manual"


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
        "schema_version": 4,
        "profile": answers["profile"],
        "constraints": answers["constraints"],
        "compensation": answers["compensation"],
        "permissions": answers["permissions"],
        "documents": answers["documents"],
        "integrations": answers["integrations"],
    }
    rules_document = {
        "schema_version": 2,
        "search": answers["search"],
        "evaluation": {"hard_exclusions": [], "preferred_signals": [], "unknown_is_not_match": True},
        "tracker": {"backend": "local_csv", "file": "tracker.csv", "update_policy": answers["permissions"]["tracker_updates"], "stable_identity": True},
        "communications": {
            "first_contact_style": "concise",
            "external_action_mode": answers["permissions"]["external_action_mode"],
            "external_action_mode_locked": answers["permissions"]["external_action_mode_locked"],
        },
        "human_path": {
            "enabled": True,
            "search_contacts": True,
            "search_recruiter_or_poster": True,
            "search_hiring_manager": True,
            "require_current_source": True,
        },
    }

    profile_path = workspace / "profile.yaml"
    rules_path = workspace / "rules.yaml"
    backup_once(profile_path)
    backup_once(rules_path)
    atomic_write_json(profile_path, profile_document)
    atomic_write_json(rules_path, rules_document)

    bank_path = story_bank_path(profile_path)
    legacy_evidence = answers.get("profile", {}).get("verified_evidence", [])
    bank_was_empty = not bank_path.exists() or bank_path.stat().st_size == 0
    stories = load_story_bank(bank_path, legacy_evidence=legacy_evidence)
    if stories and bank_was_empty:
        save_story_bank(bank_path, stories)

    state["status"] = "complete"
    state["completed_at"] = utc_now()
    state["updated_at"] = state["completed_at"]
    atomic_write_json(state_file(workspace), state)
    return {
        "status": "complete",
        "profile": str(profile_path),
        "rules": str(rules_path),
        "story_bank": str(bank_path),
        "story_count": len(stories),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, help="Private candidate workspace")
    commands = parser.add_subparsers(dest="command", required=True)
    start = commands.add_parser("start", help="Start or resume onboarding")
    start.add_argument("--reset", action="store_true", help="Reset only the onboarding checkpoint")
    start.add_argument("--lock-draft-only", action="store_true", help="Permanently lock this checkpoint/workspace to draft-only mode")
    answer = commands.add_parser("answer", help="Store one answer and checkpoint")
    answer.add_argument("--field", required=True)
    value_group = answer.add_mutually_exclusive_group(required=True)
    value_group.add_argument("--value")
    value_group.add_argument("--json-value")
    cv_propose = commands.add_parser("cv-propose", help="Stage CV-derived fields for user confirmation")
    proposal_group = cv_propose.add_mutually_exclusive_group(required=True)
    proposal_group.add_argument("--json-value")
    proposal_group.add_argument("--json-file")
    cv_confirm = commands.add_parser("cv-confirm", help="Apply pending CV proposals after user confirmation")
    cv_confirm.add_argument("--overrides-json", default="{}")
    cv_confirm.add_argument("--reject-fields-json", default="[]")
    cv_skip = commands.add_parser("cv-skip", help="Fall back to manual onboarding when local CV extraction is unavailable")
    cv_skip.add_argument("--reason", required=True)
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
                preserve_lock = False
                if path.exists():
                    preserve_lock = bool(load_state(workspace)["answers"]["permissions"].get("external_action_mode_locked", False))
                state = new_state(lock_draft_only=args.lock_draft_only or preserve_lock)
                atomic_write_json(path, state)
            if args.lock_draft_only:
                state["answers"]["permissions"]["external_action_mode"] = "draft_only"
                state["answers"]["permissions"]["external_action_mode_locked"] = True
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
        if args.command == "cv-propose":
            if args.json_file is not None:
                payload = json.loads(Path(args.json_file).expanduser().read_text(encoding="utf-8"))
            else:
                payload = json.loads(args.json_value)
            stage_cv_proposals(state, payload)
            state["updated_at"] = utc_now()
            atomic_write_json(path, state)
            print(json.dumps(status_payload(state), indent=2, ensure_ascii=False))
            return 0
        if args.command == "cv-confirm":
            confirm_cv_proposals(
                state,
                json.loads(args.overrides_json),
                json.loads(args.reject_fields_json),
            )
            state["updated_at"] = utc_now()
            atomic_write_json(path, state)
            print(json.dumps(status_payload(state), indent=2, ensure_ascii=False))
            return 0
        if args.command == "cv-skip":
            skip_cv_import(state, args.reason)
            state["updated_at"] = utc_now()
            atomic_write_json(path, state)
            print(json.dumps(status_payload(state), indent=2, ensure_ascii=False))
            return 0
        if args.command == "answer":
            value = json.loads(args.json_value) if args.json_value is not None else args.value
            validate_answer(args.field, value)
            permissions = state["answers"]["permissions"]
            if args.field == "permissions.external_action_mode" and permissions.get("external_action_mode_locked"):
                raise ValueError("external action mode is locked to draft_only for this profile/workspace")
            if args.field == "documents.primary_cv":
                if get_nested(state["answers"], "documents.has_cv") is not True:
                    raise ValueError("documents.primary_cv requires documents.has_cv to be true")
                value = str(validate_local_cv_file(value))
            if args.field in state.get("cv_import", {}).get("applied_fields", []):
                state["cv_import"]["applied_fields"].remove(args.field)
            set_nested(state["answers"], args.field, value)
            if args.field == "documents.has_cv":
                clear_cv_applied_fields(state)
                if value is False:
                    state["answers"]["documents"]["primary_cv"] = ""
                    reset_cv_import(state, "not_applicable")
                else:
                    reset_cv_import(state)
            elif args.field == "documents.primary_cv":
                clear_cv_applied_fields(state)
                reset_cv_import(state)
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
    except (ValueError, KeyError, TypeError, json.JSONDecodeError, OSError, UnicodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
