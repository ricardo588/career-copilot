#!/usr/bin/env python3
"""Create a private, read-only vacancy shortlist from an explicit local export."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

SYSTEM_PATH_SYMLINKS = {Path("/var"), Path("/tmp")}


def load_json(path: Path, field: str) -> dict[str, Any]:
    try:
        value = json.loads(path.expanduser().read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{field} must contain JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be a JSON object")
    return value


def parse_date(value: Any, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be an ISO YYYY-MM-DD date") from exc


def string_list(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{field} must be a list of non-empty strings")
    return [item.strip() for item in value]


def candidate_filters(profile: dict[str, Any]) -> dict[str, list[str]]:
    candidate_profile = profile.get("profile", {})
    constraints = profile.get("constraints", {})
    if not isinstance(candidate_profile, dict):
        raise ValueError("profile.profile must be an object")
    if not isinstance(constraints, dict):
        raise ValueError("profile.constraints must be an object")
    return {
        "target_roles": string_list(candidate_profile.get("target_roles"), "profile.profile.target_roles"),
        "target_seniority": string_list(candidate_profile.get("target_seniority"), "profile.profile.target_seniority"),
        "target_industries": string_list(candidate_profile.get("target_industries"), "profile.profile.target_industries"),
        "countries": string_list(constraints.get("countries"), "profile.constraints.countries"),
        "locations": string_list(constraints.get("locations"), "profile.constraints.locations"),
        "work_modes": string_list(constraints.get("work_modes"), "profile.constraints.work_modes"),
        "employment_types": string_list(constraints.get("employment_types"), "profile.constraints.employment_types"),
    }


def private_input_file(raw_path: Path, field: str) -> Path:
    raw_absolute = raw_path.expanduser().absolute()
    for candidate in (raw_absolute, *raw_absolute.parents):
        if candidate.is_symlink() and candidate not in SYSTEM_PATH_SYMLINKS:
            raise ValueError(f"{field} must not be beneath a symlink")
    path = raw_absolute.resolve(strict=False)
    if not path.is_file():
        raise ValueError(f"{field} must be an existing file")
    for parent in (path.parent, *path.parents):
        if (parent / ".git").exists():
            raise ValueError(f"{field} must be outside a Git repository")
    return path


def private_path(raw_path: Path) -> Path:
    raw_absolute = raw_path.expanduser().absolute()
    for candidate in (raw_absolute, *raw_absolute.parents):
        if candidate.is_symlink() and candidate not in SYSTEM_PATH_SYMLINKS:
            raise ValueError("private discovery report cannot be beneath a symlink")
    path = raw_absolute.resolve(strict=False)
    for parent in (path.parent, *path.parents):
        if (parent / ".git").exists():
            raise ValueError("private discovery report must be outside a Git repository")
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    return path


def canonicalize_url(value: str) -> str:
    """Normalize a supplied HTTP(S) URL for stable private shortlist identity."""
    parsed = urlsplit(value)
    if parsed.scheme.casefold() not in {"https", "http"} or not parsed.netloc:
        raise ValueError("vacancies.canonical_url must be an http(s) URL")
    query = [
        (key, item)
        for key, item in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.casefold().startswith(("utm_", "trk", "tracking"))
    ]
    return urlunsplit((
        parsed.scheme.casefold(),
        parsed.netloc.casefold(),
        parsed.path.rstrip("/"),
        urlencode(query, doseq=True),
        "",
    ))


def validate_vacancy(raw: Any, as_of: date) -> dict[str, str]:
    if not isinstance(raw, dict):
        raise ValueError("vacancies entries must be JSON objects")
    result: dict[str, str] = {}
    for field in ("source", "company", "role", "location", "canonical_url", "date_posted"):
        value = raw.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"vacancies.{field} must be a non-empty string")
        result[field] = value.strip()
    result["canonical_url"] = canonicalize_url(result["canonical_url"])
    if parse_date(result["date_posted"], "vacancies.date_posted") > as_of:
        raise ValueError("vacancies.date_posted cannot be later than as_of")
    for optional in ("work_mode", "employment_type", "external_job_id"):
        value = raw.get(optional, "")
        if value is not None and not isinstance(value, str):
            raise ValueError(f"vacancies.{optional} must be a string")
        result[optional] = str(value or "").strip()
    return result


def discover_vacancies(profile: dict[str, Any], rules: dict[str, Any], payload: dict[str, Any], as_of: date) -> dict[str, Any]:
    search = rules.get("search")
    if not isinstance(search, dict):
        raise ValueError("rules.search must be an object")
    selected_sources = string_list(search.get("selected_job_portals"), "rules.search.selected_job_portals")
    if not selected_sources:
        raise ValueError("rules.search.selected_job_portals must contain at least one explicitly selected source")
    targets = {item.casefold() for item in string_list(search.get("target_companies"), "rules.search.target_companies")}
    freshness_days = search.get("freshness_days", 14)
    if isinstance(freshness_days, bool) or not isinstance(freshness_days, int) or not 1 <= freshness_days <= 365:
        raise ValueError("rules.search.freshness_days must be an integer from 1 to 365")
    vacancies = payload.get("vacancies")
    if not isinstance(vacancies, list):
        raise ValueError("import.vacancies must be a JSON array")
    selected = {item.casefold() for item in selected_sources}
    shortlist: list[dict[str, Any]] = []
    discarded: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for raw in vacancies:
        vacancy = validate_vacancy(raw, as_of)
        if vacancy["source"].casefold() not in selected:
            discarded.append({"canonical_url": vacancy["canonical_url"], "reason": "source_not_selected"})
            continue
        if (as_of - parse_date(vacancy["date_posted"], "vacancies.date_posted")).days > freshness_days:
            discarded.append({"canonical_url": vacancy["canonical_url"], "reason": "stale_posting"})
            continue
        if vacancy["canonical_url"] in seen_urls:
            discarded.append({"canonical_url": vacancy["canonical_url"], "reason": "duplicate_canonical_url"})
            continue
        seen_urls.add(vacancy["canonical_url"])
        shortlist.append({
            **vacancy,
            "target_company": vacancy["company"].casefold() in targets,
            "canonical_verification": "required_before_evaluation_or_tracker_write",
        })
    return {
        "schema_version": 1,
        "mode": "private_import_read_only",
        "as_of": as_of.isoformat(),
        "external_actions": 0,
        "candidate_filters": candidate_filters(profile),
        "selected_sources": selected_sources,
        "shortlist": shortlist,
        "discarded": discarded,
        "guardrail": "Import is private and read-only; shortlist entries are not tracker rows or application authorization.",
    }


def write_private_report(path: Path, report: dict[str, Any]) -> None:
    destination = private_path(path)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    if temporary.exists() and temporary.is_symlink():
        raise ValueError("private discovery temporary file cannot be a symlink")
    temporary.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, destination)
    if destination.is_symlink() or destination.stat().st_mode & 0o777 != 0o600:
        raise RuntimeError("private discovery report write verification failed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, help="Private profile JSON")
    parser.add_argument("--rules", required=True, help="Private rules JSON")
    parser.add_argument("--import-file", dest="import_file", required=True, help="Explicit private vacancy-export JSON")
    parser.add_argument("--output", required=True, help="Private shortlist report JSON")
    parser.add_argument("--as-of", required=True, help="YYYY-MM-DD")
    args = parser.parse_args()
    try:
        report = discover_vacancies(
            load_json(private_input_file(Path(args.profile), "profile"), "profile"),
            load_json(private_input_file(Path(args.rules), "rules"), "rules"),
            load_json(private_input_file(Path(args.import_file), "import-file"), "import"),
            parse_date(args.as_of, "as_of"),
        )
        write_private_report(Path(args.output), report)
        print(json.dumps({"mode": report["mode"], "shortlist_count": len(report["shortlist"]), "discarded_count": len(report["discarded"]), "external_actions": 0}, indent=2))
        return 0
    except (OSError, TypeError, ValueError, UnicodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
