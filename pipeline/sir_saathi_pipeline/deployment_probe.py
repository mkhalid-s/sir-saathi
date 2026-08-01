"""Read-only audit of a deployed SIR Saathi public origin."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import hashlib
import json
import os
import re
import ssl
from typing import Callable, Mapping
from urllib.error import HTTPError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from .deployment_preflight import PUBLIC_SITE_URL_ENV, _public_origin
from .state_registry import load_all_states

MAX_RESPONSE_BYTES = 1_048_576
NOT_FOUND_PATH = "/.well-known/sir-saathi-deployment-probe-not-found"
RELEASE_MANIFEST_PATH = "/release-manifest.json"
BASE_PUBLIC_ROUTES = ("/", "/accessibility/", "/data-use/", "/languages/", "/methodology/", "/privacy/")
ROUTE_AUDIT_WORKERS = 8
CSP_META = re.compile(
    r'<meta\s+http-equiv="content-security-policy"\s+content="([^"]+)"',
    re.IGNORECASE,
)
RELEASE_META = re.compile(
    r'<meta\s+name="sir-saathi-release"\s+content="([0-9a-f]{40})"', re.IGNORECASE
)
RELEASE_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ProbeResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes
    final_url: str


Fetcher = Callable[[str, float], ProbeResponse]


def expected_nationwide_routes() -> tuple[str, ...]:
    state_routes = (f"/states/{state_id.casefold()}/" for state_id in load_all_states())
    return tuple(sorted((*BASE_PUBLIC_ROUTES, *state_routes)))


def _route_check_id(path: str) -> str:
    return "home" if path == "/" else path.strip("/").replace("/", "_")


def fetch(url: str, timeout_seconds: float) -> ProbeResponse:
    request = Request(
        url,
        headers={"Accept": "text/html, application/json", "User-Agent": "sir-saathi-deployment-probe/1"},
    )
    try:
        response = urlopen(request, timeout=timeout_seconds, context=ssl.create_default_context())
    except HTTPError as error:
        response = error
    with response:
        body = response.read(MAX_RESPONSE_BYTES + 1)
        if len(body) > MAX_RESPONSE_BYTES:
            raise ValueError("response exceeded the deployment probe size limit")
        return ProbeResponse(
            status=response.status,
            headers={name.casefold(): value for name, value in response.headers.items()},
            body=body,
            final_url=response.geturl(),
        )


def _same_origin(origin: str, target: str) -> bool:
    try:
        expected = urlparse(origin)
        actual = urlparse(target)
        return actual.scheme == "https" and actual.netloc.casefold() == expected.netloc.casefold()
    except ValueError:
        return False


def _csp_directives(value: str) -> dict[str, set[str]]:
    directives: dict[str, set[str]] = {}
    for raw_directive in value.split(";"):
        tokens = raw_directive.strip().split()
        if tokens:
            directives[tokens[0].casefold()] = set(tokens[1:])
    return directives


def probe(
    origin: str,
    *,
    expected_commit: str,
    timeout_seconds: float = 10,
    fetcher: Fetcher = fetch,
) -> dict[str, object]:
    normalized_origin, _hostname = _public_origin(origin)
    if not normalized_origin:
        return {
            "ready": False,
            "checks_passed": 0,
            "checks_total": 1,
            "blockers": ["origin.invalid_https_origin"],
            "release_commit": None,
            "values_redacted": True,
        }
    if not RELEASE_COMMIT_PATTERN.fullmatch(expected_commit):
        return {
            "ready": False,
            "checks_passed": 0,
            "checks_total": 1,
            "blockers": ["release.invalid_expected_commit"],
            "release_commit": None,
            "values_redacted": True,
        }
    if timeout_seconds <= 0 or timeout_seconds > 60:
        raise ValueError("timeout_seconds must be between 0 and 60")

    checks: list[tuple[str, bool]] = []

    def check(identifier: str, passed: bool) -> None:
        checks.append((identifier, passed))

    def request_surface(name: str, path: str) -> ProbeResponse | None:
        try:
            response = fetcher(urljoin(f"{normalized_origin}/", path.lstrip("/")), timeout_seconds)
        except Exception:
            check(f"{name}.request_succeeded", False)
            return None
        check(f"{name}.request_succeeded", True)
        check(f"{name}.same_https_origin", _same_origin(normalized_origin, response.final_url))
        return response

    pwa_release_commit = None
    api_release_commit = None
    home = request_surface("home", "/")
    if home:
        headers = {name.casefold(): value for name, value in home.headers.items()}
        raw_body = home.body.decode("utf-8", errors="replace")
        body = raw_body.casefold()
        check("home.status_200", home.status == 200)
        check("home.html_content_type", "text/html" in headers.get("content-type", "").casefold())
        check("home.pwa_manifest", 'rel="manifest"' in body and "/manifest.webmanifest" in body)
        check("header.hsts", "max-age=" in headers.get("strict-transport-security", "").casefold())
        check("header.no_sniff", headers.get("x-content-type-options", "").casefold() == "nosniff")
        check("header.anti_framing", headers.get("x-frame-options", "").casefold() == "deny")
        check("header.referrer", headers.get("referrer-policy", "").casefold() == "no-referrer")
        check("header.permissions", bool(headers.get("permissions-policy", "").strip()))
        check(
            "header.cross_origin_resource",
            headers.get("cross-origin-resource-policy", "").casefold() == "same-origin",
        )
        csp = _csp_directives(headers.get("content-security-policy", ""))
        check("csp.default_deny", csp.get("default-src") == {"'none'"})
        check("csp.no_object", csp.get("object-src") == {"'none'"})
        check("csp.no_framing", csp.get("frame-ancestors") == {"'none'"})
        check("csp.turnstile_frame", "https://challenges.cloudflare.com" in csp.get("frame-src", set()))
        meta_match = CSP_META.search(raw_body)
        meta_csp = _csp_directives(meta_match.group(1)) if meta_match else {}
        meta_scripts = meta_csp.get("script-src", set())
        meta_styles = meta_csp.get("style-src", set())
        check(
            "csp.hash_bound_meta",
            meta_csp.get("default-src") == {"'none'"}
            and "'self'" in meta_scripts
            and "https://challenges.cloudflare.com" in meta_scripts
            and any(source.startswith("'sha256-") for source in meta_scripts)
            and "'unsafe-inline'" not in meta_scripts
            and "'self'" in meta_styles
            and any(source.startswith("'sha256-") for source in meta_styles)
            and "'unsafe-inline'" not in meta_styles,
        )
        release_match = RELEASE_META.search(raw_body)
        pwa_release_commit = release_match.group(1).casefold() if release_match else None
        check("home.release_commit", pwa_release_commit is not None)

    health = request_surface("api_health", "/api/health")
    if health:
        headers = {name.casefold(): value for name, value in health.headers.items()}
        check("api_health.status_200", health.status == 200)
        check("api_health.json_content_type", "application/json" in headers.get("content-type", "").casefold())
        check("api_health.no_store", "no-store" in headers.get("cache-control", "").casefold())
        try:
            payload = json.loads(health.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = None
        check("api_health.payload", payload == {"status": "ok"})

    readiness = request_surface("api_readiness", "/api/ready")
    if readiness:
        headers = {name.casefold(): value for name, value in readiness.headers.items()}
        check("api_readiness.status_200", readiness.status == 200)
        check("api_readiness.json_content_type", "application/json" in headers.get("content-type", "").casefold())
        check("api_readiness.no_store", "no-store" in headers.get("cache-control", "").casefold())
        try:
            payload = json.loads(readiness.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = None
        check(
            "api_readiness.payload",
            isinstance(payload, dict)
            and payload.get("status") == "ready"
            and payload.get("ready") is True
            and payload.get("blockers") == [],
        )

    version = request_surface("api_version", "/api/version")
    if version:
        headers = {name.casefold(): value for name, value in version.headers.items()}
        check("api_version.status_200", version.status == 200)
        check("api_version.json_content_type", "application/json" in headers.get("content-type", "").casefold())
        check("api_version.no_store", "no-store" in headers.get("cache-control", "").casefold())
        try:
            payload = json.loads(version.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = None
        candidate = payload.get("release_commit") if isinstance(payload, dict) else None
        api_release_commit = candidate if isinstance(candidate, str) and RELEASE_COMMIT_PATTERN.fullmatch(candidate) else None
        check("api_version.payload", api_release_commit is not None and payload == {"release_commit": api_release_commit})

    expected_routes = expected_nationwide_routes()
    route_hashes: dict[str, str] | None = None
    release_manifest = request_surface("release_manifest", RELEASE_MANIFEST_PATH)
    if release_manifest:
        headers = {name.casefold(): value for name, value in release_manifest.headers.items()}
        check("release_manifest.status_200", release_manifest.status == 200)
        check(
            "release_manifest.json_content_type",
            "application/json" in headers.get("content-type", "").casefold(),
        )
        check("release_manifest.revalidatable", "no-cache" in headers.get("cache-control", "").casefold())
        try:
            payload = json.loads(release_manifest.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = None
        routes = payload.get("routes") if isinstance(payload, dict) else None
        candidate_hashes = {
            item.get("path"): item.get("sha256")
            for item in routes
            if isinstance(item, dict)
        } if isinstance(routes, list) else {}
        manifest_structurally_valid = (
            isinstance(payload, dict)
            and set(payload) == {"schema_version", "release_commit", "route_count", "routes"}
            and payload.get("schema_version") == 1
            and isinstance(payload.get("release_commit"), str)
            and RELEASE_COMMIT_PATTERN.fullmatch(payload["release_commit"])
            and payload.get("route_count") == len(expected_routes)
            and isinstance(routes, list)
            and len(routes) == len(expected_routes)
            and all(isinstance(item, dict) and set(item) == {"path", "sha256"} for item in routes)
            and set(candidate_hashes) == set(expected_routes)
            and all(isinstance(value, str) and SHA256_PATTERN.fullmatch(value) for value in candidate_hashes.values())
        )
        manifest_valid = manifest_structurally_valid and payload.get("release_commit") == expected_commit
        check("release_manifest.payload", manifest_valid)
        if manifest_structurally_valid:
            route_hashes = candidate_hashes

    def audit_route(path: str) -> bool:
        if route_hashes is None:
            return False
        try:
            response = fetcher(urljoin(f"{normalized_origin}/", path.lstrip("/")), timeout_seconds)
        except Exception:
            return False
        headers = {name.casefold(): value for name, value in response.headers.items()}
        return (
            response.status == 200
            and _same_origin(normalized_origin, response.final_url)
            and "text/html" in headers.get("content-type", "").casefold()
            and hashlib.sha256(response.body).hexdigest() == route_hashes[path]
        )

    if route_hashes is None:
        route_results = (False for _path in expected_routes)
    else:
        with ThreadPoolExecutor(max_workers=ROUTE_AUDIT_WORKERS) as executor:
            route_results = tuple(executor.map(audit_route, expected_routes))
    for path, passed in zip(expected_routes, route_results, strict=True):
        check(f"nationwide_route.{_route_check_id(path)}", passed)

    verified_release_commit = None
    if home and version:
        commits_match = pwa_release_commit is not None and pwa_release_commit == api_release_commit
        check("release.pwa_api_match", commits_match)
        expected_matches = commits_match and pwa_release_commit == expected_commit
        check("release.expected_commit", expected_matches)
        if expected_matches:
            verified_release_commit = expected_commit

    not_found = request_surface("not_found", NOT_FOUND_PATH)
    if not_found:
        headers = {name.casefold(): value for name, value in not_found.headers.items()}
        body = not_found.body.decode("utf-8", errors="replace").casefold()
        check("not_found.status_404", not_found.status == 404)
        check("not_found.html_content_type", "text/html" in headers.get("content-type", "").casefold())
        check("not_found.noindex", 'name="robots"' in body and "noindex" in body)

    blockers = [identifier for identifier, passed in checks if not passed]
    return {
        "ready": not blockers,
        "checks_passed": len(checks) - len(blockers),
        "checks_total": len(checks),
        "blockers": blockers,
        "release_commit": verified_release_commit,
        "values_redacted": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit a deployed origin without printing response data.")
    parser.add_argument("--origin", default=os.environ.get(PUBLIC_SITE_URL_ENV, ""))
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--timeout-seconds", type=float, default=10)
    args = parser.parse_args(argv)
    report = probe(args.origin, expected_commit=args.expected_commit, timeout_seconds=args.timeout_seconds)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
