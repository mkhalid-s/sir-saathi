"""Local-only, explainable cross-year candidate matching.

Matches are proposals for human review, never identity or eligibility decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Iterable


@dataclass(frozen=True)
class MatchRecord:
    voter_record_id: str
    state_id: str
    ac_number: int
    geography_scope: str
    part_number: int | None
    part_geography_scope: str | None
    roll_year: int
    name_normalized: str
    name_phonetic: str | None
    relative_name_normalized: str
    age: int | None
    gender: str | None


@dataclass(frozen=True)
class MatchCandidate:
    base_voter_record_id: str
    current_voter_record_id: str
    score: float
    name_score: float
    relative_score: float
    age_score: float
    gender_score: float
    same_part: bool
    status: str = "proposed"


def _similarity(left: str | None, right: str | None) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left.casefold(), right.casefold()).ratio()


def _name_similarity(base: MatchRecord, current: MatchRecord) -> float:
    return max(
        _similarity(base.name_normalized, current.name_normalized),
        _similarity(base.name_phonetic, current.name_normalized),
        _similarity(base.name_normalized, current.name_phonetic),
        _similarity(base.name_phonetic, current.name_phonetic),
    )


def _age_similarity(base: MatchRecord, current: MatchRecord) -> float:
    if base.age is None or current.age is None:
        return 0.0
    if not 17 <= base.age <= 130 or not 17 <= current.age <= 130:
        return 0.0
    expected_current_age = base.age + (current.roll_year - base.roll_year)
    difference = abs(current.age - expected_current_age)
    if difference <= 1:
        return 1.0
    if difference <= 3:
        return 0.7
    if difference <= 5:
        return 0.3
    return 0.0


def score_candidate(base: MatchRecord, current: MatchRecord) -> MatchCandidate | None:
    if (
        base.state_id != current.state_id
        or base.ac_number != current.ac_number
        or base.geography_scope != current.geography_scope
        or not base.geography_scope.startswith("reviewed:")
    ):
        return None
    if current.roll_year <= base.roll_year:
        return None
    name_score = _name_similarity(base, current)
    if name_score < 0.5:
        return None
    relative_score = _similarity(base.relative_name_normalized, current.relative_name_normalized)
    age_score = _age_similarity(base, current)
    gender_score = 1.0 if base.gender and base.gender == current.gender else 0.0
    same_part = bool(
        base.part_number is not None
        and current.part_number is not None
        and base.part_number == current.part_number
        and base.part_geography_scope is not None
        and base.part_geography_scope == current.part_geography_scope
        and base.part_geography_scope.startswith("reviewed:")
    )
    geography_bonus = 0.05 if same_part else 0.0
    score = min(
        1.0,
        0.55 * name_score
        + 0.2 * relative_score
        + 0.15 * age_score
        + 0.05 * gender_score
        + geography_bonus,
    )
    return MatchCandidate(
        base_voter_record_id=base.voter_record_id,
        current_voter_record_id=current.voter_record_id,
        score=round(score, 4),
        name_score=round(name_score, 4),
        relative_score=round(relative_score, 4),
        age_score=round(age_score, 4),
        gender_score=round(gender_score, 4),
        same_part=same_part,
    )


def propose_matches(
    base_records: Iterable[MatchRecord],
    current_records: Iterable[MatchRecord],
    *,
    threshold: float = 0.72,
    max_candidates_per_current: int = 3,
) -> list[MatchCandidate]:
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")
    if max_candidates_per_current < 1 or max_candidates_per_current > 10:
        raise ValueError("max_candidates_per_current must be between 1 and 10")
    bases = tuple(base_records)
    proposals: list[MatchCandidate] = []
    for current in current_records:
        candidates = [candidate for base in bases if (candidate := score_candidate(base, current)) is not None]
        candidates = [candidate for candidate in candidates if candidate.score >= threshold]
        candidates.sort(key=lambda candidate: (-candidate.score, candidate.base_voter_record_id))
        proposals.extend(candidates[:max_candidates_per_current])
    return proposals


def safe_match_report(candidates: Iterable[MatchCandidate]) -> dict[str, Any]:
    proposals = tuple(candidates)
    by_current: dict[str, list[MatchCandidate]] = {}
    for proposal in proposals:
        by_current.setdefault(proposal.current_voter_record_id, []).append(proposal)
    ambiguous = sum(
        len(options) > 1 and abs(options[0].score - options[1].score) < 0.08
        for options in by_current.values()
    )
    return {
        "local_only": True,
        "safe_for_public": False,
        "decision_boundary": "candidate proposals require human review and never determine voter eligibility",
        "proposal_count": len(proposals),
        "current_records_with_candidates": len(by_current),
        "ambiguous_current_records": ambiguous,
        "score_bands": {
            "high_0_90_plus": sum(proposal.score >= 0.9 for proposal in proposals),
            "review_0_80_to_0_89": sum(0.8 <= proposal.score < 0.9 for proposal in proposals),
            "weak_below_0_80": sum(proposal.score < 0.8 for proposal in proposals),
        },
    }
