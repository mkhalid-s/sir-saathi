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
EXPECTED_CHANNELS = {"portal", "ceo_directory", "helpline", "email"}


@dataclass(frozen=True)
class AssistanceSource:
    source_id: str
    label: str
    url: str
    last_verified: date
    max_age_days: int


@dataclass(frozen=True)
class AssistanceChannel:
    channel_id: str
    kind: str
    href: str
    source_ids: tuple[str, ...]
    label_key: str
    description_key: str
    action_key: str


@dataclass(frozen=True)
class AssistanceCatalogue:
    sources: tuple[AssistanceSource, ...]
    channels: tuple[AssistanceChannel, ...]


def _required(data: dict[str, Any], key: str) -> Any:
    if key not in data:
        raise ValueError(f"missing required key: {key}")
    return data[key]


def _official_https_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and parsed.hostname in {"eci.gov.in", "www.eci.gov.in", "voters.eci.gov.in"}


def parse_assistance_catalogue(data: dict[str, Any]) -> AssistanceCatalogue:
    if not isinstance(data, dict) or data.get("schema_version") != 2:
        raise ValueError("official assistance schema_version must be 2")
    source_items = _required(data, "sources")
    if not isinstance(source_items, list) or not source_items:
        raise ValueError("official assistance sources must be a non-empty list")
    try:
        sources = tuple(
            AssistanceSource(
                source_id=str(_required(item, "source_id")).strip(),
                label=str(_required(item, "label")).strip(),
                url=str(_required(item, "url")).strip(),
                last_verified=date.fromisoformat(str(_required(item, "last_verified"))),
                max_age_days=int(_required(item, "max_age_days")),
            )
            for item in source_items
        )
    except (AttributeError, TypeError) as exc:
        raise ValueError("invalid official assistance source") from exc
    source_ids = {source.source_id for source in sources}
    if len(source_ids) != len(sources) or any(not source_id for source_id in source_ids):
        raise ValueError("official assistance source IDs must be unique and non-empty")
    for source in sources:
        if not source.label or not _official_https_url(source.url):
            raise ValueError("official assistance source must have a label and official ECI HTTPS URL")
        if not 1 <= source.max_age_days <= 90:
            raise ValueError("official assistance max_age_days must be between 1 and 90")

    channel_items = _required(data, "channels")
    if not isinstance(channel_items, list):
        raise ValueError("official assistance channels must be a list")
    try:
        channels = tuple(
            AssistanceChannel(
                channel_id=str(_required(item, "channel_id")),
                kind=str(_required(item, "kind")),
                href=str(_required(item, "href")),
                source_ids=tuple(str(value) for value in _required(item, "source_ids")),
                label_key=str(_required(item, "label_key")),
                description_key=str(_required(item, "description_key")),
                action_key=str(_required(item, "action_key")),
            )
            for item in channel_items
        )
    except (AttributeError, TypeError) as exc:
        raise ValueError("invalid official assistance channel") from exc
    if {channel.channel_id for channel in channels} != EXPECTED_CHANNELS or len(channels) != len(EXPECTED_CHANNELS):
        raise ValueError("official assistance must define portal, CEO directory, helpline, and email exactly once")
    expected_kinds = {"portal": "web", "ceo_directory": "web", "helpline": "phone", "email": "email"}
    for channel in channels:
        if channel.kind != expected_kinds[channel.channel_id]:
            raise ValueError(f"invalid assistance channel kind: {channel.channel_id}")
        if not channel.source_ids or len(set(channel.source_ids)) != len(channel.source_ids):
            raise ValueError(f"assistance channel sources must be unique and non-empty: {channel.channel_id}")
        if set(channel.source_ids) - source_ids:
            raise ValueError(f"assistance channel references an unknown source: {channel.channel_id}")
        if not all(key.startswith(f"assistance.{channel.channel_id}.") for key in (
            channel.label_key, channel.description_key, channel.action_key
        )):
            raise ValueError(f"invalid assistance translation keys: {channel.channel_id}")
    by_id = {channel.channel_id: channel for channel in channels}
    if not _official_https_url(by_id["portal"].href):
        raise ValueError("assistance portal must use an official ECI HTTPS URL")
    if by_id["ceo_directory"].href != "https://www.eci.gov.in/ceo-contact-details":
        raise ValueError("assistance CEO directory must use the reviewed ECI URL")
    if by_id["helpline"].href != "tel:1950":
        raise ValueError("assistance helpline must use the reviewed 1950 short code")
    if by_id["email"].href.casefold() != "mailto:complaints@eci.gov.in":
        raise ValueError("assistance email must use the reviewed ECI complaints address")
    return AssistanceCatalogue(sources=sources, channels=channels)


def load_assistance_catalogue(path: str | Path = DEFAULT_ASSISTANCE_PATH) -> AssistanceCatalogue:
    with Path(path).open(encoding="utf-8") as handle:
        return parse_assistance_catalogue(json.load(handle))


def assistance_freshness(*, today: date | None = None) -> dict[str, object]:
    catalogue = load_assistance_catalogue()
    effective_date = today or date.today()
    ages = [(effective_date - source.last_verified).days for source in catalogue.sources]
    blockers = []
    if any(age < 0 for age in ages):
        blockers.append("official_assistance.source_date_in_future")
    if any(age > source.max_age_days for age, source in zip(ages, catalogue.sources)):
        blockers.append("official_assistance.source_stale")
    return {
        "ready": not blockers,
        "source_count": len(catalogue.sources),
        "oldest_age_days": max(ages),
        "stale_count": sum(age > source.max_age_days for age, source in zip(ages, catalogue.sources)),
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
