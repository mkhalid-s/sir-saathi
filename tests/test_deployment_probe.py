from pipeline.sir_saathi_pipeline.deployment_probe import NOT_FOUND_PATH, ProbeResponse, probe

RELEASE_COMMIT = "b" * 40

SECURITY_HEADERS = {
    "content-type": "text/html; charset=utf-8",
    "strict-transport-security": "max-age=31536000",
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "no-referrer",
    "permissions-policy": "geolocation=(), microphone=(), camera=()",
    "cross-origin-resource-policy": "same-origin",
    "content-security-policy": (
        "default-src 'none'; object-src 'none'; frame-ancestors 'none'; "
        "frame-src https://challenges.cloudflare.com"
    ),
}
HASHED_META = (
    '<meta http-equiv="content-security-policy" content="default-src \'none\'; '
    "script-src 'self' https://challenges.cloudflare.com 'sha256-example'; "
    "style-src 'self' 'sha256-example';\">"
)


def valid_fetcher(url: str, _timeout: float) -> ProbeResponse:
    if url.endswith("/api/version"):
        return ProbeResponse(
            200,
            {"content-type": "application/json", "cache-control": "no-store"},
            ('{"release_commit":"' + RELEASE_COMMIT + '"}').encode(),
            url,
        )
    if url.endswith("/api/ready"):
        return ProbeResponse(
            200,
            {"content-type": "application/json", "cache-control": "no-store"},
            b'{"status":"ready","mode":"guidance","ready":true,"blockers":[]}',
            url,
        )
    if url.endswith("/api/health"):
        return ProbeResponse(
            200,
            {"content-type": "application/json", "cache-control": "no-store"},
            b'{"status":"ok"}',
            url,
        )
    if url.endswith(NOT_FOUND_PATH):
        return ProbeResponse(
            404,
            {"content-type": "text/html"},
            b'<meta name="robots" content="noindex, nofollow">',
            url,
        )
    return ProbeResponse(
        200,
        SECURITY_HEADERS,
        f'{HASHED_META}<meta name="sir-saathi-release" content="{RELEASE_COMMIT}">'
        '<link rel="manifest" href="/manifest.webmanifest">'.encode(),
        url,
    )


def test_deployment_probe_accepts_complete_same_origin_surface() -> None:
    report = probe("https://sirsaathi.org/", expected_commit=RELEASE_COMMIT, fetcher=valid_fetcher)

    assert report["ready"] is True
    assert report["checks_passed"] == report["checks_total"]
    assert report["checks_total"] == 42
    assert report["blockers"] == []
    assert report["release_commit"] == RELEASE_COMMIT
    assert report["values_redacted"] is True


def test_deployment_probe_reports_stable_ids_without_response_data() -> None:
    private_response = "private-upstream-debug-value"

    def unsafe_fetcher(url: str, _timeout: float) -> ProbeResponse:
        if url.endswith("/api/health"):
            return ProbeResponse(
                200,
                {"content-type": "text/plain", "cache-control": "public"},
                private_response.encode(),
                "http://internal.example.test/health",
            )
        return valid_fetcher(url, _timeout)

    report = probe("https://sirsaathi.org", expected_commit=RELEASE_COMMIT, fetcher=unsafe_fetcher)

    assert report["ready"] is False
    assert report["blockers"] == [
        "api_health.same_https_origin",
        "api_health.json_content_type",
        "api_health.no_store",
        "api_health.payload",
    ]
    assert private_response not in str(report)
    assert "internal.example.test" not in str(report)


def test_deployment_probe_fails_closed_for_invalid_origin_and_network_failure() -> None:
    invalid = probe("http://localhost:4321", expected_commit=RELEASE_COMMIT, fetcher=valid_fetcher)
    assert invalid == {
        "ready": False,
        "checks_passed": 0,
        "checks_total": 1,
        "blockers": ["origin.invalid_https_origin"],
        "release_commit": None,
        "values_redacted": True,
    }

    def failed_fetcher(_url: str, _timeout: float) -> ProbeResponse:
        raise OSError("private network detail")

    failed = probe("https://sirsaathi.org", expected_commit=RELEASE_COMMIT, fetcher=failed_fetcher)
    assert failed["ready"] is False
    assert failed["checks_total"] == 5
    assert failed["blockers"] == [
        "home.request_succeeded",
        "api_health.request_succeeded",
        "api_readiness.request_succeeded",
        "api_version.request_succeeded",
        "not_found.request_succeeded",
    ]
    assert "private network detail" not in str(failed)


def test_deployment_probe_rejects_stale_or_mixed_release_identity() -> None:
    stale = probe("https://sirsaathi.org", expected_commit="a" * 40, fetcher=valid_fetcher)
    assert stale["ready"] is False
    assert stale["release_commit"] is None
    assert stale["blockers"] == ["release.expected_commit"]

    def mixed_fetcher(url: str, timeout: float) -> ProbeResponse:
        response = valid_fetcher(url, timeout)
        if url.endswith("/api/version"):
            return ProbeResponse(
                response.status,
                response.headers,
                b'{"release_commit":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}',
                response.final_url,
            )
        return response

    mixed = probe("https://sirsaathi.org", expected_commit=RELEASE_COMMIT, fetcher=mixed_fetcher)
    assert mixed["release_commit"] is None
    assert mixed["blockers"] == ["release.pwa_api_match", "release.expected_commit"]

    malformed = probe("https://sirsaathi.org", expected_commit="short", fetcher=valid_fetcher)
    assert malformed["blockers"] == ["release.invalid_expected_commit"]
