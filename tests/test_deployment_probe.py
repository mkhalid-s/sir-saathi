from pipeline.sir_saathi_pipeline.deployment_probe import NOT_FOUND_PATH, ProbeResponse, probe


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


def valid_fetcher(url: str, _timeout: float) -> ProbeResponse:
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
        b'<link rel="manifest" href="/manifest.webmanifest">',
        url,
    )


def test_deployment_probe_accepts_complete_same_origin_surface() -> None:
    report = probe("https://sirsaathi.org/", fetcher=valid_fetcher)

    assert report["ready"] is True
    assert report["checks_passed"] == report["checks_total"]
    assert report["checks_total"] == 26
    assert report["blockers"] == []
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

    report = probe("https://sirsaathi.org", fetcher=unsafe_fetcher)

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
    invalid = probe("http://localhost:4321", fetcher=valid_fetcher)
    assert invalid == {
        "ready": False,
        "checks_passed": 0,
        "checks_total": 1,
        "blockers": ["origin.invalid_https_origin"],
        "values_redacted": True,
    }

    def failed_fetcher(_url: str, _timeout: float) -> ProbeResponse:
        raise OSError("private network detail")

    failed = probe("https://sirsaathi.org", fetcher=failed_fetcher)
    assert failed["ready"] is False
    assert failed["checks_total"] == 3
    assert failed["blockers"] == [
        "home.request_succeeded",
        "api_health.request_succeeded",
        "not_found.request_succeeded",
    ]
    assert "private network detail" not in str(failed)
