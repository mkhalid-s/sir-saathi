"""Maharashtra 2002 VirgoD3 parser adapter.

This module keeps the public import path stable while the legacy CLI remains at
`pipeline/parse_2002.py`.
"""

from __future__ import annotations

from pipeline.parse_2002 import (
    decode_bold,
    detect_section_header,
    extract_metadata_from_page1,
    has_bold_repeats,
    parse_pdf,
    parse_voter_line,
    save_results,
)

__all__ = [
    "decode_bold",
    "detect_section_header",
    "extract_metadata_from_page1",
    "has_bold_repeats",
    "parse_pdf",
    "parse_voter_line",
    "save_results",
]
