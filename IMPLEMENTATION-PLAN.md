# SIR Saathi — Implementation Plan

> The complete blueprint to build the tool we envisioned.
> Start: Anushakti Nagar (Trombay), Mumbai Suburban
> Goal: A voter types their name and gets complete clarity — across all years, all rolls, with guidance on what to do next.

---

## The User Journey (What We're Building)

### Screen 1: Welcome
```
┌──────────────────────────────────────┐
│         🇮🇳 SIR Saathi               │
│    Your Voter Registration Guide     │
│                                      │
│  [मराठी]  [हिंदी]  [English]         │
│                                      │
│  ┌──────────────────────────────┐    │
│  │ 🔍 Search by Name            │    │
│  │    OR                        │    │
│  │ 🔍 Search by Voter ID (EPIC) │    │
│  └──────────────────────────────┘    │
│                                      │
│  Select your area:                   │
│  District: [Mumbai Suburban    ▼]    │
│  AC:       [172-Anushakti Nagar ▼]   │
│                                      │
│  Name: [________________]            │
│    OR                                │
│  EPIC:  [________________]           │
│                                      │
│         [ 🔍 SEARCH ]               │
│                                      │
│  Don't know your AC?                 │
│  [Search all of Maharashtra →]       │
└──────────────────────────────────────┘
```

**What happens on search:**
- If EPIC number → exact lookup across all years (instant)
- If name → fuzzy search within selected AC (or all MH if no AC selected)
- Search runs against: 2002 roll + 2024 roll + 2026 SIR roll (when available)

### Screen 2: Search Results
```
┌──────────────────────────────────────┐
│  Results for "Sample Voter"          │
│  in Anushakti Nagar (AC 172)         │
│                                      │
│  ┌────────────────────────────────┐  │
│  │ ✅ FOUND in 2002 Base Roll     │  │
│  │ Name: नमूना मतदाता            │  │
│  │ Part: 21 | Serial: 137         │  │
│  │ Age (2002): 47                 │  │
│  │ EPIC: MT/00/000/XXXXXXX        │  │
│  │ Address: [redacted]            │  │
│  │ Polling Stn: Sample polling    │  │
│  │              station           │  │
│  └────────────────────────────────┘  │
│                                      │
│  ┌────────────────────────────────┐  │
│  │ ✅ FOUND in 2024 Election Roll │  │
│  │ Name: Sample Voter             │  │
│  │ Part: 1 | Serial: ???          │  │
│  │ Age (2024): 69                 │  │
│  │ EPIC: XXX0000XXX               │  │
│  │ Polling Stn: Sample polling    │  │
│  │              station           │  │
│  └────────────────────────────────┘  │
│                                      │
│  ┌────────────────────────────────┐  │
│  │ ⏳ 2026 SIR Roll               │  │
│  │ Not yet published for          │  │
│  │ Maharashtra (Phase 3 starting) │  │
│  │                                │  │
│  │ [🔔 Notify me when available]  │  │
│  └────────────────────────────────┘  │
│                                      │
│  ┌────────────────────────────────┐  │
│  │ 📊 YOUR DETAILS COMPARISON     │  │
│  │                                │  │
│  │         2002        2024       │  │
│  │ Name:   नमूना       Sample     │  │
│  │         मतदाता      Voter      │  │
│  │ Age:    47          69  ✅     │  │
│  │ EPIC:   MT/00/000/  XXX...     │  │
│  │         XXXXXXX                │  │
│  │ AC:     046 Trombay → 172      │  │
│  │         Anushakti Nagar        │  │
│  │ Status: AC changed (merged)    │  │
│  │                                │  │
│  │ ⚠️ Note: Your AC changed from │  │
│  │ Trombay (046) to Anushakti    │  │
│  │ Nagar (172) due to 2008       │  │
│  │ delimitation. This is normal.  │  │
│  └────────────────────────────────┘  │
│                                      │
│  [ What should I do? → ]             │
└──────────────────────────────────────┘
```

