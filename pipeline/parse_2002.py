#!/usr/bin/env python3
"""
Universal parser for 2002 Maharashtra Electoral Roll PDFs.

Design: STRUCTURAL detection — identifies voter records by their data pattern
(gender marker + age + optional EPIC), not by hardcoded header text.
Works across any AC, district, or polling station without modification.

Font encoding: These PDFs use a legacy font, not Unicode Devanagari.
pdfplumber extracts markers as:
  Relation: '{É' = husband (पती), '´É' = father (वडील)
  Gender:   '{ÉÖ' = male (पुरुष), 'ºjÉÒ' = female (स्त्री)
  EPIC:     MT/DD/AAA/NNNNNNN

Output: JSON + CSV with all extracted voter records + section/area metadata.
"""

import re
import json
import csv
import sys
from pathlib import Path

try:
    import pdfplumber
except ImportError:  # pragma: no cover - exercised only without optional dependency
    pdfplumber = None


# --- Structural markers (encoding-specific, not content-specific) ---

RELATION_MARKERS = {"{É": "husband", "´É": "father"}
GENDER_MARKERS = {"{ÉÖ": "M", "ºjÉÒ": "F"}
EPIC_RE = re.compile(r'MT/\d{2}/\d{3}/\d{7}')

# The structural signature of a voter line:
#   <digits> <token> <text> <gender_marker> <age> [<EPIC>]
# Gender marker is the key anchor — no other line type contains '{ÉÖ' or 'ºjÉÒ' followed by a number.
# Known edge cases in source PDFs:
#   - Age can be 0 (missing) or -1 (placeholder)
#   - Age can be >130 (pdfplumber column misalignment — corrupt but record is real)
#   - EPIC can be split by space: 'MT/07/046/000 360'
#   - EPIC can have garbled suffix: 'MT/07/046/20353ÚÆ' (font encoding leak)
GENDER_ANCHOR = re.compile(
    r'(\{ÉÖ|ºjÉÒ)\s+(-?\d{1,4})'  # gender + age (allow up to 4 digits for corrupt ages)
    r'(?:\s+MT/\d{2}/\d{3}/.+)?'  # EPIC (any chars after MT/DD/AAA/ — handles all corruption)
    r'\s*$'
)

# Relation marker (single token between spaces)
RELATION_SPLIT = re.compile(r'\s(\{É|´É)\s')


def has_bold_repeats(line):
    """True if line contains characters repeated 4+ times (bold rendering artifact)."""
    return bool(re.search(r'(.)\1{3,}', line))


def decode_bold(line):
    """De-duplicate bold-rendered text (each char printed 4x)."""
    return re.sub(r'(.)\1{3}', r'\1', line)


