import pytest
from starlette.responses import Response

from services.api.app import create_app
from services.api.readiness import configured_deployment_mode, configured_release_commit, runtime_readiness


class Dependency:
    def __init__(self, ready: bool) -> None:
        self._ready = ready

    def ready(self) -> bool:
        return self._ready


class SharedDependency(Dependency):
    shared = True


def call_ready(app):
    route = next(route for route in app.routes if getattr(route, "path", None) == "/api/ready")
    response = Response()
    return route.endpoint(response), response.status_code


def test_deployment_mode_defaults_to_safe_guidance_and_rejects_unknown_values() -> None:
    assert configured_deployment_mode({}) == "guidance"
    assert configured_deployment_mode({"SIR_SAATHI_DEPLOYMENT_MODE": "indexed-search"}) == "indexed-search"
    with pytest.raises(ValueError, match="SIR_SAATHI_DEPLOYMENT_MODE"):
        configured_deployment_mode({"SIR_SAATHI_DEPLOYMENT_MODE": "automatic"})
    assert configured_release_commit({}) == "development"
    assert configured_release_commit({"SIR_SAATHI_RELEASE_COMMIT": "a" * 40}) == "a" * 40
    with pytest.raises(ValueError, match="SIR_SAATHI_RELEASE_COMMIT"):
        configured_release_commit({"SIR_SAATHI_RELEASE_COMMIT": "main"})


def test_api_version_exposes_only_configured_non_secret_release_commit() -> None:
    app = create_app(release_commit="c" * 40)
    route = next(route for route in app.routes if getattr(route, "path", None) == "/api/version")
    assert route.endpoint() == {"release_commit": "c" * 40}


def test_guidance_readiness_does_not_depend_on_indexed_search_services() -> None:
    report = runtime_readiness(
        mode="guidance",
        abuse_verifier=None,
        search_backend=None,
        rate_limiter=Dependency(False),
        trusted_proxy_hops=0,
    )
    assert report == {"status": "ready", "mode": "guidance", "ready": True, "blockers": []}

    payload, status_code = call_ready(create_app())
    assert status_code == 200
    assert payload == report


def test_indexed_search_readiness_fails_closed_with_stable_non_secret_blockers() -> None:
    report = runtime_readiness(
        mode="indexed-search",
        abuse_verifier=None,
        search_backend=Dependency(False),
        rate_limiter=Dependency(True),
        trusted_proxy_hops=0,
    )
    assert report == {
        "status": "not_ready",
        "mode": "indexed-search",
        "ready": False,
        "blockers": [
            "indexed_search.turnstile_unavailable",
            "indexed_search.database_unavailable",
            "indexed_search.shared_limiter_unavailable",
            "indexed_search.trusted_proxy_unconfigured",
        ],
    }

    payload, status_code = call_ready(
        create_app(
            deployment_mode="indexed-search",
            search_backend=Dependency(False),
            rate_limiter=Dependency(True),
        )
    )
    assert status_code == 503
    assert payload == report
    assert "private" not in str(payload)


def test_indexed_search_readiness_requires_every_live_server_owned_gate() -> None:
    report = runtime_readiness(
        mode="indexed-search",
        abuse_verifier=object(),
        search_backend=Dependency(True),
        rate_limiter=SharedDependency(True),
        trusted_proxy_hops=1,
    )
    assert report == {"status": "ready", "mode": "indexed-search", "ready": True, "blockers": []}

    payload, status_code = call_ready(
        create_app(
            deployment_mode="indexed-search",
            abuse_verifier=object(),
            search_backend=Dependency(True),
            rate_limiter=SharedDependency(True),
            trusted_proxy_hops=1,
        )
    )
    assert status_code == 200
    assert payload == report
