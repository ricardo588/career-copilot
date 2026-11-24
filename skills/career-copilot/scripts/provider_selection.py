#!/usr/bin/env python3
"""Deterministic local public-provider guidance; it never performs acquisition."""

from __future__ import annotations

import argparse
import json
import os
import stat
from pathlib import Path
from typing import Any


REGISTRY_VERSION = "2026-11-24"
SYSTEM_PATH_SYMLINKS = {Path("/var"), Path("/tmp")}
PROVIDERS = {
    "greenhouse_public_board": {"name": "Greenhouse Job Board", "acquisition_state": "integrated_read_only", "coverage": "Candidate-confirmed public Greenhouse boards across supported geographies.", "evidence_url": "https://developers.greenhouse.io/job-board.html", "evidence_checked_on": "2026-11-24"},
    "lever_public_postings": {"name": "Lever Postings", "acquisition_state": "integrated_read_only", "coverage": "Candidate-confirmed public Lever sites across supported geographies.", "evidence_url": "https://github.com/lever/postings-api", "evidence_checked_on": "2026-11-24"},
    "occ_mundial": {"name": "OCC Mundial", "acquisition_state": "coverage_only", "coverage": "Mexico-focused job-board coverage.", "evidence_url": "https://www.occ.com.mx/empleos/en-ciudad-de-mexico/", "evidence_checked_on": "2026-11-24"},
    "get_on_board": {"name": "Get on Board", "acquisition_state": "coverage_only", "coverage": "Latin America-focused technology-role coverage.", "evidence_url": "https://www.getonbrd.com/", "evidence_checked_on": "2026-11-24"},
    "we_work_remotely": {"name": "We Work Remotely", "acquisition_state": "coverage_only", "coverage": "Remote-work and contract-work coverage.", "evidence_url": "https://weworkremotely.com/remote-jobs", "evidence_checked_on": "2026-11-24"},
    "remoteok": {"name": "Remote OK", "acquisition_state": "coverage_only", "coverage": "Candidate-selected remote coverage.", "evidence_url": "https://remoteok.com/", "evidence_checked_on": "2026-11-24"},
    "the_ladders": {"name": "The Ladders", "acquisition_state": "coverage_only", "coverage": "United States senior-role coverage.", "evidence_url": "https://www.theladders.com/", "evidence_checked_on": "2026-11-24"},
}


class SelectionError(ValueError):
    pass


def values(document: dict[str, Any], *path: str) -> list[str]:
    current: Any = document
    for item in path:
        if not isinstance(current, dict):
            return []
        current = current.get(item)
    return [value for value in current if isinstance(value, str)] if isinstance(current, list) else []


def text(items: list[str]) -> str:
    return " ".join(items).casefold()


def selected(provider_id: str, reason: str) -> dict[str, Any]:
    provider = PROVIDERS[provider_id]
    return {"id": provider_id, "name": provider["name"], "acquisition_state": provider["acquisition_state"], "reason": reason, "coverage": provider["coverage"], "evidence_url": provider["evidence_url"], "evidence_checked_on": provider["evidence_checked_on"], "registry_version": REGISTRY_VERSION, "explicit_action_required": True}


