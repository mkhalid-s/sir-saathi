"""Parser adapters for state/year/source-specific roll formats."""

from .maharashtra_2002 import parse_pdf, parse_voter_line

__all__ = ["parse_pdf", "parse_voter_line"]
