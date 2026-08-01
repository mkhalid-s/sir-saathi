import hashlib
import json
from pathlib import Path

import pytest

from pipeline.sir_saathi_pipeline.deployment_probe import expected_nationwide_routes
from pipeline.sir_saathi_pipeline.release_bundle import (
    ReleaseBundleError,
    create_bundle,
    verify_bundle,
)

RELEASE_COMMIT = "c" * 40


def populated_dist(root: Path) -> Path:
    dist = root / "dist"
    routes = []
    for route in expected_nationwide_routes():
        relative = "index.html" if route == "/" else f"{route.strip('/')}/index.html"
        path = dist / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        body = f"<!doctype html><title>{route}</title>".encode()
        path.write_bytes(body)
        routes.append({"path": route, "sha256": hashlib.sha256(body).hexdigest()})
    (dist / "404.html").write_text("not found", encoding="utf-8")
    (dist / "manifest.webmanifest").write_text("{}", encoding="utf-8")
    (dist / "sw.js").write_text("// governed worker", encoding="utf-8")
    (dist / "release-manifest.json").write_text(json.dumps({
        "schema_version": 1,
        "release_commit": RELEASE_COMMIT,
        "route_count": len(routes),
        "routes": routes,
    }), encoding="utf-8")
    return dist


def test_release_bundle_is_deterministic_and_independently_verifiable(tmp_path: Path) -> None:
    dist = populated_dist(tmp_path)
    first = tmp_path / "first.tar.gz"
    second = tmp_path / "second.tar.gz"

    first_report = create_bundle(dist, first, RELEASE_COMMIT)
    second_report = create_bundle(dist, second, RELEASE_COMMIT)

    assert first.read_bytes() == second.read_bytes()
    assert first_report == second_report
    assert first_report["verified"] is True
    assert first_report["release_commit"] == RELEASE_COMMIT
    assert first_report["file_count"] == 46
    assert first_report["values_redacted"] is True
    assert verify_bundle(first, RELEASE_COMMIT) == first_report


def test_release_bundle_rejects_html_that_differs_from_the_route_manifest(tmp_path: Path) -> None:
    dist = populated_dist(tmp_path)
    (dist / "states/in-wb/index.html").write_text("altered", encoding="utf-8")

    with pytest.raises(ReleaseBundleError, match="release_manifest.invalid"):
        create_bundle(dist, tmp_path / "release.tar.gz", RELEASE_COMMIT)


def test_release_bundle_requires_the_exact_governed_nationwide_route_set(tmp_path: Path) -> None:
    dist = populated_dist(tmp_path)
    manifest_path = dist / "release-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    fake_path = dist / "replacement-help/index.html"
    fake_path.parent.mkdir(parents=True)
    fake_body = b"replacement route must not satisfy nationwide scope"
    fake_path.write_bytes(fake_body)
    accessibility = next(item for item in manifest["routes"] if item["path"] == "/accessibility/")
    accessibility.update({
        "path": "/replacement-help/",
        "sha256": hashlib.sha256(fake_body).hexdigest(),
    })
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ReleaseBundleError, match="release_manifest.invalid_nationwide_scope"):
        create_bundle(dist, tmp_path / "release.tar.gz", RELEASE_COMMIT)


def test_release_bundle_rejects_symlinks_and_existing_outputs(tmp_path: Path) -> None:
    dist = populated_dist(tmp_path)
    (dist / "linked.html").symlink_to(dist / "index.html")
    with pytest.raises(ReleaseBundleError, match="source.symlink_not_allowed"):
        create_bundle(dist, tmp_path / "release.tar.gz", RELEASE_COMMIT)

    (dist / "linked.html").unlink()
    output = tmp_path / "existing.tar.gz"
    output.write_bytes(b"preserve me")
    with pytest.raises(ReleaseBundleError, match="output.exists"):
        create_bundle(dist, output, RELEASE_COMMIT)
    assert output.read_bytes() == b"preserve me"


def test_release_bundle_fails_closed_for_wrong_commit_and_corrupt_archive(tmp_path: Path) -> None:
    dist = populated_dist(tmp_path)
    bundle = tmp_path / "release.tar.gz"
    create_bundle(dist, bundle, RELEASE_COMMIT)

    with pytest.raises(ReleaseBundleError, match="bundle.metadata_invalid"):
        verify_bundle(bundle, "d" * 40)
    bundle.write_bytes(bundle.read_bytes()[:100])
    with pytest.raises(ReleaseBundleError, match="bundle.unreadable"):
        verify_bundle(bundle, RELEASE_COMMIT)
