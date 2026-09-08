#!/usr/bin/env python3
"""Acquire explicit public ATS feeds read-only; never submit applications."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


FetchJson = Callable[[str], object]
SOURCE_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")
ACTION_KINDS = {"tracker_write", "application", "message", "contact"}
SYSTEM_PATH_SYMLINKS = {Path("/var"), Path("/tmp")}


def _parse_iso_day(value: Any, field: str) -> str:
    try:
        return date.fromisoformat(str(value)[:10]).isoformat()
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must start with an ISO YYYY-MM-DD date") from exc


def _epoch_day(value: Any, field: str) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be an epoch timestamp in milliseconds")
    try:
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc).date().isoformat()
    except (OverflowError, OSError, ValueError) as exc:
        raise ValueError(f"{field} is not a valid epoch timestamp") from exc


def _text(value: Any, field: str) -> str:
    result = str(value or "").strip()
    if not result:
        raise ValueError(f"{field} is required in the public feed")
    return result


def _source_identifier(value: str) -> str:
    if not SOURCE_IDENTIFIER.fullmatch(value):
        raise ValueError("source identifier must contain only letters, digits, underscores or hyphens")
    return value


def _provider_job_url(value: Any, field: str, *, hosts: set[str]) -> str:
    """Accept only a documented provider-hosted job page, never an application URL."""
    url = _text(value, field)
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    path_parts = [part for part in parsed.path.split("/") if part]
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port or host not in hosts or len(path_parts) != 3 or path_parts[1] != "jobs":
        raise ValueError(f"{field} must be an HTTPS provider-hosted job page")
    return url


def _lever_hosted_job_url(value: Any, field: str) -> str:
    """Accept only a documented Lever-hosted posting page, excluding /apply."""
    url = _text(value, field)
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    path_parts = [part for part in parsed.path.split("/") if part]
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port or host not in {"jobs.lever.co", "jobs.eu.lever.co"} or len(path_parts) != 2:
        raise ValueError(f"{field} must be an HTTPS Lever-hosted job page")
    return url


def greenhouse_url(board_token: str) -> str:
    return f"https://boards-api.greenhouse.io/v1/boards/{_source_identifier(board_token)}/jobs"


def lever_url(site: str) -> str:
    return f"https://api.lever.co/v0/postings/{_source_identifier(site)}?mode=json"


def normalize_greenhouse_jobs(payload: object, company: str) -> list[dict[str, str]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
        raise ValueError("Greenhouse public board response must contain a jobs array")
    result = []
    for index, raw in enumerate(payload["jobs"]):
        if not isinstance(raw, dict):
            raise ValueError(f"Greenhouse job {index} must be an object")
        location = raw.get("location")
        if not isinstance(location, dict):
            location = {}
        result.append({
            "source": "greenhouse_public_board",
            "company": _text(company, "company"),
            "role": _text(raw.get("title"), f"Greenhouse job {index}.title"),
            "location": str(location.get("name") or "Unknown").strip() or "Unknown",
            "canonical_url": _provider_job_url(
                raw.get("absolute_url"), f"Greenhouse job {index}.absolute_url", hosts={"boards.greenhouse.io"},
            ),
            "source_updated_on": _parse_iso_day(raw.get("updated_at"), f"Greenhouse job {index}.updated_at"),
            "work_mode": "",
            "employment_type": "",
            "external_job_id": _text(raw.get("id"), f"Greenhouse job {index}.id"),
        })
    return result


def normalize_lever_postings(payload: object, company: str) -> list[dict[str, str]]:
    if not isinstance(payload, list):
        raise ValueError("Lever public postings response must be an array")
    result = []
    for index, raw in enumerate(payload):
        if not isinstance(raw, dict):
            raise ValueError(f"Lever posting {index} must be an object")
        categories = raw.get("categories")
        if not isinstance(categories, dict):
            categories = {}
        result.append({
            "source": "lever_public_postings",
            "company": _text(company, "company"),
            "role": _text(raw.get("text"), f"Lever posting {index}.text"),
            "location": str(categories.get("location") or "Unknown").strip() or "Unknown",
            "canonical_url": _lever_hosted_job_url(raw.get("hostedUrl"), f"Lever posting {index}.hostedUrl"),
            "date_posted": _epoch_day(raw.get("createdAt"), f"Lever posting {index}.createdAt"),
            "work_mode": str(raw.get("workplaceType") or "").strip(),
            "employment_type": str(categories.get("commitment") or "").strip(),
            "external_job_id": _text(raw.get("id"), f"Lever posting {index}.id"),
        })
    return result


def acquire_public_feed(kind: str, source_identifier: str, company: str, as_of: date, fetch_json: FetchJson) -> dict[str, Any]:
    """Retrieve exactly one explicit public job feed through a GET-only adapter."""
    if kind == "greenhouse_public_board":
        url = greenhouse_url(source_identifier)
        vacancies = normalize_greenhouse_jobs(fetch_json(url), company)
    elif kind == "lever_public_postings":
        url = lever_url(source_identifier)
        vacancies = normalize_lever_postings(fetch_json(url), company)
    else:
        raise ValueError("kind must be greenhouse_public_board or lever_public_postings")
    return {
        "schema_version": 1,
        "mode": "explicit_public_read_only_acquisition",
        "adapter": kind,
        "source_identifier": source_identifier,
        "source_url": url,
        "retrieved_on": as_of.isoformat(),
        "external_actions": 1,
        "external_action_type": "read_only_get",
        "vacancies": vacancies,
        "guardrail": "This is one explicit public GET only; it does not authenticate, submit an application, write a tracker, contact anyone, or authorize any mutation.",
    }


def audit_catalog(catalog: dict[str, dict[str, str]], as_of: date, *, max_age_days: int) -> dict[str, Any]:
    """Review dated catalog metadata locally; this function never opens evidence URLs."""
    if max_age_days < 0:
        raise ValueError("max_age_days must be non-negative")
    review_required = []
    for portal_id, entry in sorted(catalog.items()):
        if not isinstance(entry, dict):
            raise ValueError(f"catalog.{portal_id} must be an object")
        if not str(entry.get("evidence_url", "")).startswith("https://"):
            raise ValueError(f"catalog.{portal_id}.evidence_url must be HTTPS")
        checked = _parse_iso_day(entry.get("evidence_checked_on"), f"catalog.{portal_id}.evidence_checked_on")
        if date.fromisoformat(checked) > as_of:
            raise ValueError(f"catalog.{portal_id}.evidence_checked_on cannot be later than as_of")
        if not str(entry.get("evidence_scope", "")).strip():
            raise ValueError(f"catalog.{portal_id}.evidence_scope is required")
        if (as_of - date.fromisoformat(checked)).days > max_age_days:
            review_required.append(portal_id)
    return {
        "schema_version": 1,
        "mode": "local_catalog_freshness_audit",
        "as_of": as_of.isoformat(),
        "max_age_days": max_age_days,
        "valid_entries": len(catalog),
        "review_required": review_required,
        "external_actions": 0,
        "guardrail": "This audit only identifies records for human source review; it does not open URLs or refresh evidence.",
    }


def propose_external_action(action: str, target: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Create a reviewable plan, never an executable mutation."""
    if action not in ACTION_KINDS:
        raise ValueError("action must be tracker_write, application, message or contact")
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    target = target.strip()
    if not target:
        raise ValueError("target is required")
    plan = {"domain": "career-copilot/external-action-draft/v1", "action": action, "target": target, "payload": payload}
    approval = hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
    return {
        "status": "draft_only",
        "action": action,
        "target": target,
        "payload": payload,
        "approval_sha256": approval,
        "external_actions": 0,
        "guardrail": "Reviewable draft only. It cannot execute; any future provider-specific mutation requires confirm_each_external, an exact approval hash, a current target read and verified readback.",
    }


