"""FastAPI app factory for SIR Saathi.

The pure functions are importable in tests without requiring a running server.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from pipeline.sir_saathi_pipeline.guidance import GuidanceInput, get_guidance
from pipeline.sir_saathi_pipeline.state_registry import load_all_states

from .models import InternalVoterRecord
from .pilot_data import load_sanitized_pilot_records
from .search import SearchRequest, search_records

try:  # FastAPI is installed in deployment/CI environments.
    from fastapi import FastAPI, HTTPException
except Exception:  # pragma: no cover - local environments may not have FastAPI yet
    FastAPI = None  # type: ignore[assignment]
    HTTPException = Exception  # type: ignore[assignment]


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
        }
        for state in states.values()
    ]


def guidance_payload(payload: dict[str, Any]) -> dict[str, Any]:
    request = GuidanceInput(
        state_id=payload["state_id"],
        situation=payload["situation"],
        blo_visited=payload.get("blo_visited", "unknown"),
        enumeration_form_received=payload.get("enumeration_form_received", "unknown"),
        enumeration_form_submitted=payload.get("enumeration_form_submitted", "unknown"),
        current_roll_found=payload.get("current_roll_found", "unknown"),
        base_roll_found=payload.get("base_roll_found", "unknown"),
    )
    result = get_guidance(request)
    data = asdict(result)
    if result.deadline:
        data["deadline"] = result.deadline.isoformat()
    return data


def search_payload(payload: dict[str, Any], records: list[InternalVoterRecord] | None = None) -> dict[str, Any]:
    request = SearchRequest(
        state_id=payload["state_id"],
        query=payload["query"],
        ac_number=payload.get("ac_number"),
        part_number=payload.get("part_number"),
        limit=payload.get("limit", 10),
    )
    results = search_records(request, list(records) if records is not None else list(load_sanitized_pilot_records()))
    return {"results": [record.to_dict() for record in results], "count": len(results)}


def create_app():
    if FastAPI is None:
        raise RuntimeError("FastAPI is required to create the API app")

    app = FastAPI(title="SIR Saathi API", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/states")
    def states() -> list[dict[str, Any]]:
        return list_states_payload()

    @app.post("/guidance")
    def guidance(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return guidance_payload(payload)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/search")
    def search(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return search_payload(payload)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return app


app = create_app() if FastAPI is not None else None
