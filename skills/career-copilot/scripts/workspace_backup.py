#!/usr/bin/env python3
"""Create, verify, and restore encrypted Career Copilot workspace backups."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Iterable, Sequence


ARCHIVE_FORMAT = "career-copilot-workspace-backup"
ARCHIVE_VERSION = 1
MANIFEST_NAME = "manifest.json"
FILES_PREFIX = "files"


class BackupError(ValueError):
    """User-facing validation or workflow error."""


@dataclass(frozen=True)
class WorkspaceInventory:
    directories: list[str]
    files: list[str]


@dataclass(frozen=True)
class VerificationResult:
    directories: int
    files: int


def containing_git_root(path: Path) -> Path | None:
    start = path if path.is_dir() else path.parent
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def ensure_no_symlink_ancestors(path: Path, label: str) -> None:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current = current / part
        if current.exists() and current.is_symlink():
            raise BackupError(f"{label} cannot traverse a symlinked path component: {current}")


def resolve_private_path(path: Path, label: str, *, must_exist: bool) -> Path:
    expanded = path.expanduser()
    if expanded.exists() and expanded.is_symlink():
        raise BackupError(f"{label} cannot be a symlink: {expanded}")
    resolved = expanded.resolve(strict=must_exist)
    ensure_no_symlink_ancestors(resolved, label)
    return resolved


def assert_private_boundary(path: Path, skill_dir: Path, label: str) -> None:
    profile_root = skill_dir.resolve().parents[1]
    if path == profile_root or profile_root in path.parents:
        raise BackupError(
            f"{label} must be outside the Career Copilot profile/distribution directory"
        )
    git_root = containing_git_root(path)
    if git_root is not None:
        raise BackupError(f"{label} must be outside a Git repository: {git_root}")


def assert_regular_workspace_root(path: Path, label: str) -> None:
    if not path.exists():
        return
    if path.is_symlink():
        raise BackupError(f"{label} cannot be a symlink: {path}")
    if not path.is_dir():
        raise BackupError(f"{label} must be a directory: {path}")


def iter_workspace_entries(source: Path) -> WorkspaceInventory:
    directories: list[str] = []
    files: list[str] = []

    def walk(current: Path, rel_base: Path = Path(".")) -> None:
        entries = sorted(current.iterdir(), key=lambda item: item.name)
        for entry in entries:
            rel = entry.relative_to(source).as_posix()
            if entry.is_symlink():
                raise BackupError(f"private workspace cannot contain symlinks: {entry}")
            if entry.is_dir():
                directories.append(rel)
                walk(entry, rel_base / entry.name)
                continue
            if entry.is_file():
                files.append(rel)
                continue
            raise BackupError(f"private workspace cannot contain unsupported entries: {entry}")

    walk(source)
    return WorkspaceInventory(directories=directories, files=files)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_file_bytes(path: Path) -> bytes:
    with path.open("rb") as handle:
        return handle.read()


def add_tar_bytes(tar: tarfile.TarFile, name: str, data: bytes, mode: int = 0o600) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = mode
    info.mtime = 0
    tar.addfile(info, io.BytesIO(data))


# Avoid importing io unless needed elsewhere.
import io  # noqa: E402  # isort: skip


def build_manifest(source: Path, inventory: WorkspaceInventory) -> dict:
    directories = [{"path": path, "mode": 0o700} for path in inventory.directories]
    files = []
    for rel in inventory.files:
        file_path = source / rel
        files.append(
            {
                "path": rel,
                "mode": 0o600,
                "size": file_path.stat().st_size,
                "sha256": sha256_file(file_path),
            }
        )
    return {
        "format": ARCHIVE_FORMAT,
        "version": ARCHIVE_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "directories": directories,
        "files": files,
    }


def write_tar_archive(source: Path, tar_path: Path, manifest: dict, inventory: WorkspaceInventory) -> None:
    with tarfile.open(tar_path, mode="w") as tar:
        manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode(
            "utf-8"
        )
        add_tar_bytes(tar, MANIFEST_NAME, manifest_bytes)
        for rel in inventory.files:
            file_path = source / rel
            data = read_file_bytes(file_path)
            info = tarfile.TarInfo(f"{FILES_PREFIX}/{rel}")
            info.size = len(data)
            info.mode = 0o600
            info.mtime = 0
            tar.addfile(info, io.BytesIO(data))


def ensure_age_available(age_bin: str) -> None:
    if shutil.which(age_bin) is None:
        raise BackupError(f"age CLI not found on PATH: {age_bin}")


def run_age_encrypt(
    *,
    age_bin: str,
    tar_path: Path,
    output_path: Path,
    recipient: str | None = None,
    passphrase_mode: bool = False,
) -> None:
    ensure_age_available(age_bin)
    if bool(recipient) == passphrase_mode:
        raise BackupError("backup encryption requires exactly one of recipient or passphrase mode")

    cmd = [age_bin, "--encrypt", "--output", str(output_path)]
    if recipient is not None:
        cmd.extend(["--recipient", recipient])
    else:
        # age reads the passphrase from its own terminal prompt; never accept it
        # as an argument, environment variable or repository file.
        cmd.append("--passphrase")
    cmd.append(str(tar_path))
    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError as exc:
        raise BackupError(f"age CLI not found: {age_bin}") from exc
    except subprocess.CalledProcessError as exc:
        raise BackupError(f"age encryption failed: exit {exc.returncode}") from exc


def run_age_decrypt(
    *,
    age_bin: str,
    archive_path: Path,
    tar_path: Path,
    identities: list[Path] | None = None,
    passphrase_mode: bool = False,
) -> None:
    ensure_age_available(age_bin)
    if bool(identities) == passphrase_mode:
        raise BackupError("backup decryption requires exactly one of identity or passphrase mode")

    cmd = [age_bin, "--decrypt", "--output", str(tar_path)]
    if identities:
        for identity in identities:
            cmd.extend(["--identity", str(identity)])
    else:
        # See encrypt: let age prompt directly, never route the secret through us.
        cmd.append("--passphrase")
    cmd.append(str(archive_path))
    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError as exc:
        raise BackupError(f"age CLI not found: {age_bin}") from exc
    except subprocess.CalledProcessError as exc:
        raise BackupError(f"age decryption failed: exit {exc.returncode}") from exc


def parse_manifest(tar_path: Path) -> dict:
    with tarfile.open(tar_path, mode="r") as tar:
        names = [member.name for member in tar.getmembers()]
        if MANIFEST_NAME not in names:
            raise BackupError("backup archive is missing manifest.json")
        manifest_member = tar.getmember(MANIFEST_NAME)
        if not manifest_member.isfile():
            raise BackupError("backup manifest must be a regular file")
        manifest_text = tar.extractfile(manifest_member)
        if manifest_text is None:
            raise BackupError("unable to read backup manifest")
        manifest = json.loads(manifest_text.read().decode("utf-8"))
        validate_manifest_schema(manifest)
        validate_tar_contents(tar, manifest)
        return manifest


def validate_manifest_schema(manifest: dict) -> None:
    if manifest.get("format") != ARCHIVE_FORMAT:
        raise BackupError("backup manifest format mismatch")
    if manifest.get("version") != ARCHIVE_VERSION:
        raise BackupError("backup manifest version mismatch")
    for key in ("directories", "files"):
        if key not in manifest or not isinstance(manifest[key], list):
            raise BackupError(f"backup manifest missing {key}")


def validate_manifest_relpath(relpath: str, *, context: str) -> None:
    posix = PurePosixPath(relpath)
    if posix.is_absolute() or any(part in {"", ".", ".."} for part in posix.parts):
        raise BackupError(f"{context} contains an unsafe path: {relpath}")


def validate_tar_contents(tar: tarfile.TarFile, manifest: dict) -> None:
    expected_files = {item["path"]: item for item in manifest["files"]}
    expected_dirs = {item["path"] for item in manifest["directories"]}
    seen_files: set[str] = set()
    seen_entries: set[str] = set()

    for member in tar.getmembers():
        if member.name in seen_entries:
            raise BackupError(f"archive contains duplicate entry: {member.name}")
        seen_entries.add(member.name)
        if member.name == MANIFEST_NAME:
            continue
        if member.name.startswith(f"{FILES_PREFIX}/"):
            rel = member.name[len(FILES_PREFIX) + 1 :]
            validate_manifest_relpath(rel, context="archive file entry")
            if not member.isfile():
                raise BackupError(f"archive entry is not a regular file: {member.name}")
            file_meta = expected_files.get(rel)
            if file_meta is None:
                raise BackupError(f"archive contains unexpected file: {rel}")
            extracted = tar.extractfile(member)
            if extracted is None:
                raise BackupError(f"unable to read archive file: {rel}")
            data = extracted.read()
            if len(data) != file_meta["size"]:
                raise BackupError(f"archive file size mismatch: {rel}")
            if hashlib.sha256(data).hexdigest() != file_meta["sha256"]:
                raise BackupError(f"archive file checksum mismatch: {rel}")
            seen_files.add(rel)
            continue
        raise BackupError(f"archive contains unexpected entry: {member.name}")

    missing_files = set(expected_files) - seen_files
    if missing_files:
        raise BackupError(f"archive is missing files: {sorted(missing_files)}")
    if expected_dirs:
        for rel in expected_dirs:
            validate_manifest_relpath(rel, context="archive directory entry")


def extract_verified_archive(tar_path: Path, target: Path) -> VerificationResult:
    manifest = parse_manifest(tar_path)
    directories = [item["path"] for item in manifest["directories"]]
    files = manifest["files"]

    target.mkdir(parents=True, exist_ok=True)
    os.chmod(target, 0o700)
    for rel in directories:
        directory = target / rel
        directory.mkdir(parents=True, exist_ok=True)
        os.chmod(directory, 0o700)
    for item in files:
        rel = item["path"]
        archive_name = f"{FILES_PREFIX}/{rel}"
        with tarfile.open(tar_path, mode="r") as tar:
            member = tar.getmember(archive_name)
            extracted = tar.extractfile(member)
            if extracted is None:
                raise BackupError(f"unable to extract archive file: {rel}")
            destination = target / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("wb") as handle:
                shutil.copyfileobj(extracted, handle)
            os.chmod(destination, 0o600)

    normalize_tree(target, directories, [item["path"] for item in files])
    verify_tree(target, manifest)
    return VerificationResult(directories=len(directories), files=len(files))


def normalize_tree(root: Path, directories: Iterable[str], files: Iterable[str]) -> None:
    os.chmod(root, 0o700)
    for rel in directories:
        os.chmod(root / rel, 0o700)
    for rel in files:
        os.chmod(root / rel, 0o600)


def verify_tree(root: Path, manifest: dict) -> None:
    for directory in manifest["directories"]:
        rel = directory["path"]
        validate_manifest_relpath(rel, context="restore directory entry")
        directory_path = root / rel
        if not directory_path.exists() or not directory_path.is_dir() or directory_path.is_symlink():
            raise BackupError(f"restored directory missing or invalid: {rel}")
        if stat_mode(directory_path) != 0o700:
            raise BackupError(f"restored directory mode mismatch: {rel}")

    for file_entry in manifest["files"]:
        rel = file_entry["path"]
        validate_manifest_relpath(rel, context="restore file entry")
        file_path = root / rel
        if not file_path.exists() or not file_path.is_file() or file_path.is_symlink():
            raise BackupError(f"restored file missing or invalid: {rel}")
        if stat_mode(file_path) != 0o600:
            raise BackupError(f"restored file mode mismatch: {rel}")
        if sha256_file(file_path) != file_entry["sha256"]:
            raise BackupError(f"restored file checksum mismatch: {rel}")


def stat_mode(path: Path) -> int:
    return path.stat().st_mode & 0o777


def backup_create(
    *,
    source: Path,
    output: Path,
    skill_dir: Path,
    age_bin: str,
    recipient: str | None,
    passphrase_mode: bool,
    overwrite: bool,
) -> dict:
    source = resolve_private_path(source, "source workspace", must_exist=True)
    assert_private_boundary(source, skill_dir, "source workspace")
    assert_regular_workspace_root(source, "source workspace")
    inventory = iter_workspace_entries(source)
    manifest = build_manifest(source, inventory)

    output = resolve_private_path(output, "backup output", must_exist=False)
    assert_private_boundary(output, skill_dir, "backup output")
    if output.exists() and output.is_symlink():
        raise BackupError(f"backup output cannot be a symlink: {output}")
    if output.exists() and not overwrite:
        raise BackupError(f"backup output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        tar_path = Path(tmpdir) / "workspace-backup.tar"
        write_tar_archive(source, tar_path, manifest, inventory)
        encrypted_tmp = Path(tmpdir) / "workspace-backup.age"
        run_age_encrypt(
            age_bin=age_bin,
            tar_path=tar_path,
            output_path=encrypted_tmp,
            recipient=recipient,
            passphrase_mode=passphrase_mode,
        )
        os.replace(encrypted_tmp, output)

    return {"files": len(inventory.files), "directories": len(inventory.directories), "output": str(output)}


def backup_verify(
    *,
    archive: Path,
    age_bin: str,
    identities: list[Path] | None,
    passphrase_mode: bool,
) -> dict:
    archive = resolve_private_path(archive, "backup archive", must_exist=True)
    with tempfile.TemporaryDirectory() as tmpdir:
        tar_path = Path(tmpdir) / "workspace-backup.tar"
        run_age_decrypt(
            age_bin=age_bin,
            archive_path=archive,
            tar_path=tar_path,
            identities=identities,
            passphrase_mode=passphrase_mode,
        )
        manifest = parse_manifest(tar_path)
    return {"files": len(manifest["files"]), "directories": len(manifest["directories"]) }


def backup_restore(
    *,
    archive: Path,
    target: Path,
    skill_dir: Path,
    age_bin: str,
    identities: list[Path] | None,
    passphrase_mode: bool,
) -> dict:
    archive = resolve_private_path(archive, "backup archive", must_exist=True)
    target = target.expanduser()
    if target.exists() and target.is_symlink():
        raise BackupError(f"restore target cannot be a symlink: {target}")
    target_resolved = target.resolve(strict=False)
    ensure_no_symlink_ancestors(target_resolved, "restore target")
    assert_private_boundary(target_resolved, skill_dir, "restore target")
    if target.exists():
        if target.is_symlink():
            raise BackupError(f"restore target cannot be a symlink: {target}")
        if not target.is_dir():
            raise BackupError(f"restore target must be a directory: {target}")
        if any(target.iterdir()):
            raise BackupError(f"restore target must be new or empty: {target}")
    else:
        if not target.parent.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
        if target.parent.is_symlink():
            raise BackupError(f"restore target parent cannot be a symlink: {target.parent}")

    with tempfile.TemporaryDirectory(dir=str(target.parent)) as tmpdir:
        staging = Path(tmpdir) / target.name
        run_age_decrypt(
            age_bin=age_bin,
            archive_path=archive,
            tar_path=staging.with_suffix(".tar"),
            identities=identities,
            passphrase_mode=passphrase_mode,
        )
        tar_path = staging.with_suffix(".tar")
        result = extract_verified_archive(tar_path, staging)
        if target.exists():
            target.rmdir()
        os.replace(staging, target)
        manifest = parse_manifest(tar_path)
        verify_tree(target, manifest)
    return {
        "files": result.files,
        "directories": result.directories,
        "target": str(target.resolve()),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--age-bin", default="age", help="age executable name or path")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="Create an encrypted workspace backup")
    create.add_argument("--source", required=True, help="Source workspace directory")
    create.add_argument("--output", required=True, help="Encrypted backup archive")
    auth = create.add_mutually_exclusive_group(required=True)
    auth.add_argument("--recipient", help="age recipient public key")
    auth.add_argument("--passphrase", action="store_true", help="Use age passphrase mode")
    create.add_argument("--overwrite-output", action="store_true", help="Replace an existing archive")

    verify = subparsers.add_parser("verify", help="Verify an encrypted workspace backup")
    verify.add_argument("--archive", required=True, help="Encrypted backup archive")
    verify_auth = verify.add_mutually_exclusive_group(required=True)
    verify_auth.add_argument("--identity", action="append", dest="identities", help="age identity file")
    verify_auth.add_argument("--passphrase", action="store_true", help="Use age passphrase mode")

    restore = subparsers.add_parser("restore", help="Restore an encrypted workspace backup")
    restore.add_argument("--archive", required=True, help="Encrypted backup archive")
    restore.add_argument("--target", required=True, help="Restore target directory")
    restore_auth = restore.add_mutually_exclusive_group(required=True)
    restore_auth.add_argument("--identity", action="append", dest="identities", help="age identity file")
    restore_auth.add_argument("--passphrase", action="store_true", help="Use age passphrase mode")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    skill_dir = Path(__file__).resolve().parents[1]

    try:
        if args.command == "create":
            result = backup_create(
                source=Path(args.source),
                output=Path(args.output),
                skill_dir=skill_dir,
                age_bin=args.age_bin,
                recipient=args.recipient,
                passphrase_mode=args.passphrase,
                overwrite=args.overwrite_output,
            )
            print(
                f"backup created: {result['files']} file(s), {result['directories']} directorie(s) -> {result['output']}"
            )
            return 0
        if args.command == "verify":
            result = backup_verify(
                archive=Path(args.archive),
                age_bin=args.age_bin,
                identities=[Path(item) for item in args.identities] if args.identities else None,
                passphrase_mode=args.passphrase,
            )
            print(f"backup verified: {result['files']} file(s), {result['directories']} directorie(s)")
            return 0
        if args.command == "restore":
            result = backup_restore(
                archive=Path(args.archive),
                target=Path(args.target),
                skill_dir=skill_dir,
                age_bin=args.age_bin,
                identities=[Path(item) for item in args.identities] if args.identities else None,
                passphrase_mode=args.passphrase,
            )
            print(f"backup restored: {result['files']} file(s), {result['directories']} directorie(s) -> {result['target']}")
            return 0
        raise BackupError(f"unknown command: {args.command}")
    except BackupError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
