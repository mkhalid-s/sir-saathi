import json

from pipeline.sir_saathi_pipeline.cross_year_matching import (
    MatchRecord,
    propose_matches,
    safe_match_report,
    score_candidate,
)


def record(record_id: str, *, year: int, name: str, relative: str, age: int, part: int = 21) -> MatchRecord:
    return MatchRecord(
        voter_record_id=record_id,
        state_id="IN-MH",
        ac_number=172,
        part_number=part,
        roll_year=year,
        name_normalized=name,
        name_phonetic=name,
        relative_name_normalized=relative,
        age=age,
        gender="F",
    )


def test_cross_year_score_uses_name_relative_age_gender_and_geography() -> None:
    base = record("base-1", year=2002, name="aasha paatil", relative="mohan paatil", age=20)
    current = record("current-1", year=2026, name="asha patil", relative="mohan patil", age=44)
    candidate = score_candidate(base, current)
    assert candidate is not None
    assert candidate.score >= 0.9
    assert candidate.same_part is True
    assert candidate.age_score == 1.0
    assert candidate.status == "proposed"


def test_cross_year_matching_is_ac_scoped_and_forward_only() -> None:
    base = record("base-1", year=2002, name="asha patil", relative="mohan patil", age=20)
    wrong_ac = MatchRecord(**{**record("current-1", year=2026, name="asha patil", relative="mohan patil", age=44).__dict__, "ac_number": 173})
    older = record("older", year=2001, name="asha patil", relative="mohan patil", age=19)
    assert score_candidate(base, wrong_ac) is None
    assert score_candidate(base, older) is None


def test_match_proposals_are_bounded_and_do_not_auto_confirm() -> None:
    bases = [
        record("base-1", year=2002, name="asha patil", relative="mohan patil", age=20),
        record("base-2", year=2002, name="asha patil", relative="mohan patil", age=20),
    ]
    current = [record("current-1", year=2026, name="asha patil", relative="mohan patil", age=44)]
    proposals = propose_matches(bases, current, max_candidates_per_current=1)
    assert len(proposals) == 1
    assert proposals[0].status == "proposed"


def test_placeholder_ages_do_not_contribute_to_match_score() -> None:
    base = record("base-1", year=2002, name="asha patil", relative="mohan patil", age=-1)
    current = record("current-1", year=2026, name="asha patil", relative="mohan patil", age=44)
    candidate = score_candidate(base, current)
    assert candidate is not None
    assert candidate.age_score == 0.0


def test_safe_match_report_contains_aggregates_not_record_ids_or_names() -> None:
    bases = [record("private-base-id", year=2002, name="private name", relative="relative", age=20)]
    current = [record("private-current-id", year=2026, name="private name", relative="relative", age=44)]
    report = safe_match_report(propose_matches(bases, current))
    encoded = json.dumps(report)
    assert report["safe_for_public"] is False
    assert report["proposal_count"] == 1
    assert "human review" in report["decision_boundary"]
    assert "private-base-id" not in encoded
    assert "private-current-id" not in encoded
    assert "private name" not in encoded
