import json

import pytest

from pipeline.sir_saathi_pipeline.db_loader import MissingStateError, load_ingestion_batch
from pipeline.sir_saathi_pipeline.ingestion import ParsedRollInput, SourceDocumentInput, build_ingestion_batch


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
    def __init__(self, state_exists: bool):
        self.state_exists = state_exists
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _traceback):
        return False

    def execute(self, query, params=()):
        self.executed.append((" ".join(query.split()), params))

    def fetchone(self):
        return (1,) if self.state_exists else None


class FakeConnection:
    def __init__(self, *, state_exists: bool = True):
        self.cursor_obj = FakeCursor(state_exists=state_exists)
        self.transaction_entered = False
        self.transaction_exited = False
        self.transaction_failed = False

    def cursor(self):
        return self.cursor_obj

    def transaction(self):
        return FakeTransaction(self)


def sample_batch():
    parsed = ParsedRollInput(
        state_id="IN-MH",
        roll_year=2002,
        roll_kind="historical_base_roll",
        language="mr",
        source_label="Synthetic loader source",
        parser_name="parse_2002",
        metadata={
            "ac_number": 172,
            "part_number": 21,
            "total_voters": 2,
            "ac_name_encoded": "Trombay",
            "ac_reservation_encoded": "general",
            "polling_station_name_encoded": "Pilot polling station",
        },
        voters=(
            {
                "serial_number": 1,
                "voter_name": "Sample Voter",
                "relation_type": "father",
                "relative_name": "Example Parent",
                "age": 41,
                "gender": "M",
                "epic_number": "sample-card-0001",
                "data_quality": "ok",
            },
            {
                "serial_number": 2,
                "voter_name": "Second Voter",
                "relation_type": "spouse",
                "relative_name": "Example Spouse",
                "age": 39,
                "gender": "F",
                "epic_number": "sample-card-0002",
                "data_quality": "missing_age,review",
            },
        ),
        source_document=SourceDocumentInput(
            state_id="IN-MH",
            source_uri="local://synthetic/pilot-roll.pdf",
            local_path="data/local/pilot-roll.pdf",
            checksum="sha256:syntheticchecksum",
            parser_hint="parse_2002",
        ),
    )
    return build_ingestion_batch(parsed, hash_salt="unit-test-salt")


def test_load_ingestion_batch_uses_transaction_and_safe_summary() -> None:
    connection = FakeConnection()
    summary = load_ingestion_batch(connection, sample_batch())
    encoded = json.dumps(summary.as_dict())

    assert connection.transaction_entered is True
    assert connection.transaction_exited is True
    assert connection.transaction_failed is False
    assert summary.loaded is True
    assert summary.row_counts == {
        "assembly_constituencies": 1,
        "polling_stations": 1,
        "roll_versions": 1,
        "source_documents": 1,
        "extraction_runs": 1,
        "voter_records": 2,
    }
    assert "Sample Voter" not in encoded
    assert "sample-card" not in encoded


def test_load_ingestion_batch_checks_state_before_writes() -> None:
    connection = FakeConnection(state_exists=False)

    with pytest.raises(MissingStateError, match="state row must exist"):
        load_ingestion_batch(connection, sample_batch())

    assert connection.transaction_entered is True
    assert connection.transaction_failed is True
    assert len(connection.cursor_obj.executed) == 1
    assert connection.cursor_obj.executed[0][0].startswith("SELECT 1 FROM states")


def test_load_ingestion_batch_uses_fk_order_and_idempotent_upserts() -> None:
    connection = FakeConnection()
    load_ingestion_batch(connection, sample_batch())

    executed_sql = [query for query, _params in connection.cursor_obj.executed]
    inserts = [query for query in executed_sql if query.startswith("INSERT INTO")]
    expected_order = [
        "INSERT INTO assembly_constituencies",
        "INSERT INTO polling_stations",
        "INSERT INTO roll_versions",
        "INSERT INTO source_documents",
        "INSERT INTO extraction_runs",
        "INSERT INTO voter_records",
        "INSERT INTO voter_records",
    ]

    assert [query.split(" (")[0] for query in inserts] == expected_order
    assert all("ON CONFLICT" in query and "DO UPDATE" in query for query in inserts)
    assert any("quality_summary" in query and "%s::jsonb" in query for query in inserts)