def select_providers(profile: dict[str, Any], rules: dict[str, Any]) -> dict[str, Any]:
    """Select local coverage guidance only from declared profile and rules."""
    roles = text(values(profile, "profile", "target_roles"))
    seniority = text(values(profile, "profile", "target_seniority"))
    geography = text(values(profile, "constraints", "countries") + values(profile, "constraints", "locations"))
    modes = text(values(profile, "constraints", "work_modes"))
    employment = text(values(profile, "constraints", "employment_types"))
    requested = {item.casefold() for item in values(rules, "search", "selected_job_portals")}
    selection = [selected("greenhouse_public_board", "Official ATS coverage requires an explicit candidate-confirmed board identifier."), selected("lever_public_postings", "Official ATS coverage requires an explicit candidate-confirmed site identifier.")]
    if "mexico" in geography or "méxico" in geography:
        selection.append(selected("occ_mundial", "Mexico is an explicitly declared eligible geography."))
    latin_terms = (
        "argentina", "belize", "bolivia", "brazil", "brasil", "chile", "colombia", "costa rica", "cuba",
        "dominican republic", "ecuador", "el salvador", "guatemala", "guyana", "haiti", "honduras", "jamaica",
        "mexico", "méxico", "nicaragua", "panama", "panamá", "paraguay", "peru", "perú", "puerto rico",
        "suriname", "trinidad", "uruguay", "venezuela", "latin america", "latinoamérica", "latam",
    )
    if any(term in geography for term in latin_terms):
        selection.append(selected("get_on_board", "Latin America is an explicitly declared eligible geography."))
    contract_terms = ("contract", "contractor", "freelance", "consult", "independent", "por proyecto")
    if "remote" in modes or "remoto" in modes or any(term in employment for term in contract_terms):
        selection.append(selected("we_work_remotely", "Declared work mode or employment type includes remote or contract coverage."))
    if "remoteok" in requested:
        selection.append(selected("remoteok", "The candidate explicitly selected this coverage-only portal in local rules."))
    executive_terms = ("director", "executive", "vice president", "vp", "chief", "head of")
    if ("united states" in geography or "usa" in geography or "u.s." in geography) and any(term in seniority or term in roles for term in executive_terms):
        selection.append(selected("the_ladders", "United States geography and executive seniority are explicitly declared."))
    ids = {item["id"] for item in selection}
    not_selected = [{"id": provider_id, "reason": "Declared profile and local rules did not select this coverage guidance."} for provider_id in sorted(set(PROVIDERS) - ids)]
    unknowns = []
    if not geography:
        unknowns.append("eligible_geography_not_declared")
    if not modes:
        unknowns.append("work_mode_not_declared")
    if not employment:
        unknowns.append("employment_type_not_declared")
    return {"schema_version": 1, "registry_version": REGISTRY_VERSION, "selected": selection, "not_selected": not_selected, "unknowns": unknowns, "limitations": ["Recommendations are coverage guidance only; no provider was queried and no current vacancy availability was asserted."], "external_actions": 0, "network_requests": 0, "tracker_mutations": 0}


def _canonical_system_path(path: Path) -> Path:
    for symlink in SYSTEM_PATH_SYMLINKS:
        if path == symlink or symlink in path.parents:
            return symlink.resolve() / path.relative_to(symlink)
    return path


def _lexical_absolute(raw: str) -> Path:
    return _canonical_system_path(Path(os.path.abspath(os.path.expanduser(raw))))


def _open_absolute_directory(path: Path) -> int:
    if not path.is_absolute():
        raise SelectionError("private path must be absolute")
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    root_fd = os.open("/", flags)
    current_fd = root_fd
    try:
        for component in path.parts[1:]:
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
        raise
    finally:
        if root_fd >= 0:
            os.close(root_fd)


def _validate_private_path(path: Path, workspace: Path, label: str) -> Path:
    distribution = Path(__file__).resolve().parents[3]
    if path == distribution or distribution in path.parents or workspace == distribution or distribution in workspace.parents or workspace in distribution.parents:
        raise SelectionError("private workspace cannot contain or be inside the distribution repository")
    for ancestor in (path, *path.parents):
        if ancestor.is_symlink() and ancestor not in SYSTEM_PATH_SYMLINKS:
            raise SelectionError(f"{label} cannot be beneath a symlink")
        if (ancestor / ".git").exists():
            raise SelectionError(f"{label} cannot be beneath a Git repository")
    try:
        path.relative_to(workspace)
    except ValueError as error:
        raise SelectionError(f"{label} must be within the private workspace") from error
    return path


def open_private_workspace(raw: str) -> tuple[Path, int]:
    workspace = _lexical_absolute(raw)
    _validate_private_path(workspace, workspace, "private workspace")
    try:
        return workspace, _open_absolute_directory(workspace)
    except OSError as error:
        raise SelectionError("private workspace must exist and cannot be beneath a symlink") from error


