"""Server-owned Cloudflare Turnstile verification with fail-closed defaults."""

from __future__ import annotations

import json
from typing import Any, Callable, Protocol
from urllib.parse import urlencode
from urllib.request import Request, urlopen

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
TURNSTILE_SECRET_ENV = "SIR_SAATHI_TURNSTILE_SECRET"
TURNSTILE_HOSTNAME_ENV = "SIR_SAATHI_TURNSTILE_HOSTNAME"
TURNSTILE_ACTION = "voter_search"


class AbuseVerifier(Protocol):
    def verify(self, challenge_response: str | None, *, remote_ip: str | None) -> bool: ...


Transport = Callable[[str, dict[str, str], float], dict[str, Any]]


def _post_form(url: str, fields: dict[str, str], timeout: float) -> dict[str, Any]:
    request = Request(
        url,
        data=urlencode(fields).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed Cloudflare URL
        return json.loads(response.read().decode("utf-8"))


class CloudflareTurnstileVerifier:
    def __init__(
        self,
        *,
        secret: str,
        expected_hostname: str | None = None,
        expected_action: str = TURNSTILE_ACTION,
        timeout_seconds: float = 3.0,
        transport: Transport = _post_form,
    ) -> None:
        if not secret.strip():
            raise ValueError("Turnstile server secret is required")
        self._secret = secret
        self._expected_hostname = expected_hostname
        self._expected_action = expected_action
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    def verify(self, challenge_response: str | None, *, remote_ip: str | None) -> bool:
        normalized_response = (challenge_response or "").strip()
        if not normalized_response or len(normalized_response) > 2048:
            return False
        fields = {"secret": self._secret, "response": normalized_response}
        if remote_ip:
            fields["remoteip"] = remote_ip
        try:
            result = self._transport(TURNSTILE_VERIFY_URL, fields, self._timeout_seconds)
        except Exception:
            return False
        if not isinstance(result, dict):
            return False
        if result.get("success") is not True:
            return False
        if self._expected_hostname and result.get("hostname") != self._expected_hostname:
            return False
        if self._expected_action and result.get("action") != self._expected_action:
            return False
        return True
