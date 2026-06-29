# Pipeline Refactor

The original CLI scripts remain available:

```sh
python pipeline/transliterate.py --test
python pipeline/parse_2002.py path/to/local-roll.pdf data/parsed
```

The same capabilities are now available through package imports:

```python
from pipeline.sir_saathi_pipeline.transliteration import virgo_to_devanagari
from pipeline.sir_saathi_pipeline.parsers.maharashtra_2002 import parse_voter_line
```

Raw PDFs and parsed outputs remain local-only under ignored paths. Tests use sanitized strings and do not commit voter records.