def private_input(raw: str, workspace: Path, label: str) -> Path:
    path = _validate_private_path(_lexical_absolute(raw), workspace, label)
    if not path.is_file():
        raise SelectionError(f"{label} must be an existing regular file")
    return path


def private_output(raw: str, workspace: Path) -> Path:
    path = _validate_private_path(_lexical_absolute(raw), workspace, "output")
    if path == workspace or not path.name or ".." in path.relative_to(workspace).parts:
        raise SelectionError("invalid private output path")
    return path


def _secure_parent_fd(workspace: Path, workspace_fd: int, destination: Path) -> tuple[int, str]:
    relative = destination.relative_to(workspace)
    root_fd, current_fd = os.dup(workspace_fd), None
    try:
        current_fd = root_fd
        for component in relative.parts[:-1]:
            try:
                os.mkdir(component, mode=0o700, dir_fd=current_fd)
            except FileExistsError:
                pass
            next_fd = os.open(component, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0), dir_fd=current_fd)
            if current_fd != root_fd:
                os.close(current_fd)
            current_fd = next_fd
        if current_fd == root_fd:
            root_fd = -1
        return current_fd, relative.name
    except Exception:
        if current_fd is not None and current_fd != root_fd:
            os.close(current_fd)
        raise
    finally:
        if root_fd >= 0:
            os.close(root_fd)


def _ensure_workspace_not_git(workspace_fd: int) -> None:
    try:
        os.stat(".git", dir_fd=workspace_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    raise SelectionError("private workspace became a Git repository")


def _secure_read_private_document(workspace: Path, workspace_fd: int, path: Path, label: str) -> dict[str, Any]:
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
                raise SelectionError(f"{label} must be an existing regular file")
            with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
                descriptor = -1
                raw = handle.read()
        finally:
            if descriptor >= 0:
                os.close(descriptor)
    except OSError as error:
        raise SelectionError(f"{label} cannot be read safely from the private workspace") from error
    finally:
        os.close(parent_fd)
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as error:
        raise SelectionError(f"invalid {label}: {error}") from error
    if not isinstance(document, dict):
        raise SelectionError(f"{label} must be a JSON object")
    return document


def write_private_output(workspace: Path, workspace_fd: int, path: Path, payload: dict[str, Any]) -> None:
    _ensure_workspace_not_git(workspace_fd)
    parent_fd, name = _secure_parent_fd(workspace, workspace_fd, path)
    temporary = f".{name}.{os.urandom(12).hex()}.tmp"
    try:
        try:
            os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            raise SelectionError("output already exists")
        except FileNotFoundError:
            pass
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600, dir_fd=parent_fd)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                descriptor = -1
                handle.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
                handle.flush(); os.fsync(handle.fileno())
        finally:
            if descriptor >= 0:
                os.close(descriptor)
        os.replace(temporary, name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
        os.chmod(name, 0o600, dir_fd=parent_fd, follow_symlinks=False)
        try:
            _ensure_workspace_not_git(workspace_fd)
        except SelectionError:
            os.unlink(name, dir_fd=parent_fd)
            raise
    finally:
        try:
            os.unlink(temporary, dir_fd=parent_fd)
        except FileNotFoundError:
            pass
        os.close(parent_fd)


def load_document(path: Path, label: str) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SelectionError(f"invalid {label}: {error}") from error
    if not isinstance(document, dict):
        raise SelectionError(f"{label} must be a JSON object")
    return document


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--rules", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    workspace_fd = -1
    try:
        workspace, workspace_fd = open_private_workspace(args.workspace)
        profile = _secure_read_private_document(workspace, workspace_fd, private_input(args.profile, workspace, "profile"), "profile")
        rules = _secure_read_private_document(workspace, workspace_fd, private_input(args.rules, workspace, "rules"), "rules")
        output = private_output(args.output, workspace)
        write_private_output(workspace, workspace_fd, output, select_providers(profile, rules))
    except (OSError, SelectionError, ValueError) as error:
        print(f"ERROR: {error}")
        return 2
    finally:
        if workspace_fd >= 0:
            os.close(workspace_fd)
    print(f"provider selection: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
