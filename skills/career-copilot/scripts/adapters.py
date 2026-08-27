#!/usr/bin/env python3
"""Optional, dry-run-first adapters for Sheets, Gmail and Obsidian."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Optional


Runner = Callable[[list[str]], dict[str, Any]]


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


def sheets_update(
    runner: Runner,
    sheet_id: str,
    range_name: str,
    values: list[list[Any]],
    apply: bool = False,
    profile: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    plan = {"adapter": "google_sheets", "operation": "update", "sheet": sheet_hint(sheet_id), "range": range_name, "rows": len(values), "apply": apply}
    if not apply:
        return {"status": "dry_run", "plan": plan}
    require_external_permission(profile)
    params = json.dumps({"spreadsheetId": sheet_id, "range": range_name, "valueInputOption": "RAW"}, separators=(",", ":"))
    body = json.dumps({"values": values}, separators=(",", ":"))
    runner(["gws", "sheets", "spreadsheets", "values", "update", "--params", params, "--json", body])
    readback = sheets_read(runner, sheet_id, range_name)
    verified = readback.get("values") == values
    if not verified:
        raise RuntimeError("Sheets readback did not match requested values")
    return {"status": "applied", "verified": True, "plan": plan}


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
) -> dict[str, Any]:
    plan = {"adapter": "gmail", "operation": "mark_read", "message_id": message_id, "apply": apply}
    if not apply:
        return {"status": "dry_run", "plan": plan}
    require_external_permission(profile)
    params = json.dumps({"userId": user_id, "id": message_id}, separators=(",", ":"))
    runner(["gws", "gmail", "users", "messages", "modify", "--params", params, "--json", '{"removeLabelIds":["UNREAD"]}'])
    readback = gmail_get(runner, message_id, user_id)
    labels = readback.get("labelIds", [])
    if "UNREAD" in labels:
        raise RuntimeError("Gmail readback still contains UNREAD")
    return {"status": "applied", "verified": True, "plan": plan}


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

    sheets_set = commands.add_parser("sheets-update")
    sheets_set.add_argument("--sheet-id", required=True)
    sheets_set.add_argument("--range", required=True)
    sheets_set.add_argument("--values-json", required=True)
    sheets_set.add_argument("--profile", help="Private profile.yaml; required with --apply")
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
        elif args.command == "sheets-update":
            values = json.loads(args.values_json)
            if not isinstance(values, list) or any(not isinstance(row, list) for row in values):
                raise ValueError("values-json must be a JSON array of row arrays")
            result = sheets_update(
                run_json_command, args.sheet_id, args.range, values, args.apply,
                load_profile(args.profile),
            )
        elif args.command == "gmail-search":
            result = gmail_search(run_json_command, args.query, args.user_id, args.max_results)
        elif args.command == "gmail-get":
            result = gmail_get(run_json_command, args.message_id, args.user_id)
        elif args.command == "gmail-mark-read":
            result = gmail_mark_read(
                run_json_command, args.message_id, args.user_id, args.apply,
                load_profile(args.profile),
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
