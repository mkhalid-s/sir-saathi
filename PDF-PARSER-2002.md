# 2002 Maharashtra Electoral Roll PDF Parser — Technical Documentation

> Created: 2026-04-11
> Parser: `pipeline/parse_2002.py`
> Validated: 367 PDFs, 431,257 records, **100% parse rate**

---

## 1. The Problem

2002 Maharashtra electoral rolls are scanned/generated PDFs using a legacy **VirgoD3** Devanagari font that maps Unicode Latin codepoints to Devanagari glyphs. When pdfplumber extracts text, it produces garbled Latin characters — not readable Devanagari or English.

Example: legacy VirgoD3 text is extracted as Latin-looking characters and must be decoded before display or search.

## 2. Font Encoding: VirgoD3 Markers

The parser does NOT attempt full transliteration. Instead it uses **structural markers** — encoded character sequences that reliably identify record components:

| Marker | Encoded | Meaning |
|--------|---------|---------|
| Relation: husband (पती) | `{É` | Prefixes husband's name |
| Relation: father (वडील) | `´É` | Prefixes father's name |
| Gender: male (पुरुष) | `{ÉÖ` | Male voter |
| Gender: female (स्त्री) | `ºjÉÒ` | Female voter |
| EPIC format | `MT/DD/AAA/NNNNNNN` | Maharashtra voter ID |

### Bold Section Headers
PDF renders bold text by printing each character 4x. Detected via `re.search(r'(.)\1{3,}', line)` and decoded via `re.sub(r'(.)\1{3}', r'\1', text)`.

## 3. Structural Detection (No Hardcoded Content)

The parser is **content-agnostic** — it identifies voter records by their structural signature, not by matching specific names, addresses, or header text. This makes it work across any AC, district, or polling station in Maharashtra (using the VirgoD3 font).

### Voter Line Pattern
```
<serial 1-4 digits> <house_number> <voter_name> <relation_marker> <relative_name> <gender_marker> <age> [<EPIC>]
```

The `GENDER_ANCHOR` regex anchors on the gender marker + age at the end of line:
```python
GENDER_ANCHOR = re.compile(
    r'(\{ÉÖ|ºjÉÒ)\s+(-?\d{1,4})'    # gender + age
    r'(?:\s+MT/\d{2}/\d{3}/.+)?'       # optional EPIC (any format)
    r'\s*$'
)
```

### Section Header Detection
Bold-repeated lines that start with a number but do NOT contain a gender+age pattern.

### Page 1 Metadata Extraction
Label-based search (not fixed line numbers) extracts: state, AC, part number, PC, revision year, dates, taluka, district, polling station, pincode, voter counts.

## 4. Edge Cases Handled

These were discovered during validation across all 367 Trombay PDFs:

### 4.1 Age Field Anomalies
| Pattern | Count | Cause | Handling |
|---------|-------|-------|----------|
| Age = 0 | 343 | Missing data in source PDF | Parsed, flagged `missing_age` |
| Age = -1 | 36 | Placeholder in source PDF | Parsed, flagged `missing_age` |
| Age > 130 (e.g. 259, 320) | 36 | pdfplumber column misalignment | Parsed, flagged `corrupt_age` |
| Age < 17 | 55 | Possibly underage registration | Parsed, flagged `underage` |

### 4.2 EPIC Number Corruption
| Pattern | Example | Count | Cause |
|---------|---------|-------|-------|
| Split by space | `MT/00/000/000 000` | ~60 | pdfplumber table cell boundary |
| Garbled suffix | `MT/00/000/XXXXXÚÆ` | ~19 | Font encoding leak into digits |
| Dot prefix | `MT/00/000/.XXXXXX` | 1 | Extraction artifact |
| Dash prefix | `MT/00/000/-XXXXXX` | 1 | Extraction artifact |
| Split differently | `MT/00/000/XX XXXX` | 1 | Irregular space position |

All are captured as records; corrupted EPICs are stored empty (not garbage data).

### 4.3 Truncated Lines
| Pattern | Example | Count | Cause |
|---------|---------|-------|-------|
| Fragment only | `491 ´É {ÉÖ 1` | 7 | pdfplumber failed to extract full line |

These have serial + gender + age but no name. Stored with `data_quality: truncated_line`.

### 4.4 Missing Relation Markers
pdfplumber sometimes drops single-character table cells, losing the `{É`/`´É` relation marker. These records are parsed with `relation_type: unknown` and the voter+relative names combined.

## 5. Data Quality System

Every parsed record includes a `data_quality` field:

| Flag | Meaning | Downstream Action |
|------|---------|-------------------|
| `ok` | Clean record, all fields valid | Direct insert |
| `missing_age` | Age is 0 or -1 | Insert, flag for manual review |
| `corrupt_age` | Age > 130 (misaligned column) | Insert, set age=NULL |
| `underage` | Age < 17 | Insert, flag for verification |
| `truncated_line` | Name missing (pdfplumber failure) | Insert skeleton, flag for manual recovery from source PDF |

