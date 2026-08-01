from dataclasses import replace
import importlib

import pytest

from services.api.search import SearchRequest
from services.api.search_backend import (
    PUBLIC_SEARCH_STATEMENT_TIMEOUT_MS,
    PostgresSearchBackend,
    configured_search_backend,
    public_search_sql,
)
from services.api.models import InternalVoterRecord
from services.api.privacy import RateLimitDecision

api_app = importlib.import_module("services.api.app")


class SharedLimiter:
    shared = True

    def check(self, _key, *, now=None):
        return RateLimitDecision(allowed=True, remaining=29)


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def execute(self, query, params):
        self.executed.append((" ".join(query.split()), params))

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, rows):
        self.cursor_obj = FakeCursor(rows)
        self.closed = False

    def cursor(self):
        return self.cursor_obj

    def close(self):
        self.closed = True


def test_public_search_sql_requires_enabled_exact_roll_and_geography_scope() -> None:
    query = " ".join(public_search_sql().split())
    assert "JOIN public_search_scopes scope" in query
    assert "scope.roll_version_id = vr.roll_version_id" in query
    assert "scope.ac_id = vr.ac_id" in query
    assert "scope.enabled = TRUE" in query
    assert "ac.ac_number = %s" in query
    assert "LIMIT %s" in query


def test_postgres_backend_uses_bounded_parameters_and_closes_connection() -> None:
    connection = FakeConnection([{
        "state_id": "IN-MH", "ac_number": 172, "part_number": 21, "serial_number": 7,
        "name": "Sample Voter", "roll_year": 2026, "roll_kind": "final_roll",
        "data_quality": "ok", "source_label": "Reviewed official roll",
        "confidence": 0.91, "epic_last4": "1234",
    }])
    backend = PostgresSearchBackend(lambda: connection)
    request = SearchRequest(state_id="IN-MH", query="  Sample   Voter ", ac_number=172, part_number=21, limit=5)
    results = backend.search(request)
    assert connection.cursor_obj.executed[0] == ("SET TRANSACTION READ ONLY", ())
    assert connection.cursor_obj.executed[1] == (
        f"SET LOCAL statement_timeout = '{PUBLIC_SEARCH_STATEMENT_TIMEOUT_MS}ms'", ()
    )
    assert connection.cursor_obj.executed[2][1] == ("sample voter", "IN-MH", 172, 21, 21, 0.2, 5)
    assert connection.closed is True
    assert results[0].name == "Sample Voter"
    assert results[0].epic_last4 == "1234"


def test_postgres_backend_readiness_is_non_sensitive_and_closes_connection() -> None:
    connection = FakeConnection([])
    assert PostgresSearchBackend(lambda: connection).ready() is True
    assert connection.cursor_obj.executed == [("SELECT 1", ())]
    assert connection.closed is True
    assert PostgresSearchBackend(lambda: (_ for _ in ()).throw(TimeoutError("private"))).ready() is False


def test_configured_postgres_backend_uses_a_bounded_connect_timeout(monkeypatch) -> None:
    captured = {}

    def connect(database_url, **kwargs):
        captured.update({"database_url": database_url, **kwargs})
        raise TimeoutError("synthetic")

    import psycopg

    monkeypatch.setenv("SIR_SAATHI_DATABASE_URL", "postgresql://database.internal/sir_saathi")
    monkeypatch.setattr(psycopg, "connect", connect)
    backend = configured_search_backend()
    assert backend is not None
    assert backend.ready() is False
    assert captured["connect_timeout"] == 3
    assert f"statement_timeout={PUBLIC_SEARCH_STATEMENT_TIMEOUT_MS}" in captured["options"]
    assert "default_transaction_read_only=on" in captured["options"]


def test_postgres_backend_closes_connection_when_query_fails() -> None:
    class FailingCursor(FakeCursor):
        def execute(self, query, params):
            super().execute(query, params)
            if "WITH search_input" in query:
                raise TimeoutError("synthetic statement timeout")

    connection = FakeConnection([])
    connection.cursor_obj = FailingCursor([])
    backend = PostgresSearchBackend(lambda: connection)
    with pytest.raises(TimeoutError, match="statement timeout"):
        backend.search(SearchRequest(state_id="IN-MH", query="sample", ac_number=172))
    assert connection.closed is True


def test_search_backend_is_called_only_after_launch_policy_passes(monkeypatch) -> None:
    states = api_app.load_all_states()
    launch_ready = replace(states["IN-MH"], public_launch_ready=True, data_capability="validated_indexed_search")
    monkeypatch.setattr(api_app, "load_all_states", lambda: {**states, "IN-MH": launch_ready})

    class Backend:
        called = False

        def search(self, _request):
            self.called = True
            return []

    backend = Backend()
    result = api_app.search_payload(
        {"state_id": "IN-MH", "query": "sample", "ac_number": 172},
        abuse_verification_passed=True,
        search_backend=backend,
        rate_limiter=SharedLimiter(),
    )
    assert result == {"results": [], "count": 0}
    assert backend.called is True


def test_search_backend_is_not_called_when_launch_policy_fails() -> None:
    class Backend:
        def search(self, _request):
            raise AssertionError("backend must not run before launch gates")

    with pytest.raises(ValueError, match="not enabled for public launch"):
        api_app.search_payload(
            {"state_id": "IN-MH", "query": "sample", "ac_number": 172},
            abuse_verification_passed=True,
            search_backend=Backend(),
            rate_limiter=SharedLimiter(),
        )


def test_backend_results_are_redacted_and_fail_closed_on_scope_breach(monkeypatch) -> None:
    states = api_app.load_all_states()
    launch_ready = replace(states["IN-MH"], public_launch_ready=True, data_capability="validated_indexed_search")
    monkeypatch.setattr(api_app, "load_all_states", lambda: {**states, "IN-MH": launch_ready})

    def voter(*, state_id="IN-MH"):
        return InternalVoterRecord(
            state_id=state_id, ac_number=172, part_number=21, serial_number=7,
            name="Asha Patil", roll_year=2026, roll_kind="final_roll", data_quality="ok",
            source_label="Reviewed official roll", confidence=0.91, epic_last4="1234",
        )

    class Backend:
        def __init__(self, records):
            self.records = records

        def search(self, _request):
            return self.records

    result = api_app.search_payload(
        {"state_id": "IN-MH", "query": "aasa", "ac_number": 172},
        abuse_verification_passed=True,
        search_backend=Backend([voter()]),
        rate_limiter=SharedLimiter(),
    )
    assert result["results"][0]["display_name"] == "Asha Patil"
    assert result["results"][0]["epic_hint"] == "***1234"
    with pytest.raises(ValueError, match="outside the requested state/AC scope"):
        api_app.search_payload(
            {"state_id": "IN-MH", "query": "aasa", "ac_number": 172},
            abuse_verification_passed=True,
            search_backend=Backend([voter(state_id="IN-WB")]),
            rate_limiter=SharedLimiter(),
        )