def parse_voter_line(line):
    """Try to parse a voter record from a text line using structural matching.

    Returns dict with voter fields, or None if line is not a voter record.
    The only requirement: line must contain a gender marker + age pattern at the end.
    No hardcoded addresses, polling station names, or header text.
    """
    line = line.strip()
    if not line:
        return None

    # STRUCTURAL GATE: must contain gender+age anchor near end
    gm = GENDER_ANCHOR.search(line)
    if not gm:
        return None

    # Must start with a serial number
    head = re.match(r'^(\d{1,4})\s+(\S+)\s+', line)
    if not head:
        return None

    serial = int(head.group(1))
    house = head.group(2)

    # Extract fields from the anchored end
    gender = GENDER_MARKERS[gm.group(1)]
    age = int(gm.group(2))

    # Flag invalid ages but don't reject the record — pdfplumber misalignment
    # can produce ages like 259, 320 (actually shifted house numbers)
    if age < -1 or age > 130:
        age = None  # Mark as corrupt — record is still valid

    # Extract EPIC if present (may be split by space: 'MT/07/046/000 360')
    epic = ""
    em = EPIC_RE.search(line, gm.start())
    if em:
        epic = em.group()
    else:
        em_broken = re.search(r'(MT/\d{2}/\d{3}/)(\d{3,4})\s+(\d{1,4})', line[gm.start():])
        if em_broken:
            digits = (em_broken.group(2) + em_broken.group(3)).zfill(7)
            epic = em_broken.group(1) + digits

    # Middle portion: everything between house_number and gender marker
    middle = line[head.end():gm.start()].strip()

    # Try to split middle on relation marker
    rm = RELATION_SPLIT.search(middle)
    if rm:
        voter_name = middle[:rm.start()].strip()
        relation = RELATION_MARKERS.get(rm.group(1), rm.group(1))
        relative_name = middle[rm.end():].strip()
    else:
        # No relation marker (dropped by pdfplumber) — store combined names
        voter_name = middle.strip()
        relation = "unknown"
        relative_name = ""

    if not voter_name:
        # Truncated line from pdfplumber — serial + gender + age exist but name is missing.
        # Still count as a record (for 100% accounting) with data_quality flag.
        voter_name = ""

    # Build quality flags for downstream validation/retry queues
    issues = []
    if not voter_name:
        issues.append("truncated_line")
    if age is None:
        issues.append("corrupt_age")
    elif age == 0 or age == -1:
        issues.append("missing_age")
    elif age < 17:
        issues.append("underage")

    return {
        "serial_number": serial,
        "house_number": house,
        "voter_name": voter_name,
        "relation_type": relation,
        "relative_name": relative_name,
        "gender": gender,
        "age": age,
        "epic_number": epic,
        "data_quality": "ok" if not issues else ",".join(issues),
    }


def detect_section_header(line):
    """Detect bold section/area headers. Returns (section_num, area_name) or None.

    These lines have each character repeated 4x (bold artifact) and do NOT
    contain a gender+age pattern. Structural detection, no hardcoded text.
    """
    if not has_bold_repeats(line):
        return None
    # Must start with a number (section number)
    m = re.match(r'^(\d{1,3})\s+', line)
    if not m:
        return None
    # Must NOT be a voter line (no gender+age at end)
    if GENDER_ANCHOR.search(line):
        return None

    section_num = int(m.group(1))
    area_decoded = decode_bold(line[m.end():].strip())
    return section_num, area_decoded