### Screen 3: Guidance (Based on Their Situation)
```
┌──────────────────────────────────────┐
│  📋 What Should You Do?              │
│                                      │
│  Based on your records:              │
│                                      │
│  ✅ Your name is in the 2024 roll.   │
│  ✅ Your 2002 record exists.         │
│  ✅ Age matches across years.        │
│                                      │
│  When SIR 2026 happens for           │
│  Maharashtra:                        │
│                                      │
│  1. Your 2024 record will be         │
│     compared against your 2002       │
│     base record.                     │
│                                      │
│  2. Since your AC changed (Trombay   │
│     → Anushakti Nagar), ensure your  │
│     address is updated.              │
│                                      │
│  📝 RECOMMENDED ACTION:              │
│  ┌────────────────────────────────┐  │
│  │ File Form 8 (Correction) to    │  │
│  │ update your address if it has   │  │
│  │ changed since 2002.             │  │
│  │                                │  │
│  │ Documents needed:              │  │
│  │ ☐ Aadhaar Card                 │  │
│  │ ☐ Current address proof        │  │
│  │                                │  │
│  │ [📄 Fill Form 8 Online →]      │  │
│  │ [📍 Find nearest ERO office →] │  │
│  └────────────────────────────────┘  │
│                                      │
│  📞 Helpline: 1800-208-2026         │
│  🏢 Your ERO: Mumbai Suburban        │
│     District Election Office         │
└──────────────────────────────────────┘
```

### Screen 4: For Voters NOT Found
```
┌──────────────────────────────────────┐
│  ❌ Name Not Found                   │
│                                      │
│  We could not find "Xyz Abc" in      │
│  any electoral roll for              │
│  Anushakti Nagar (AC 172).           │
│                                      │
│  This could mean:                    │
│  • You may be registered in a        │
│    different AC                      │
│  • Your name may be spelled          │
│    differently in the records        │
│  • You may not be registered yet     │
│                                      │
│  TRY THESE:                          │
│  ┌────────────────────────────────┐  │
│  │ 1. [Search in nearby ACs →]    │  │
│  │    Chembur (173), Kurla (174)  │  │
│  │                                │  │
│  │ 2. [Search by EPIC number →]   │  │
│  │    If you have your voter ID   │  │
│  │                                │  │
│  │ 3. [Search with different      │  │
│  │    spelling →]                 │  │
│  │    Try: phonetic variations    │  │
│  │                                │  │
│  │ 4. [Register as new voter →]   │  │
│  │    File Form 6 online          │  │
│  └────────────────────────────────┘  │
│                                      │
│  💡 Did you know?                    │
│  During SIR, some names may be       │
│  temporarily under adjudication.     │
│  This doesn't mean you've been       │
│  deleted. [Learn more →]             │
└──────────────────────────────────────┘
```

---

## Complete Data Flow

```
┌─────────────────────────────────────────────────────┐
│                    DATA LAYER                        │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ 2002 PDFs│  │ 2024 PDFs│  │ ECI API Metadata │  │
│  │ (text)   │  │ (image)  │  │ (already have)   │  │
│  └────┬─────┘  └────┬─────┘  └────────┬─────────┘  │
│       │              │                 │             │
│       ▼              ▼                 │             │
│  ┌─────────┐  ┌──────────┐            │             │
│  │pdfplumber│  │PaddleOCR │            │             │
│  │ extract  │  │+ parsing │            │             │
│  └────┬─────┘  └────┬─────┘            │             │
│       │              │                 │             │
│       └──────┬───────┘                 │             │
│              ▼                         │             │
│  ┌───────────────────┐                 │             │
│  │  Normalize +      │                 │             │
│  │  Transliterate    │                 │             │
│  │  + Phonetic codes │                 │             │
│  └────────┬──────────┘                 │             │
│           ▼                            │             │
│  ┌────────────────────────────────┐    │             │
│  │        PostgreSQL              │◄───┘             │
│  │                                │                  │
│  │  voters_2002 (parsed voters)   │                  │
│  │  voters_2024 (parsed voters)   │                  │
│  │  voters_2026 (when available)  │                  │
│  │  polling_stations (API data)   │                  │
│  │  acs (API data)                │                  │
│  │  districts (API data)          │                  │
│  └────────────┬───────────────────┘                  │
│               │                                      │
└───────────────┼──────────────────────────────────────┘
                │
┌───────────────┼──────────────────────────────────────┐
│               ▼        API LAYER                     │
│  ┌────────────────────────────┐                      │
│  │     FastAPI Backend        │                      │
│  │                            │                      │
│  │  GET  /api/search          │ ← Name/EPIC search   │
│  │       ?name=sharma         │   across all years   │
│  │       &ac=172              │                      │
│  │       &type=fuzzy          │                      │
│  │                            │                      │
│  │  GET  /api/compare/{epic}  │ ← Compare across     │
│  │                            │   2002 vs 2024       │
│  │                            │                      │
│  │  GET  /api/guidance        │ ← What should I do?  │
│  │       ?situation=mismatch  │                      │
│  │                            │                      │
│  │  GET  /api/polling-station │ ← Find your booth    │
│  │       ?ac=172&part=1       │                      │
│  │                            │                      │
│  │  GET  /api/acs             │ ← Dropdown data      │
│  │  GET  /api/districts       │                      │
│  └────────────┬───────────────┘                      │
│               │                                      │
└───────────────┼──────────────────────────────────────┘
                │
┌───────────────┼──────────────────────────────────────┐
│               ▼       FRONTEND                       │
│  ┌────────────────────────────┐                      │
│  │     Next.js PWA            │                      │
│  │                            │                      │
│  │  / (home — search)         │                      │
│  │  /results (voter found)    │                      │
│  │  /compare (cross-year)     │                      │
│  │  /guide (what to do)       │                      │
│  │  /booth-finder             │                      │
│  │  /forms (form helper)      │                      │
│  │                            │                      │
│  │  i18n: Marathi, Hindi, En  │                      │
│  │  Mobile-first, PWA         │                      │
│  └────────────────────────────┘                      │
│                                                      │
│  Hosted: Cloudflare Pages (free)                     │
│  API: Oracle Cloud Free VM                           │
└──────────────────────────────────────────────────────┘
```

