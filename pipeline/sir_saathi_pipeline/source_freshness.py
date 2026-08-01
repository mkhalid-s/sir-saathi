"""Deterministic freshness policy for public election-source metadata."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime
import json
from typing import Any
from zoneinfo import ZoneInfo

from .state_registry import DataSource, StateConfig, load_all_states

ACTIVE_PHASES = {
    "pre_enumeration",
    "enumeration_open",
    "pre_draft_publication",
    "claims_and_objections_open",
    "claims_disposal",
}
ACTIVE_MAX_AGE_DAYS = 7
INACTIVE_MAX_AGE_DAYS = 90
INDIA_TIME_ZONE = ZoneInfo("Asia/Kolkata")


@dataclass(frozen=True)
class SourceFreshness:
    state_id: str
    source_label: str
    last_verified: date
    age_days: int
    max_age_days: int

    @property
    def stale(self) -> bool:
        return self.age_days < 0 or self.age_days > self.max_age_days

    @property
    def expiring(self) -> bool:
        return not self.stale and self.age_days >= max(1, self.max_age_days - 2)

    def as_dict(self) -> dict[str, Any]:
        return {
            "state_id": self.state_id,
            "source_label": self.source_label,
            "last_verified": self.last_verified.isoformat(),
            "age_days": self.age_days,
            "max_age_days": self.max_age_days,
            "status": "invalid_future_date" if self.age_days < 0 else "stale" if self.stale else "expiring" if self.expiring else "fresh",
        }


def freshness_window_days(state: StateConfig, today: date) -> int:
    phase = state.schedule.status_on(today)
    if phase in ACTIVE_PHASES or state.schedule_provenance.confidence == "reported":
        return ACTIVE_MAX_AGE_DAYS
    return INACTIVE_MAX_AGE_DAYS


def assess_source(state: StateConfig, source: DataSource, today: date) -> SourceFreshness:
    return SourceFreshness(
        state_id=state.state_id,
        source_label=source.label,
        last_verified=source.last_verified,
        age_days=(today - source.last_verified).days,
        max_age_days=freshness_window_days(state, today),
    )


def build_freshness_report(*, today: date, states: dict[str, StateConfig] | None = None) -> dict[str, Any]:
    registry = states or load_all_states()
    findings = [
        assess_source(state, source, today)
        for state in registry.values()
        for source in state.official_sources
    ]
    stale = [finding.as_dict() for finding in findings if finding.stale]
    expiring = [finding.as_dict() for finding in findings if finding.expiring]
    return {
        "as_of": today.isoformat(),
        "policy": {
            "active_max_age_days": ACTIVE_MAX_AGE_DAYS,
            "inactive_max_age_days": INACTIVE_MAX_AGE_DAYS,
        },
        "jurisdiction_count": len(registry),
        "source_count": len(findings),
        "fresh_count": sum(not finding.stale and not finding.expiring for finding in findings),
        "expiring_count": len(expiring),
        "stale_count": len(stale),
        "ready": not stale,
        "expiring": expiring,
        "stale": stale,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Report official source freshness without voter data.")
    parser.add_argument(
        "--today",
        type=date.fromisoformat,
        default=datetime.now(INDIA_TIME_ZONE).date(),
        help="Policy date in YYYY-MM-DD; defaults to the current date in India.",
    )
    parser.add_argument("--fail-on-stale", action="store_true", help="Exit non-zero when any source is stale.")
    args = parser.parse_args(argv)
    report = build_freshness_report(today=args.today)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if args.fail_on_stale and not report["ready"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
