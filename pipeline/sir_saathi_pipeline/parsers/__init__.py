"""Parser adapters for state/year/source-specific roll formats."""

from .maharashtra_2002 import parse_pdf, parse_voter_line
from .registry import PARSERS, ParserSpec, parser_spec, validate_parser_scope

__all__ = ["PARSERS", "ParserSpec", "parse_pdf", "parse_voter_line", "parser_spec", "validate_parser_scope"]
