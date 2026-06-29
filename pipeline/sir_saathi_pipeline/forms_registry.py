"""Typed loader for public SIR action forms and common documents."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FORMS_PATH = ROOT / "config" / "forms" / "sir-actions.json"


@dataclass(frozen=True)
class FormConfig:
    form_id: str
    label: str
    purpose: str
    official_portal: str


@dataclass(frozen=True)
class FormsCatalogue:
    forms: tuple[FormConfig, ...]
    common_documents: dict[str, tuple[str, ...]]


def _require(data: dict[str, Any], key: str) -> Any:
    if key not in data:
        raise ValueError(f"missing required key: {key}")
    return data[key]


def parse_forms_catalogue(data: dict[str, Any]) -> FormsCatalogue:
    forms_raw = _require(data, "forms")
    common_documents_raw = _require(data, "common_documents")
    forms = tuple(
        FormConfig(
            form_id=form_id,
            label=_require(form_data, "label"),
            purpose=_require(form_data, "purpose"),
            official_portal=_require(form_data, "official_portal"),
        )
        for form_id, form_data in sorted(forms_raw.items())
    )
    common_documents = {
        category: tuple(str(item) for item in documents)
        for category, documents in sorted(common_documents_raw.items())
    }
    return FormsCatalogue(forms=forms, common_documents=common_documents)


def load_forms_catalogue(path: str | Path = DEFAULT_FORMS_PATH) -> FormsCatalogue:
    catalogue_path = Path(path)
    with catalogue_path.open(encoding="utf-8") as handle:
        return parse_forms_catalogue(json.load(handle))
