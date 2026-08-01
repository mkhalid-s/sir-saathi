"""Encrypted PostgreSQL backup creation and non-destructive archive verification."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATABASE_URL_ENV = "SIR_SAATHI_DATABASE_URL"
BACKUP_DIR_ENV = "SIR_SAATHI_BACKUP_DIR"
AGE_RECIPIENT_ENV = "SIR_SAATHI_AGE_RECIPIENT"
AGE_IDENTITY_ENV = "SIR_SAATHI_AGE_IDENTITY_FILE"


def _private_directory(raw_path: str) -> Path:
    path = Path(raw_path)
    if not path.is_absolute():
        raise ValueError(f"{BACKUP_DIR_ENV} must be an absolute path")
    resolved = path.resolve()
    if resolved == Path("/") or resolved == ROOT or ROOT in resolved.parents:
        raise ValueError("backup directory must stay outside the repository")
    if path.is_symlink():
        raise ValueError("backup directory must be a real directory, not a symlink")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not resolved.is_dir():
        raise ValueError("backup directory must be a real directory, not a symlink")
    if resolved.stat().st_mode & 0o077:
        raise ValueError("backup directory permissions must be 0700 or stricter")
    return resolved


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_command(name: str) -> str:
    command = shutil.which(name)
    if not command:
        raise RuntimeError(f"required backup command is unavailable: {name}")
    return command


def _private_regular_file(path: Path, label: str) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} must be an absolute regular file")
    resolved = path.resolve()
    if resolved == ROOT or ROOT in resolved.parents:
        raise ValueError(f"{label} must stay outside the repository")
    if resolved.stat().st_mode & 0o077:
        raise ValueError(f"{label} permissions must be 0600 or stricter")
    return resolved


def _private_output(path: Path):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    return os.fdopen(descriptor, "wb")


def create_backup(*, database_url: str, backup_dir: Path, recipient: str) -> dict[str, Any]:
    if not database_url.strip():
        raise ValueError(f"{DATABASE_URL_ENV} must not be empty")
    recipient = recipient.strip()
    if not recipient or any(character.isspace() for character in recipient):
        raise ValueError(f"{AGE_RECIPIENT_ENV} must contain one age recipient")
    pg_dump = _require_command("pg_dump")
    age = _require_command("age")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    unique_suffix = secrets.token_hex(4)
    filename = f"sir-saathi-{timestamp}-{unique_suffix}.dump.age"
    final_path = backup_dir / filename
    partial_path = backup_dir / f".{filename}.partial"
    checksum_path = backup_dir / f"{filename}.sha256"
    child_env = {**os.environ, "PGDATABASE": database_url}

    try:
        with _private_output(partial_path) as encrypted:
            dump = subprocess.Popen(
                [pg_dump, "--format=custom", "--no-owner", "--no-privileges"],
                env=child_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            if dump.stdout is None:  # pragma: no cover - guaranteed by PIPE
                raise RuntimeError("database backup stream could not be created")
            encrypt = subprocess.Popen(
                [age, "--encrypt", "--recipient", recipient],
                stdin=dump.stdout,
                stdout=encrypted,
                stderr=subprocess.DEVNULL,
            )
            dump.stdout.close()
            encrypt_status = encrypt.wait()
            dump_status = dump.wait()
            if dump_status != 0 or encrypt_status != 0:
                raise RuntimeError("encrypted database backup failed")
            encrypted.flush()
            os.fsync(encrypted.fileno())
        if partial_path.stat().st_size == 0:
            raise RuntimeError("encrypted database backup is empty")
        partial_path.rename(final_path)
        checksum = _sha256(final_path)
        with _private_output(checksum_path) as checksum_file:
            checksum_file.write(f"{checksum}  {filename}\n".encode("ascii"))
            checksum_file.flush()
            os.fsync(checksum_file.fileno())
        return {
            "backup_filename": filename,
            "checksum": checksum,
            "encrypted": True,
            "plaintext_written_to_disk": False,
            "size_bytes": final_path.stat().st_size,
        }
    except Exception:
        partial_path.unlink(missing_ok=True)
        final_path.unlink(missing_ok=True)
        checksum_path.unlink(missing_ok=True)
        raise


def verify_backup(*, backup_path: Path, identity_path: Path) -> dict[str, Any]:
    age = _require_command("age")
    pg_restore = _require_command("pg_restore")
    backup_path = _private_regular_file(backup_path, "backup")
    if backup_path.suffixes[-2:] != [".dump", ".age"]:
        raise ValueError("backup filename must end in .dump.age")
    identity_path = _private_regular_file(identity_path, "age identity")
    checksum_path = backup_path.with_name(f"{backup_path.name}.sha256")
    if not checksum_path.is_file() or checksum_path.is_symlink():
        raise ValueError("encrypted backup checksum file is missing")
    _private_regular_file(checksum_path, "backup checksum")
    expected_parts = checksum_path.read_text(encoding="ascii").strip().split()
    if len(expected_parts) != 2 or expected_parts[1] != backup_path.name:
        raise ValueError("encrypted backup checksum file is malformed")
    actual_checksum = _sha256(backup_path)
    if not secrets.compare_digest(expected_parts[0], actual_checksum):
        raise ValueError("encrypted backup checksum does not match")

    decrypt = subprocess.Popen(
        [age, "--decrypt", "--identity", str(identity_path), str(backup_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if decrypt.stdout is None:  # pragma: no cover - guaranteed by PIPE
        raise RuntimeError("backup decryption stream could not be created")
    inspect = subprocess.Popen(
        [pg_restore, "--list"],
        stdin=decrypt.stdout,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    decrypt.stdout.close()
    inspect_status = inspect.wait()
    decrypt_status = decrypt.wait()
    if decrypt_status != 0 or inspect_status != 0:
        raise RuntimeError("encrypted backup archive verification failed")
    return {
        "archive_valid": True,
        "backup_filename": backup_path.name,
        "checksum": actual_checksum,
        "encrypted": True,
        "plaintext_written_to_disk": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create or verify encrypted SIR Saathi database backups.")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("create", help="Stream a custom PostgreSQL dump directly into age encryption.")
    verify = subcommands.add_parser("verify", help="Verify checksum, decryption, and archive structure.")
    verify.add_argument("--backup", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "create":
            required = {
                DATABASE_URL_ENV: os.environ.get(DATABASE_URL_ENV),
                BACKUP_DIR_ENV: os.environ.get(BACKUP_DIR_ENV),
                AGE_RECIPIENT_ENV: os.environ.get(AGE_RECIPIENT_ENV),
            }
            missing = [name for name, value in required.items() if not value]
            if missing:
                raise ValueError(f"required environment is missing: {', '.join(missing)}")
            report = create_backup(
                database_url=required[DATABASE_URL_ENV] or "",
                backup_dir=_private_directory(required[BACKUP_DIR_ENV] or ""),
                recipient=required[AGE_RECIPIENT_ENV] or "",
            )
        else:
            identity = os.environ.get(AGE_IDENTITY_ENV)
            if not identity:
                raise ValueError(f"required environment is missing: {AGE_IDENTITY_ENV}")
            report = verify_backup(backup_path=args.backup, identity_path=Path(identity))
    except (ValueError, RuntimeError):
        print(json.dumps({"error": "backup operation failed", "ready": False}))
        return 1
    print(json.dumps({**report, "ready": True}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
