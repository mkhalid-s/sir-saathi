"""FastAPI app factory for SIR Saathi.

The pure functions are importable in tests without requiring a running server.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from pipeline.sir_saathi_pipeline.forms_registry import load_forms_catalogue
from pipeline.sir_saathi_pipeline.guidance import GuidanceInput, get_guidance
from pipeline.sir_saathi_pipeline.state_registry import load_all_states

from .models import InternalVoterRecord
from .pilot_data import load_sanitized_pilot_records
from .privacy import (
    DEFAULT_SEARCH_RATE_LIMITER,
    InMemoryRateLimiter,
    RateLimitExceeded,
    assert_rate_limit_allowed,
    assert_search_launch_allowed,
    search_rate_limit_key,
)
from .schemas import GuidanceRequest, SearchRequestPayload, SearchResponsePayload, ValidationError
from .search import SearchRequest, search_records

try:  # FastAPI is installed in deployment/CI environments.
    from fastapi import FastAPI, HTTPException, Request
except Exception:  # pragma: no cover - local environments may not have FastAPI yet
    FastAPI = None  # type: ignore[assignment]
    HTTPException = Exception  # type: ignore[assignment]
    Request = object  # type: ignore[assignment]

API_PREFIX = "/api"
API_ROUTES = {
    f"{API_PREFIX}/health",
    f"{API_PREFIX}/states",
    f"{API_PREFIX}/forms",
    f"{API_PREFIX}/guidance",
    f"{API_PREFIX}/search",
}


def list_states_payload() -> list[dict[str, Any]]:
    states = load_all_states()
    return [
        {
            "state_id": state.state_id,
            "name": state.name,
            "languages": list(state.languages),
            "data_capability": state.data_capability,
            "public_launch_ready": state.public_launch_ready,
            "sir_status": state.schedule.status,
            "final_roll_date": state.schedule.final_roll_date.isoformat() if state.schedule.final_roll_date else None,
            "official_sources": [
                {
                    "label": source.label,
                    "url": source.url,
                    "source_type": source.source_type,
                    "last_verified": source.last_verified.isoformat(),
                }
                for source in state.official_sources
            ],
        }
        for state in states.values()
    ]


def forms_payload() -> dict[str, Any]:
    catalogue = load_forms_catalogue()
    return {
        "forms": [
            {
                "form_id": form.form_id,
                "label": form.label,
                "purpose": form.purpose,
                "official_portal": form.official_portal,
            }
            for form in catalogue.forms
        ],
        "common_documents": {
            category: list(documents)
            for category, documents in catalogue.common_documents.items()
        },
    }


def _guidance_request(payload: dict[str, Any] | GuidanceRequest) -> GuidanceRequest:
    if isinstance(payload, GuidanceRequest):
        return payload
    return GuidanceRequest.model_validate(payload)


def guidance_payload(payload: dict[str, Any] | GuidanceRequest) -> dict[str, Any]:
    validated = _guidance_request(payload)
    request = GuidanceInput(
        state_id=validated.state_id,
        situation=validated.situation,
        blo_visited=validated.blo_visited,
        enumeration_form_received=validated.enumeration_form_received,
        enumeration_form_submitted=validated.enumeration_form_submitted,
        current_roll_found=validated.current_roll_found,
        base_roll_found=validated.base_roll_found,
    )
    result = get_guidance(request)
    data = asdict(result)
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
    rate_limiter: InMemoryRateLimiter | None = None,
    client_identity: str | None = None,
) -> dict[str, Any]:
    validated = _search_request(payload)
    states = load_all_states()
    if validated.state_id not in states:
        raise ValueError(f"unknown state_id: {validated.state_id}")
    assert_search_launch_allowed(
        states[validated.state_id],
        turnstile_verified=validated.turnstile_verified,
        use_sanitized_pilot=validated.use_sanitized_pilot,
    )
    request = SearchRequest(
        state_id=validated.state_id,
        query=validated.query,
        ac_number=validated.ac_number,
        part_number=validated.part_number,
        limit=validated.limit,
    )
    if rate_limiter is not None:
        key = search_rate_limit_key(
            client_identity=client_identity,
            state_id=request.state_id,
            ac_number=request.ac_number,
        )
        assert_rate_limit_allowed(rate_limiter.check(key))
    if records is None:
        if not validated.use_sanitized_pilot:
            raise ValueError("no public search backend is enabled")
        record_source = list(load_sanitized_pilot_records())
    else:
        record_source = list(records)
    results = search_records(request, record_source)
    response = SearchResponsePayload(results=[record.to_dict() for record in results], count=len(results))
    return response.model_dump()


def api_route_paths() -> set[str]:
    return set(API_ROUTES)


def create_app():
    if FastAPI is None:
        raise RuntimeError("FastAPI is required to create the API app")

    app = FastAPI(title="SIR Saathi API", version="0.1.0")

    @app.get(f"{API_PREFIX}/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get(f"{API_PREFIX}/states")
    def states() -> list[dict[str, Any]]:
        return list_states_payload()

    @app.get(f"{API_PREFIX}/forms")
    def forms() -> dict[str, Any]:
        return forms_payload()

    @app.post(f"{API_PREFIX}/guidance")
    def guidance(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return guidance_payload(payload)
        except (KeyError, ValueError, ValidationError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post(f"{API_PREFIX}/search")
    def search(payload: dict[str, Any], request: Request) -> dict[str, Any]:
        try:
            client_host = request.client.host if request.client else None
            return search_payload(payload, rate_limiter=DEFAULT_SEARCH_RATE_LIMITER, client_identity=client_host)
        except RateLimitExceeded as exc:
            raise HTTPException(status_code=429, detail=str(exc)) from exc
        except (KeyError, ValueError, ValidationError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return app


app = create_app() if FastAPI is not None else None