---

## Implementation Steps — In Order

### STEP 1: Parse the Data We Already Have (Day 1 Morning)

**1a. Parse 2002 Trombay PDF → structured data**

Input: `samples/trombay_2002_part21.pdf` (text-searchable, 739 voters)
Tool: pdfplumber + regex
Output: JSON/CSV with all 739 voter records

Fields to extract:
- serial_number
- house_number
- voter_name (Marathi)
- voter_name_roman (transliterated)
- voter_name_phonetic (soundex)
- relation_type (प→husband, व→father)
- relative_name
- gender (पु→M, स्त्री→F)
- age
- epic_number (MT/07/046/XXXXXXX)

**1b. Parse 2024 Anushakti Nagar PDF → structured data**

Input: `samples/2024-FC-EROLLGEN-S13-172-FinalRoll-Revision2-ENG-1-WI.pdf` (image-based, 977 voters)
Tool: PaddleOCR (or Ollama + GLM-OCR)
Output: JSON/CSV with all 977 voter records

Fields to extract:
- serial_number
- name (English)
- name_phonetic (soundex)
- father_or_husband_name
- relation_type
- house_number
- age
- gender
- epic_number (NCT format)
- section_name

**1c. Load ECI API metadata into database**

Input: Our already-downloaded JSON files
- all_states.json
- mh_districts.json
- mh_all_acs.json
- mh_all_polling_stations.json

### STEP 2: Set Up Database (Day 1 Afternoon)

PostgreSQL with:
- `voters` table (universal schema, partitioned by state_code + ac_number)
- `polling_stations` table (from API metadata)
- `acs` table
- `districts` table
- pg_trgm extension for fuzzy search
- Indexes on name_roman, name_phonetic, epic_number

Insert:
- 739 voters from 2002 Trombay
- 977 voters from 2024 Anushakti Nagar Part 1
- 100,253 polling stations from API
- 288 ACs
- 36 districts

### STEP 3: Build Search API (Day 2 Morning)

FastAPI with these endpoints:

```python
# Search by name (fuzzy, across all years)
GET /api/search?name=sample+voter&ac=172
→ Returns matches from 2002 AND 2024, ranked by similarity

# Search by EPIC (exact, across all years)
GET /api/search?epic=EPIC_PLACEHOLDER
→ Returns exact match from whichever year has it

# Compare a voter across years
GET /api/compare?epic=EPIC_PLACEHOLDER
→ Returns: {2002: {...}, 2024: {...}, differences: [...]}

# Get guidance based on situation
GET /api/guidance?found_2002=true&found_2024=true&ac_changed=true
→ Returns: recommended actions, forms, documents

# Dropdown data
GET /api/districts
GET /api/acs?district=Mumbai+Suburban
GET /api/polling-stations?ac=172
```

### STEP 4: Build Frontend (Day 2 Afternoon + Day 3)

Next.js with these pages:

```
/                    → Search page (Screen 1 above)
/results?q=...       → Results page (Screen 2)
/compare?epic=...    → Cross-year comparison
/guide?situation=... → Guidance page (Screen 3)
/not-found          → Help for not-found (Screen 4)
/booth-finder       → Find your polling station
```

i18n with Marathi, Hindi, English from day 1.
Mobile-first CSS. PWA enabled.

### STEP 5: Deploy (Day 3)

- Frontend → Cloudflare Pages (free)
- Backend API + PostgreSQL → Oracle Cloud Free VM (or even Railway free tier for faster setup)
- Domain → sirsaathi.in (or use free subdomain initially)