def extract_metadata_from_page1(pdf):
    """Extract ALL metadata from the cover page structurally.

    Page 1 is a fixed-layout form. Fields are extracted by line position
    and pattern — no hardcoded addresses or names. Everything that applies
    to every voter in this part is captured here.

    Fields extracted:
      - State code + name
      - AC number + name (encoded) + reservation status
      - Part number
      - PC number + name (encoded)
      - Revision year, type, qualification date, publication date
      - Part boundary description (area covered)
      - Village/City, Taluka, District (encoded)
      - Area type (urban/rural)
      - Polling station number, name, address, pincode
      - Polling station reservation + category
      - Voter counts (male, female, total)
      - Serial number range
    """
    text = pdf.pages[0].extract_text() or ""
    lines_raw = text.split('\n')
    # De-bold for reliable extraction
    lines = [decode_bold(l.strip()) for l in lines_raw]

    meta = {
        # Will be filled below — all from the PDF, nothing hardcoded
        "state_code": "",
        "state_name_encoded": "",
        "ac_number": 0,
        "ac_name_encoded": "",
        "ac_reservation_encoded": "",
        "part_number": 0,
        "pc_number": 0,
        "pc_name_encoded": "",
        "revision_year": 0,
        "revision_type_encoded": "",
        "qualification_date": "",
        "publication_date": "",
        "part_boundary_encoded": "",
        "village_city_encoded": "",
        "taluka_encoded": "",
        "district_encoded": "",
        "area_type_encoded": "",
        "polling_station_number": 0,
        "polling_station_name_encoded": "",
        "polling_station_address_encoded": "",
        "pincode": "",
        "station_reservation_encoded": "",
        "station_category_encoded": "",
        "serial_start": 0,
        "serial_end": 0,
        "male_voters": 0,
        "female_voters": 0,
        "total_voters": 0,
    }

    # Join all decoded lines into one searchable text
    full = "\n".join(lines)

    # === LABEL-BASED EXTRACTION (searches full text, not fixed line numbers) ===

    # State: "BºÉ NN" pattern
    m = re.search(r'BºÉ\s*(\d+)', full)
    if m:
        meta["state_code"] = "S" + m.group(1)
    m = re.search(r'BºÉ\s*\d+\)\s*(.+)', full)
    if m:
        meta["state_name_encoded"] = m.group(1).strip().split('\n')[0]

    # AC number + name: "NNN <ac_name_text> ªÉÉnùÒ" pattern
    m = re.search(r'xÉÉÆ´É\s+(\d{2,3})\s+(.+?)(?:\s+ªÉÉnùÒ|\s*$)', full, re.MULTILINE)
    if m and int(m.group(1)) < 300:
        meta["ac_number"] = int(m.group(1))
        meta["ac_name_encoded"] = m.group(2).strip()

    # AC reservation: "ÎºlÉiÉÒ <value>" (first occurrence)
    m = re.search(r'ÎºlÉiÉÒ\s+(\S+)', full)
    if m:
        meta["ac_reservation_encoded"] = m.group(1).strip()

    # Part number: standalone "0NNN" on its own line
    m = re.search(r'^(0\d{3})$', full, re.MULTILINE)
    if m:
        meta["part_number"] = int(m.group(1))

    # PC number + name: 2-digit number at start of line after PC label
    m = re.search(r'±ÉÉäEòºÉ¦ÉÉ.*?:\s*\n\s*(\d{2})(.+)', full)
    if m:
        meta["pc_number"] = int(m.group(1))
        meta["pc_name_encoded"] = m.group(2).strip()

    # Revision year: "´É¹ÉÇ : YYYY"
    m = re.search(r'´É¹ÉÇ\s*:\s*(\d{4})', full)
    if m:
        meta["revision_year"] = int(m.group(1))

    # Revision type: "º´É¯õ{É : <type>"
    m = re.search(r'º´É¯õ{É\s*:\s*(.+)', full)
    if m:
        meta["revision_type_encoded"] = m.group(1).strip()

    # Dates: DD/MM/YYYY patterns
    dates = re.findall(r'(\d{2}/\d{2}/\d{4})', full)
    if len(dates) >= 1:
        meta["qualification_date"] = dates[0]
    if len(dates) >= 2:
        meta["publication_date"] = dates[1]

    # Taluka: "iÉÉ±ÉÖEòÉ <value>"
    m = re.search(r'iÉÉ±ÉÖEòÉ\s+(.+)', full)
    if m:
        meta["taluka_encoded"] = m.group(1).strip().split('\n')[0]

    # District: "ÊVÉ±½øÉ <value>"
    m = re.search(r'ÊVÉ±½øÉ\s+(.+)', full)
    if m:
        meta["district_encoded"] = m.group(1).strip().split('\n')[0]

    # Village/City: "¶É½ø®ô<value>" (after "MÉÉÆ´É/¶É½ø®ô" label)
    m = re.search(r'¶É½ø®ô(.+)', full)
    if m:
        meta["village_city_encoded"] = m.group(1).strip().split('\n')[0]

    # Area type: "¶É½ø®Ò" (urban) near classification label "´ÉMÉÔEò®ôhÉ"
    classification_block = re.search(r'´ÉMÉÔEò®ôhÉ.*?(?:3\.|¨ÉiÉnùÉxÉ EåòpùÉSÉÉ)', full, re.DOTALL)
    if classification_block:
        block = classification_block.group()
        if "¶É½ø®Ò" in block:
            meta["area_type_encoded"] = "¶É½ø®Ò"  # Urban
        elif "OÉÉ¨ÉÒhÉ" in block:
            meta["area_type_encoded"] = "OÉÉ¨ÉÒhÉ"  # Rural

    # Polling station number + name: "xÉÉÆ´É : NNN <name>" (after "Eåòpù +xÉÖGò¨ÉÉÆEò")
    m = re.search(r'Eåòpù\s+.xÉÖGò¨ÉÉÆEò.*?:\s*(\d+)\s+(.+?)(?:\s+¨ÉÚ³÷|\n)', full)
    if m:
        meta["polling_station_number"] = int(m.group(1))
        meta["polling_station_name_encoded"] = m.group(2).strip()

    # Polling station address: lines after "{ÉkÉÉ :" label until "¨ÉÆbý³÷" (mandal)
    m = re.search(r'{ÉkÉÉ\s*:\s*(.+?)(?:¨ÉÆbý³÷|iÉÉ±ÉÖEòÉ)', full, re.DOTALL)
    if m:
        addr_block = m.group(1).strip()
        # Clean up: remove line labels like "ºÉVÉÉ" (saja)
        addr_lines = [l.strip() for l in addr_block.split('\n')
                       if l.strip() and l.strip() != "ºÉVÉÉ"]
        meta["polling_station_address_encoded"] = " ".join(addr_lines)

    # Pincode: 6-digit number starting with 4 (Mumbai) — search page 1 first
    pin_m = re.search(r'(4\d{5})', full)
    if pin_m:
        meta["pincode"] = pin_m.group(1)

    # Pincode fallback: search data page 2 header (section address often has pincode)
    if not meta["pincode"] and len(pdf.pages) > 1:
        p2_text = decode_bold(pdf.pages[1].extract_text() or "")
        pin_m2 = re.search(r'(4\d{5})', p2_text)
        if pin_m2:
            meta["pincode"] = pin_m2.group(1)

    # Part boundary description: text between the boundary label and "¨ÉÚ³÷ MÉÉÆ´É"
    m = re.search(r'iÉ{É¶ÉÒ±É\s+(.+?)¨ÉÚ³÷\s+MÉÉÆ´É', full, re.DOTALL)
    if m:
        meta["part_boundary_encoded"] = " ".join(m.group(1).strip().split())

    # === VOTER COUNTS (from page 1 table or last page summary) ===
    last_text = decode_bold(pdf.pages[-1].extract_text() or "")
    for t in [full, last_text]:
        # Pattern: "1 NNN NNN NNN NNN" (start, end, male, female, total)
        counts = re.findall(r'(\d{1,4})\s+(\d{2,4})\s+(\d{2,4})\s+(\d{2,4})\s+(\d{2,4})', t)
        for start, end, m_count, f_count, total in counts:
            s, e, mi, fi, ti = int(start), int(end), int(m_count), int(f_count), int(total)
            if mi + fi == ti and ti > 50 and s == 1:
                meta["serial_start"] = s
                meta["serial_end"] = e
                meta["male_voters"] = mi
                meta["female_voters"] = fi
                meta["total_voters"] = ti
                break
        if meta["total_voters"] > 0:
            break

    # Fallback: simpler 3-number pattern
    if meta["total_voters"] == 0:
        for t in [full, last_text]:
            for mc, fc, tc in re.findall(r'(\d{2,4})\s+(\d{2,4})\s+(\d{2,4})', t):
                mi, fi, ti = int(mc), int(fc), int(tc)
                if mi + fi == ti and ti > 50:
                    meta["male_voters"] = mi
                    meta["female_voters"] = fi
                    meta["total_voters"] = ti
                    break

    return meta


