"""Source manifest models for local-only ingestion runs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

RollKind = Literal["base_roll", "current_roll", "draft_roll", "final_roll", "supplement", "deletion"]


@dataclass(frozen=True)
class SourceManifest:
    state_id: str
    roll_year: int
    roll_kind: RollKind
    source_uri: str
    local_path: Path | None = None
    parser_hint: str | None = None
    language: str | None = None

    @property
    def is_local_only(self) -> bool:
        return self.local_path is not None
