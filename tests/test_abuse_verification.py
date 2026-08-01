import importlib

from services.api.abuse_verification import (
    CloudflareTurnstileVerifier,
    TURNSTILE_HOSTNAME_ENV,
    TURNSTILE_SECRET_ENV,
    TURNSTILE_VERIFY_URL,
)
from services.api.app import configured_abuse_verifier

app_module = importlib.import_module("services.api.app")


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
    }
    monkeypatch.setattr(app_module, "configured_abuse_verifier", lambda: sentinels["abuse_verifier"])
    monkeypatch.setattr(app_module, "configured_search_backend", lambda: sentinels["search_backend"])
    monkeypatch.setattr(app_module, "configured_rate_limiter", lambda: sentinels["rate_limiter"])
    monkeypatch.setattr(app_module, "configured_trusted_proxy_hops", lambda: sentinels["trusted_proxy_hops"])
    monkeypatch.setattr(app_module, "create_app", lambda **kwargs: kwargs)
    assert app_module.create_configured_app() == sentinels
