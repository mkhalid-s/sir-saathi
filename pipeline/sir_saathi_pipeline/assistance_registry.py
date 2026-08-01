"""Governed nationwide official voter-assistance channels."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ASSISTANCE_PATH = ROOT / "config" / "official-assistance.json"
EXPECTED_CHANNELS = {"portal", "helpline", "email"}


@dataclass(frozen=True)
class AssistanceSource:
    label: str
    url: str
    last_verified: date
    max_age_days: int


@dataclass(frozen=True)
class AssistanceChannel:
    channel_id: str
    kind: str
    href: str
    label_key: str
    description_key: str
    action_key: str


@dataclass(frozen=True)
class AssistanceCatalogue:
    source: AssistanceSource
    channels: tuple[AssistanceChannel, ...]


def _required(data: dict[str, Any], key: str) -> Any:
    if key not in data:
        raise ValueError(f"missing required key: {key}")
    return data[key]


def _official_https_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and parsed.hostname in {"eci.gov.in", "www.eci.gov.in", "voters.eci.gov.in"}


def parse_assistance_catalogue(data: dict[str, Any]) -> AssistanceCatalogue:
    if data.get("schema_version") != 1:
        raise ValueError("official assistance schema_version must be 1")
    source_raw = _required(data, "source")
    source = AssistanceSource(
        label=str(_required(source_raw, "label")).strip(),
        url=str(_required(source_raw, "url")).strip(),
        last_verified=date.fromisoformat(str(_required(source_raw, "last_verified"))),
        max_age_days=int(_required(source_raw, "max_age_days")),
    )
    if not source.label or not _official_https_url(source.url):
        raise ValueError("official assistance source must have a label and official ECI HTTPS URL")
    if not 1 <= source.max_age_days <= 90:
        raise ValueError("official assistance max_age_days must be between 1 and 90")

    channels = tuple(
        AssistanceChannel(
            channel_id=str(_required(item, "channel_id")),
            kind=str(_required(item, "kind")),
            href=str(_required(item, "href")),
            label_key=str(_required(item, "label_key")),
            description_key=str(_required(item, "description_key")),
            action_key=str(_required(item, "action_key")),
        )
        for item in _required(data, "channels")
    )
    if {channel.channel_id for channel in channels} != EXPECTED_CHANNELS or len(channels) != len(EXPECTED_CHANNELS):
        raise ValueError("official assistance must define portal, helpline, and email exactly once")
    expected_kinds = {"portal": "web", "helpline": "phone", "email": "email"}
    for channel in channels:
        if channel.kind != expected_kinds[channel.channel_id]:
            raise ValueError(f"invalid assistance channel kind: {channel.channel_id}")
        if not all(key.startswith(f"assistance.{channel.channel_id}.") for key in (
            channel.label_key, channel.description_key, channel.action_key
        )):
            raise ValueError(f"invalid assistance translation keys: {channel.channel_id}")
    by_id = {channel.channel_id: channel for channel in channels}
    if not _official_https_url(by_id["portal"].href):
        raise ValueError("assistance portal must use an official ECI HTTPS URL")
    if by_id["helpline"].href != "tel:1950":
        raise ValueError("assistance helpline must use the reviewed 1950 short code")
    if by_id["email"].href.casefold() != "mailto:complaints@eci.gov.in":
        raise ValueError("assistance email must use the reviewed ECI complaints address")
    return AssistanceCatalogue(source=source, channels=channels)


def load_assistance_catalogue(path: str | Path = DEFAULT_ASSISTANCE_PATH) -> AssistanceCatalogue:
    with Path(path).open(encoding="utf-8") as handle:
        return parse_assistance_catalogue(json.load(handle))


def assistance_freshness(*, today: date | None = None) -> dict[str, object]:
    catalogue = load_assistance_catalogue()
    effective_date = today or date.today()
    age_days = (effective_date - catalogue.source.last_verified).days
    blockers = []
    if age_days < 0:
        blockers.append("official_assistance.source_date_in_future")
    elif age_days > catalogue.source.max_age_days:
        blockers.append("official_assistance.source_stale")
    return {
        "ready": not blockers,
        "source_count": 1,
        "age_days": age_days,
        "max_age_days": catalogue.source.max_age_days,
        "blockers": blockers,
        "values_redacted": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check official voter-assistance source freshness.")
    parser.add_argument("--fail-on-stale", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = assistance_freshness()
    except (OSError, ValueError):
        report = {"ready": False, "source_count": 0, "blockers": ["official_assistance.invalid"], "values_redacted": True}
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if args.fail_on_stale and not report["ready"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
