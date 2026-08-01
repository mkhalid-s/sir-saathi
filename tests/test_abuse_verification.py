import importlib
from dataclasses import replace
from types import SimpleNamespace

import pytest

from pipeline.sir_saathi_pipeline.state_registry import load_all_states
from services.api.abuse_verification import (
    CloudflareTurnstileVerifier,
    TURNSTILE_HOSTNAME_ENV,
    TURNSTILE_SECRET_ENV,
    TURNSTILE_VERIFY_URL,
)
from services.api.app import configured_abuse_verifier, create_app
from services.api.privacy import RateLimitDecision

app_module = importlib.import_module("services.api.app")


class SharedRecordingLimiter:
    shared = True

    def __init__(self):
        self.keys = []

    def check(self, key, *, now=None):
        del now
        self.keys.append(key)
        return RateLimitDecision(allowed=True, remaining=29)


def search_endpoint(app):
    return next(route.endpoint for route in app.routes if getattr(route, "path", None) == "/api/search")


def synthetic_request():
    return SimpleNamespace(client=SimpleNamespace(host="203.0.113.10"), headers={})


def test_turnstile_verification_is_server_owned_and_checks_context() -> None:
    captured = {}

    def transport(url, fields, timeout):
        captured.update({"url": url, "fields": fields, "timeout": timeout})
        return {"success": True, "hostname": "sir-saathi.example", "action": "voter_search"}

    verifier = CloudflareTurnstileVerifier(
        secret="server-only-test-value",
        expected_hostname="sir-saathi.example",
        transport=transport,
    )
    assert verifier.verify("opaque-client-response", remote_ip="203.0.113.7") is True
    assert captured["url"] == TURNSTILE_VERIFY_URL
    assert captured["fields"]["response"] == "opaque-client-response"
    assert captured["fields"]["remoteip"] == "203.0.113.7"
    assert captured["timeout"] == 3.0


def test_turnstile_verification_fails_closed_for_errors_or_wrong_context() -> None:
    wrong_action = CloudflareTurnstileVerifier(
        secret="server-only-test-value",
        transport=lambda *_args: {"success": True, "action": "different_action"},
    )
    unavailable = CloudflareTurnstileVerifier(
        secret="server-only-test-value",
        transport=lambda *_args: (_ for _ in ()).throw(TimeoutError()),
    )
    assert wrong_action.verify("opaque-response", remote_ip=None) is False
    assert unavailable.verify("opaque-response", remote_ip=None) is False
    assert unavailable.verify(None, remote_ip=None) is False


def test_turnstile_verification_rejects_wrong_hostname_and_malformed_json_shape() -> None:
    wrong_hostname = CloudflareTurnstileVerifier(
        secret="server-only-test-value",
        expected_hostname="sir-saathi.example",
        transport=lambda *_args: {
            "success": True,
            "hostname": "lookalike.example",
            "action": "voter_search",
        },
    )
    malformed = CloudflareTurnstileVerifier(
        secret="server-only-test-value",
        transport=lambda *_args: [],
    )
    assert wrong_hostname.verify("opaque-response", remote_ip=None) is False
    assert malformed.verify("opaque-response", remote_ip=None) is False


def test_disabled_scope_is_rejected_before_external_verification() -> None:
    class Verifier:
        def __init__(self):
            self.calls = 0

        def verify(self, *_args, **_kwargs):
            self.calls += 1
            return True

    verifier = Verifier()
    limiter = SharedRecordingLimiter()
    endpoint = search_endpoint(create_app(abuse_verifier=verifier, rate_limiter=limiter))
    with pytest.raises(app_module.HTTPException) as exc_info:
        endpoint({
            "state_id": "IN-MH",
            "query": "sample",
            "ac_number": 172,
            "turnstile_response": "opaque-response",
        }, synthetic_request())
    assert exc_info.value.status_code == 400
    assert verifier.calls == 0
    assert limiter.keys == []


def test_public_route_rejects_client_controlled_sanitized_pilot() -> None:
    limiter = SharedRecordingLimiter()
    endpoint = search_endpoint(create_app(rate_limiter=limiter))
    with pytest.raises(app_module.HTTPException) as exc_info:
        endpoint({
            "state_id": "IN-MH",
            "query": "sample",
            "ac_number": 172,
            "use_sanitized_pilot": True,
        }, synthetic_request())
    assert exc_info.value.status_code == 400
    assert "not available through the public API" in exc_info.value.detail
    assert limiter.keys == []