class _NoRedirect(HTTPRedirectHandler):
    """Reject provider redirects rather than letting a public read leave its allowlist."""

    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


def _fetch_json(url: str) -> object:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "Career-Copilot/0.11 read-only"}, method="GET")
    opener = build_opener(_NoRedirect())
    with opener.open(request, timeout=20) as response:  # nosec B310: URL is constructed from a validated adapter identifier.
        return json.loads(response.read().decode("utf-8"))


def _validate_private_output(raw_path: Path) -> Path:
    """Reject unsafe output paths before the acquisition GET can run."""
    raw = raw_path.expanduser().absolute()
    for candidate in (raw, *raw.parents):
        if candidate.is_symlink() and candidate not in SYSTEM_PATH_SYMLINKS:
            raise ValueError("private output cannot be beneath a symlink")
    output = raw.resolve(strict=False)
    for parent in (output.parent, *output.parents):
        if (parent / ".git").exists():
            raise ValueError("private output must be outside a Git repository")
    return output


def _private_output(raw_path: Path) -> Path:
    output = _validate_private_output(raw_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(output.parent, 0o700)
    return output


def write_private_report(path: Path, report: dict[str, Any]) -> None:
    output = _private_output(path)
    temporary = output.with_suffix(output.suffix + ".tmp")
    if temporary.exists() and temporary.is_symlink():
        raise ValueError("private temporary output cannot be a symlink")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, output)
    if output.is_symlink() or output.stat().st_mode & 0o777 != 0o600:
        raise RuntimeError("private report write verification failed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", choices=("greenhouse_public_board", "lever_public_postings"), required=True)
    parser.add_argument("--source-identifier", required=True, help="Explicit public Greenhouse board token or Lever site identifier")
    parser.add_argument("--company", required=True, help="Candidate-supplied company label for this explicit source")
    parser.add_argument("--as-of", required=True, help="Explicit YYYY-MM-DD retrieval date")
    parser.add_argument("--output", required=True, help="Private JSON acquisition report outside Git")
    args = parser.parse_args()
    try:
        output = _validate_private_output(Path(args.output))
        report = acquire_public_feed(args.adapter, args.source_identifier, args.company, date.fromisoformat(args.as_of), _fetch_json)
        write_private_report(output, report)
        print(json.dumps({"mode": report["mode"], "adapter": report["adapter"], "vacancy_count": len(report["vacancies"]), "external_actions": report["external_actions"]}))
        return 0
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
