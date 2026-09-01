#!/usr/bin/env python3
"""Maintain a private, evidence-backed target-company registry without authorizing contact."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
IDENTITY_STATUSES = {"confirmed", "unknown", "confidential"}
ACTIVE_STATUSES = {"active", "archived"}
PREFERENCE_ASSERTION_WORDS = {"best", "excellent", "good company", "great company", "definitely hiring", "is hiring"}


def load_document(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.expanduser().read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} must contain JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object in {path}")
    return value


def parse_date(value: Any, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be an ISO YYYY-MM-DD date") from exc


def private_path(raw_path: Path) -> Path:
    expanded = raw_path.expanduser()
    if expanded.is_symlink():
        raise ValueError("private target-company registry cannot be a symlink")
    path = expanded.resolve(strict=False)
    for parent in (path.parent, *path.parents):
        if parent.is_symlink():
            raise ValueError("private target-company registry cannot be beneath a symlink")
        if (parent / ".git").exists():
            raise ValueError("private target-company registry must be outside a Git repository")
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    return path


def write_registry(path: Path, registry: dict[str, Any]) -> None:
    destination = private_path(path)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    if temporary.exists() and temporary.is_symlink():
        raise ValueError("private target-company temporary file cannot be a symlink")
    temporary.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, destination)
    if destination.is_symlink() or destination.stat().st_mode & 0o777 != 0o600:
        raise RuntimeError("private target-company registry write verification failed")


def load_registry(path: Path) -> dict[str, Any]:
    destination = private_path(path)
    if not destination.exists():
        return {"schema_version": SCHEMA_VERSION, "companies": []}
    if destination.is_symlink():
        raise ValueError("private target-company registry cannot be a symlink")
    registry = load_document(destination)
    validate_registry(registry)
    return registry


def _normalized_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def _company_id(company: str, identity: dict[str, Any]) -> str:
    basis = company or str(identity.get("status", "unknown")) + "\n" + str(identity.get("reason", ""))
    return "company-" + hashlib.sha256(basis.casefold().encode("utf-8")).hexdigest()[:12]


def _string_list(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{field} must be a list of non-empty strings")
    return [item.strip() for item in value]


def _validate_source_item(item: Any, field: str, as_of: date, *, require_status: bool = False) -> dict[str, str]:
    if not isinstance(item, dict):
        raise ValueError(f"{field} entries must be objects")
    summary = str(item.get("summary", "")).strip()
    source_url = str(item.get("source_url", "")).strip()
    checked_at = str(item.get("checked_at", "")).strip()
    if not summary:
        raise ValueError(f"{field}.summary is required")
    if not source_url.startswith(("https://", "http://")):
        raise ValueError(f"{field}.source_url must be an http(s) URL")
    if parse_date(checked_at, f"{field}.checked_at") > as_of:
        raise ValueError(f"{field}.checked_at cannot be later than as_of")
    result = {"summary": summary, "source_url": source_url, "checked_at": checked_at}
    if require_status:
        status = str(item.get("status", "")).strip()
        if status not in {"confirmed", "none_found", "unverified"}:
            raise ValueError(f"{field}.status must be confirmed, none_found or unverified")
        result["status"] = status
    return result


def _identity(raw: Any, company: str) -> dict[str, str]:
    if raw is None:
        if not company:
            raise ValueError("company is required unless client_identity is explicitly unknown or confidential")
        return {"status": "confirmed"}
    if not isinstance(raw, dict):
        raise ValueError("client_identity must be an object")
    status = str(raw.get("status", "")).strip()
    if status not in IDENTITY_STATUSES:
        raise ValueError("client_identity.status must be confirmed, unknown or confidential")
    if status == "confirmed" and not company:
        raise ValueError("confirmed client identity requires company")
    if status in {"unknown", "confidential"} and company:
        raise ValueError("unknown/confidential client identity cannot include a company name")
    result = {"status": status}
    reason = str(raw.get("reason", "")).strip()
    if reason:
        result["reason"] = reason
    return result


def _preference(raw: Any, as_of: date) -> dict[str, str]:
    if not isinstance(raw, dict):
        raise ValueError("candidate_preference must be an object")
    statement = str(raw.get("statement", "")).strip()
    if not statement:
        raise ValueError("candidate_preference.statement is required")
    normalized = statement.casefold()
    if any(word in normalized for word in PREFERENCE_ASSERTION_WORDS):
        raise ValueError("candidate preference must describe the candidate's interest, not assert company quality or hiring")
    declared_at = str(raw.get("declared_at", "")).strip()
    if parse_date(declared_at, "candidate_preference.declared_at") > as_of:
        raise ValueError("candidate_preference.declared_at cannot be later than as_of")
    return {"kind": "candidate_preference", "statement": statement, "declared_at": declared_at}


def _latest_checked(items: list[dict[str, str]]) -> str:
    return max((item["checked_at"] for item in items), default="")


def _dedupe_append(existing: list[dict[str, str]], additions: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = {(item.get("summary"), item.get("source_url"), item.get("checked_at"), item.get("status", "")) for item in existing}
    result = list(existing)
    for item in additions:
        signature = (item.get("summary"), item.get("source_url"), item.get("checked_at"), item.get("status", ""))
        if signature not in seen:
            result.append(item)
            seen.add(signature)
    return result


def validate_registry(registry: dict[str, Any]) -> None:
    if registry.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported target-company registry schema")
    companies = registry.get("companies")
    if not isinstance(companies, list) or any(not isinstance(item, dict) for item in companies):
        raise ValueError("registry.companies must be a list of objects")
    ids = [str(item.get("id", "")) for item in companies]
    if any(not item for item in ids) or len(ids) != len(set(ids)):
        raise ValueError("registry company identities must be unique")


def _new_company(record: dict[str, Any], as_of: date) -> dict[str, Any]:
    company_input = str(record.get("company", "")).strip()
    identity = _identity(record.get("client_identity"), company_input)
    company = company_input or ("Unknown client" if identity["status"] == "unknown" else "Confidential client")
    signals = [_validate_source_item(item, "current_signals", as_of) for item in record.get("current_signals", [])]
    human_paths = [_validate_source_item(item, "human_paths", as_of, require_status=True) for item in record.get("human_paths", [])]
    if not signals:
        raise ValueError("at least one sourced current_signals entry is required")
    created_at = as_of.isoformat()
    return {
        "id": _company_id(company_input, identity),
        "company": company,
        "client_identity": identity,
        "status": "active",
        "candidate_preference": _preference(record.get("candidate_preference"), as_of),
        "role_families": _string_list(record.get("role_families"), "role_families"),
        "relevant_units": _string_list(record.get("relevant_units"), "relevant_units"),
        "current_signals": signals,
        "human_paths": human_paths,
        "company_last_verified": _latest_checked(signals),
        "human_path_last_verified": _latest_checked(human_paths),
        "risks": _string_list(record.get("risks"), "risks"),
        "questions": _string_list(record.get("questions"), "questions"),
        "next_research_action": str(record.get("next_research_action", "")).strip(),
        "contact_authorization": "not_granted_by_research",
        "history": [{"event": "added", "recorded_at": created_at, "signal_count": len(signals), "human_path_count": len(human_paths)}],
    }


def upsert_registry(registry: dict[str, Any], record: dict[str, Any], as_of: date) -> tuple[dict[str, Any], dict[str, str]]:
    validate_registry(registry)
    candidate = _new_company(record, as_of)
    companies = [dict(item) for item in registry["companies"]]
    existing_index = next((index for index, item in enumerate(companies) if item.get("id") == candidate["id"]), None)
    if existing_index is None:
        companies.append(candidate)
        return {"schema_version": SCHEMA_VERSION, "companies": companies}, {"action": "added", "id": candidate["id"]}
    existing = companies[existing_index]
    if existing.get("status") not in ACTIVE_STATUSES:
        raise ValueError("existing company status is invalid")
    existing_signals = [item for item in existing.get("current_signals", []) if isinstance(item, dict)]
    existing_paths = [item for item in existing.get("human_paths", []) if isinstance(item, dict)]
    candidate["current_signals"] = _dedupe_append(existing_signals, candidate["current_signals"])
    candidate["human_paths"] = _dedupe_append(existing_paths, candidate["human_paths"])
    candidate["company_last_verified"] = _latest_checked(candidate["current_signals"])
    candidate["human_path_last_verified"] = _latest_checked(candidate["human_paths"])
    candidate["status"] = existing.get("status", "active")
    if candidate["status"] == "archived":
        candidate["archived_at"] = existing.get("archived_at", "")
    candidate["history"] = list(existing.get("history", [])) + [{"event": "refreshed", "recorded_at": as_of.isoformat(), "signal_count": len(record.get("current_signals", [])), "human_path_count": len(record.get("human_paths", []))}]
    companies[existing_index] = candidate
    return {"schema_version": SCHEMA_VERSION, "companies": companies}, {"action": "refreshed", "id": candidate["id"]}


def archive_company(registry: dict[str, Any], company_id: str, as_of: date, reason: str) -> tuple[dict[str, Any], dict[str, str]]:
    validate_registry(registry)
    reason = reason.strip()
    if not reason:
        raise ValueError("archive reason is required")
    companies = [dict(item) for item in registry["companies"]]
    for index, item in enumerate(companies):
        if item.get("id") != company_id:
            continue
        if item.get("status") == "archived":
            return {"schema_version": SCHEMA_VERSION, "companies": companies}, {"action": "already_archived", "id": company_id}
        item["status"] = "archived"
        item["archived_at"] = as_of.isoformat()
        item["archive_reason"] = reason
        item["history"] = list(item.get("history", [])) + [{"event": "archived", "recorded_at": as_of.isoformat(), "reason": reason}]
        companies[index] = item
        return {"schema_version": SCHEMA_VERSION, "companies": companies}, {"action": "archived", "id": company_id}
    raise ValueError("company identity was not found")


def review_registry(registry: dict[str, Any], as_of: date, *, company_stale_after_days: int, human_path_stale_after_days: int) -> dict[str, Any]:
    validate_registry(registry)
    if company_stale_after_days < 0 or human_path_stale_after_days < 0:
        raise ValueError("stale-after day values must be non-negative")
    company_stale: list[str] = []
    human_path_stale: list[str] = []
    active_count = 0
    for item in registry["companies"]:
        if item.get("status") != "active":
            continue
        active_count += 1
        company_checked = str(item.get("company_last_verified", ""))
        human_checked = str(item.get("human_path_last_verified", ""))
        if not company_checked or (as_of - parse_date(company_checked, "company_last_verified")).days > company_stale_after_days:
            company_stale.append(str(item["id"]))
        if not human_checked or (as_of - parse_date(human_checked, "human_path_last_verified")).days > human_path_stale_after_days:
            human_path_stale.append(str(item["id"]))
    return {"as_of": as_of.isoformat(), "active_count": active_count, "company_evidence_stale": company_stale, "human_path_evidence_stale": human_path_stale, "mutation": "none"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", required=True, help="Private JSON registry outside Git")
    parser.add_argument("--as-of", required=True, help="Explicit YYYY-MM-DD date")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--upsert", help="Private JSON target-company input")
    mode.add_argument("--archive", help="Stable company ID to archive")
    mode.add_argument("--review", action="store_true", help="Read-only evidence freshness review")
    parser.add_argument("--reason", help="Required when archiving")
    parser.add_argument("--company-stale-after-days", type=int, default=30)
    parser.add_argument("--human-path-stale-after-days", type=int, default=30)
    args = parser.parse_args()
    try:
        as_of = parse_date(args.as_of, "as_of")
        registry_path = Path(args.registry)
        registry = load_registry(registry_path)
        if args.review:
            result = review_registry(registry, as_of, company_stale_after_days=args.company_stale_after_days, human_path_stale_after_days=args.human_path_stale_after_days)
        elif args.archive:
            registry, result = archive_company(registry, args.archive, as_of, args.reason or "")
            write_registry(registry_path, registry)
        else:
            registry, result = upsert_registry(registry, load_document(Path(args.upsert)), as_of)
            write_registry(registry_path, registry)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