def parse_pdf(pdf_path):
    """Parse a 2002 MH electoral roll PDF. Returns (metadata, voters, failures)."""
    if pdfplumber is None:
        raise RuntimeError("pdfplumber required: pip install pdfplumber")
    pdf = pdfplumber.open(pdf_path)
    metadata = extract_metadata_from_page1(pdf)
    voters = []
    seen_serials = set()
    failures = []
    current_section = 0
    current_section_name = ""
    sections = {}

    # Data pages: skip page 1 (cover) and last page (summary)
    for page in pdf.pages[1:-1]:
        text = page.extract_text()
        if not text:
            continue

        for line in text.split('\n'):
            stripped = line.strip()
            if not stripped:
                continue

            # 1. Try section header detection (bold repeated chars, no gender marker)
            sec = detect_section_header(stripped)
            if sec:
                current_section, current_section_name = sec
                sections[current_section] = current_section_name
                continue

            # 2. Try voter record detection (structural: gender+age anchor)
            record = parse_voter_line(stripped)
            if record:
                record["section_number"] = current_section
                record["section_name"] = current_section_name
                if record["serial_number"] not in seen_serials:
                    seen_serials.add(record["serial_number"])
                    voters.append(record)

            # Everything else (page headers, column labels, footers, addresses)
            # is silently skipped — no hardcoded list needed.

    pdf.close()

    metadata["sections"] = sections

    # Enrich records
    for v in voters:
        v["state_code"] = metadata["state_code"]
        v["ac_number"] = metadata["ac_number"]
        v["part_number"] = metadata["part_number"]
        v["year"] = metadata["revision_year"]

    return metadata, voters, failures


