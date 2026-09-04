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


def gmail_mark_read(
    runner: Runner,
    message_id: str,
    user_id: str = "me",
    apply: bool = False,
    profile: Optional[dict[str, Any]] = None,
    workspace: Optional[Path] = None,
) -> dict[str, Any]:
    plan = {"adapter": "gmail", "operation": "mark_read", "message_id": message_id, "apply": apply}
    if not apply:
        return {"status": "dry_run", "plan": plan}
    root, mode, attempt_ref = _audit_before_mutation(workspace, plan, profile, f"message:{message_id}")
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


def obsidian_write(vault: Path, relative_path: str, content: str, apply: bool = False) -> dict[str, Any]:
    target = safe_obsidian_path(vault, relative_path)
    plan = {"adapter": "obsidian", "operation": "write_note", "relative_path": relative_path, "characters": len(content), "apply": apply}
    if not apply:
        return {"status": "dry_run", "plan": plan}
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, target)
    if target.read_text(encoding="utf-8") != content:
        raise RuntimeError("Obsidian note readback verification failed")
    return {"status": "applied", "verified": True, "plan": plan}


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

    gmail_modify = commands.add_parser("gmail-mark-read")
    gmail_modify.add_argument("--message-id", required=True)
    gmail_modify.add_argument("--user-id", default="me")
    gmail_modify.add_argument("--profile", help="Private profile.yaml; required with --apply")
    gmail_modify.add_argument("--workspace", help="Private workspace for required audit events; required with --apply")
    gmail_modify.add_argument("--apply", action="store_true")

    obsidian = commands.add_parser("obsidian-write")
    obsidian.add_argument("--vault", required=True)
    obsidian.add_argument("--relative-path", required=True)
    obsidian.add_argument("--content-file", required=True)
    obsidian.add_argument("--apply", action="store_true")
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
        elif args.command == "gmail-mark-read":
            result = gmail_mark_read(
                run_json_command, args.message_id, args.user_id, args.apply,
                load_profile(args.profile), Path(args.workspace) if args.workspace else None,
            )
        elif args.command == "obsidian-write":
            content = Path(args.content_file).read_text(encoding="utf-8")
            result = obsidian_write(Path(args.vault), args.relative_path, content, args.apply)
        else:
            raise ValueError(f"unsupported command: {args.command}")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (ValueError, RuntimeError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
