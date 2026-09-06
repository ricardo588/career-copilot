#!/usr/bin/env python3
"""Optional, dry-run-first adapters for Sheets, Gmail and Obsidian."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional


Runner = Callable[[list[str]], dict[str, Any]]
AUDIT_RESULTS = {"attempted", "blocked", "failed", "applied", "verified"}
_TRACKER_RECONCILIATION: Any = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _private_workspace(workspace: Path) -> Path:
    """Normalize a user-owned workspace without allowing repository paths or symlinks."""
    raw = workspace.expanduser()
    if raw.exists() and raw.is_symlink():
        raise ValueError("private workspace cannot be a symlink")
    path = raw.resolve()
    distribution_root = Path(__file__).resolve().parents[3]
    if path == distribution_root or distribution_root in path.parents:
        raise ValueError("private workspace must be outside the Career Copilot distribution")
    for ancestor in (path, *path.parents):
        if ancestor.is_symlink():
            raise ValueError("private workspace cannot be beneath a symlink")
        if (ancestor / ".git").exists():
            raise ValueError("private workspace must be outside a Git repository")
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, 0o700)
    return path


def _private_append_path(workspace: Path, relative_path: str) -> Path:
    root = _private_workspace(workspace)
    target = root / relative_path
    if target.exists() and target.is_symlink():
        raise ValueError("private artifact cannot be a symlink")
    target.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(target.parent, 0o700)
    return target


def _append_jsonl(path: Path, event: dict[str, Any]) -> None:
    """Append exactly one durable JSON record; never rewrite existing events."""
    if path.exists() and path.is_symlink():
        raise ValueError("private artifact cannot be a symlink")
    descriptor = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
            descriptor = -1
            handle.write(json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _plan_hash(plan: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def _reconciliation_approval_hash(write_plan: dict[str, Any], sheet_id: str) -> str:
    """Bind a review token to one private spreadsheet without exposing its ID."""
    return _plan_hash({
        "domain": "career-copilot/sheets-reconcile-apply/v1",
        "spreadsheet_id": sheet_id,
        "write_plan": write_plan,
    })


def append_external_audit(
    workspace: Path,
    *,
    adapter: str,
    operation: str,
    target_ref: str,
    plan: dict[str, Any],
    authorization_mode: str,
    result: str,
    readback_ref: str = "",
    detail: str = "",
) -> str:
    """Append a minimal lifecycle event. Append-only is operational, not tamper-proof."""
    if result not in AUDIT_RESULTS:
        raise ValueError(f"unsupported audit result: {result}")
    event_id = str(uuid.uuid4())
    event = {
        "event_id": event_id,
        "timestamp": _utc_now(),
        "adapter": adapter,
        "operation": operation,
        "target_ref": target_ref,
        "payload_plan_sha256": _plan_hash(plan),
        "authorization_mode": authorization_mode,
        "result": result,
        "readback_ref": readback_ref,
    }
    if detail:
        event["detail"] = detail[:240]
    _append_jsonl(_private_append_path(workspace, "audit/external-actions.jsonl"), event)
    return f"audit/external-actions.jsonl#{event_id}"


def record_gmail_evidence(
    workspace: Path,
    *,
    account_ref: str,
    message_id: str,
    supported_fact: str,
    retrieved_at: Optional[str] = None,
    thread_id: str = "",
    excerpt: str = "",
    content_sha256: str = "",
    support_status: str = "direct",
) -> str:
    """Store minimal private, directly supported Gmail evidence and return an opaque reference."""
    if support_status != "direct":
        raise ValueError("ambiguous or contradictory Gmail messages cannot support a tracker change")
    if not account_ref.strip() or not message_id.strip() or not supported_fact.strip():
        raise ValueError("Gmail evidence requires account_ref, message_id and supported_fact")
    if bool(excerpt.strip()) == bool(content_sha256.strip()):
        raise ValueError("Gmail evidence requires exactly one minimal excerpt or content_sha256")
    if excerpt and len(excerpt.strip()) > 500:
        raise ValueError("Gmail evidence excerpt must be 500 characters or fewer")
    if content_sha256 and not re.fullmatch(r"[0-9a-f]{64}", content_sha256.strip()):
        raise ValueError("Gmail evidence content_sha256 must be a lowercase SHA-256 hash")
    event_id = str(uuid.uuid4())
    event = {
        "evidence_id": event_id,
        "retrieved_at": retrieved_at or _utc_now(),
        "account_ref": account_ref.strip(),
        "message_id": message_id.strip(),
        "thread_id": thread_id.strip(),
        "supported_fact": supported_fact.strip(),
        "support": {"excerpt": excerpt.strip()} if excerpt else {"content_sha256": content_sha256.strip()},
    }
    _append_jsonl(_private_append_path(workspace, "evidence/gmail-evidence.jsonl"), event)
    return f"evidence/gmail-evidence.jsonl#{event_id}"


def _audit_before_mutation(
    workspace: Optional[Path], plan: dict[str, Any], profile: Optional[dict[str, Any]], target_ref: str,
) -> tuple[Path, str, str]:
    if workspace is None:
        raise ValueError("external mutations require --workspace for private audit logging")
    root = _private_workspace(workspace)
    try:
        authorization_mode = require_external_permission(profile)
    except ValueError as exc:
        append_external_audit(root, adapter=plan["adapter"], operation=plan["operation"], target_ref=target_ref,
                              plan=plan, authorization_mode="draft_only", result="blocked", detail=str(exc))
        raise
    audit_ref = append_external_audit(root, adapter=plan["adapter"], operation=plan["operation"], target_ref=target_ref,
                                      plan=plan, authorization_mode=authorization_mode, result="attempted")
    return root, authorization_mode, audit_ref


def load_profile(path: Optional[str]) -> Optional[dict[str, Any]]:
    if not path:
        return None
    text = Path(path).read_text(encoding="utf-8")
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise ValueError("profile is not JSON-compatible YAML; install PyYAML or finalize onboarding") from exc
        loaded = yaml.safe_load(text)
    if not isinstance(loaded, dict):
        raise ValueError("profile must contain a mapping")
    return loaded


def require_external_permission(profile: Optional[dict[str, Any]]) -> str:
    if profile is None:
        raise ValueError("external mutations require --profile so Career Copilot can enforce its action policy")
    permissions = profile.get("permissions", {})
    mode = permissions.get("external_action_mode")
    if mode is None:
        legacy = permissions.get("external_actions")
        mode = "confirm_each_external" if legacy == "explicit_confirmation" else "draft_only"
    locked = bool(permissions.get("external_action_mode_locked", False))
    if locked and mode != "draft_only":
        raise ValueError("invalid policy: a locked profile must use draft_only")
    if mode == "draft_only":
        raise ValueError("external mutation blocked: profile is draft_only")
    if mode != "confirm_each_external":
        raise ValueError(f"unsupported external action mode: {mode}")
    return mode


def run_json_command(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"command failed: {command[0]}")
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("adapter command returned non-JSON output") from exc
    if not isinstance(result, dict):
        raise RuntimeError("adapter command returned an unexpected JSON shape")
    return result


def sheet_hint(sheet_id: str) -> str:
    return "…" + sheet_id[-4:] if len(sheet_id) >= 4 else "configured"


def sheets_read(runner: Runner, sheet_id: str, range_name: str) -> dict[str, Any]:
    params = json.dumps({"spreadsheetId": sheet_id, "range": range_name}, separators=(",", ":"))
    return runner(["gws", "sheets", "spreadsheets", "values", "get", "--params", params])


def _tracker_reconciliation_module() -> Any:
    """Load the pure planner next to this adapter without changing sys.path."""
    global _TRACKER_RECONCILIATION
    if _TRACKER_RECONCILIATION is not None:
        return _TRACKER_RECONCILIATION
    path = Path(__file__).with_name("tracker_reconciliation.py")
    spec = importlib.util.spec_from_file_location("career_tracker_reconciliation", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load tracker reconciliation planner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    _TRACKER_RECONCILIATION = module
    return module


def _range_start_row(range_name: str) -> int:
    """Extract the explicit A1 start row; named ranges are unsafe for row planning."""
    match = re.search(r"(?:!|^)\$?[A-Z]+\$?([1-9][0-9]*)", range_name)
    if match is None:
        raise ValueError("Sheets reconciliation requires an A1 range with an explicit start row")
    return int(match.group(1))


def _sheet_snapshot(response: dict[str, Any], range_name: str, header_row: int) -> dict[str, Any]:
    """Convert a Sheets values response into a pure-planner snapshot.

    The requested A1 range must begin at its header row. Fully blank rows are
    formatting/empty rows and are intentionally not tracker records; any
    non-blank row with a missing business ID remains visible to the planner and
    fails closed under its configured integrity policy.
    """
    if _range_start_row(range_name) != header_row:
        raise ValueError("Sheets reconciliation range must start at --header-row")
    values = response.get("values")
    if not isinstance(values, list) or not values or not isinstance(values[0], list):
        raise ValueError("Sheets reconciliation response must include a header row")
    headers = values[0]
    if not headers:
        raise ValueError("Sheets reconciliation header row is empty")
    rows: list[dict[str, Any]] = []
    for offset, raw_row in enumerate(values[1:], start=1):
        if not isinstance(raw_row, list):
            raise ValueError("Sheets reconciliation response contains a non-row value")
        if len(raw_row) > len(headers):
            raise ValueError("Sheets reconciliation row has more values than its header row")
        if not any(str(value).strip() for value in raw_row):
            continue
        row_values = {
            str(header): raw_row[index] if index < len(raw_row) else ""
            for index, header in enumerate(headers)
        }
        rows.append({"physical_row": header_row + offset, "values": row_values})
    return {"headers": headers, "rows": rows}


def sheets_reconcile(
    runner: Runner,
    sheet_id: str,
    range_name: str,
    header_row: int,
    fields: dict[str, Any],
    intended_record: dict[str, Any],
    *,
    operation: str = "upsert",
    create_physical_row: Optional[int] = None,
    require_contiguous_business_ids: bool = True,
    reject_duplicate_business_ids: bool = True,
) -> dict[str, Any]:
    """Read once and produce a non-mutating reconciliation plan.

    This B1 command has no apply mode by design. It cannot call a Sheets write
    endpoint; B2 will add a separately reviewed, gated write path.
    """
    response = sheets_read(runner, sheet_id, range_name)
    snapshot = _sheet_snapshot(response, range_name, header_row)
    planner = _tracker_reconciliation_module()
    plan = planner.reconcile(
        snapshot,
        fields,
        intended_record,
        operation=operation,
        create_physical_row=create_physical_row,
        require_contiguous_business_ids=require_contiguous_business_ids,
        reject_duplicate_business_ids=reject_duplicate_business_ids,
    )
    return {
        "status": "dry_run",
        "adapter": "google_sheets",
        "operation": "reconcile",
        "target": {"sheet": sheet_hint(sheet_id), "range": range_name, "header_row": header_row},
        "plan": plan,
    }


def _column_number(label: str) -> int:
    result = 0
    for character in label.upper():
        if character < "A" or character > "Z":
            raise ValueError("A1 column labels must contain letters only")
        result = result * 26 + (ord(character) - ord("A") + 1)
    return result


def _column_label(number: int) -> str:
    if number < 1:
        raise ValueError("A1 column number must be positive")
    result = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(ord("A") + remainder) + result
    return result


def _explicit_a1_bounds(range_name: str) -> tuple[str, int, int, int, int]:
    """Parse a closed A1 rectangle; B2 execution never guesses its bounds."""
    match = re.fullmatch(
        r"((?:'[^']+'|[^!]+)!)?\$?([A-Za-z]+)\$?([1-9][0-9]*):\$?([A-Za-z]+)\$?([1-9][0-9]*)",
        range_name,
    )
    if match is None or not match.group(1):
        raise ValueError("Sheets reconciliation apply requires a closed A1 range with a sheet name")
    sheet_prefix = match.group(1)
    first_column, first_row = _column_number(match.group(2)), int(match.group(3))
    last_column, last_row = _column_number(match.group(4)), int(match.group(5))
    if last_column < first_column or last_row < first_row:
        raise ValueError("Sheets reconciliation A1 range must have increasing bounds")
    return sheet_prefix, first_column, first_row, last_column, last_row


def _reconciliation_write_plan(
    sheet_id: str,
    range_name: str,
    header_row: int,
    fields: dict[str, Any],
    reconciliation: dict[str, Any],
) -> dict[str, Any]:
    """Convert one safe planner decision into exact single-cell write requests."""
    sheet_prefix, first_column, first_row, last_column, last_row = _explicit_a1_bounds(range_name)
    if first_row != header_row:
        raise ValueError("Sheets reconciliation range must start at --header-row")
    decision = reconciliation["plan"]
    outcome = decision.get("decision")
    write_plan = {
        "adapter": "google_sheets",
        "operation": "reconcile_apply",
        "target": {"sheet": sheet_hint(sheet_id), "range": range_name, "header_row": header_row},
        "decision": outcome,
        "reconciliation": decision,
        "writes": [],
    }
    if outcome not in {"update_plan", "create_plan"}:
        return write_plan
    physical_row = decision.get("physical_row")
    if not isinstance(physical_row, int) or not first_row < physical_row <= last_row:
        raise ValueError("planned physical row must be inside the explicit snapshot range below its header")
    headers = reconciliation.get("snapshot_headers")
    if not isinstance(headers, list) or any(not isinstance(item, str) for item in headers):
        raise ValueError("reconciliation did not retain valid snapshot headers")
    header_positions = {header: index for index, header in enumerate(headers)}
    if len(header_positions) != len(headers):
        raise ValueError("reconciliation snapshot headers must be unique")
    for change in decision.get("changes", []):
        if not isinstance(change, dict):
            raise ValueError("planner changes must be mappings")
        header = change.get("header")
        new_value = change.get("new_value")
        if not isinstance(header, str) or header not in header_positions or not isinstance(new_value, str):
            raise ValueError("planner change is malformed")
        column = first_column + header_positions[header]
        if column > last_column:
            raise ValueError("planned header falls outside the explicit snapshot range")
        write_plan["writes"].append({
            "range": f"{sheet_prefix}{_column_label(column)}{physical_row}",
            "values": [[new_value]],
        })
    if not write_plan["writes"]:
        raise ValueError("writable reconciliation decision did not contain any changes")
    return write_plan


def sheets_reconcile_apply(
    runner: Runner,
    sheet_id: str,
    range_name: str,
    header_row: int,
    fields: dict[str, Any],
    intended_record: dict[str, Any],
    *,
    operation: str = "upsert",
    create_physical_row: Optional[int] = None,
    apply: bool = False,
    approved_plan_sha256: str = "",
    profile: Optional[dict[str, Any]] = None,
    workspace: Optional[Path] = None,
) -> dict[str, Any]:
    """Re-plan from live data, then optionally apply a hash-approved cell plan.

    Every call reads the current explicit snapshot. Apply calls require the hash
    produced by a prior dry run, enforce confirm_each_external, write only the
    planned cells, and verify every written cell by exact readback.
    """
    response = sheets_read(runner, sheet_id, range_name)
    snapshot = _sheet_snapshot(response, range_name, header_row)
    planner = _tracker_reconciliation_module()
    decision = planner.reconcile(
        snapshot, fields, intended_record, operation=operation,
        create_physical_row=create_physical_row,
        require_contiguous_business_ids=True, reject_duplicate_business_ids=True,
    )
    reconciliation = {
        "status": "dry_run", "adapter": "google_sheets", "operation": "reconcile",
        "target": {"sheet": sheet_hint(sheet_id), "range": range_name, "header_row": header_row},
        "plan": decision, "snapshot_headers": snapshot["headers"],
    }
    write_plan = _reconciliation_write_plan(sheet_id, range_name, header_row, fields, reconciliation)
    approval_sha256 = _reconciliation_approval_hash(write_plan, sheet_id)
    result = {"status": "dry_run", "plan": write_plan, "approval_sha256": approval_sha256}
    if not apply:
        return result
    if write_plan["decision"] not in {"update_plan", "create_plan", "no_change"}:
        raise ValueError(
            "reconciliation decision is not applicable: "
            f"{write_plan['decision'] or 'missing decision'}"
        )
    if not re.fullmatch(r"[0-9a-f]{64}", approved_plan_sha256):
        raise ValueError("--approved-plan-sha256 must be a lowercase SHA-256 hash from a dry run")
    if approved_plan_sha256 != approval_sha256:
        if workspace is None:
            raise ValueError("approved plan hash does not match the current live reconciliation plan")
        root = _private_workspace(workspace)
        target_ref = f"{sheet_hint(sheet_id)}:{range_name}"
        try:
            authorization_mode = require_external_permission(profile)
        except ValueError:
            authorization_mode = "draft_only"
        append_external_audit(root, adapter="google_sheets", operation="reconcile_apply", target_ref=target_ref,
                              plan=write_plan, authorization_mode=authorization_mode, result="blocked",
                              detail="approved plan hash does not match current live reconciliation plan")
        raise ValueError("approved plan hash does not match the current live reconciliation plan")
    if not write_plan["writes"]:
        return {"status": "no_change", "verified": True, "plan": write_plan, "approval_sha256": approval_sha256}
    target_ref = f"{sheet_hint(sheet_id)}:{range_name}"
    if workspace is None:
        raise ValueError("external mutations require --workspace for private audit logging")
    root = _private_workspace(workspace)
    try:
        authorization_mode = require_external_permission(profile)
    except ValueError as exc:
        append_external_audit(root, adapter="google_sheets", operation="reconcile_apply", target_ref=target_ref,
                              plan=write_plan, authorization_mode="draft_only", result="blocked", detail=str(exc))
        raise
    attempt_ref = append_external_audit(root, adapter="google_sheets", operation="reconcile_apply", target_ref=target_ref,
                                        plan=write_plan, authorization_mode=authorization_mode, result="attempted")
    applied_refs: list[str] = []
    try:
        for write in write_plan["writes"]:
            params = json.dumps({"spreadsheetId": sheet_id, "range": write["range"], "valueInputOption": "RAW"}, separators=(",", ":"))
            body = json.dumps({"values": write["values"]}, separators=(",", ":"))
            runner(["gws", "sheets", "spreadsheets", "values", "update", "--params", params, "--json", body])
            # Sheets has no multi-cell transaction through this minimal API. Record
            # each completed narrow write so a later provider failure is not
            # misrepresented as an all-or-nothing non-event.
            applied_refs.append(append_external_audit(
                root, adapter="google_sheets", operation="reconcile_apply", target_ref=target_ref,
                plan=write_plan, authorization_mode=authorization_mode, result="applied",
            ))
    except Exception as exc:
        append_external_audit(root, adapter="google_sheets", operation="reconcile_apply", target_ref=target_ref,
                              plan=write_plan, authorization_mode=authorization_mode, result="failed",
                              detail=f"{len(applied_refs)} cell write(s) completed before failure: {exc}")
        raise
    try:
        for write in write_plan["writes"]:
            readback = sheets_read(runner, sheet_id, write["range"])
            values = readback.get("values", [])
            actual = ""
            if values and isinstance(values[0], list) and values[0]:
                actual = str(values[0][0])
            if actual != write["values"][0][0]:
                raise RuntimeError(f"Sheets readback did not match requested value for {write['range']}")
    except Exception as exc:
        append_external_audit(root, adapter="google_sheets", operation="reconcile_apply", target_ref=target_ref,
                              plan=write_plan, authorization_mode=authorization_mode, result="failed", detail=str(exc))
        raise
    verified_ref = append_external_audit(root, adapter="google_sheets", operation="reconcile_apply", target_ref=target_ref,
                                         plan=write_plan, authorization_mode=authorization_mode, result="verified", readback_ref=applied_refs[-1])
    return {"status": "applied", "verified": True, "plan": write_plan, "approval_sha256": approval_sha256,
            "audit_refs": [attempt_ref, *applied_refs, verified_ref]}


def sheets_update(
    runner: Runner,
    sheet_id: str,
    range_name: str,
    values: list[list[Any]],
    apply: bool = False,
    profile: Optional[dict[str, Any]] = None,
    workspace: Optional[Path] = None,
) -> dict[str, Any]:
    plan = {"adapter": "google_sheets", "operation": "update", "sheet": sheet_hint(sheet_id), "range": range_name, "rows": len(values), "apply": apply}
    if not apply:
        return {"status": "dry_run", "plan": plan}
    root, mode, attempt_ref = _audit_before_mutation(workspace, plan, profile, f"{plan['sheet']}:{range_name}")
    params = json.dumps({"spreadsheetId": sheet_id, "range": range_name, "valueInputOption": "RAW"}, separators=(",", ":"))
    body = json.dumps({"values": values}, separators=(",", ":"))
    try:
        runner(["gws", "sheets", "spreadsheets", "values", "update", "--params", params, "--json", body])
    except Exception as exc:
        append_external_audit(root, adapter="google_sheets", operation="update", target_ref=f"{plan['sheet']}:{range_name}",
                              plan=plan, authorization_mode=mode, result="failed", detail=str(exc))
        raise
    applied_ref = append_external_audit(root, adapter="google_sheets", operation="update", target_ref=f"{plan['sheet']}:{range_name}",
                                        plan=plan, authorization_mode=mode, result="applied")
    try:
        readback = sheets_read(runner, sheet_id, range_name)
        verified = readback.get("values") == values
        if not verified:
            raise RuntimeError("Sheets readback did not match requested values")
    except Exception as exc:
        append_external_audit(root, adapter="google_sheets", operation="update", target_ref=f"{plan['sheet']}:{range_name}",
                              plan=plan, authorization_mode=mode, result="failed", detail=str(exc))
        raise
    verified_ref = append_external_audit(root, adapter="google_sheets", operation="update", target_ref=f"{plan['sheet']}:{range_name}",
                                         plan=plan, authorization_mode=mode, result="verified", readback_ref=applied_ref)
    return {"status": "applied", "verified": True, "plan": plan, "audit_refs": [attempt_ref, applied_ref, verified_ref]}


def gmail_search(runner: Runner, query: str, user_id: str = "me", max_results: int = 20) -> dict[str, Any]:
    params = json.dumps({"userId": user_id, "q": query, "maxResults": max_results}, separators=(",", ":"))
    return runner(["gws", "gmail", "users", "messages", "list", "--params", params])


def gmail_get(runner: Runner, message_id: str, user_id: str = "me") -> dict[str, Any]:
    params = json.dumps({"userId": user_id, "id": message_id, "format": "full"}, separators=(",", ":"))
    return runner(["gws", "gmail", "users", "messages", "get", "--params", params])


def _gmail_triage_already_processed(workspace: Path, fingerprint: str, message_id: str) -> bool:
    ledger = workspace / "triage" / "gmail-triage.jsonl"
    if not ledger.exists():
        return False
    if ledger.is_symlink():
        raise ValueError("private artifact cannot be a symlink")
    for line in ledger.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError("Gmail triage ledger is invalid") from exc
        if event.get("message_fingerprint") == fingerprint and event.get("outcome") == "proposed":
            if event.get("message_id") != message_id:
                raise ValueError("Gmail triage fingerprint collision requires human review")
            return True
    return False


def gmail_triage(
    runner: Runner,
    message_id: str,
    *,
    workspace: Path,
    account_ref: str,
    user_id: str = "me",
    supported_fact: str = "",
    excerpt: str = "",
    content_sha256: str = "",
) -> dict[str, Any]:
    """Read one Gmail message and create a private, non-mutating review proposal."""
    if not message_id.strip() or not account_ref.strip():
        raise ValueError("Gmail triage requires message_id and account_ref")
    message = gmail_get(runner, message_id, user_id)
    if message.get("id") != message_id:
        raise ValueError("Gmail readback did not return the requested message")
    root = _private_workspace(workspace)
    event_id = str(uuid.uuid4())
    fingerprint = _plan_hash({"account_ref": account_ref.strip(), "message_id": message_id, "thread_id": message.get("threadId", "")})
    if _gmail_triage_already_processed(root, fingerprint, message_id):
        return {
            "status": "already_processed",
            "message_ref": f"gmail:{message_id}",
            "proposal": {"kind": "gmail_evidence_review", "message_fingerprint": fingerprint},
        }
    evidence_ref = ""
    if supported_fact.strip():
        evidence_ref = record_gmail_evidence(
            root, account_ref=account_ref, message_id=message_id, thread_id=str(message.get("threadId", "")),
            supported_fact=supported_fact, excerpt=excerpt, content_sha256=content_sha256,
        )
    _append_jsonl(_private_append_path(root, "triage/gmail-triage.jsonl"), {
        "triage_id": event_id,
        "retrieved_at": _utc_now(),
        "account_ref": account_ref.strip(),
        "message_id": message_id,
        "thread_id": str(message.get("threadId", "")),
        "message_fingerprint": fingerprint,
        "evidence_ref": evidence_ref,
        "outcome": "proposed",
    })
    return {
        "status": "proposed",
        "message_ref": f"gmail:{message_id}",
        "proposal": {
            "kind": "gmail_evidence_review",
            "triage_ref": f"triage/gmail-triage.jsonl#{event_id}",
            "message_fingerprint": fingerprint,
            "evidence_ref": evidence_ref,
        },
    }


def gmail_reconciliation_proposal(
    snapshot: dict[str, Any],
    fields: dict[str, Any],
    record: dict[str, Any],
    evidence_ref: str,
    *,
    operation: str = "upsert",
    create_physical_row: Optional[int] = None,
) -> dict[str, Any]:
    """Bind reviewed Gmail evidence to a pure, read-only tracker plan."""
    if not re.fullmatch(r"evidence/gmail-evidence\.jsonl#[0-9a-fA-F-]{36}", evidence_ref):
        raise ValueError("Gmail reconciliation requires an opaque Gmail evidence reference")
    planner = _tracker_reconciliation_module()
    plan = planner.reconcile(
        snapshot, fields, record, operation=operation, create_physical_row=create_physical_row,
        require_contiguous_business_ids=True, reject_duplicate_business_ids=True,
    )
    return {"status": "dry_run", "plan": plan, "evidence_ref": evidence_ref}


def gmail_mark_read(
    runner: Runner,
    message_id: str,
    user_id: str = "me",
    apply: bool = False,
    profile: Optional[dict[str, Any]] = None,
    workspace: Optional[Path] = None,
    approved_plan_sha256: str = "",
) -> dict[str, Any]:
    plan = {"adapter": "gmail", "operation": "mark_read", "message_id": message_id, "user_id": user_id}
    approval_sha256 = _plan_hash({"domain": "career-copilot/gmail-mark-read/v1", "plan": plan})
    if not apply:
        return {"status": "dry_run", "plan": plan, "approval_sha256": approval_sha256}
    if approved_plan_sha256 != approval_sha256:
        raise ValueError("gmail mark-read requires the current approved plan hash")
    root, mode, attempt_ref = _audit_before_mutation(workspace, plan, profile, f"message:{message_id}")
    current = gmail_get(runner, message_id, user_id)
    if current.get("id") != message_id or "UNREAD" not in current.get("labelIds", []):
        append_external_audit(root, adapter="gmail", operation="mark_read", target_ref=f"message:{message_id}",
                              plan=plan, authorization_mode=mode, result="failed", detail="stale approval or message is no longer unread")
        raise ValueError("gmail mark-read approval is stale or the message is no longer unread")
    params = json.dumps({"userId": user_id, "id": message_id}, separators=(",", ":"))
    try:
        runner(["gws", "gmail", "users", "messages", "modify", "--params", params, "--json", '{"removeLabelIds":["UNREAD"]}'])
    except Exception as exc:
        append_external_audit(root, adapter="gmail", operation="mark_read", target_ref=f"message:{message_id}",
                              plan=plan, authorization_mode=mode, result="failed", detail=str(exc))
        raise
    applied_ref = append_external_audit(root, adapter="gmail", operation="mark_read", target_ref=f"message:{message_id}",
                                        plan=plan, authorization_mode=mode, result="applied")
    try:
        readback = gmail_get(runner, message_id, user_id)
        labels = readback.get("labelIds", [])
        if "UNREAD" in labels:
            raise RuntimeError("Gmail readback still contains UNREAD")
    except Exception as exc:
        append_external_audit(root, adapter="gmail", operation="mark_read", target_ref=f"message:{message_id}",
                              plan=plan, authorization_mode=mode, result="failed", detail=str(exc))
        raise
    verified_ref = append_external_audit(root, adapter="gmail", operation="mark_read", target_ref=f"message:{message_id}",
                                         plan=plan, authorization_mode=mode, result="verified", readback_ref=applied_ref)
    return {"status": "applied", "verified": True, "plan": plan, "audit_refs": [attempt_ref, applied_ref, verified_ref]}


def safe_obsidian_path(vault: Path, relative_path: str) -> Path:
    vault = vault.expanduser().resolve()
    target = (vault / relative_path).resolve()
    if target == vault or vault not in target.parents:
        raise ValueError("Obsidian note path must remain inside the configured vault")
    if target.suffix.casefold() != ".md":
        raise ValueError("Obsidian note must use a .md extension")
    return target


def _require_private_obsidian_vault(vault: Path) -> None:
    raw = vault.expanduser()
    if raw.is_symlink():
        raise ValueError("Obsidian vault cannot be a symlink")
    root = raw.resolve()
    distribution_root = Path(__file__).resolve().parents[3]
    if root == distribution_root or distribution_root in root.parents:
        raise ValueError("Obsidian vault must be outside the Career Copilot distribution")
    for ancestor in (root, *root.parents):
        if (ancestor / ".git").exists():
            raise ValueError("Obsidian vault must be outside a Git repository")


def obsidian_write(
    vault: Path,
    relative_path: str,
    content: str,
    apply: bool = False,
    profile: Optional[dict[str, Any]] = None,
    workspace: Optional[Path] = None,
    approved_plan_sha256: str = "",
) -> dict[str, Any]:
    target = safe_obsidian_path(vault, relative_path)
    plan = {
        "adapter": "obsidian",
        "operation": "write_note",
        "relative_path": relative_path,
        "vault_path_sha256": hashlib.sha256(str(vault.expanduser().resolve()).encode("utf-8")).hexdigest(),
        "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
    }
    approval_sha256 = _plan_hash({"domain": "career-copilot/obsidian-write/v1", "plan": plan})
    if not apply:
        return {"status": "dry_run", "plan": plan, "approval_sha256": approval_sha256}
    if approved_plan_sha256 != approval_sha256:
        raise ValueError("Obsidian write requires the current approved plan hash")
    root, mode, attempt_ref = _audit_before_mutation(workspace, plan, profile, f"note:{relative_path}")
    try:
        _require_private_obsidian_vault(vault)
        _atomic_obsidian_write(target, content)
        if target.read_text(encoding="utf-8") != content:
            raise RuntimeError("Obsidian note readback verification failed")
    except Exception as exc:
        append_external_audit(root, adapter="obsidian", operation="write_note", target_ref=f"note:{relative_path}",
                              plan=plan, authorization_mode=mode, result="failed", detail=str(exc))
        raise
    applied_ref = append_external_audit(root, adapter="obsidian", operation="write_note", target_ref=f"note:{relative_path}",
                                        plan=plan, authorization_mode=mode, result="applied")
    verified_ref = append_external_audit(root, adapter="obsidian", operation="write_note", target_ref=f"note:{relative_path}",
                                         plan=plan, authorization_mode=mode, result="verified", readback_ref=applied_ref)
    return {"status": "applied", "verified": True, "plan": plan, "audit_refs": [attempt_ref, applied_ref, verified_ref]}


def _atomic_obsidian_write(target: Path, content: str) -> None:
    """Replace one Markdown target using a private, randomly named sibling file."""
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.parent.is_symlink():
        raise ValueError("Obsidian note parent cannot be a symlink")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        if temporary.exists() or temporary.is_symlink():
            temporary.unlink()


def _kanban_artifact(artifact: dict[str, Any]) -> tuple[str, str]:
    if not isinstance(artifact, dict):
        raise ValueError("Kanban artifact must be an object")
    artifact_ref = artifact.get("artifact_ref")
    card_text = artifact.get("card_text")
    if not isinstance(artifact_ref, str) or not artifact_ref.strip():
        raise ValueError("Kanban artifact requires a non-empty opaque artifact_ref")
    if not isinstance(card_text, str) or not card_text.strip() or "\n" in card_text:
        raise ValueError("Kanban artifact requires one non-empty single-line card_text")
    return artifact_ref.strip(), card_text.strip()


def _kanban_card_marker(artifact_ref: str) -> str:
    return "cc-" + hashlib.sha256(artifact_ref.encode("utf-8")).hexdigest()[:20]


def _new_kanban_board(lane: str, card_line: str) -> str:
    return (
        "---\nkanban-plugin: board\n---\n\n"
        f"## {lane}\n\n{card_line}\n\n"
        "%% kanban:settings\n```\n{\"kanban-plugin\":\"board\"}\n```\n%%\n"
    )


def _require_kanban_board_grammar(existing: str) -> None:
    frontmatter = re.match(r"\A---\r?\n(?P<body>.*?)\r?\n---\r?\n", existing, re.DOTALL)
    if not frontmatter:
        raise ValueError("existing Kanban board must begin with valid frontmatter")
    declarations = [line.strip() for line in frontmatter.group("body").splitlines() if line.strip() == "kanban-plugin: board"]
    if len(declarations) != 1:
        raise ValueError("existing Kanban board frontmatter must declare kanban-plugin: board exactly once")
    settings = list(re.finditer(r"(?m)^%% kanban:settings\s*$", existing))
    if len(settings) != 1 or not re.match(r"\r?\n```", existing[settings[0].end():]):
        raise ValueError("existing Kanban board must include one valid kanban:settings block")


def _append_kanban_card(existing: str, lane: str, card_line: str) -> tuple[str, str]:
    _require_kanban_board_grammar(existing)
    lane_pattern = re.compile(rf"(?m)^##\s+{re.escape(lane)}\s*$")
    matches = list(lane_pattern.finditer(existing))
    if len(matches) != 1:
        raise ValueError("configured Kanban lane must appear exactly once")
    start = matches[0].end()
    next_boundary = re.search(r"(?m)^(?:##\s+|\*\*\*\s*$|%% kanban:settings)", existing[start:])
    end = start + next_boundary.start() if next_boundary else len(existing)
    marker = card_line.rsplit("^", 1)[-1]
    matching = [match for match in re.finditer(rf"(?m)^- \[[ xX]\] .*\^{re.escape(marker)}[ \t]*$", existing)]
    if len(matching) > 1:
        raise ValueError("Kanban card marker is ambiguous")
    if matching:
        match = matching[0]
        if match.group(0) == card_line:
            return existing, "no_change"
        return existing[:match.start()] + card_line + existing[match.end():], "update_card_plan"
    insertion = "\n\n" + card_line + "\n"
    return existing[:end].rstrip("\n") + insertion + existing[end:], "append_card_plan"


def obsidian_kanban_project(
    vault: Path,
    relative_path: str,
    lane: str,
    artifact: dict[str, Any],
    apply: bool = False,
    profile: Optional[dict[str, Any]] = None,
    workspace: Optional[Path] = None,
    approved_plan_sha256: str = "",
) -> dict[str, Any]:
    """Preview one reviewed artifact as a card in a local Obsidian Kanban board."""
    target = safe_obsidian_path(vault, relative_path)
    if not isinstance(lane, str) or not lane.strip() or "\n" in lane or lane.strip().casefold() == "archive":
        raise ValueError("Kanban lane must be one non-Archive line")
    artifact_ref, card_text = _kanban_artifact(artifact)
    marker = _kanban_card_marker(artifact_ref)
    card_line = f"- [ ] {card_text} ^{marker}"
    existing = target.read_text(encoding="utf-8") if target.exists() else ""
    if target.exists():
        markdown, decision = _append_kanban_card(existing, lane.strip(), card_line)
    else:
        markdown = _new_kanban_board(lane.strip(), card_line)
        decision = "create_board_plan"
    plan = {
        "adapter": "obsidian_kanban",
        "operation": "project_card",
        "decision": decision,
        "relative_path": relative_path,
        "vault_path_sha256": hashlib.sha256(str(vault.expanduser().resolve()).encode("utf-8")).hexdigest(),
        "lane": lane.strip(),
        "artifact_ref_sha256": hashlib.sha256(artifact_ref.encode("utf-8")).hexdigest(),
        "card_marker": marker,
        "current_content_sha256": hashlib.sha256(existing.encode("utf-8")).hexdigest(),
        "content_sha256": hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
    }
    approval_sha256 = _plan_hash({"domain": "career-copilot/obsidian-kanban-project/v1", "plan": plan})
    if not apply:
        return {"status": "dry_run", "plan": plan, "markdown": markdown, "approval_sha256": approval_sha256}
    if not re.fullmatch(r"[0-9a-f]{64}", approved_plan_sha256):
        raise ValueError("Obsidian Kanban projection requires a 64-character lowercase SHA-256 approved plan hash")
    if approved_plan_sha256 != approval_sha256:
        raise ValueError("Obsidian Kanban projection requires the current approved plan hash")
    if decision == "no_change":
        if workspace is None:
            raise ValueError("external mutations require --workspace for private audit logging")
        _private_workspace(workspace)
        require_external_permission(profile)
        _require_private_obsidian_vault(vault)
        current = target.read_text(encoding="utf-8") if target.exists() else ""
        if hashlib.sha256(current.encode("utf-8")).hexdigest() != plan["current_content_sha256"]:
            raise ValueError("Obsidian Kanban board changed after review")
        return {"status": "no_change", "verified": True, "plan": plan, "audit_refs": []}
    root, mode, attempt_ref = _audit_before_mutation(workspace, plan, profile, f"kanban:{relative_path}:{marker}")
    try:
        _require_private_obsidian_vault(vault)
        current = target.read_text(encoding="utf-8") if target.exists() else ""
        if hashlib.sha256(current.encode("utf-8")).hexdigest() != plan["current_content_sha256"]:
            raise ValueError("Obsidian Kanban board changed after review")
        _atomic_obsidian_write(target, markdown)
        if target.read_text(encoding="utf-8") != markdown:
            raise RuntimeError("Obsidian Kanban readback verification failed")
    except Exception as exc:
        append_external_audit(root, adapter="obsidian_kanban", operation="project_card", target_ref=f"kanban:{relative_path}:{marker}",
                              plan=plan, authorization_mode=mode, result="failed", detail=str(exc))
        raise
    applied_ref = append_external_audit(root, adapter="obsidian_kanban", operation="project_card", target_ref=f"kanban:{relative_path}:{marker}",
                                        plan=plan, authorization_mode=mode, result="applied")
    verified_ref = append_external_audit(root, adapter="obsidian_kanban", operation="project_card", target_ref=f"kanban:{relative_path}:{marker}",
                                         plan=plan, authorization_mode=mode, result="verified", readback_ref=applied_ref)
    return {"status": "applied", "verified": True, "plan": plan, "audit_refs": [attempt_ref, applied_ref, verified_ref]}


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)

    sheets_get = commands.add_parser("sheets-read")
    sheets_get.add_argument("--sheet-id", required=True)
    sheets_get.add_argument("--range", required=True)

    sheets_reconcile_parser = commands.add_parser("sheets-reconcile")
    sheets_reconcile_parser.add_argument("--sheet-id", required=True)
    sheets_reconcile_parser.add_argument("--range", required=True, help="A1 range beginning at --header-row")
    sheets_reconcile_parser.add_argument("--header-row", required=True, type=int)
    sheets_reconcile_parser.add_argument("--fields-json", required=True, help="Logical field-to-header JSON mapping")
    sheets_reconcile_parser.add_argument("--record-json", required=True, help="Intended logical record JSON")
    sheets_reconcile_parser.add_argument("--operation", choices=("upsert", "create", "update"), default="upsert")
    sheets_reconcile_parser.add_argument("--create-physical-row", type=int)

    sheets_reconcile_apply_parser = commands.add_parser("sheets-reconcile-apply")
    sheets_reconcile_apply_parser.add_argument("--sheet-id", required=True)
    sheets_reconcile_apply_parser.add_argument("--range", required=True, help="Closed A1 range beginning at --header-row")
    sheets_reconcile_apply_parser.add_argument("--header-row", required=True, type=int)
    sheets_reconcile_apply_parser.add_argument("--fields-json", required=True, help="Logical field-to-header JSON mapping")
    sheets_reconcile_apply_parser.add_argument("--record-json", required=True, help="Intended logical record JSON")
    sheets_reconcile_apply_parser.add_argument("--operation", choices=("upsert", "create", "update"), default="upsert")
    sheets_reconcile_apply_parser.add_argument("--create-physical-row", type=int)
    sheets_reconcile_apply_parser.add_argument("--approved-plan-sha256", default="", help="Required with --apply; from the reviewed dry run")
    sheets_reconcile_apply_parser.add_argument("--profile", help="Private profile.yaml; required with --apply")
    sheets_reconcile_apply_parser.add_argument("--workspace", help="Private workspace for required audit events; required with --apply")
    sheets_reconcile_apply_parser.add_argument("--apply", action="store_true", help="Execute only the hash-approved, current plan")

    sheets_set = commands.add_parser("sheets-update")
    sheets_set.add_argument("--sheet-id", required=True)
    sheets_set.add_argument("--range", required=True)
    sheets_set.add_argument("--values-json", required=True)
    sheets_set.add_argument("--profile", help="Private profile.yaml; required with --apply")
    sheets_set.add_argument("--workspace", help="Private workspace for required audit events; required with --apply")
    sheets_set.add_argument("--apply", action="store_true")

    gmail_find = commands.add_parser("gmail-search")
    gmail_find.add_argument("--query", required=True)
    gmail_find.add_argument("--user-id", default="me")
    gmail_find.add_argument("--max-results", type=int, default=20)

    gmail_read = commands.add_parser("gmail-get")
    gmail_read.add_argument("--message-id", required=True)
    gmail_read.add_argument("--user-id", default="me")

    gmail_triage_parser = commands.add_parser("gmail-triage")
    gmail_triage_parser.add_argument("--message-id", required=True)
    gmail_triage_parser.add_argument("--account-ref", required=True)
    gmail_triage_parser.add_argument("--workspace", required=True)
    gmail_triage_parser.add_argument("--supported-fact", default="", help="Directly supported fact; optional")
    gmail_triage_parser.add_argument("--excerpt", default="", help="Minimal excerpt (500 chars max); required with --supported-fact unless --content-sha256 is used")
    gmail_triage_parser.add_argument("--content-sha256", default="", help="Content hash; alternative to --excerpt for --supported-fact")
    gmail_triage_parser.add_argument("--user-id", default="me")

    gmail_reconcile_parser = commands.add_parser("gmail-reconcile")
    gmail_reconcile_parser.add_argument("--snapshot-json", required=True, help="Validated tracker snapshot JSON")
    gmail_reconcile_parser.add_argument("--fields-json", required=True, help="Logical field-to-header JSON mapping")
    gmail_reconcile_parser.add_argument("--record-json", required=True, help="Intended tracker record JSON")
    gmail_reconcile_parser.add_argument("--evidence-ref", required=True, help="Opaque private Gmail evidence reference")
    gmail_reconcile_parser.add_argument("--operation", choices=("upsert", "create", "update"), default="upsert")
    gmail_reconcile_parser.add_argument("--create-physical-row", type=int)

    gmail_modify = commands.add_parser("gmail-mark-read")
    gmail_modify.add_argument("--message-id", required=True)
    gmail_modify.add_argument("--user-id", default="me")
    gmail_modify.add_argument("--profile", help="Private profile.yaml; required with --apply")
    gmail_modify.add_argument("--workspace", help="Private workspace for required audit events; required with --apply")
    gmail_modify.add_argument("--approved-plan-sha256", default="", help="Required with --apply; from the reviewed dry run")
    gmail_modify.add_argument("--apply", action="store_true")

    obsidian = commands.add_parser("obsidian-write")
    obsidian.add_argument("--vault", required=True)
    obsidian.add_argument("--relative-path", required=True)
    obsidian.add_argument("--content-file", required=True)
    obsidian.add_argument("--profile", help="Private profile.yaml; required with --apply")
    obsidian.add_argument("--workspace", help="Private workspace for required audit events; required with --apply")
    obsidian.add_argument("--approved-plan-sha256", default="", help="Required with --apply; from the reviewed dry run")
    obsidian.add_argument("--apply", action="store_true")

    kanban = commands.add_parser("obsidian-kanban-project", help="Preview or apply one approved local Obsidian Kanban card projection")
    kanban.add_argument("--vault", required=True)
    kanban.add_argument("--relative-path", required=True)
    kanban.add_argument("--lane", required=True, help="Explicit existing or initial Kanban lane heading")
    kanban.add_argument("--artifact-json", required=True, help="Reviewed artifact JSON with opaque artifact_ref and single-line card_text")
    kanban.add_argument("--profile", help="Private profile.yaml; required with --apply")
    kanban.add_argument("--workspace", help="Private workspace for required audit events; required with --apply")
    kanban.add_argument("--approved-plan-sha256", default="", help="Required with --apply; from the reviewed dry run")
    kanban.add_argument("--apply", action="store_true", help="Execute only the hash-approved, current plan")
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "sheets-read":
            result = sheets_read(run_json_command, args.sheet_id, args.range)
        elif args.command == "sheets-reconcile":
            fields = json.loads(args.fields_json)
            record = json.loads(args.record_json)
            if not isinstance(fields, dict) or not isinstance(record, dict):
                raise ValueError("fields-json and record-json must both be JSON objects")
            result = sheets_reconcile(
                run_json_command, args.sheet_id, args.range, args.header_row, fields, record,
                operation=args.operation,
                create_physical_row=args.create_physical_row,
                require_contiguous_business_ids=True,
                reject_duplicate_business_ids=True,
            )
        elif args.command == "sheets-reconcile-apply":
            fields = json.loads(args.fields_json)
            record = json.loads(args.record_json)
            if not isinstance(fields, dict) or not isinstance(record, dict):
                raise ValueError("fields-json and record-json must both be JSON objects")
            result = sheets_reconcile_apply(
                run_json_command, args.sheet_id, args.range, args.header_row, fields, record,
                operation=args.operation, create_physical_row=args.create_physical_row,
                apply=args.apply, approved_plan_sha256=args.approved_plan_sha256,
                profile=load_profile(args.profile), workspace=Path(args.workspace) if args.workspace else None,
            )
        elif args.command == "sheets-update":
            values = json.loads(args.values_json)
            if not isinstance(values, list) or any(not isinstance(row, list) for row in values):
                raise ValueError("values-json must be a JSON array of row arrays")
            result = sheets_update(
                run_json_command, args.sheet_id, args.range, values, args.apply,
                load_profile(args.profile), Path(args.workspace) if args.workspace else None,
            )
        elif args.command == "gmail-search":
            result = gmail_search(run_json_command, args.query, args.user_id, args.max_results)
        elif args.command == "gmail-get":
            result = gmail_get(run_json_command, args.message_id, args.user_id)
        elif args.command == "gmail-triage":
            result = gmail_triage(
                run_json_command, args.message_id, workspace=Path(args.workspace),
                account_ref=args.account_ref, user_id=args.user_id, supported_fact=args.supported_fact,
                excerpt=args.excerpt, content_sha256=args.content_sha256,
            )
        elif args.command == "gmail-reconcile":
            snapshot = json.loads(args.snapshot_json)
            fields = json.loads(args.fields_json)
            record = json.loads(args.record_json)
            if not isinstance(snapshot, dict) or not isinstance(fields, dict) or not isinstance(record, dict):
                raise ValueError("snapshot-json, fields-json and record-json must all be JSON objects")
            result = gmail_reconciliation_proposal(
                snapshot, fields, record, args.evidence_ref, operation=args.operation,
                create_physical_row=args.create_physical_row,
            )
        elif args.command == "gmail-mark-read":
            result = gmail_mark_read(
                run_json_command, args.message_id, args.user_id, args.apply,
                load_profile(args.profile), Path(args.workspace) if args.workspace else None,
                args.approved_plan_sha256,
            )
        elif args.command == "obsidian-write":
            content = Path(args.content_file).read_text(encoding="utf-8")
            result = obsidian_write(
                Path(args.vault), args.relative_path, content, args.apply,
                load_profile(args.profile), Path(args.workspace) if args.workspace else None,
                args.approved_plan_sha256,
            )
        elif args.command == "obsidian-kanban-project":
            artifact = json.loads(args.artifact_json)
            if not isinstance(artifact, dict):
                raise ValueError("artifact-json must be a JSON object")
            result = obsidian_kanban_project(
                Path(args.vault), args.relative_path, args.lane, artifact, args.apply,
                load_profile(args.profile), Path(args.workspace) if args.workspace else None,
                args.approved_plan_sha256,
            )
        else:
            raise ValueError(f"unsupported command: {args.command}")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (ValueError, RuntimeError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
