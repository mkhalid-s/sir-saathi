"""Typed request/response schemas for the public API.

These lightweight schemas keep validation deterministic in local/CI environments and
can be replaced with Pydantic models once the deployment environment pins Python
API dependencies.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, ClassVar

STATUSES = {"yes", "no", "unknown"}
SITUATIONS = {
    "existing_voter",
    "new_voter",
    "missing_name",
    "shifted_address",
    "correction",
    "deceased_family",
    "duplicate_entry",
    "portal_failed",
}


class ValidationError(ValueError):
    """Request validation failed."""


def _reject_extra(data: dict[str, Any], allowed: set[str]) -> None:
    extra = sorted(set(data) - allowed)
    if extra:
        raise ValidationError(f"unknown fields: {', '.join(extra)}")


def _string(data: dict[str, Any], key: str, *, min_length: int = 0, max_length: int = 10_000) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise ValidationError(f"{key} must be a string")
    normalized = " ".join(value.strip().split())
    if len(normalized) < min_length or len(normalized) > max_length:
        raise ValidationError(f"{key} length is invalid")
    return normalized


def _optional_int(data: dict[str, Any], key: str, *, minimum: int, maximum: int) -> int | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationError(f"{key} must be an integer")
    if value < minimum or value > maximum:
        raise ValidationError(f"{key} is out of range")
    return value


def _int(data: dict[str, Any], key: str, *, minimum: int, maximum: int, default: int | None = None) -> int:
    value = data.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationError(f"{key} must be an integer")
    if value < minimum or value > maximum:
        raise ValidationError(f"{key} is out of range")
    return value


@dataclass(frozen=True)
class GuidanceRequest:
    allowed_fields: ClassVar[set[str]] = {
        "state_id",
        "situation",
        "blo_visited",
        "enumeration_form_received",
        "enumeration_form_submitted",
        "current_roll_found",
        "base_roll_found",
    }

    state_id: str
    situation: str
    blo_visited: str = "unknown"
    enumeration_form_received: str = "unknown"
    enumeration_form_submitted: str = "unknown"
    current_roll_found: str = "unknown"
    base_roll_found: str = "unknown"

    @classmethod
    def model_validate(cls, payload: dict[str, Any]) -> "GuidanceRequest":
        _reject_extra(payload, cls.allowed_fields)
        state_id = _string(payload, "state_id", min_length=2, max_length=16)
        situation = _string(payload, "situation", min_length=2, max_length=64)
        if situation not in SITUATIONS:
            raise ValidationError("situation is not supported")
        statuses = {
            key: _string(payload, key, min_length=2, max_length=16) if key in payload else "unknown"
            for key in [
                "blo_visited",
                "enumeration_form_received",
                "enumeration_form_submitted",
                "current_roll_found",
                "base_roll_found",
            ]
        }
        for key, value in statuses.items():
            if value not in STATUSES:
                raise ValidationError(f"{key} must be yes, no, or unknown")
        return cls(state_id=state_id, situation=situation, **statuses)


@dataclass(frozen=True)
class SearchRequestPayload:
    allowed_fields: ClassVar[set[str]] = {
        "state_id",
        "query",
        "ac_number",
        "part_number",
        "limit",
        "use_sanitized_pilot",
        "turnstile_verified",
    }

    state_id: str
    query: str
    ac_number: int
    part_number: int | None = None
    limit: int = 10
    use_sanitized_pilot: bool = False
    turnstile_verified: bool = False

    @classmethod
    def model_validate(cls, payload: dict[str, Any]) -> "SearchRequestPayload":
        _reject_extra(payload, cls.allowed_fields)
        state_id = _string(payload, "state_id", min_length=2, max_length=16)
        query = _string(payload, "query", min_length=2, max_length=80)
        ac_number = _int(payload, "ac_number", minimum=1, maximum=999)
        part_number = _optional_int(payload, "part_number", minimum=1, maximum=9999)
        limit = _int(payload, "limit", minimum=1, maximum=20, default=10)
        use_sanitized_pilot = payload.get("use_sanitized_pilot", False)
        turnstile_verified = payload.get("turnstile_verified", False)
        if not isinstance(use_sanitized_pilot, bool):
            raise ValidationError("use_sanitized_pilot must be a boolean")
        if not isinstance(turnstile_verified, bool):
            raise ValidationError("turnstile_verified must be a boolean")
        return cls(
            state_id=state_id,
            query=query,
            ac_number=ac_number,
            part_number=part_number,
            limit=limit,
            use_sanitized_pilot=use_sanitized_pilot,
            turnstile_verified=turnstile_verified,
        )


@dataclass(frozen=True)
class PublicVoterRecordPayload:
    state_id: str
    ac_number: int | None
    part_number: int | None
    serial_number: int | None
    display_name: str
    roll_year: int
    roll_kind: str
    data_quality: str
    source_label: str
    confidence: float
    epic_hint: str | None = None


@dataclass(frozen=True)
class SearchResponsePayload:
    results: list[dict[str, object | None]]
    count: int

    def model_dump(self) -> dict[str, object]:
        return asdict(self)
