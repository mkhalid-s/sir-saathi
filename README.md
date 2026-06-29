# SIR Saathi

SIR Saathi is a civic-tech research and prototype repository for helping voters navigate India's Special Intensive Revision (SIR) process. The current work focuses on Maharashtra electoral roll research, PDF parsing, transliteration, and product planning.

## What is included

- Research notes on SIR data sources, extraction strategy, and product architecture.
- Python utilities for parsing 2002 Maharashtra electoral roll PDFs that use legacy VirgoD3 font encoding.
- A VirgoD3-to-Devanagari/Roman transliteration utility for search/display experiments.
- Public-safe documentation and implementation notes.

## What is not included

This repository intentionally does not commit raw electoral roll PDFs, parsed voter records, local generated outputs, credentials, or private configuration. Keep those files local under ignored paths such as `data/` and local sample PDF folders.

## Setup

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Usage

Run the transliteration smoke tests:

```sh
python pipeline/transliterate.py --test
```

Parse a local electoral roll PDF into a local output directory:

```sh
python pipeline/parse_2002.py path/to/local-roll.pdf data/parsed
```

The parser output is ignored by Git because it may contain voter records.

## Public Data And Privacy

Electoral rolls are public documents, but bulk voter data can still create privacy and misuse risks. Treat parsed exports, PDFs, full EPIC values, addresses, and generated datasets as local-only unless you have completed a separate legal/privacy review and redaction process.

## License

Code and documentation in this repository are released under the MIT License. See `LICENSE`.
