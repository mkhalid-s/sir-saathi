import json

import pytest

from pipeline.sir_saathi_pipeline import local_search


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _traceback):
        return False

    def execute(self, query, params=()):
        self.executed.append((" ".join(query.split()), params))

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, rows):
        self.cursor_obj = FakeCursor(rows)

    def cursor(self):
        return self.cursor_obj


def sample_rows():
    return [
        {
            "name": "Matched Person",
            "age": 41,
            "gender": "M",
            "relation_type": "father",
            "ac_number": 172,
            "part_number": 21,
            "serial_number": 7,
            "epic_last4": "1234",
            "data_quality": "ok",
            "score": 0.83,
            "epic_hash": "must-not-leak",
            "relative_name_normalized": "must-not-leak",
        }
    ]


def test_search_loaded_rolls_uses_state_ac_and_trigram_similarity() -> None:
    connection = FakeConnection(sample_rows())
    request = local_search.LocalSearchRequest(state_id="IN-MH", ac_number=172, query="Hidden Query")

    results = local_search.search_loaded_rolls(connection, request)
    query, params = connection.cursor_obj.executed[0]

    assert "similarity(vr.name_normalized" in query
    assert "FROM voter_records" in query
    assert "JOIN assembly_constituencies" in query
    assert "WHERE vr.state_id = %s" in query
    assert "AND ac.ac_number = %s" in query
    assert params == ("hidden query", "IN-MH", 172, "hidden query", 0.2, 10)
    assert len(results) == 1
    assert results[0].name == "Matched Person"


def test_search_report_redacts_query_and_epic_by_default() -> None:
    request = local_search.LocalSearchRequest(state_id="IN-MH", ac_number=172, query="Hidden Query")
    result = local_search.LocalSearchResult(
        name="Matched Person",
        age=41,
        gender="M",
        relation_type="father",
        ac_number=172,
        part_number=21,
        serial_number=7,
        score=0.83,
        data_quality="ok",
        epic_last4="1234",
    )

    report = local_search.search_report(request, [result], elapsed_ms=12.345)
    encoded = json.dumps(report)

    assert report["local_only"] is True
    assert report["safe_for_public"] is False
    assert report["query_summary"] == "len:12 prefix:hi"
    assert report["elapsed_ms"] == 12.35
    assert "Hidden Query" not in encoded
    assert "epic_hash" not in encoded
    assert "epic_last4" not in encoded


def test_search_report_can_include_epic_last4_explicitly() -> None:
    request = local_search.LocalSearchRequest(
        state_id="IN-MH",
        ac_number=172,
        query="Hidden Query",
        include_epic_last4=True,
    )
    result = local_search.LocalSearchResult(
        name="Matched Person",
        age=41,
        gender="M",
        relation_type="father",
        ac_number=172,
        part_number=21,
        serial_number=7,
        score=0.83,
        data_quality="ok",
        epic_last4="1234",
    )

    report = local_search.search_report(request, [result], elapsed_ms=1)

    assert report["results"][0]["epic_last4"] == "1234"


def test_local_search_request_validates_scope_and_limits() -> None:
    with pytest.raises(ValueError, match="state_id"):
        local_search.LocalSearchRequest(state_id="", ac_number=172, query="Name").validate()
    with pytest.raises(ValueError, match="ac_number"):
        local_search.LocalSearchRequest(state_id="IN-MH", ac_number=0, query="Name").validate()
    with pytest.raises(ValueError, match="at least two"):
        local_search.LocalSearchRequest(state_id="IN-MH", ac_number=172, query="A").validate()
    with pytest.raises(ValueError, match="limit"):
        local_search.LocalSearchRequest(state_id="IN-MH", ac_number=172, query="Name", limit=21).validate()
    with pytest.raises(ValueError, match="threshold"):
        local_search.LocalSearchRequest(state_id="IN-MH", ac_number=172, query="Name", threshold=1.5).validate()


def test_validate_local_search_returns_safe_report() -> None:
    connection = FakeConnection(sample_rows())
    request = local_search.LocalSearchRequest(state_id="IN-MH", ac_number=172, query="Hidden Query")

    report = local_search.validate_local_search(connection, request)
    encoded = json.dumps(report)

    assert report["result_count"] == 1
    assert report["results"][0]["name"] == "Matched Person"
    assert "Hidden Query" not in encoded
    assert "must-not-leak" not in encoded


def test_main_requires_database_url(tmp_path, capsys, monkeypatch) -> None:
    monkeypatch.delenv(local_search.DATABASE_URL_ENV, raising=False)

    exit_code = local_search.main(["--state", "IN-MH", "--ac", "172", "--name", "Hidden Query"])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert output["local_only"] is True
    assert output["safe_for_public"] is False
    assert local_search.DATABASE_URL_ENV in output["error"]


def test_main_calls_search_fn_and_avoids_raw_query(capsys, monkeypatch) -> None:
    calls = []
    monkeypatch.setenv(local_search.DATABASE_URL_ENV, "postgresql://local/sir_saathi")

    def fake_search(database_url, request):
        calls.append((database_url, request))
        return local_search.search_report(
            request,
            [
                local_search.LocalSearchResult(
                    name="Matched Person",
                    age=41,
                    gender="M",
                    relation_type="father",
                    ac_number=172,
                    part_number=21,
                    serial_number=7,
                    score=0.83,
                    data_quality="ok",
                )
            ],
            elapsed_ms=2,
        )

    exit_code = local_search.main(
        ["--state", "IN-MH", "--ac", "172", "--name", "Hidden Query"],
        search_fn=fake_search,
    )
    output = json.loads(capsys.readouterr().out)
    encoded = json.dumps(output)

    assert exit_code == 0
    assert calls and calls[0][0] == "postgresql://local/sir_saathi"
    assert calls[0][1].normalized_query == "hidden query"
    assert output["result_count"] == 1
    assert "Hidden Query" not in encoded


def test_main_returns_safe_failure_report(capsys, monkeypatch) -> None:
    monkeypatch.setenv(local_search.DATABASE_URL_ENV, "postgresql://local/sir_saathi")

    def failing_search(_database_url, _request):
        raise RuntimeError("db unavailable")

    exit_code = local_search.main(
        ["--state", "IN-MH", "--ac", "172", "--name", "Hidden Query"],
        search_fn=failing_search,
    )
    output = json.loads(capsys.readouterr().out)
    encoded = json.dumps(output)

    assert exit_code == 1
    assert output["result_count"] == 0
    assert output["error"] == "db unavailable"
    assert "Hidden Query" not in encoded
