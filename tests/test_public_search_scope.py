import json
from contextlib import nullcontext
from dataclasses import replace

from pipeline.sir_saathi_pipeline import public_search_scope
from pipeline.sir_saathi_pipeline.state_registry import load_all_states


READY_ROW = {
    "roll_version_id": "roll-1",
    "state_id": "IN-MH",
    "roll_year": 2002,
    "roll_kind": "historical_base_roll",
    "ac_id": "ac-1",
    "ac_number": 172,
    "geography_version": "roll-2002",
    "source_documents": 1,
    "extraction_runs": 1,
    "validated_runs": 1,
    "nonvalidated_runs": 0,
    "expected_records": 2,
    "parsed_records": 2,
    "voter_records": 2,
    "ok_records": 2,
    "issue_records": 0,
    "currently_enabled": False,
    "reviewed_by": None,
    "reviewed_at": None,
}


class FakeCursor:
    def __init__(self, *rows):
        self.rows = list(rows)
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _traceback):
        return False

    def execute(self, query, params=()):
        self.executed.append((" ".join(query.split()), params))

    def fetchone(self):
        return self.rows.pop(0)


class FakeConnection:
    def __init__(self, *rows):
        self.cursors = [FakeCursor(row) for row in rows]
        self.transaction_count = 0

    def cursor(self):
        return self.cursors.pop(0)

    def transaction(self):
        self.transaction_count += 1
        return nullcontext()


def request():
    return public_search_scope.ScopeRequest("IN-MH", 172, "roll-1", "ac-1")


def states(*, launch_ready=True):
    registry = load_all_states()
    registry["IN-MH"] = replace(registry["IN-MH"], public_launch_ready=launch_ready)
    return registry


def test_inspect_scope_requires_exact_roll_and_versioned_ac() -> None:
    connection = FakeConnection(READY_ROW)

    report = public_search_scope.inspect_scope(connection, request(), states=states())

    assert report["ready_to_enable"] is True
    assert report["loaded_data"]["voter_records"] == 2
    assert report["loaded_data"]["geography_version"] == "roll-2002"


def test_inspect_scope_query_is_exact_and_parameterized() -> None:
    cursor = FakeCursor(READY_ROW)
    connection = FakeConnection()
    connection.cursors = [cursor]

    public_search_scope.inspect_scope(connection, request(), states=states())

    query, params = cursor.executed[0]
    assert "WHERE sd.roll_version_id = %s" in query
    assert "WHERE roll_version_id = %s AND ac_id = %s AND state_id = %s" in query
    assert params == ("roll-1", "roll-1", "ac-1", "IN-MH", "ac-1", "roll-1", "IN-MH", 172)


def test_enable_is_dry_run_by_default() -> None:
    connection = FakeConnection(READY_ROW)

    report = public_search_scope.change_authorization(
        connection,
        request(),
        action="enable",
        reviewed_by="reviewer@example.test",
        reason="Pilot acceptance record OPS-42",
        apply=False,
        states=states(),
    )

    assert report["dry_run"] is True
    assert report["applied"] is False
    assert connection.transaction_count == 0


def test_change_metadata_is_required_and_bounded() -> None:
    connection = FakeConnection(READY_ROW)
    for reviewed_by, reason, expected in [
        (" ", "approved", "reviewed_by is required"),
        ("reviewer", " ", "reason is required"),
        ("r" * 201, "approved", "reviewed_by must be 200"),
        ("reviewer", "x" * 501, "reason must be 500"),
    ]:
        try:
            public_search_scope.change_authorization(
                connection,
                request(),
                action="enable",
                reviewed_by=reviewed_by,
                reason=reason,
                apply=False,
                states=states(),
            )
        except ValueError as exc:
            assert expected in str(exc)
        else:
            raise AssertionError("expected invalid review metadata to fail")


def test_enable_appends_event_and_updates_scope_atomically() -> None:
    changed = {"enabled": True, "reviewed_by": "reviewer-1", "reviewed_at": "2026-08-01T00:00:00Z"}
    write_cursor = FakeCursor(READY_ROW, changed)
    connection = FakeConnection()
    connection.cursors = [write_cursor]

    report = public_search_scope.change_authorization(
        connection,
        request(),
        action="enable",
        reviewed_by="reviewer-1",
        reason="Approved evidence ticket OPS-42",
        apply=True,
        states=states(),
    )

    assert report["applied"] is True
    assert report["authorization"]["currently_enabled"] is True
    assert report["event_id"].startswith("scope-event-")
    assert connection.transaction_count == 1
    assert write_cursor.executed[0][0] == "SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"
    query, params = write_cursor.executed[2]
    assert "INSERT INTO public_search_scope_events" in query
    assert "INSERT INTO public_search_scopes" in query
    assert params[3:6] == ("enable", "reviewer-1", "Approved evidence ticket OPS-42")
    snapshot = json.loads(params[6])
    assert snapshot["ready_to_enable"] is True
    assert "results" not in snapshot


def test_enable_fails_closed_without_mutating_when_readiness_blocked() -> None:
    connection = FakeConnection(READY_ROW)

    report = public_search_scope.change_authorization(
        connection,
        request(),
        action="enable",
        reviewed_by="reviewer-1",
        reason="Should remain blocked",
        apply=True,
        states=states(launch_ready=False),
    )

    assert report["applied"] is False
    assert "state config is not marked public_launch_ready" in report["blockers"]
    assert connection.transaction_count == 1
    assert len(connection.cursors) == 0


def test_disable_remains_available_when_launch_readiness_is_blocked() -> None:
    changed = {"enabled": False, "reviewed_by": "reviewer-1", "reviewed_at": "2026-08-01T00:00:00Z"}
    cursor = FakeCursor(READY_ROW, changed)
    connection = FakeConnection()
    connection.cursors = [cursor]

    report = public_search_scope.change_authorization(
        connection,
        request(),
        action="disable",
        reviewed_by="reviewer-1",
        reason="Emergency revocation",
        apply=True,
        states=states(launch_ready=False),
    )

    assert report["applied"] is True
    assert report["authorization"]["currently_enabled"] is False


def test_cli_requires_explicit_review_metadata_and_apply_is_separate(capsys, monkeypatch) -> None:
    monkeypatch.setenv(public_search_scope.DATABASE_URL_ENV, "postgresql://local/test")
    base_args = ["--state", "IN-MH", "--ac", "172", "--roll-version-id", "roll-1", "--ac-id", "ac-1"]

    exit_code = public_search_scope.main([*base_args, "--enable"])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert output["applied"] is False
    assert "--reviewed-by and --reason" in output["error"]


def test_cli_outputs_safe_dry_run(capsys, monkeypatch) -> None:
    monkeypatch.setenv(public_search_scope.DATABASE_URL_ENV, "postgresql://local/test")
    calls = []

    def fake_scope(database_url, req, **kwargs):
        calls.append((database_url, req, kwargs))
        return {"safe_aggregate_report": True, "ready_to_enable": True, "blockers": [], "applied": False, "dry_run": True}

    exit_code = public_search_scope.main(
        [
            "--state", "IN-MH", "--ac", "172", "--roll-version-id", "roll-1", "--ac-id", "ac-1",
            "--enable", "--reviewed-by", "reviewer-1", "--reason", "OPS-42 approved",
        ],
        scope_fn=fake_scope,
    )
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["dry_run"] is True
    assert calls[0][2]["apply"] is False
