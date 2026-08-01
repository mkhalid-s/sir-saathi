"""Create and verify deterministic, commit-bound static PWA release bundles."""

from __future__ import annotations

import argparse
import gzip
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path, PurePosixPath
import re
import tarfile
import tempfile
from typing import Any

from .deployment_probe import expected_nationwide_routes

COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
BUNDLE_METADATA = "sir-saathi-release-bundle.json"
BUNDLE_PREFIX = "web"
SCHEMA_VERSION = 1
MAX_BUNDLE_FILES = 10_000
MAX_BUNDLE_BYTES = 100 * 1024 * 1024
REQUIRED_FILES = {"index.html", "manifest.webmanifest", "release-manifest.json", "sw.js"}


class ReleaseBundleError(ValueError):
    """A stable, non-sensitive release-bundle validation failure."""


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _require_commit(value: str) -> str:
    if not COMMIT_PATTERN.fullmatch(value):
        raise ReleaseBundleError("release.invalid_expected_commit")
    return value


def _safe_relative_path(value: str) -> bool:
    path = PurePosixPath(value)
    return bool(value) and not path.is_absolute() and ".." not in path.parts and str(path) == value


def _route_file(path: str) -> str | None:
    if path == "/":
        return "index.html"
    if path.startswith("/") and path.endswith("/") and "//" not in path:
        relative = path.strip("/")
        if _safe_relative_path(relative):
            return f"{relative}/index.html"
    return None


def _validate_release_manifest(files: dict[str, bytes], expected_commit: str) -> None:
    expected_routes = set(expected_nationwide_routes())
    try:
        payload = json.loads(files["release-manifest.json"])
    except (KeyError, json.JSONDecodeError, UnicodeDecodeError):
        raise ReleaseBundleError("release_manifest.unreadable") from None
    routes = payload.get("routes") if isinstance(payload, dict) else None
    if not (
        isinstance(payload, dict)
        and set(payload) == {"schema_version", "release_commit", "route_count", "routes"}
        and payload.get("schema_version") == 1
        and payload.get("release_commit") == expected_commit
        and isinstance(payload.get("route_count"), int)
        and isinstance(routes, list)
        and payload["route_count"] == len(routes) == len(expected_routes)
    ):
        raise ReleaseBundleError("release_manifest.invalid")
    seen: set[str] = set()
    for route in routes:
        if not isinstance(route, dict) or set(route) != {"path", "sha256"}:
            raise ReleaseBundleError("release_manifest.invalid")
        path = route.get("path")
        digest = route.get("sha256")
        filename = _route_file(path) if isinstance(path, str) else None
        if (
            filename is None
            or path in seen
            or not isinstance(digest, str)
            or not SHA256_PATTERN.fullmatch(digest)
            or filename not in files
            or _sha256(files[filename]) != digest
        ):
            raise ReleaseBundleError("release_manifest.invalid")
        seen.add(path)
    if seen != expected_routes:
        raise ReleaseBundleError("release_manifest.invalid_nationwide_scope")


def _source_files(source: Path, expected_commit: str) -> tuple[dict[str, bytes], dict[str, Any]]:
    if not source.is_dir() or source.is_symlink():
        raise ReleaseBundleError("source.invalid_directory")
    files: dict[str, bytes] = {}
    for path in sorted(source.rglob("*")):
        if path.is_symlink():
            raise ReleaseBundleError("source.symlink_not_allowed")
        if path.is_dir():
            continue
        if not path.is_file():
            raise ReleaseBundleError("source.unsupported_entry")
        relative = path.relative_to(source).as_posix()
        if not _safe_relative_path(relative):
            raise ReleaseBundleError("source.unsafe_path")
        files[relative] = path.read_bytes()
    if len(files) > MAX_BUNDLE_FILES or sum(map(len, files.values())) > MAX_BUNDLE_BYTES:
        raise ReleaseBundleError("source.size_limit")
    if not REQUIRED_FILES.issubset(files):
        raise ReleaseBundleError("source.required_files_missing")
    _validate_release_manifest(files, expected_commit)
    inventory = [
        {"path": path, "sha256": _sha256(body), "size": len(body)}
        for path, body in files.items()
    ]
    metadata = {
        "schema_version": SCHEMA_VERSION,
        "release_commit": expected_commit,
        "file_count": len(inventory),
        "files": inventory,
    }
    return files, metadata


def _tar_info(name: str, size: int) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.size = size
    info.mode = 0o644
    info.mtime = 0
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    return info


