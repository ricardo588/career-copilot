#!/usr/bin/env python3
"""Local, deterministic, read-only reviews for explicit Hunter snapshots.

This module intentionally has no network, browser, credential, or external-action
path. It reads user-supplied local files and writes only explicit private outputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


class ReviewError(ValueError):
    """Raised when an input or private output contract is invalid."""


REQUIRED_FIELDS = (
    "business_id", "company", "role", "source", "status", "result",
    "status_date", "notes", "canonical_url", "contact",
)
TRACKING_PREFIXES = ("utm_", "trk", "tracking")
SPANISH_MONTHS = {
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
    "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12,
}
SYSTEM_PATH_SYMLINKS = {Path("/var"), Path("/tmp")}


def scalar(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple, set)):
        raise ReviewError("snapshot values must be scalar")
    return str(value).strip()


def parse_mapping(text: str) -> dict[str, Any]:
    """Parse the deliberately small public mapping YAML grammar without PyYAML."""
    sections: dict[str, Any] = {"fields": {}, "status_groups": {}, "review_thresholds": {}}
    current: str | None = None
    current_group: str | None = None
    seen_sections: set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        token = line.strip()
        if indent == 0:
            if token == "schema_version: 1":
                continue
            if token.endswith(":") and token[:-1] in sections:
                if token[:-1] in seen_sections:
                    raise ReviewError("duplicate mapping section")
                seen_sections.add(token[:-1])
                current, current_group = token[:-1], None
                continue
            raise ReviewError("invalid mapping structure")
        if current == "fields" and indent == 2 and ":" in token:
            key, value = token.split(":", 1)
            key = key.strip()
            if key in sections["fields"]:
                raise ReviewError("duplicate mapping key")
            sections["fields"][key] = scalar(value.strip().strip('"'))
        elif current == "status_groups":
            if indent == 2 and token.endswith(":"):
                current_group = token[:-1]
                if current_group in sections["status_groups"]:
                    raise ReviewError("duplicate mapping key")
                sections["status_groups"][current_group] = []
            elif indent == 4 and token.startswith("-") and current_group:
                sections["status_groups"][current_group].append(scalar(token[1:].strip().strip('"')))
            elif indent == 2 and ":" in token:
                key, value = token.split(":", 1)
                if value.strip() != "[]":
                    raise ReviewError("status group must be a list")
                if key.strip() in sections["status_groups"]:
                    raise ReviewError("duplicate mapping key")
                sections["status_groups"][key.strip()] = []
                current_group = key.strip()
            else:
                raise ReviewError("invalid status_groups mapping")
        elif current == "review_thresholds" and indent == 2 and ":" in token:
            key, value = token.split(":", 1)
            key = key.strip()
            if key in sections["review_thresholds"]:
                raise ReviewError("duplicate mapping key")
            raw = scalar(value)
            sections["review_thresholds"][key] = None if raw == "null" else int(raw)
        else:
            raise ReviewError("invalid mapping structure")
    if set(sections["fields"]) != set(REQUIRED_FIELDS):
        raise ReviewError("mapping must define exactly the required fields")
    if len(set(sections["fields"].values())) != len(REQUIRED_FIELDS):
        raise ReviewError("mapping fields must use unique headers")
    if set(sections["status_groups"]) != {"terminal", "active", "review"}:
        raise ReviewError("mapping must define terminal, active, and review groups")
    if set(sections["review_thresholds"]) != {"status_age_days"}:
        raise ReviewError("review_thresholds must define exactly status_age_days")
    statuses = [status for values in sections["status_groups"].values() for status in values]
    if len(set(statuses)) != len(statuses):
        raise ReviewError("a status cannot appear in multiple status groups")
    threshold = sections["review_thresholds"].get("status_age_days")
    if threshold is not None and threshold < 0:
        raise ReviewError("status_age_days must be null or a non-negative integer")
    return sections


def load_snapshot_bytes(payload: bytes) -> dict[str, Any]:
    try:
        raw = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReviewError(f"invalid snapshot: {error}") from error
    if not isinstance(raw, dict) or not isinstance(raw.get("headers"), list) or not isinstance(raw.get("rows"), list):
        raise ReviewError("snapshot requires headers and rows lists")
    headers = raw["headers"]
    if any(not isinstance(item, str) or item != item.strip() or not item for item in headers):
        raise ReviewError("snapshot headers must be non-empty trimmed strings")
    if len(set(headers)) != len(headers):
        raise ReviewError("duplicate snapshot headers")
    return raw


def load_snapshot(path: Path) -> dict[str, Any]:
    try:
        return load_snapshot_bytes(path.read_bytes())
    except OSError as error:
        raise ReviewError(f"invalid snapshot: {error}") from error


def canonicalize_url(value: Any) -> tuple[str, str]:
    raw = scalar(value)
    if not raw:
        return "", "missing"
    parts = urlsplit(raw)
    if not parts.scheme or not parts.netloc:
        return raw, "invalid"
    query = [(key, item) for key, item in parse_qsl(parts.query, keep_blank_values=True)
             if not key.casefold().startswith(TRACKING_PREFIXES)]
    return urlunsplit((parts.scheme.casefold(), parts.netloc.casefold(), parts.path.rstrip("/"), urlencode(query), "")), "valid"


def parse_status_date(value: str) -> tuple[date | None, str]:
    if not value:
        return None, "missing"
    try:
        return date.fromisoformat(value), "valid"
    except ValueError:
        pass
    match = re.fullmatch(r"(\d{1,2})/([A-Za-z]{3})/(\d{4})", value.casefold())
    if match and match.group(2) in SPANISH_MONTHS:
        try:
            return date(int(match.group(3)), SPANISH_MONTHS[match.group(2)], int(match.group(1))), "valid"
        except ValueError:
            pass
    return None, "invalid"


def normalize(snapshot: dict[str, Any], mapping: dict[str, Any], as_of: date) -> list[dict[str, Any]]:
    headers = snapshot["headers"]
    fields = mapping["fields"]
    required_headers = set(fields.values())
    missing = sorted(required_headers - set(headers))
    if missing:
        raise ReviewError(f"missing required snapshot headers: {', '.join(missing)}")
    rows: list[dict[str, Any]] = []
    seen_physical: set[int] = set()
    groups = mapping["status_groups"]
    status_lookup = {status: group for group, values in groups.items() for status in values}
    for raw in snapshot["rows"]:
        if not isinstance(raw, dict) or not isinstance(raw.get("physical_row"), int) or raw["physical_row"] < 1:
            raise ReviewError("physical_row must be a positive integer")
        physical = raw["physical_row"]
        if physical in seen_physical:
            raise ReviewError(f"duplicate physical_row: {physical}")
        seen_physical.add(physical)
        values = raw.get("values")
        if not isinstance(values, dict) or any(key not in headers for key in values):
            raise ReviewError("row values must map known headers")
        data = {logical: scalar(values.get(header, "")) for logical, header in fields.items()}
        raw_id = data["business_id"]
        identity_state = "valid" if re.fullmatch(r"[1-9][0-9]*", raw_id) else ("missing_id" if not raw_id else "malformed_id")
        url, url_state = canonicalize_url(data["canonical_url"])
        parsed_date, date_state = parse_status_date(data["status_date"])
        status_group = status_lookup.get(data["status"], "unclassified")
        rows.append({**data, "physical_row": physical, "opportunity_id": raw_id,
                     "identity_state": identity_state, "canonical_url_normalized": url,
                     "url_state": url_state, "status_date_parsed": parsed_date,
                     "status_date_state": date_state, "status_group": status_group,
                     "notes_present": bool(data["notes"])})
    ids = Counter(row["opportunity_id"] for row in rows if row["identity_state"] == "valid")
    for row in rows:
        if row["identity_state"] == "valid" and ids[row["opportunity_id"]] > 1:
            row["identity_state"] = "duplicate_id"
    return sorted(rows, key=lambda item: item["physical_row"])


def report_for(rows: list[dict[str, Any]], snapshot_bytes: bytes, snapshot: dict[str, Any], as_of: date, status_age_days: int | None) -> dict[str, Any]:
    valid_urls: dict[str, list[str]] = {}
    for item in rows:
        if item["url_state"] == "valid":
            valid_urls.setdefault(item["canonical_url_normalized"], []).append(item["opportunity_id"])
    duplicate_urls = [{"canonical_url_normalized": url, "opportunity_ids": ids}
                      for url, ids in sorted(valid_urls.items()) if len(ids) > 1]
    prioritized_reviews = []
    if status_age_days is not None:
        for item in rows:
            if item["status_date_state"] == "valid" and (as_of - item["status_date_parsed"]).days > status_age_days:
                prioritized_reviews.append({"opportunity_id": item["opportunity_id"], "reason": "status_review_due"})
    report = {
        "schema_version": 1,
        "as_of": as_of.isoformat(),
        "snapshot_sha256": hashlib.sha256(snapshot_bytes).hexdigest(),
        "retrieved_at": snapshot.get("metadata", {}).get("retrieved_at"),
        "summary": {"rows": len(rows)},
        "integrity": {
            "missing_ids": sum(item["identity_state"] == "missing_id" for item in rows),
            "malformed_ids": sum(item["identity_state"] == "malformed_id" for item in rows),
            "duplicate_ids": sorted({item["opportunity_id"] for item in rows if item["identity_state"] == "duplicate_id"}),
            "unclassified_statuses": sorted({item["status"] for item in rows if item["status_group"] == "unclassified"}),
        },
        "funnel": {"status_groups": dict(sorted(Counter(item["status_group"] for item in rows).items())),
                   "status_raw": dict(sorted(Counter(item["status"] for item in rows).items())),
                   "result_raw": dict(sorted(Counter(item["result"] for item in rows).items()))},
        "sourcing": {"by_source": dict(sorted(Counter(item["source"] or "unclassified" for item in rows).items()))},
        "evidence_quality": {
            "missing_urls": sum(item["url_state"] == "missing" for item in rows),
            "invalid_urls": sum(item["url_state"] == "invalid" for item in rows),
            "missing_status_dates": sum(item["status_date_state"] == "missing" for item in rows),
            "invalid_status_dates": sum(item["status_date_state"] == "invalid" for item in rows),
            "contact_signals_unverified": sum(bool(item["contact"]) for item in rows),
            "notes_present": sum(item["notes_present"] for item in rows),
        },
        "identity_risks": {"duplicate_canonical_urls": duplicate_urls, "possible_duplicate_requires_review": []},
        "prioritized_reviews": sorted(prioritized_reviews, key=lambda item: (item["reason"], item["opportunity_id"])),
        "limitations": ["No external sources were consulted; vacancy freshness, fit, relationships, authorization, applications, and results were not verified."],
        "safety": {"external_actions": 0, "network_requests": 0, "input_mutated": False, "output_schema_valid": True},
    }
    return report


def _canonical_system_path(path: Path) -> Path:
    for symlink in SYSTEM_PATH_SYMLINKS:
        if path == symlink or symlink in path.parents:
            return symlink.resolve() / path.relative_to(symlink)
    return path


def _open_absolute_directory(path: Path, *, create: bool) -> int:
    """Walk an absolute path from / without following any user-controlled link."""
    if not path.is_absolute():
        raise ReviewError("private path must be absolute")
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    root_fd = os.open("/", flags)
    current_fd = root_fd
    try:
        for component in path.parts[1:]:
            if create:
                try:
                    os.mkdir(component, mode=0o700, dir_fd=current_fd)
                except FileExistsError:
                    pass
            next_fd = os.open(component, flags, dir_fd=current_fd)
            if current_fd != root_fd:
                os.close(current_fd)
            current_fd = next_fd
        if current_fd == root_fd:
            root_fd = -1
        return current_fd
    except Exception:
        if current_fd != root_fd:
            os.close(current_fd)
        if root_fd >= 0:
            os.close(root_fd)
            root_fd = -1
        raise
    finally:
        if root_fd >= 0:
            os.close(root_fd)


def private_workspace(raw: str) -> Path:
    workspace = _canonical_system_path(Path(os.path.abspath(os.path.expanduser(raw))))
    repository = Path(__file__).resolve().parents[3]
    if workspace == repository or repository in workspace.parents or workspace in repository.parents:
        raise ReviewError("private workspace cannot contain or be inside the distribution repository")
    for ancestor in (workspace, *workspace.parents):
        if (ancestor / ".git").exists():
            raise ReviewError("private workspace cannot be beneath a Git repository")
    try:
        descriptor = _open_absolute_directory(workspace, create=True)
    except OSError as error:
        raise ReviewError("private workspace cannot be beneath a symlink") from error
    try:
        os.fchmod(descriptor, 0o700)
    finally:
        os.close(descriptor)
    return workspace


def open_private_workspace(raw: str) -> tuple[Path, int]:
    workspace = private_workspace(raw)
    try:
        return workspace, _open_absolute_directory(workspace, create=False)
    except OSError as error:
        raise ReviewError("private workspace cannot be beneath a symlink") from error


def private_output(workspace: Path, raw: str) -> Path:
    workspace = _canonical_system_path(workspace)
    path = _canonical_system_path(Path(os.path.abspath(os.path.expanduser(raw))))
    for ancestor in (path, *path.parents):
        if ancestor.is_symlink() and ancestor not in SYSTEM_PATH_SYMLINKS:
            raise ReviewError("output cannot be beneath a symlink")
    if workspace not in (path, *path.parents):
        raise ReviewError("output must be within the private workspace")
    relative = path.relative_to(workspace)
    if not relative.name or ".." in relative.parts:
        raise ReviewError("invalid private output path")
    return path


def private_input(workspace: Path, raw: str, label: str) -> Path:
    workspace = _canonical_system_path(workspace)
    path = _canonical_system_path(Path(os.path.abspath(os.path.expanduser(raw))))
    for ancestor in (path, *path.parents):
        if ancestor.is_symlink() and ancestor not in SYSTEM_PATH_SYMLINKS:
            raise ReviewError(f"{label} cannot be beneath a symlink")
        if (ancestor / ".git").exists():
            raise ReviewError(f"{label} cannot be beneath a Git repository")
    if workspace not in (path, *path.parents):
        raise ReviewError(f"{label} must be within the private workspace")
    if not path.is_file():
        raise ReviewError(f"{label} must be an existing regular file")
    return path


def secure_read_private_input(workspace: Path, workspace_fd: int, path: Path, label: str) -> bytes:
    relative = path.relative_to(workspace)
    parent_fd = os.dup(workspace_fd)
    try:
        for component in relative.parts[:-1]:
            next_fd = os.open(component, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0), dir_fd=parent_fd)
            os.close(parent_fd)
            parent_fd = next_fd
        descriptor = os.open(relative.name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=parent_fd)
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise ReviewError(f"{label} must be an existing regular file")
            with os.fdopen(descriptor, "rb") as handle:
                descriptor = -1
                return handle.read()
        finally:
            if descriptor >= 0:
                os.close(descriptor)
    except OSError as error:
        raise ReviewError(f"{label} cannot be read safely from the private workspace") from error
    finally:
        os.close(parent_fd)


def markdown_for(artifact: dict[str, Any]) -> str:
    if "summary" in artifact:
        return "# Hunter process review\n\n" + f"- Rows: {artifact['summary']['rows']}\n- As of: {artifact['as_of']}\n- Snapshot SHA-256: `{artifact['snapshot_sha256']}`\n"
    opportunity = artifact["opportunity"]
    return "# Hunter decision packet\n\n" + "\n".join([
        f"- No: {opportunity['No']}", f"- Company: {opportunity['company']}", f"- Role: {opportunity['role']}",
        f"- Recommendation: {artifact['recommendation']}", "", artifact["authorization_limit"], "",
    ])


def _secure_parent_fd(workspace: Path, workspace_fd: int, destination: Path) -> tuple[int, str]:
    """Open the output parent through no-follow descriptors anchored at workspace."""
    try:
        relative = destination.relative_to(workspace)
    except ValueError as error:
        raise ReviewError("output must be within the private workspace") from error
    if not relative.name or relative.is_absolute() or ".." in relative.parts:
        raise ReviewError("invalid private output path")
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory = getattr(os, "O_DIRECTORY", 0)
    root_fd = os.dup(workspace_fd)
    current_fd = root_fd
    try:
        for component in relative.parts[:-1]:
            try:
                os.mkdir(component, mode=0o700, dir_fd=current_fd)
            except FileExistsError:
                pass
            next_fd = os.open(component, os.O_RDONLY | directory | nofollow, dir_fd=current_fd)
            if current_fd != root_fd:
                os.close(current_fd)
            current_fd = next_fd
            os.fchmod(current_fd, 0o700)
        if current_fd == root_fd:
            root_fd = -1
        return current_fd, relative.name
    except Exception:
        if current_fd != root_fd:
            os.close(current_fd)
        if root_fd >= 0:
            os.close(root_fd)
            root_fd = -1
        raise
    finally:
        if root_fd >= 0:
            os.close(root_fd)


def _ensure_workspace_not_git(workspace_fd: int) -> None:
    try:
        os.stat(".git", dir_fd=workspace_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    raise ReviewError("private workspace became a Git repository")


def _secure_atomic_write(workspace: Path, workspace_fd: int, destination: Path, content: str, overwrite: bool) -> None:
    _ensure_workspace_not_git(workspace_fd)
    parent_fd, name = _secure_parent_fd(workspace, workspace_fd, destination)
    temporary_name = f".{name}.{os.urandom(12).hex()}.tmp"
    try:
        try:
            os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            exists = True
        except FileNotFoundError:
            exists = False
        if exists and not overwrite:
            raise ReviewError("output exists; pass --overwrite to replace it")
        descriptor = os.open(temporary_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600, dir_fd=parent_fd)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                descriptor = -1
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
        finally:
            if descriptor >= 0:
                os.close(descriptor)
        os.replace(temporary_name, name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
        os.chmod(name, 0o600, dir_fd=parent_fd, follow_symlinks=False)
        try:
            _ensure_workspace_not_git(workspace_fd)
        except ReviewError:
            os.unlink(name, dir_fd=parent_fd)
            raise
    finally:
        try:
            os.unlink(temporary_name, dir_fd=parent_fd)
        except FileNotFoundError:
            pass
        os.close(parent_fd)


def _ensure_output_available(workspace: Path, workspace_fd: int, destination: Path, overwrite: bool) -> None:
    parent_fd, name = _secure_parent_fd(workspace, workspace_fd, destination)
    try:
        try:
            os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            return
        if not overwrite:
            raise ReviewError("output exists; pass --overwrite to replace it")
    finally:
        os.close(parent_fd)


def atomic_pair(workspace: Path, json_path: Path, markdown_path: Path, report: dict[str, Any], overwrite: bool, workspace_fd: int | None = None) -> None:
    workspace = _canonical_system_path(workspace)
    json_path = _canonical_system_path(json_path)
    markdown_path = _canonical_system_path(markdown_path)
    if json_path == markdown_path:
        raise ReviewError("JSON and Markdown outputs must differ")
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    owned_fd = workspace_fd is None
    descriptor = _open_absolute_directory(workspace, create=False) if owned_fd else workspace_fd
    try:
        _ensure_output_available(workspace, descriptor, json_path, overwrite)
        _ensure_output_available(workspace, descriptor, markdown_path, overwrite)
        _secure_atomic_write(workspace, descriptor, json_path, payload, overwrite)
        _secure_atomic_write(workspace, descriptor, markdown_path, markdown_for(report), overwrite)
    finally:
        if owned_fd:
            os.close(descriptor)


def load_context_bytes(payload: bytes) -> dict[str, Any]:
    try:
        context = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReviewError(f"invalid context: {error}") from error
    allowed = {"schema_version", "vacancy_evidence", "requirement_matrix", "human_path"}
    if not isinstance(context, dict) or set(context) - allowed or context.get("schema_version") != 1:
        raise ReviewError("context must use schema_version 1 and known fields only")
    return context


def load_context(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    try:
        return load_context_bytes(path.read_bytes())
    except OSError as error:
        raise ReviewError(f"invalid context: {error}") from error


def evidence_state(context: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    vacancy = context.get("vacancy_evidence")
    requirement = context.get("requirement_matrix")
    human = context.get("human_path")
    vacancy_state = "not_supplied"
    if isinstance(vacancy, dict) and isinstance(vacancy.get("source_url"), str) and parse_status_date(scalar(vacancy.get("verified_at")))[1] == "valid":
        vacancy_state = scalar(vacancy.get("state")) if scalar(vacancy.get("state")) in {"confirmed", "unverified", "stale"} else "unverified"
    requirement_state = "not_supplied"
    if isinstance(requirement, dict) and scalar(requirement.get("ref")):
        requirement_state = scalar(requirement.get("state")) if scalar(requirement.get("state")) in {"confirmed", "unverified", "stale"} else "unverified"
    human_state, authorization_not_granted = "not_supplied", True
    if isinstance(human, dict) and parse_status_date(scalar(human.get("retrieved_at")))[1] == "valid" and isinstance(human.get("relationships"), list):
        human_state = "unverified"
        for relationship in human["relationships"]:
            if not isinstance(relationship, dict):
                continue
            authorization = relationship.get("authorization")
            exact = (scalar(relationship.get("name")) == item["contact"] and scalar(relationship.get("current_company")) == item["company"]
                     and scalar(relationship.get("source_url")) and scalar(relationship.get("confidence")) == "confirmed")
            if exact:
                human_state = "confirmed"
                authorization_not_granted = not isinstance(authorization, dict) or not any(authorization.get(key) is True for key in ("contact", "reference", "referral", "follow_up", "introduce"))
                break
    return {"vacancy_evidence": {"state": vacancy_state}, "requirement_matrix": {"state": requirement_state},
            "human_path": {"state": human_state, "authorization_not_granted": authorization_not_granted}}


def packet_for(rows: list[dict[str, Any]], opportunity_id: str, snapshot_bytes: bytes, snapshot: dict[str, Any], as_of: date, context: dict[str, Any]) -> dict[str, Any]:
    matches = [row for row in rows if row["opportunity_id"] == opportunity_id]
    if len(matches) != 1 or matches[0]["identity_state"] != "valid":
        raise ReviewError("opportunity_id must exist exactly once and have a valid identity")
    item = matches[0]
    additional = evidence_state(context, item)
    recommendation = "maintain_history" if item["status_group"] == "terminal" else (
        "prepare_decision_material" if additional["vacancy_evidence"]["state"] == "confirmed" else "verify_primary_source")
    return {
        "schema_version": 1, "as_of": as_of.isoformat(), "snapshot_sha256": hashlib.sha256(snapshot_bytes).hexdigest(),
        "retrieved_at": snapshot.get("metadata", {}).get("retrieved_at"),
        "opportunity": {"No": item["opportunity_id"], "company": item["company"], "role": item["role"], "source": item["source"],
                        "status_raw": item["status"], "result_raw": item["result"], "status_date_raw": item["status_date"], "canonical_url_raw": item["canonical_url"]},
        "contact": {"state": "contact_signal_unverified" if item["contact"] else "not_supplied", "authorization": "not_supplied"},
        "additional_evidence": additional, "recommendation": recommendation,
        "authorization_limit": "Borrador/revisión solamente. Ricardo debe aprobar y ejecutar cualquier acción externa exacta.",
        "safety": {"external_actions": 0, "network_requests": 0, "input_mutated": False, "output_schema_valid": True},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only Hunter process review")
    sub = parser.add_subparsers(dest="command", required=True)
    report_parser = sub.add_parser("report")
    for option in ("snapshot", "mapping", "workspace", "as_of", "output_json", "output_md"):
        report_parser.add_argument("--" + option.replace("_", "-"), required=True)
    report_parser.add_argument("--overwrite", action="store_true")
    packet_parser = sub.add_parser("packet")
    for option in ("snapshot", "mapping", "workspace", "as_of", "opportunity_id", "output_json", "output_md"):
        packet_parser.add_argument("--" + option.replace("_", "-"), required=True)
    packet_parser.add_argument("--context")
    packet_parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    workspace_fd = -1
    try:
        as_of = date.fromisoformat(args.as_of)
        workspace, workspace_fd = open_private_workspace(args.workspace)
        snapshot_path = private_input(workspace, args.snapshot, "snapshot")
        mapping_path = private_input(workspace, args.mapping, "mapping")
        snapshot_bytes = secure_read_private_input(workspace, workspace_fd, snapshot_path, "snapshot")
        mapping_bytes = secure_read_private_input(workspace, workspace_fd, mapping_path, "mapping")
        snapshot = load_snapshot_bytes(snapshot_bytes)
        try:
            mapping = parse_mapping(mapping_bytes.decode("utf-8"))
        except UnicodeDecodeError as error:
            raise ReviewError(f"invalid mapping: {error}") from error
        rows = normalize(snapshot, mapping, as_of)
        context_path = getattr(args, "context", None)
        context = {} if not context_path else load_context_bytes(secure_read_private_input(workspace, workspace_fd, private_input(workspace, context_path, "context"), "context"))
        report = report_for(rows, snapshot_bytes, snapshot, as_of, mapping["review_thresholds"].get("status_age_days")) if args.command == "report" else packet_for(
            rows, args.opportunity_id, snapshot_bytes, snapshot, as_of, context)
        json_path = private_output(workspace, args.output_json)
        md_path = private_output(workspace, args.output_md)
        atomic_pair(workspace, json_path, md_path, report, args.overwrite, workspace_fd)
    except (OSError, ReviewError, ValueError) as error:
        print(f"ERROR: {error}")
        return 2
    finally:
        if workspace_fd >= 0:
            os.close(workspace_fd)
    print(f"report: {json_path}\nmarkdown: {md_path}\nrows: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
