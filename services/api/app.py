"""FastAPI app factory for SIR Saathi.

The pure functions are importable in tests without requiring a running server.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime
import logging
import os
from typing import Any
from zoneinfo import ZoneInfo

from pipeline.sir_saathi_pipeline.forms_registry import load_forms_catalogue
from pipeline.sir_saathi_pipeline.assistance_registry import load_assistance_catalogue
from pipeline.sir_saathi_pipeline.guidance import GuidanceInput, get_guidance
from pipeline.sir_saathi_pipeline.state_registry import load_all_states
from pipeline.sir_saathi_pipeline.source_freshness import assess_source, freshness_window_days
from pipeline.sir_saathi_pipeline.translations import locale_status_payload, resolve_locale, translate_message

from .abuse_verification import (
    AbuseVerifier,
    CloudflareTurnstileVerifier,
    TURNSTILE_HOSTNAME_ENV,
    TURNSTILE_SECRET_ENV,
)
from .body_limit import BoundedApiBodyMiddleware, MAX_API_BODY_BYTES
from .models import InternalVoterRecord
from .pilot_data import load_sanitized_pilot_records
from .privacy import (
    DEFAULT_SEARCH_RATE_LIMITER,
    RateLimiter,
    RateLimitExceeded,
    RateLimiterUnavailable,
    assert_rate_limit_allowed,
    assert_search_launch_allowed,
    configured_rate_limiter,
    configured_trusted_proxy_hops,
    resolve_client_ip,
    search_rate_limit_key,
    verification_rate_limit_key,
)
from .schemas import GuidanceRequest, SearchRequestPayload, SearchResponsePayload, ValidationError
from .search import SearchRequest, redact_backend_results, search_records
from .search_backend import SearchBackend, configured_search_backend
from .readiness import GUIDANCE_MODE, configured_deployment_mode, configured_release_commit, runtime_readiness

try:  # FastAPI is installed in deployment/CI environments.
    from fastapi import FastAPI, HTTPException, Request, Response
except Exception:  # pragma: no cover - local environments may not have FastAPI yet
    FastAPI = None  # type: ignore[assignment]
    HTTPException = Exception  # type: ignore[assignment]
    Request = object  # type: ignore[assignment]
    Response = object  # type: ignore[assignment]

API_PREFIX = "/api"
INDIA_TIME_ZONE = ZoneInfo("Asia/Kolkata")
API_ROUTES = {
    f"{API_PREFIX}/health",
    f"{API_PREFIX}/ready",
    f"{API_PREFIX}/version",
    f"{API_PREFIX}/states",
    f"{API_PREFIX}/forms",
    f"{API_PREFIX}/locales",
    f"{API_PREFIX}/assistance",
    f"{API_PREFIX}/guidance",
    f"{API_PREFIX}/search",
}
SEARCH_AUDIT_LOGGER = logging.getLogger("sir_saathi.public_search")
SEARCH_AUDIT_EVENTS = frozenset({
    "backend_unavailable",
    "completed",
    "limiter_unavailable",
    "pilot_rejected",
    "rate_limited",
    "request_rejected",
    "verification_rejected",
})


def _log_search_event(event: str, *, level: int = logging.INFO) -> None:
    """Log only a stable event ID—never payloads, identities, tokens, or results."""

    if event not in SEARCH_AUDIT_EVENTS:
        raise ValueError("unknown public-search audit event")
    SEARCH_AUDIT_LOGGER.log(level, "public_search_event=%s", event)


def _date_payload(value: date | None) -> str | None:
    return value.isoformat() if value else None


def list_states_payload(*, today: date | None = None, locale: str = "en") -> list[dict[str, Any]]:
    states = load_all_states()
    effective_date = today or datetime.now(INDIA_TIME_ZONE).date()
    resolved = resolve_locale(locale)
    return [
        {
            "state_id": state.state_id,
            "name": translate_message(resolved.used, f"jurisdiction.{state.state_id}"),
            "locale_requested": resolved.requested,
            "locale_used": resolved.used,
            "locale_fallback": resolved.fallback,
            "languages": list(state.languages),
            "data_capability": state.data_capability,
            "public_launch_ready": state.public_launch_ready,
            "sir_status": state.schedule.status,
            "current_phase": state.schedule.status_on(effective_date),
            "current_phase_label": translate_message(
                resolved.used, f"status.{state.schedule.status_on(effective_date)}"
            ),
            "data_capability_label": translate_message(
                resolved.used, f"capability.{state.data_capability}"
            ),
            "sir_schedule": {
                "phase": state.schedule.phase,
                "qualifying_date": _date_payload(state.schedule.qualifying_date),
                "enumeration_start": _date_payload(state.schedule.enumeration_start),
                "enumeration_end": _date_payload(state.schedule.enumeration_end),
                "draft_roll_date": _date_payload(state.schedule.draft_roll_date),
                "claims_start": _date_payload(state.schedule.claims_start),
                "claims_end": _date_payload(state.schedule.claims_end),
                "final_roll_date": _date_payload(state.schedule.final_roll_date),
                "status": state.schedule.status,
                "current_phase": state.schedule.status_on(effective_date),
            },
            "schedule_provenance": {
                "label": state.schedule_provenance.label,
                "source_type": state.schedule_provenance.source_type,
                "confidence": state.schedule_provenance.confidence,
                "notes": state.schedule_provenance.notes,
            },
            "ceo_portal": state.ceo_portal,
            "final_roll_date": _date_payload(state.schedule.final_roll_date),
            "official_sources": [
                {
                    "label": source.label,
                    "url": source.url,
                    "source_type": source.source_type,
                    "last_verified": source.last_verified.isoformat(),
                    "freshness": assess_source(state, source, effective_date).as_dict()["status"],
                    "age_days": assess_source(state, source, effective_date).age_days,
                }
                for source in state.official_sources
            ],
            "source_freshness_policy_days": freshness_window_days(state, effective_date),
        }
        for state in states.values()
    ]


def forms_payload(locale: str = "en") -> dict[str, Any]:
    catalogue = load_forms_catalogue()
    resolved = resolve_locale(locale)
    return {
        "locale_requested": resolved.requested,
        "locale_used": resolved.used,
        "locale_fallback": resolved.fallback,
        "forms": [
            {
                "form_id": form.form_id,
                "label": translate_message(resolved.used, f"forms.{form.form_id}.label"),
                "purpose": translate_message(resolved.used, f"forms.{form.form_id}.purpose"),
                "official_portal": form.official_portal,
            }
            for form in catalogue.forms
        ],
        "common_documents": {
            category: [translate_message(resolved.used, f"document.{category}") for _document in documents]
            for category, documents in catalogue.common_documents.items()
        },
    }


def assistance_payload(locale: str = "en") -> dict[str, Any]:
    """Return the governed official escalation catalogue without user data."""

    catalogue = load_assistance_catalogue()
    resolved = resolve_locale(locale)
    return {
        "locale_requested": resolved.requested,
        "locale_used": resolved.used,
        "locale_fallback": resolved.fallback,
        "sources": [
            {
                "source_id": source.source_id,
                "label": source.label,
                "url": source.url,
                "last_verified": source.last_verified.isoformat(),
                "max_age_days": source.max_age_days,
            }
            for source in catalogue.sources
        ],
        "channels": [
            {
                "channel_id": channel.channel_id,
                "kind": channel.kind,
                "href": channel.href,
                "source_ids": list(channel.source_ids),
                "label": translate_message(resolved.used, channel.label_key),
                "description": translate_message(resolved.used, channel.description_key),
                "action": translate_message(resolved.used, channel.action_key),
            }
            for channel in catalogue.channels
        ],
    }


def locales_payload() -> dict[str, Any]:
    """Return public locale readiness without draft strings or review identities."""

    return locale_status_payload()


def _guidance_request(payload: dict[str, Any] | GuidanceRequest) -> GuidanceRequest:
    if isinstance(payload, GuidanceRequest):
        return payload
    return GuidanceRequest.model_validate(payload)


def guidance_payload(
    payload: dict[str, Any] | GuidanceRequest,
    *,
    today: date | None = None,
) -> dict[str, Any]:
    validated = _guidance_request(payload)
    resolved = resolve_locale(validated.locale)
    request = GuidanceInput(
        state_id=validated.state_id,
        situation=validated.situation,
        blo_visited=validated.blo_visited,
        enumeration_form_received=validated.enumeration_form_received,
        enumeration_form_submitted=validated.enumeration_form_submitted,
        current_roll_found=validated.current_roll_found,
        base_roll_found=validated.base_roll_found,
        today=today or datetime.now(INDIA_TIME_ZONE).date(),
    )
    result = get_guidance(request, locale=resolved.used)
    data = asdict(result)
    data["locale_requested"] = resolved.requested
    data["locale_used"] = resolved.used
    data["locale_fallback"] = resolved.fallback
    if result.deadline:
        data["deadline"] = result.deadline.isoformat()
    return data


def _search_request(payload: dict[str, Any] | SearchRequestPayload) -> SearchRequestPayload:
    if isinstance(payload, SearchRequestPayload):
        return payload
    return SearchRequestPayload.model_validate(payload)


def search_payload(
    payload: dict[str, Any] | SearchRequestPayload,
    records: list[InternalVoterRecord] | None = None,
    *,
    rate_limiter: RateLimiter | None = None,
    client_identity: str | None = None,
    abuse_verification_passed: bool = False,
    search_backend: SearchBackend | None = None,
) -> dict[str, Any]:
    validated = _search_request(payload)
    states = load_all_states()
    if validated.state_id not in states:
        raise ValueError(f"unknown state_id: {validated.state_id}")
    assert_search_launch_allowed(
        states[validated.state_id],
        abuse_verification_passed=abuse_verification_passed,
        use_sanitized_pilot=validated.use_sanitized_pilot,
    )
    if not validated.use_sanitized_pilot and (rate_limiter is None or not rate_limiter.shared):
        raise RateLimiterUnavailable("public search requires a shared rate limiter")
    request = SearchRequest(
        state_id=validated.state_id,
        query=validated.query,
        ac_number=validated.ac_number,
        part_number=validated.part_number,
        limit=validated.limit,
    )
    if rate_limiter is not None:
        key = search_rate_limit_key(client_identity=client_identity)
        assert_rate_limit_allowed(rate_limiter.check(key))
    if records is None:
        if not validated.use_sanitized_pilot:
            if search_backend is None:
                raise ValueError("no public search backend is enabled")
            results = redact_backend_results(request, search_backend.search(request))
        else:
            record_source = list(load_sanitized_pilot_records())
            results = search_records(request, record_source)
    else:
        record_source = list(records)
        results = search_records(request, record_source)
    response = SearchResponsePayload(results=[record.to_dict() for record in results], count=len(results))
    return response.model_dump()


def api_route_paths() -> set[str]:
    return set(API_ROUTES)


def configured_abuse_verifier() -> AbuseVerifier | None:
    secret = os.environ.get(TURNSTILE_SECRET_ENV)
    if not secret:
        return None
    return CloudflareTurnstileVerifier(
        secret=secret,
        expected_hostname=os.environ.get(TURNSTILE_HOSTNAME_ENV),
    )


def create_app(
    *,
    abuse_verifier: AbuseVerifier | None = None,
    search_backend: SearchBackend | None = None,
    rate_limiter: RateLimiter = DEFAULT_SEARCH_RATE_LIMITER,
    trusted_proxy_hops: int = 0,
    deployment_mode: str = GUIDANCE_MODE,
    release_commit: str = "development",
):
    if FastAPI is None:
        raise RuntimeError("FastAPI is required to create the API app")

    app = FastAPI(title="SIR Saathi API", version="0.1.0")
    app.add_middleware(BoundedApiBodyMiddleware, max_bytes=MAX_API_BODY_BYTES)

    @app.get(f"{API_PREFIX}/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get(f"{API_PREFIX}/ready")
    def ready(response: Response) -> dict[str, object]:
        report = runtime_readiness(
            mode=deployment_mode,
            abuse_verifier=abuse_verifier,
            search_backend=search_backend,
            rate_limiter=rate_limiter,
            trusted_proxy_hops=trusted_proxy_hops,
        )
        if not report["ready"]:
            response.status_code = 503
        return report

    @app.get(f"{API_PREFIX}/version")
    def version() -> dict[str, str]:
        return {"release_commit": release_commit}

    @app.get(f"{API_PREFIX}/states")
    def states(locale: str = "en") -> list[dict[str, Any]]:
        return list_states_payload(locale=locale)

    @app.get(f"{API_PREFIX}/forms")
    def forms(locale: str = "en") -> dict[str, Any]:
        return forms_payload(locale=locale)

    @app.get(f"{API_PREFIX}/locales")
    def locales() -> dict[str, Any]:
        return locales_payload()

    @app.get(f"{API_PREFIX}/assistance")
    def assistance(locale: str = "en") -> dict[str, Any]:
        return assistance_payload(locale=locale)

    @app.post(f"{API_PREFIX}/guidance")
    def guidance(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return guidance_payload(payload)
        except (KeyError, ValueError, ValidationError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post(f"{API_PREFIX}/search")
    def search(payload: dict[str, Any], request: Request) -> dict[str, Any]:
        rejection_event = "request_rejected"
        try:
            client_host = resolve_client_ip(
                peer_ip=request.client.host if request.client else None,
                forwarded_for=request.headers.get("x-forwarded-for"),
                trusted_proxy_hops=trusted_proxy_hops,
            )
            validated = _search_request(payload)
            if validated.use_sanitized_pilot:
                rejection_event = "pilot_rejected"
                raise ValueError("sanitized pilot search is not available through the public API")
            verification_passed = False
            states_by_id = load_all_states()
            if validated.state_id not in states_by_id:
                raise ValueError(f"unknown state_id: {validated.state_id}")
            # Check every launch prerequisite except the token itself before
            # spending an external verification call.
            assert_search_launch_allowed(
                states_by_id[validated.state_id],
                abuse_verification_passed=True,
                use_sanitized_pilot=False,
            )
            if rate_limiter is None or not rate_limiter.shared:
                raise RateLimiterUnavailable("public search requires a shared rate limiter")
            assert_rate_limit_allowed(
                rate_limiter.check(verification_rate_limit_key(client_identity=client_host))
            )
            if abuse_verifier is not None:
                verification_passed = abuse_verifier.verify(
                    validated.turnstile_response,
                    remote_ip=client_host,
                )
            if not verification_passed:
                rejection_event = "verification_rejected"
            response_payload = search_payload(
                validated,
                rate_limiter=rate_limiter,
                client_identity=client_host,
                abuse_verification_passed=verification_passed,
                search_backend=search_backend,
            )
            _log_search_event("completed")
            return response_payload
        except RateLimitExceeded as exc:
            _log_search_event("rate_limited", level=logging.WARNING)
            raise HTTPException(status_code=429, detail=str(exc)) from exc
        except RateLimiterUnavailable as exc:
            _log_search_event("limiter_unavailable", level=logging.ERROR)
            raise HTTPException(status_code=503, detail="Search is temporarily unavailable") from exc
        except (KeyError, ValueError, ValidationError) as exc:
            _log_search_event(rejection_event, level=logging.WARNING)
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            _log_search_event("backend_unavailable", level=logging.ERROR)
            raise HTTPException(status_code=503, detail="Search is temporarily unavailable") from exc

    return app


def create_configured_app():
    """Deployment factory that applies every server-owned environment setting."""

    return create_app(
        abuse_verifier=configured_abuse_verifier(),
        search_backend=configured_search_backend(),
        rate_limiter=configured_rate_limiter(),
        trusted_proxy_hops=configured_trusted_proxy_hops(),
        deployment_mode=configured_deployment_mode(),
        release_commit=configured_release_commit(),
    )


app = create_configured_app() if FastAPI is not None else None