def create_bundle(source: Path, output: Path, expected_commit: str, *, replace: bool = False) -> dict[str, Any]:
    expected_commit = _require_commit(expected_commit)
    source = source.resolve()
    output = output.resolve()
    if source == output or source in output.parents:
        raise ReleaseBundleError("output.inside_source")
    if output.exists() and not replace:
        raise ReleaseBundleError("output.exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    files, metadata = _source_files(source, expected_commit)
    metadata_body = (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode()
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix=f".{output.name}.", delete=False) as temporary:
            temporary_path = Path(temporary.name)
            with gzip.GzipFile(filename="", mode="wb", fileobj=temporary, mtime=0) as compressed:
                with tarfile.open(fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT) as archive:
                    archive.addfile(_tar_info(BUNDLE_METADATA, len(metadata_body)), BytesIO(metadata_body))
                    for path, body in files.items():
                        archive.addfile(_tar_info(f"{BUNDLE_PREFIX}/{path}", len(body)), BytesIO(body))
            temporary.flush()
            os.fsync(temporary.fileno())
        os.chmod(temporary_path, 0o644)
        os.replace(temporary_path, output)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return verify_bundle(output, expected_commit)


def verify_bundle(bundle: Path, expected_commit: str) -> dict[str, Any]:
    expected_commit = _require_commit(expected_commit)
    try:
        bundle_body = bundle.read_bytes()
        if len(bundle_body) > MAX_BUNDLE_BYTES:
            raise ReleaseBundleError("bundle.size_limit")
        members: dict[str, bytes] = {}
        with tarfile.open(fileobj=BytesIO(bundle_body), mode="r:gz") as archive:
            entries = archive.getmembers()
            if len(entries) > MAX_BUNDLE_FILES + 1:
                raise ReleaseBundleError("bundle.file_limit")
            if sum(entry.size for entry in entries) > MAX_BUNDLE_BYTES:
                raise ReleaseBundleError("bundle.size_limit")
            for entry in entries:
                if not entry.isfile() or not _safe_relative_path(entry.name) or entry.name in members:
                    raise ReleaseBundleError("bundle.unsafe_entry")
                extracted = archive.extractfile(entry)
                if extracted is None:
                    raise ReleaseBundleError("bundle.unreadable")
                body = extracted.read(MAX_BUNDLE_BYTES + 1)
                if len(body) != entry.size or len(body) > MAX_BUNDLE_BYTES:
                    raise ReleaseBundleError("bundle.size_limit")
                members[entry.name] = body
    except ReleaseBundleError:
        raise
    except (OSError, tarfile.TarError, EOFError):
        raise ReleaseBundleError("bundle.unreadable") from None
    try:
        metadata = json.loads(members.pop(BUNDLE_METADATA))
    except (KeyError, json.JSONDecodeError, UnicodeDecodeError):
        raise ReleaseBundleError("bundle.metadata_unreadable") from None
    inventory = metadata.get("files") if isinstance(metadata, dict) else None
    if not (
        isinstance(metadata, dict)
        and set(metadata) == {"schema_version", "release_commit", "file_count", "files"}
        and metadata.get("schema_version") == SCHEMA_VERSION
        and metadata.get("release_commit") == expected_commit
        and isinstance(inventory, list)
        and metadata.get("file_count") == len(inventory)
    ):
        raise ReleaseBundleError("bundle.metadata_invalid")
    expected_members: set[str] = set()
    site_files: dict[str, bytes] = {}
    for item in inventory:
        if not isinstance(item, dict) or set(item) != {"path", "sha256", "size"}:
            raise ReleaseBundleError("bundle.metadata_invalid")
        path, digest, size = item.get("path"), item.get("sha256"), item.get("size")
        if not isinstance(path, str) or not _safe_relative_path(path):
            raise ReleaseBundleError("bundle.metadata_invalid")
        member_name = f"{BUNDLE_PREFIX}/{path}"
        body = members.get(member_name)
        if (
            member_name in expected_members
            or body is None
            or not isinstance(size, int)
            or not isinstance(digest, str)
            or not SHA256_PATTERN.fullmatch(digest)
            or len(body) != size
            or _sha256(body) != digest
        ):
            raise ReleaseBundleError("bundle.content_mismatch")
        expected_members.add(member_name)
        site_files[path] = body
    if set(members) != expected_members:
        raise ReleaseBundleError("bundle.unexpected_content")
    _validate_release_manifest(site_files, expected_commit)
    return {
        "verified": True,
        "release_commit": expected_commit,
        "file_count": len(site_files),
        "bundle_sha256": _sha256(bundle_body),
        "bundle_bytes": len(bundle_body),
        "values_redacted": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create or verify a deterministic static PWA release bundle.")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--create", type=Path, metavar="DIST")
    action.add_argument("--verify", type=Path, metavar="BUNDLE")
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.create:
            if args.output is None:
                parser.error("--output is required with --create")
            report = create_bundle(args.create, args.output, args.expected_commit, replace=args.replace)
        else:
            if args.output is not None or args.replace:
                parser.error("--output and --replace are only valid with --create")
            report = verify_bundle(args.verify, args.expected_commit)
    except ReleaseBundleError as error:
        print(json.dumps({"verified": False, "blockers": [str(error)], "values_redacted": True}, sort_keys=True))
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