### STEP 6: Expand Data (Days 4-7)

- Download more 2002 PDFs from CEO MH (Trombay area: all parts)
- OCR more 2024 PDFs (if user downloads from browser)
- Parse and add to database
- Each new PDF = more voters searchable

### STEP 7: Add Intelligence (Week 2)

- AI chatbot using Ollama (local, free) for Q&A
- "Why was my name deleted?" explainer
- Form pre-filler
- RTI template generator
- WhatsApp integration (future)

---

## What Makes This POWERFUL (Not Just a Directory)

| Feature | Why It's Different |
|---------|-------------------|
| **Cross-year search** | No other tool shows your 2002 AND 2024 records side by side |
| **Automatic comparison** | We tell you what changed, not just show raw data |
| **Guided action** | Based on YOUR specific situation, not generic advice |
| **Fuzzy + phonetic search** | Handles spelling variations across 24 years of records |
| **Transliteration** | Search in English, find Marathi records (and vice versa) |
| **Mobile-first + multilingual** | Works for the actual people who need it |
| **Explains SIR** | "Your AC changed due to delimitation — this is normal" |
| **Pre-fills forms** | Don't just tell people what form — fill it for them |

---

## File Structure of the App

```
sir-saathi/
├── app/                          # Next.js frontend
│   ├── page.tsx                  # Home/Search (Screen 1)
│   ├── results/page.tsx          # Results (Screen 2)
│   ├── compare/page.tsx          # Cross-year comparison
│   ├── guide/page.tsx            # Guidance (Screen 3)
│   ├── not-found/page.tsx        # Not found help (Screen 4)
│   ├── booth-finder/page.tsx     # Polling station finder
│   ├── components/
│   │   ├── SearchBox.tsx
│   │   ├── VoterCard.tsx         # Shows one voter record
│   │   ├── ComparisonTable.tsx   # Side-by-side years
│   │   ├── GuidanceWizard.tsx    # What should I do
│   │   ├── LanguageSwitcher.tsx
│   │   └── PollingStationMap.tsx
│   ├── i18n/
│   │   ├── en.json
│   │   ├── mr.json               # Marathi
│   │   └── hi.json               # Hindi
│   └── layout.tsx
│
├── api/                          # FastAPI backend
│   ├── main.py                   # FastAPI app
│   ├── search.py                 # Search logic (pg_trgm + phonetic)
│   ├── compare.py                # Cross-year comparison
│   ├── guidance.py               # Situation-based guidance engine
│   ├── models.py                 # Pydantic models
│   └── db.py                     # PostgreSQL connection
│
├── pipeline/                     # Data processing
│   ├── parse_2002.py             # Parser for 2002 text-searchable PDFs
│   ├── parse_2024.py             # Parser for 2024 image-based PDFs (OCR)
│   ├── normalize.py              # Transliteration + phonetic + universal format
│   ├── load_api_metadata.py      # Load ECI API data into DB
│   └── download_pdfs.py          # PDF downloader (CEO MH portal)
│
├── data/                         # Already have this
│   ├── api-metadata/
│   ├── opencity-csv/
│   └── github-tools/
│
├── samples/                      # Already have this
│   ├── trombay_2002_part21.pdf
│   └── 2024-FC-EROLLGEN-...pdf
│
├── sql/
│   ├── schema.sql                # Database schema
│   └── seed.sql                  # Initial data load
│
├── RESEARCH.md
├── FUNDING-AND-SCALING.md
├── TECHNICAL-ARCHITECTURE.md
├── DATA-SOURCES-AND-GAPS.md
└── IMPLEMENTATION-PLAN.md        # This file
```

---

## The Expansion Pattern

Once Anushakti Nagar works perfectly:

```
Week 1: Anushakti Nagar (AC 172) — 262 polling stations
        ↓ same pipeline, just more PDFs
Week 2: All Mumbai Suburban (26 ACs) — 7,574 stations
        ↓ same pipeline, just more PDFs
Week 3: All Mumbai (City + Suburban) — 36 ACs
        ↓ same pipeline
Week 4: Pune, Thane, Nagpur
        ↓ same pipeline
Month 2: All Maharashtra (288 ACs, 100K stations)
        ↓ add WB parser config
Month 3: West Bengal
        ↓ add more state configs
Month 6: All India
```

Each expansion is: download PDFs → parse → insert into same database → same search works.
The app code doesn't change. Only data grows.

---

## Start Point

STEP 1a: Parse the 2002 Trombay PDF.
We have pdfplumber installed. We have the PDF. We've seen the data structure.
This is the first concrete code to write.