def test_verification_is_rate_limited_before_external_call(monkeypatch, caplog) -> None:
    state = load_all_states()["IN-WB"]
    launch_ready = replace(state, public_launch_ready=True, data_capability="validated_indexed_search")
    monkeypatch.setattr(app_module, "load_all_states", lambda: {"IN-WB": launch_ready})
    limiter = SharedRecordingLimiter()

    class Verifier:
        def verify(self, *_args, **_kwargs):
            assert len(limiter.keys) == 1
            assert limiter.keys[0].startswith("verification:client:")
            return True

    class Backend:
        def search(self, _request):
            return []

    endpoint = search_endpoint(create_app(abuse_verifier=Verifier(), search_backend=Backend(), rate_limiter=limiter))
    with caplog.at_level("INFO", logger="sir_saathi.public_search"):
        response = endpoint({
            "state_id": "IN-WB",
            "query": "sample",
            "ac_number": 1,
            "turnstile_response": "opaque-response",
        }, synthetic_request())
    assert response == {"results": [], "count": 0}
    assert [key.split(":", 1)[0] for key in limiter.keys] == ["verification", "search"]
    assert "public_search_event=completed" in caplog.text


def test_backend_failure_is_generic_and_does_not_log_exception_detail(monkeypatch, caplog) -> None:
    state = load_all_states()["IN-WB"]
    launch_ready = replace(state, public_launch_ready=True, data_capability="validated_indexed_search")
    monkeypatch.setattr(app_module, "load_all_states", lambda: {"IN-WB": launch_ready})

    class Verifier:
        def verify(self, *_args, **_kwargs):
            return True

    class Backend:
        def search(self, _request):
            raise RuntimeError("Sample Voter opaque-response must not reach logs")

    endpoint = search_endpoint(create_app(
        abuse_verifier=Verifier(),
        search_backend=Backend(),
        rate_limiter=SharedRecordingLimiter(),
    ))
    with caplog.at_level("INFO", logger="sir_saathi.public_search"):
        with pytest.raises(app_module.HTTPException) as exc_info:
            endpoint({
                "state_id": "IN-WB",
                "query": "Sample Voter",
                "ac_number": 1,
                "turnstile_response": "opaque-response",
            }, synthetic_request())
    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Search is temporarily unavailable"
    assert "public_search_event=backend_unavailable" in caplog.text
    assert "Sample Voter" not in caplog.text
    assert "opaque-response" not in caplog.text


def test_abuse_verifier_is_configured_only_from_server_environment(monkeypatch) -> None:
    monkeypatch.delenv(TURNSTILE_SECRET_ENV, raising=False)
    monkeypatch.delenv(TURNSTILE_HOSTNAME_ENV, raising=False)
    assert configured_abuse_verifier() is None

    monkeypatch.setenv(TURNSTILE_SECRET_ENV, "server-only-test-value")
    monkeypatch.setenv(TURNSTILE_HOSTNAME_ENV, "sir-saathi.example")
    assert isinstance(configured_abuse_verifier(), CloudflareTurnstileVerifier)


def test_deployment_factory_applies_all_server_owned_configuration(monkeypatch) -> None:
    sentinels = {
        "abuse_verifier": object(),
        "search_backend": object(),
        "rate_limiter": object(),
        "trusted_proxy_hops": 1,
        "deployment_mode": "indexed-search",
    }
    monkeypatch.setattr(app_module, "configured_abuse_verifier", lambda: sentinels["abuse_verifier"])
    monkeypatch.setattr(app_module, "configured_search_backend", lambda: sentinels["search_backend"])
    monkeypatch.setattr(app_module, "configured_rate_limiter", lambda: sentinels["rate_limiter"])
    monkeypatch.setattr(app_module, "configured_trusted_proxy_hops", lambda: sentinels["trusted_proxy_hops"])
    monkeypatch.setattr(app_module, "configured_deployment_mode", lambda: sentinels["deployment_mode"])
    monkeypatch.setattr(app_module, "create_app", lambda **kwargs: kwargs)
    assert app_module.create_configured_app() == sentinels
