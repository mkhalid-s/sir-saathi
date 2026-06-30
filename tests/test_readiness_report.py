import json

from pipeline.sir_saathi_pipeline import readiness_report
from pipeline.sir_saathi_pipeline.state_registry import load_all_states


class FakeCursor:
    def __init__(self, roll_row, voter_row, quality_rows):
        self.rows = [roll_row, voter_row]
        self.quality_rows = quality_rows
        self.executed = []
        self.fetchone_count = 0

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _traceback):
        return False

    def execute(self, query, params=()):
        self.executed.append((" ".join(query.split()), params))

    def fetchone(self):
        row = self.rows[self.fetchone_count]
        self.fetchone_count += 1
        return row

    def fetchall(self):
        return self.quality_rows


class FakeConnection:
    def __init__(self, roll_row, voter_row, quality_rows):
        self.cursor_obj = FakeCursor(roll_row, voter_row, quality_rows)

    def cursor(self):
        return self.cursor_obj


def fake_connection(
    *,
    source_documents=1,
    extraction_runs=1,
    validated_runs=1,
    nonvalidated_runs=0,
    expected_records=2,
    parsed_records=2,
    voter_records=2,
    ok_records=2,
    issue_records=0,
    quality_rows=None,
):
    return FakeConnection(
        {
            "source_documents": source_documents,
            "extraction_runs": extraction_runs,
            "validated_runs": validated_runs,
            "nonvalidated_runs": nonvalidated_runs,
            "expected_records": expected_records,
            "parsed_records": parsed_records,
        },
        {
            "voter_records": voter_records,
            "ok_records": ok_records,
            "issue_records": issue_records,
        },
        quality_rows if quality_rows is not None else [{"data_quality": "ok", "count": ok_records}],
    )


def request(part_number=None, max_quality_issue_rate=0.05):
    return readiness_report.ReadinessRequest(
        state_id="IN-WB",
        ac_number=172,
        part_number=part_number,
        max_quality_issue_rate=max_quality_issue_rate,
    )


def test_fetch_loaded_summary_queries_roll_and_scoped_voter_counts() -> None:
    connection = fake_connection(quality_rows=[{"data_quality": "ok", "count": 2}])
    summary = readiness_report.fetch_loaded_summary(connection, request(part_number=21))

    executed = connection.cursor_obj.executed
    assert "FROM roll_versions" in executed[0][0]
    assert executed[0][1] == ("IN-WB",)
    assert "AND ac.ac_number = %s" in executed[1][0]
    assert "AND ps.part_number = %s" in executed[1][0]
    assert executed[1][1] == ("IN-WB", 172, 21)
    assert "GROUP BY vr.data_quality" in executed[2][0]
    assert summary.source_documents == 1
    assert summary.voter_records == 2
    assert summary.quality_issue_rate == 0
    assert summary.quality_summary == {"ok": 2}


def test_readiness_report_blocks_when_state_config_not_public_ready() -> None:
    states = load_all_states()
    connection = fake_connection()

    report = readiness_report.validate_readiness(connection, request(), states=states)

    assert report["local_only"] is True
    assert report["safe_for_public"] is False
    assert report["ready_for_public"] is False
    assert "state config is not marked public_launch_ready" in report["blockers"]
    assert report["state_config"]["schedule_provenance"] == "official"
    assert "results" not in report


def test_readiness_report_blocks_quality_and_count_issues() -> None:
    states = load_all_states()
    connection = fake_connection(
        expected_records=3,
        parsed_records=2,
        voter_records=2,
        ok_records=1,
        issue_records=1,
        quality_rows=[{"data_quality": "ok", "count": 1}, {"data_quality": "missing_age", "count": 1}],
    )

    report = readiness_report.validate_readiness(connection, request(), states=states)

    assert "expected and parsed record counts do not match" in report["blockers"]
    assert "data quality issue rate exceeds threshold" in report["blockers"]
    assert report["loaded_data"]["quality_issue_rate"] == 0.5
    assert report["loaded_data"]["quality_summary"] == {"ok": 1, "missing_age": 1}


def test_readiness_report_blocks_missing_loaded_data() -> None:
    states = load_all_states()
    connection = fake_connection(source_documents=0, extraction_runs=0, voter_records=0, ok_records=0)

    report = readiness_report.validate_readiness(connection, request(), states=states)

    assert "no source documents loaded" in report["blockers"]
    assert "no extraction runs loaded" in report["blockers"]
    assert "no scoped voter records loaded" in report["blockers"]


def test_readiness_request_validation() -> None:
    for bad_request, expected in [
        (readiness_report.ReadinessRequest(state_id="", ac_number=172), "state_id"),
        (readiness_report.ReadinessRequest(state_id="IN-WB", ac_number=0), "ac_number"),
        (readiness_report.ReadinessRequest(state_id="IN-WB", ac_number=172, part_number=0), "part_number"),
        (readiness_report.ReadinessRequest(state_id="IN-WB", ac_number=172, max_quality_issue_rate=2), "max_quality"),
    ]:
        try:
            bad_request.validate()
        except ValueError as exc:
            assert expected in str(exc)
        else:
            raise AssertionError("expected validation failure")


def test_main_requires_database_url(capsys, monkeypatch) -> None:
    monkeypatch.delenv(readiness_report.DATABASE_URL_ENV, raising=False)

    exit_code = readiness_report.main(["--state", "IN-WB", "--ac", "172"])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert output["ready_for_public"] is False
    assert output["safe_for_public"] is False
    assert readiness_report.DATABASE_URL_ENV in output["error"]


def test_main_calls_readiness_fn_and_outputs_safe_json(capsys, monkeypatch) -> None:
    calls = []
    monkeypatch.setenv(readiness_report.DATABASE_URL_ENV, "postgresql://local/sir_saathi")

    def fake_readiness(database_url, req):
        calls.append((database_url, req))
        return {
            "local_only": True,
            "safe_for_public": False,
            "ready_for_public": False,
            "state_id": req.state_id,
            "ac_number": req.ac_number,
            "part_number": req.part_number,
            "loaded_data": {"voter_records": 2},
            "blockers": ["state config is not marked public_launch_ready"],
        }

    exit_code = readiness_report.main(
        ["--state", "IN-WB", "--ac", "172", "--part", "21"],
        readiness_fn=fake_readiness,
    )
    output = json.loads(capsys.readouterr().out)
    encoded = json.dumps(output)

    assert exit_code == 0
    assert calls and calls[0][0] == "postgresql://local/sir_saathi"
    assert calls[0][1].part_number == 21
    assert output["ready_for_public"] is False
    assert "voter_name" not in encoded
    assert "epic" not in encoded.casefold()


def test_main_returns_safe_failure_report(capsys, monkeypatch) -> None:
    monkeypatch.setenv(readiness_report.DATABASE_URL_ENV, "postgresql://local/sir_saathi")

    def failing_readiness(_database_url, _request):
        raise RuntimeError("db unavailable")

    exit_code = readiness_report.main(
        ["--state", "IN-WB", "--ac", "172"],
        readiness_fn=failing_readiness,
    )
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert output["ready_for_public"] is False
    assert output["blockers"] == ["db unavailable"]
