from pipeline.sir_saathi_pipeline.forms_registry import load_forms_catalogue
from pipeline.sir_saathi_pipeline.parsers.maharashtra_2002 import parse_voter_line
from pipeline.sir_saathi_pipeline.sources import SourceManifest
from pipeline.sir_saathi_pipeline.transliteration import virgo_to_devanagari, virgo_to_english


def test_transliteration_package_exports_legacy_helpers() -> None:
    assert virgo_to_devanagari("¶ÉäJÉ") == "शेख"
    assert "she" in virgo_to_english("¶ÉäJÉ")


def test_maharashtra_2002_parser_adapter_parses_sanitized_line() -> None:
    record = parse_voter_line("12 H001 +É {É ¤É {ÉÖ 34")
    assert record is not None
    assert record["serial_number"] == 12
    assert record["house_number"] == "H001"
    assert record["relation_type"] == "husband"
    assert record["gender"] == "M"
    assert record["age"] == 34
    assert record["epic_number"] == ""
    assert record["data_quality"] == "ok"


def test_parser_flags_missing_age_without_rejecting_record() -> None:
    record = parse_voter_line("13 H002 +É ´É ¤É ºjÉÒ 0")
    assert record is not None
    assert record["gender"] == "F"
    assert record["data_quality"] == "missing_age"


def test_source_manifest_marks_local_inputs() -> None:
    manifest = SourceManifest(
        state_id="IN-MH",
        roll_year=2002,
        roll_kind="base_roll",
        source_uri="local://sanitized-fixture",
        local_path=None,
        parser_hint="maharashtra_2002_virgod3",
    )
    assert manifest.is_local_only is False


def test_forms_catalogue_loads_official_forms() -> None:
    catalogue = load_forms_catalogue()
    form_ids = {form.form_id for form in catalogue.forms}
    assert {"enumeration_form", "form_6", "form_7", "form_8"} == form_ids
    assert catalogue.common_documents["identity"] == ("Government-issued identity proof",)
