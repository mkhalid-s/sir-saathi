"""Experimental Unicode Maharashtra current-roll parser.

The pure text parser is fixture-tested. PDF ingestion must remain disabled until
an authorized official sample validates its layout and record accounting.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

try:
    import pdfplumber
except ImportError:  # pragma: no cover
    pdfplumber = None

FIELD = re.compile(r"\s*\|\s*")
EPIC = re.compile(r"^[A-Z]{3}\d{7}$")


def _label_value(field: str, label: str) -> str | None:
    prefix = f"{label}:"
    return field[len(prefix):].strip() if field.casefold().startswith(prefix.casefold()) else None


def parse_voter_line(line: str) -> dict[str, Any] | None:
    fields = FIELD.split(line.strip())
    if len(fields) < 6 or not fields[0].isdigit():
        return None
    serial_number = int(fields[0])
    epic_number = fields[1].strip().upper()
    values: dict[str, str] = {}
    for field in fields[2:]:
        for label in ("Name", "Father", "Mother", "Husband", "Other", "House", "Age", "Gender"):
            value = _label_value(field, label)
            if value is not None:
                values[label.casefold()] = value
                break
    if not values.get("name") or not values.get("age") or not values.get("gender"):
        return None
    relation_type = next((label for label in ("father", "mother", "husband", "other") if values.get(label)), "unknown")
    issues: list[str] = []
    if epic_number and not EPIC.fullmatch(epic_number):
        issues.append("invalid_epic_format")
    try:
        age = int(values["age"])
    except ValueError:
        return None
    if age < 17 or age > 130:
        issues.append("implausible_age")
    gender_value = values["gender"].casefold()
    gender = {"male": "M", "female": "F", "third gender": "O", "other": "O"}.get(gender_value)
    if gender is None:
        issues.append("unknown_gender")
    return {
        "serial_number": serial_number,
        "house_number": values.get("house", ""),
        "voter_name": values["name"],
        "relation_type": relation_type,
        "relative_name": values.get(relation_type, ""),
        "gender": gender,
        "age": age,
        "epic_number": epic_number if EPIC.fullmatch(epic_number) else "",
        "data_quality": "ok" if not issues else ",".join(issues),
    }


def parse_text(text: str) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    def required_int(pattern: str, label: str) -> int:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            raise ValueError(f"current-roll text is missing {label}")
        return int(match.group(1))

    metadata = {
        "source_encoding": "unicode",
        "revision_year": required_int(r"Revision\s+Year\s*:\s*(\d{4})", "revision year"),
        "ac_number": required_int(r"Assembly\s+Constituency\s*:\s*(\d+)", "Assembly Constituency"),
        "part_number": required_int(r"Part\s+(?:No|Number)\s*:\s*(\d+)", "part number"),
    }
    total_match = re.search(r"Total\s+Electors\s*:\s*(\d+)", text, re.IGNORECASE)
    district_match = re.search(r"District\s*:\s*([^\n]+)", text, re.IGNORECASE)
    ac_name_match = re.search(r"Assembly\s+Constituency\s*:\s*\d+\s*-\s*([^\n]+)", text, re.IGNORECASE)
    metadata["total_voters"] = int(total_match.group(1)) if total_match else 0
    metadata["district_name"] = district_match.group(1).strip() if district_match else ""
    metadata["ac_name_encoded"] = ac_name_match.group(1).strip() if ac_name_match else f"AC {metadata['ac_number']}"
    voters: list[dict[str, Any]] = []
    failures: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not re.match(r"^\s*\d+\s*\|", line):
            continue
        record = parse_voter_line(line)
        if record is None:
            failures.append(f"line {line_number}: unparsed voter record")
        else:
            voters.append(record)
    if not metadata["total_voters"]:
        metadata["total_voters"] = len(voters)
    if metadata["total_voters"] != len(voters):
        failures.append(
            f"record count mismatch: expected {metadata['total_voters']}, parsed {len(voters)}"
        )
    return metadata, voters, failures


def parse_pdf(pdf_path: str | Path) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    if pdfplumber is None:
        raise RuntimeError("pdfplumber is required to parse current-roll PDFs")
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    return parse_text(text)