def save_results(metadata, voters, output_dir):
    """Save parsed results as JSON and CSV."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    ac = metadata["ac_number"]
    part = metadata["part_number"]
    prefix = "ac%03d_part%03d_%d" % (ac, part, metadata["revision_year"])

    # JSON
    json_path = out / (prefix + ".json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({
            "metadata": metadata,
            "voters": voters,
            "total_parsed": len(voters),
        }, f, ensure_ascii=False, indent=2)
    print("JSON: %s (%d voters)" % (json_path, len(voters)))

    # CSV
    csv_path = out / (prefix + ".csv")
    if voters:
        fields = [
            "serial_number", "section_number", "section_name", "house_number",
            "voter_name", "relation_type", "relative_name",
            "gender", "age", "epic_number",
            "state_code", "ac_number", "part_number", "year",
        ]
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(voters)
        print("CSV:  %s" % csv_path)

    return json_path, csv_path


def main():
    project_root = Path(__file__).resolve().parents[1]
    pdf_path = Path(sys.argv[1]) if len(sys.argv) > 1 else \
        project_root / "samples" / "trombay_2002_part21.pdf"
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else \
        project_root / "data" / "parsed"

    print("Parsing: %s" % pdf_path)
    metadata, voters, failures = parse_pdf(pdf_path)

    parsed = len(voters)
    total = metadata["total_voters"] or parsed
    males = sum(1 for v in voters if v["gender"] == "M")
    females = sum(1 for v in voters if v["gender"] == "F")
    with_epic = sum(1 for v in voters if v["epic_number"])
    ages = [v["age"] for v in voters]
    sections = metadata.get("sections", {})

    print("\n" + "=" * 50)
    print("AC: %d, Part: %d" % (metadata["ac_number"], metadata["part_number"]))
    print("Parsed:   %d%s" % (parsed, ("/%d (%.1f%%)" % (total, parsed/total*100)) if total else ""))
    print("Gender:   %d M / %d F" % (males, females))
    if parsed > 0:
        print("EPIC:     %d/%d (%.1f%%)" % (with_epic, parsed, with_epic/parsed*100))
    if ages:
        print("Age:      %d-%d, avg %.1f" % (min(ages), max(ages), sum(ages)/len(ages)))
    print("Sections: %d areas detected" % len(sections))

    if voters:
        print("\nSample records:")
        for v in voters[:5]:
            print("  #%3d %-8s %-30s %-7s %-20s %s %2d %s" % (
                v["serial_number"], v["house_number"],
                v["voter_name"][:30], v["relation_type"],
                v["relative_name"][:20], v["gender"], v["age"],
                v["epic_number"]))

    save_results(metadata, voters, output_dir)


if __name__ == "__main__":
    main()
