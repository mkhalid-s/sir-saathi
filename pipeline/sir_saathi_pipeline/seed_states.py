"""Local DB seed for canonical state metadata."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from typing import Any, Callable, Protocol

from pipeline.sir_saathi_pipeline.state_registry import StateConfig, load_all_states

DATABASE_URL_ENV = "SIR_SAATHI_DATABASE_URL"


class CursorLike(Protocol):
    def execute(self, query: str, params: tuple[Any, ...] = ...) -> Any: ...


class ConnectionLike(Protocol):
    def cursor(self) -> Any: ...
    def transaction(self) -> Any: ...


@dataclass(frozen=True)
class SeedSummary:
    seeded: bool
    state_ids: tuple[str, ...]
    row_counts: dict[str, int]

    def as_dict(self) -> dict[str, Any]:
        return {
            "local_only": True,
            "seeded": self.seeded,
            "state_ids": list(self.state_ids),
            "row_counts": self.row_counts,
        }


def state_row(state: StateConfig) -> tuple[Any, ...]:
    return (
        state.state_id,
        state.eci_state_code,
        state.name,
        state.default_language,
        state.data_capability,
        state.public_launch_ready,
    )


def upsert_state_sql() -> str:
    return """
        INSERT INTO states (
            state_id, eci_state_code, name, default_language,
            data_capability, public_launch_ready
        ) VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (state_id) DO UPDATE SET
            eci_state_code = EXCLUDED.eci_state_code,
            name = EXCLUDED.name,
            default_language = EXCLUDED.default_language,
            data_capability = EXCLUDED.data_capability,
            public_launch_ready = EXCLUDED.public_launch_ready
    """


def seed_states(connection: ConnectionLike, states: list[StateConfig]) -> SeedSummary:
    if not states:
        raise ValueError("at least one state is required for seeding")
    state_ids = tuple(state.state_id for state in states)
    with connection.transaction():
        with connection.cursor() as cursor:
            for state in states:
                cursor.execute(upsert_state_sql(), state_row(state))
    return SeedSummary(
        seeded=True,
        state_ids=state_ids,
        row_counts={"states": len(states)},
    )


def select_states(state_id: str | None, states: dict[str, StateConfig]) -> list[StateConfig]:
    if state_id is None:
        return [states[key] for key in sorted(states)]
    if state_id not in states:
        raise ValueError(f"unknown state_id: {state_id}")
    return [states[state_id]]


def seed_database(database_url: str, *, state_id: str | None = None) -> dict[str, Any]:
    import psycopg

    states = load_all_states()
    selected_states = select_states(state_id, states)
    with psycopg.connect(database_url) as connection:
        return seed_states(connection, selected_states).as_dict()


def failure_report(message: str) -> dict[str, Any]:
    return {
        "local_only": True,
        "seeded": False,
        "error": message,
        "row_counts": {"states": 0},
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Seed canonical SIR Saathi states into local Postgres.")
    parser.add_argument("--state", help="Optional canonical state id, for example IN-MH. Defaults to all configured states.")
    return parser


def main(
    argv: list[str] | None = None,
    *,
    seed_fn: Callable[..., dict[str, Any]] = seed_database,
) -> int:
    args = build_parser().parse_args(argv)
    database_url = os.environ.get(DATABASE_URL_ENV)
    if not database_url:
        print(json.dumps(failure_report(f"{DATABASE_URL_ENV} is required for state seeding"), indent=2, sort_keys=True))
        return 1
    try:
        report = seed_fn(database_url, state_id=args.state)
    except Exception as exc:
        print(json.dumps(failure_report(str(exc)), indent=2, sort_keys=True))
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