Multiple flags can be comma-separated: e.g. `truncated_line,missing_age`

## 6. Validation Results (Trombay AC 046)

```
Total PDFs:     367
Total Expected: 431,257
Total Parsed:   431,257
Parse Rate:     100.000000%

Quality Breakdown:
  ok:             430,786  (99.891%)
  missing_age:        379  (0.088%)
  underage:            55  (0.013%)
  corrupt_age:         36  (0.008%)
  truncated_line:       7  (0.002%)
```

## 7. Regional Font Variants

**CRITICAL**: The VirgoD3 parser only works for PDFs using the `IIDBFC+VirgoD3` font family. Other regions in Maharashtra use different fonts:

| Region | Font | Parser Status |
|--------|------|---------------|
| Mumbai Suburban (Trombay etc.) | VirgoD3 | **Working — 100%** |
| Pune (Junnar etc.) | CIDFont (different encoding) | **Not yet built** |
| Other districts | Unknown — needs sampling | **Not yet surveyed** |

### Auto-Detection Strategy
The orchestrator should read font metadata from page 1 via pdfplumber:
```python
page.chars[0]['fontname']  # e.g. 'IIDBFC+VirgoD3' or 'CIDFont+F1'
```
Route to the correct parser variant based on detected font.

### Queue Architecture (Production Design)

```
PDF arrives
  -> Font detection
  -> Route to parser variant
  -> Parse all pages
  -> Compare parsed count vs expected count (from metadata)
  -> If 100%: Done queue (insert to DB)
  -> If < 100%: Retry queue with failure details
     -> Retry with alternate extraction (e.g. different pdfplumber settings)
     -> If still < 100%: Manual review queue
```

Each parser variant handles its font's specific markers while sharing the structural detection logic (serial -> name -> gender+age -> EPIC).

## 8. Failure Root Causes (Resolved)

During development, the parser went through multiple iterations. These are the root causes found and fixed, documented for future variant development:

### Round 1: 0% parse rate
**Cause**: Regex used Unicode Devanagari characters (U+092A etc.) but PDF uses Latin-encoded VirgoD3 font.
**Fix**: Use actual encoded markers (`{É`, `´É`, `{ÉÖ`, `ºjÉÒ`).

### Round 2: ~95% parse rate (hardcoded skip lists)
**Cause**: Section headers and addresses were hardcoded — different per PDF.
**Fix**: Structural detection via GENDER_ANCHOR instead of content-based skip lists.

### Round 3: 99.86% parse rate (594 gap across 109 PDFs)
**Root Cause 1 — Age = 0** (306 records): Source PDF had literal `{ÉÖ 0` or `ºjÉÒ 0`. Sanity check `age < 17` rejected them.
**Root Cause 2 — Broken EPIC** (60 records): pdfplumber split the EPIC number (`MT/00/000/000 000`). End-of-line anchor failed.
**Root Cause 3 — Age = -1** (85 records): Source PDF had negative age placeholder. Regex `\d{1,3}` didn't match `-1`.

### Round 4: 99.999% parse rate (4 gap)
**Root Cause 4 — Garbled EPIC suffix** (4 records): Font encoding leaked into EPIC fields. EPIC regex was too strict.
**Fix**: Made EPIC matching fully permissive: `MT/\d{2}/\d{3}/.+`

### Round 5: 100.000000% (0 gap)
All edge cases handled. Every record has a `data_quality` flag for downstream processing.

## 9. Known Limitations

1. **No transliteration**: Output contains VirgoD3-encoded text, not readable Devanagari or English. A separate transliteration layer (IndicXlit or manual mapping) is needed for search/display.

2. **pdfplumber dependency**: 7 records (0.002%) are truncated because pdfplumber failed to extract complete text. Alternative extractors (PyMuPDF, Tabula) might recover these.

3. **Font variant coverage**: Only VirgoD3 is handled. Each new font variant needs its own marker mapping (~1 day of work per variant).

4. **Supplementary lists**: Sections II (additions) and III (deletions) on the last page are detected but not fully parsed — most are empty for 2002 Trombay rolls.

## 10. File Reference

| File | Purpose |
|------|---------|
| `pipeline/parse_2002.py` | Universal parser (VirgoD3 variant) |
| `data/trombay_2002_all_voters.json` | Local-only parsed voter export; do not commit raw voter data |
| `data/trombay_2002_pdfs/` | Local-only source PDFs; do not commit bulk roll data |
| `data/parsed/` | Local-only generated JSON/CSV outputs |
| `samples/validation/` | Local-only validation PDFs from multiple regions |
