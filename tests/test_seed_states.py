import json

import pytest

from pipeline.sir_saathi_pipeline import seed_states
from pipeline.sir_saathi_pipeline.state_registry import load_all_states


class FakeTransaction:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        self.connection.transaction_entered = True
        return self

    def __exit__(self, exc_type, _exc, _traceback):
        self.connection.transaction_exited = True
        self.connection.transaction_failed = exc_type is not None
        return False


class FakeCursor:
    def __init__(self):
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _traceback):
        return False

    def execute(self, query, params=()):
        self.executed.append((" ".join(query.split()), params))


class FakeConnection:
    def __init__(self):
        self.cursor_obj = FakeCursor()
        self.transaction_entered = False
        self.transaction_exited = False
        self.transaction_failed = False

    def cursor(self):
        return self.cursor_obj

    def transaction(self):
        return FakeTransaction(self)


def test_state_row_uses_canonical_config_fields() -> None:
    state = load_all_states()["IN-MH"]

    row = seed_states.state_row(state)

    assert row == (
        state.state_id,
        state.eci_state_code,
        state.name,
        state.default_language,
        state.data_capability,
        state.public_launch_ready,
    )


def test_seed_states_uses_transaction_and_idempotent_upsert() -> None:
    states = [load_all_states()["IN-MH"], load_all_states()["IN-WB"]]
    connection = FakeConnection()

    summary = seed_states.seed_states(connection, states)
    query, params = connection.cursor_obj.executed[0]

    assert connection.transaction_entered is True
    assert connection.transaction_exited is True
    assert connection.transaction_failed is False
    assert len(connection.cursor_obj.executed) == 2
    assert query.startswith("INSERT INTO states")
    assert "ON CONFLICT (state_id) DO UPDATE" in query
    assert "public_launch_ready = EXCLUDED.public_launch_ready" in query
    assert params[0] == "IN-MH"
    assert summary.as_dict() == {
        "local_only": True,
        "seeded": True,
        "state_ids": ["IN-MH", "IN-WB"],
        "row_counts": {"states": 2},
    }


def test_seed_states_requires_at_least_one_state() -> None:
    with pytest.raises(ValueError, match="at least one state"):
        seed_states.seed_states(FakeConnection(), [])


def test_select_states_can_seed_all_or_one_state() -> None:
    states = load_all_states()

    assert [state.state_id for state in seed_states.select_states(None, states)] == ["IN-MH", "IN-WB"]
    assert [state.state_id for state in seed_states.select_states("IN-WB", states)] == ["IN-WB"]

    with pytest.raises(ValueError, match="unknown state_id"):
        seed_states.select_states("IN-XX", states)


def test_main_requires_database_url(capsys, monkeypatch) -> None:
    monkeypatch.delenv(seed_states.DATABASE_URL_ENV, raising=False)

    exit_code = seed_states.main([])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert output["local_only"] is True
    assert output["seeded"] is False
    assert seed_states.DATABASE_URL_ENV in output["error"]


def test_main_calls_seed_fn_for_selected_state(capsys, monkeypatch) -> None:
    calls = []
    monkeypatch.setenv(seed_states.DATABASE_URL_ENV, "postgresql://local/sir_saathi")

    def fake_seed(database_url, *, state_id=None):
        calls.append((database_url, state_id))
        return {
            "local_only": True,
            "seeded": True,
            "state_ids": [state_id],
            "row_counts": {"states": 1},
        }

    exit_code = seed_states.main(["--state", "IN-MH"], seed_fn=fake_seed)
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert calls == [("postgresql://local/sir_saathi", "IN-MH")]
    assert output["seeded"] is True
    assert output["state_ids"] == ["IN-MH"]


def test_main_returns_safe_failure_report(capsys, monkeypatch) -> None:
    monkeypatch.setenv(seed_states.DATABASE_URL_ENV, "postgresql://local/sir_saathi")

    def failing_seed(_database_url, *, state_id=None):
        raise RuntimeError("db unavailable")

    exit_code = seed_states.main([], seed_fn=failing_seed)
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert output["seeded"] is False
    assert output["error"] == "db unavailable"
    assert output["row_counts"] == {"states": 0}
