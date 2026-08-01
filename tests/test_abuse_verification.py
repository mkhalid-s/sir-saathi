from services.api.abuse_verification import (
    CloudflareTurnstileVerifier,
    TURNSTILE_HOSTNAME_ENV,
    TURNSTILE_SECRET_ENV,
    TURNSTILE_VERIFY_URL,
)
from services.api.app import configured_abuse_verifier


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
