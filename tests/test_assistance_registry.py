from datetime import date
import json

import pytest

from pipeline.sir_saathi_pipeline.assistance_registry import (
    DEFAULT_ASSISTANCE_PATH,
    assistance_freshness,
    load_assistance_catalogue,
    parse_assistance_catalogue,
)


def canonical_data() -> dict:
    return json.loads(DEFAULT_ASSISTANCE_PATH.read_text(encoding="utf-8"))


def test_canonical_assistance_catalogue_is_exact_and_official() -> None:
    catalogue = load_assistance_catalogue()
    assert {channel.channel_id for channel in catalogue.channels} == {"portal", "ceo_directory", "helpline", "email"}
    assert {source.url for source in catalogue.sources} == {
        "https://voters.eci.gov.in/", "https://www.eci.gov.in/contact-us",
        "https://www.eci.gov.in/ceo-contact-details",
    }
    assert all(source.max_age_days == 30 for source in catalogue.sources)
    assert all(channel.source_ids for channel in catalogue.channels)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda data: data["sources"][0].update(url="http://voters.eci.gov.in/"), "official ECI HTTPS"),
        (lambda data: data["channels"][0].update(href="https://example.org/"), "official ECI HTTPS"),
        (lambda data: data["channels"][1].update(href="https://www.eci.gov.in/"), "reviewed ECI URL"),
        (lambda data: data["channels"][2].update(href="tel:1800"), "reviewed 1950"),
        (lambda data: data["channels"][3].update(href="mailto:someone@example.org"), "reviewed ECI"),
        (lambda data: data["channels"][0].update(label_key="forms.title"), "translation keys"),
        (lambda data: data["channels"][0].update(source_ids=["missing"]), "unknown source"),
    ],
)
def test_assistance_catalogue_rejects_unreviewed_channels(mutate, message: str) -> None:
    data = canonical_data()
    mutate(data)
    with pytest.raises(ValueError, match=message):
        parse_assistance_catalogue(data)


def test_assistance_source_freshness_fails_closed() -> None:
    assert assistance_freshness(today=date(2026, 8, 1)) == {
        "ready": True,
        "source_count": 3,
        "oldest_age_days": 0,
        "stale_count": 0,
        "blockers": [],
        "values_redacted": True,
    }
    assert assistance_freshness(today=date(2026, 9, 1))["blockers"] == [
        "official_assistance.source_stale"
    ]
    assert assistance_freshness(today=date(2026, 7, 31))["blockers"] == [
        "official_assistance.source_date_in_future"
    ]


@pytest.mark.parametrize("field", ["sources", "channels"])
def test_assistance_catalogue_rejects_malformed_collections(field: str) -> None:
    data = canonical_data()
    data[field] = "not-a-list"
    with pytest.raises(ValueError):
        parse_assistance_catalogue(data)
