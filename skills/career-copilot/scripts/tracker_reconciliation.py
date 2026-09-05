#!/usr/bin/env python3
"""Pure, deterministic tracker reconciliation planning for tabular backends.

This module deliberately has no network, credential, filesystem-write, or gws
integration. A backend must supply a normalized snapshot and execute a returned
plan only after its own authorization and readback controls.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


IDENTITY_FIELDS = ("external_job_id", "canonical_url")
REQUIRED_FIELD_KEYS = ("company", "role")
TRACKING_QUERY_PREFIXES = ("utm_", "trk", "tracking")


class ReconciliationError(ValueError):
    """Raised when a supplied snapshot, mapping, or request is malformed."""


@dataclass(frozen=True)
class NormalizedRow:
    physical_row: int
    values: dict[str, str]


def normalize_text(value: Any) -> str:
    """Normalize scalar input without silently accepting nested data."""
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple, set)):
        raise ReconciliationError("tracker values must be scalar")
    return str(value).strip()


def canonicalize_url(url: Any) -> str:
    """Remove common tracking keys while retaining material query parameters."""
    value = normalize_text(url)
    if not value:
        return ""
    parts = urlsplit(value)
    if not parts.scheme or not parts.netloc:
        raise ReconciliationError("canonical_url must be an absolute URL")
    query = [
        (key, item)
        for key, item in parse_qsl(parts.query, keep_blank_values=True)
        if not key.casefold().startswith(TRACKING_QUERY_PREFIXES)
    ]
    return urlunsplit((
        parts.scheme.casefold(),
        parts.netloc.casefold(),
        parts.path.rstrip("/"),
        urlencode(query, doseq=True),
        "",
    ))


def _tokens(value: Any) -> set[str]:
    return set(re.findall(r"[A-Za-zÀ-ÿ0-9+#.-]+", normalize_text(value).casefold()))


def _near_identical_role(left: str, right: str) -> bool:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    if not left_tokens or not right_tokens:
        return False
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens) >= 0.8


def _same_company_near_role(row: NormalizedRow, headers: dict[str, str], intended: dict[str, str]) -> bool:
    company_header = headers["company"]
    role_header = headers["role"]
    left_company = _tokens(row.values.get(company_header, ""))
    right_company = _tokens(intended.get("company", ""))
    return bool(left_company) and left_company == right_company and _near_identical_role(
        row.values.get(role_header, ""), intended.get("role", ""),
    )


def validate_field_mapping(headers: list[Any], fields: dict[str, Any]) -> dict[str, str]:
    """Map logical field names to unique snapshot headers, failing closed."""
    if not isinstance(headers, list) or any(not isinstance(item, str) or item != item.strip() for item in headers):
        raise ReconciliationError("snapshot headers must be trimmed strings")
    normalized_headers = [normalize_text(item) for item in headers]
    if not normalized_headers or any(not item for item in normalized_headers):
        raise ReconciliationError("snapshot headers must be non-empty")
    duplicates = sorted(header for header, count in Counter(normalized_headers).items() if count > 1)
    if duplicates:
        raise ReconciliationError(f"duplicate snapshot headers: {', '.join(duplicates)}")
    if not isinstance(fields, dict):
        raise ReconciliationError("fields must be a mapping")
    missing_keys = [key for key in REQUIRED_FIELD_KEYS if not normalize_text(fields.get(key))]
    if missing_keys:
        raise ReconciliationError(f"missing required field mapping: {', '.join(missing_keys)}")
    mapped: dict[str, str] = {}
    used_headers: set[str] = set()
    for logical, header_value in fields.items():
        logical_name = normalize_text(logical)
        header = normalize_text(header_value)
        if not logical_name or not header:
            raise ReconciliationError("field mappings must have non-empty names")
        if header not in normalized_headers:
            raise ReconciliationError(f"mapped header not found: {header}")
        if header in used_headers:
            raise ReconciliationError(f"multiple logical fields map to header: {header}")
        mapped[logical_name] = header
        used_headers.add(header)
    return mapped


def normalize_snapshot(snapshot: dict[str, Any], headers: dict[str, str]) -> list[NormalizedRow]:
    """Validate physical rows and preserve them separately from business IDs."""
    if not isinstance(snapshot, dict):
        raise ReconciliationError("snapshot must be a mapping")
    raw_rows = snapshot.get("rows")
    if not isinstance(raw_rows, list):
        raise ReconciliationError("snapshot.rows must be a list")
    raw_headers = snapshot.get("headers")
    if not isinstance(raw_headers, list):
        raise ReconciliationError("snapshot.headers must be a list")
    known_headers = {normalize_text(header) for header in raw_headers}
    rows: list[NormalizedRow] = []
    seen_physical: set[int] = set()
    for raw in raw_rows:
        if not isinstance(raw, dict):
            raise ReconciliationError("each snapshot row must be a mapping")
        physical_row = raw.get("physical_row")
        if not isinstance(physical_row, int) or physical_row < 1:
            raise ReconciliationError("physical_row must be a positive integer")
        if physical_row in seen_physical:
            raise ReconciliationError(f"duplicate physical_row: {physical_row}")
        values = raw.get("values")
        if not isinstance(values, dict):
            raise ReconciliationError("each snapshot row requires values mapping")
        unknown = sorted(normalize_text(key) for key in values if normalize_text(key) not in known_headers)
        if unknown:
            raise ReconciliationError(f"row has unmapped header(s): {', '.join(unknown)}")
        rows.append(NormalizedRow(
            physical_row=physical_row,
            values={header: normalize_text(values.get(header, "")) for header in known_headers},
        ))
        seen_physical.add(physical_row)
    return sorted(rows, key=lambda row: row.physical_row)


def audit_business_ids(
    rows: list[NormalizedRow],
    business_id_header: str | None,
    *,
    require_contiguous: bool,
    reject_duplicates: bool,
) -> dict[str, Any]:
    """Report integer business-ID health without renumbering or mutating rows."""
    if not business_id_header:
        return {
            "enabled": False,
            "record_count": len(rows),
            "max_id": None,
            "missing_ids": [],
            "duplicate_ids": {},
            "invalid_ids": [],
            "blocked": False,
        }
    values: list[tuple[int, int]] = []
    invalid: list[dict[str, Any]] = []
    for row in rows:
        raw = row.values.get(business_id_header, "")
        if not raw:
            invalid.append({"physical_row": row.physical_row, "value": "", "reason": "blank"})
            continue
        if not re.fullmatch(r"[1-9][0-9]*", raw):
            invalid.append({"physical_row": row.physical_row, "value": raw, "reason": "not_positive_integer"})
            continue
        values.append((int(raw), row.physical_row))
    grouped: dict[int, list[int]] = {}
    for identifier, physical_row in values:
        grouped.setdefault(identifier, []).append(physical_row)
    duplicates = {str(identifier): positions for identifier, positions in grouped.items() if len(positions) > 1}
    maximum = max(grouped, default=None)
    missing = list(range(1, maximum + 1)) if maximum else []
    missing = [identifier for identifier in missing if identifier not in grouped]
    blocked = bool(invalid) or (reject_duplicates and bool(duplicates)) or (require_contiguous and bool(missing))
    return {
        "enabled": True,
        "record_count": len(rows),
        "max_id": maximum,
        "missing_ids": missing,
        "duplicate_ids": duplicates,
        "invalid_ids": invalid,
        "blocked": blocked,
    }


def _stable_matches(rows: list[NormalizedRow], headers: dict[str, str], intended: dict[str, str]) -> dict[str, list[NormalizedRow]]:
    matches: dict[str, list[NormalizedRow]] = {"external_job_id": [], "canonical_url": [], "near_role": []}
    external = intended.get("external_job_id", "")
    if external and "external_job_id" in headers:
        header = headers["external_job_id"]
        matches["external_job_id"] = [row for row in rows if row.values.get(header, "") == external]
    canonical = intended.get("canonical_url", "")
    if canonical and "canonical_url" in headers:
        header = headers["canonical_url"]
        matches["canonical_url"] = [
            row for row in rows if row.values.get(header, "") and canonicalize_url(row.values[header]) == canonical
        ]
    matches["near_role"] = [row for row in rows if _same_company_near_role(row, headers, intended)]
    return matches


def _match_positions(matches: dict[str, list[NormalizedRow]]) -> dict[str, list[int]]:
    return {key: [row.physical_row for row in rows] for key, rows in matches.items() if rows}


def _plan_changes(row: NormalizedRow | None, headers: dict[str, str], intended: dict[str, str]) -> list[dict[str, str]]:
    changes: list[dict[str, str]] = []
    for logical, new_value in intended.items():
        if logical not in headers:
            continue
        header = headers[logical]
        old_value = row.values.get(header, "") if row else ""
        comparable_old = canonicalize_url(old_value) if logical == "canonical_url" and old_value else old_value
        if comparable_old != new_value:
            changes.append({"logical_field": logical, "header": header, "old_value": old_value, "new_value": new_value})
    return changes


def _result(decision: str, audit: dict[str, Any], **details: Any) -> dict[str, Any]:
    return {"decision": decision, "audit": audit, **details}


def reconcile(
    snapshot: dict[str, Any],
    fields: dict[str, Any],
    intended_record: dict[str, Any],
    *,
    operation: str = "upsert",
    create_physical_row: int | None = None,
    require_contiguous_business_ids: bool = False,
    reject_duplicate_business_ids: bool = True,
) -> dict[str, Any]:
    """Return a non-mutating reconciliation decision and exact write plan.

    `operation` is `upsert`, `create`, or `update`. A backend must pass an
    explicit `create_physical_row`; this module never guesses an append range.
    """
    if operation not in {"upsert", "create", "update"}:
        raise ReconciliationError("operation must be upsert, create, or update")
    if not isinstance(intended_record, dict):
        raise ReconciliationError("intended_record must be a mapping")
    snapshot_headers = snapshot.get("headers") if isinstance(snapshot, dict) else None
    if not isinstance(snapshot_headers, list):
        raise ReconciliationError("snapshot.headers must be a list")
    headers = validate_field_mapping(snapshot_headers, fields)
    intended = {logical: normalize_text(value) for logical, value in intended_record.items()}
    unknown_intended_fields = sorted(key for key in intended if key not in headers)
    if unknown_intended_fields:
        raise ReconciliationError(f"intended_record has unmapped field(s): {', '.join(unknown_intended_fields)}")
    for key in REQUIRED_FIELD_KEYS:
        if not intended.get(key):
            raise ReconciliationError(f"intended_record.{key} is required")
    if "canonical_url" in intended and intended["canonical_url"]:
        intended["canonical_url"] = canonicalize_url(intended["canonical_url"])
    if "business_id" in headers and intended.get("business_id") and not re.fullmatch(r"[1-9][0-9]*", intended["business_id"]):
        raise ReconciliationError("intended_record.business_id must be a positive integer")
    rows = normalize_snapshot(snapshot, headers)
    audit = audit_business_ids(
        rows,
        headers.get("business_id"),
        require_contiguous=require_contiguous_business_ids,
        reject_duplicates=reject_duplicate_business_ids,
    )
    if audit["blocked"]:
        return _result("integrity_failure", audit, reason="business_id_audit_failed")

    matches = _stable_matches(rows, headers, intended)
    stable_sets = [set(row.physical_row for row in matches[key]) for key in IDENTITY_FIELDS if matches[key]]
    if len(stable_sets) > 1 and any(item != stable_sets[0] for item in stable_sets[1:]):
        return _result("ambiguous_identity", audit, reason="conflicting_stable_identity", matches=_match_positions(matches))
    stable_rows = [row for key in IDENTITY_FIELDS for row in matches[key]]
    stable_by_position = {row.physical_row: row for row in stable_rows}
    if len(stable_by_position) > 1:
        return _result("ambiguous_identity", audit, reason="multiple_stable_matches", matches=_match_positions(matches))
    if stable_by_position:
        existing = next(iter(stable_by_position.values()))
        business_id_header = headers.get("business_id")
        requested_business_id = intended.get("business_id", "")
        if business_id_header and requested_business_id:
            conflicts = [
                row.physical_row
                for row in rows
                if row.physical_row != existing.physical_row and row.values.get(business_id_header, "") == requested_business_id
            ]
            if conflicts:
                return _result(
                    "integrity_failure",
                    audit,
                    reason="requested_business_id_already_occupied",
                    matches={"business_id": conflicts},
                )
        if operation == "create":
            return _result("duplicate_match", audit, match_type="stable", physical_row=existing.physical_row)
        changes = _plan_changes(existing, headers, intended)
        return _result(
            "no_change" if not changes else "update_plan",
            audit,
            match_type="stable",
            physical_row=existing.physical_row,
            changes=changes,
        )

    if matches["near_role"]:
        return _result(
            "ambiguous_identity",
            audit,
            reason="company_and_near_identical_role_requires_review",
            matches={"near_role": [row.physical_row for row in matches["near_role"]]},
        )
    if operation == "update":
        return _result("no_change", audit, reason="no_stable_match_for_update", changes=[])
    if not isinstance(create_physical_row, int) or create_physical_row < 1:
        return _result("integrity_failure", audit, reason="explicit_create_physical_row_required")
    if any(row.physical_row == create_physical_row for row in rows):
        return _result("integrity_failure", audit, reason="create_physical_row_already_occupied")
    if "business_id" in headers and not intended.get("business_id"):
        return _result("integrity_failure", audit, reason="explicit_business_id_required")
    if "business_id" in headers:
        requested_business_id = intended["business_id"]
        conflicts = [
            row.physical_row
            for row in rows
            if row.values.get(headers["business_id"], "") == requested_business_id
        ]
        if conflicts:
            return _result(
                "integrity_failure",
                audit,
                reason="requested_business_id_already_occupied",
                matches={"business_id": conflicts},
            )
    changes = _plan_changes(None, headers, intended)
    return _result("create_plan", audit, physical_row=create_physical_row, changes=changes)
