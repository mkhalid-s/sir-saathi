# SIR Saathi - Complete Research Report

> Compiled: 2026-04-09
> Scope: West Bengal + Maharashtra
> Purpose: Build a civic-tech tool to help voters navigate SIR (Special Intensive Revision)

**Related Documents:**
- [FUNDING-AND-SCALING.md](./FUNDING-AND-SCALING.md) — Funding sources, investment strategy, all-India scaling plan, action plan

---

## Part A: What is SIR & Why This Tool Matters

### What is SIR?

**SIR** stands for **Special Intensive Revision**, an exercise undertaken by the **Election Commission of India (ECI)** to ensure electoral rolls across India are accurate, up-to-date, and inclusive.

#### What it involves
- House-to-house verification of voters
- Addition of new eligible voters (especially first-time voters)
- Removal of ineligible, deceased, or duplicate entries
- Correction of voter details (name, address, photo, etc.)

#### Timeline
- Announced on **27 October 2025** by Chief Election Commissioner Gyanesh Kumar
- Phase 1: West Bengal, Assam (Oct-Nov 2025)
- Phase 2: 12 states/UTs including UP, MP, Gujarat, Rajasthan, Kerala, Tamil Nadu — covering **51+ crore voters** (Nov 2025-Feb 2026)
- Phase 3: Maharashtra + 21 remaining states/UTs (April 2026 onwards)

#### Why 2002 is the reference year
The 2002 electoral roll is the "Mother Roll" — the last complete from-scratch enumeration in most states. All subsequent revisions (2003-2025) were incremental. SIR 2026 compares current data against this 2002 base, flagging discrepancies.

Sources:
- https://en.wikipedia.org/wiki/Special_Intensive_Revision
- https://citizenmatters.in/sir-explained-what-every-voter-should-know/
- https://www.drishtiias.com/state-pcs-current-affairs/sir-20-to-begin-in-12-states-and-uts
- https://www.business-standard.com/india-news/sir-exercise-to-begin-in-12-states-union-territories-from-tuesday-125110300648_1.html

---

### The Problem

There is massive fuss and confusion for people living across India. Millions are unable to search/find their details, some have incorrect details, and for some details are different requiring corrections.

#### Validated Pain Points

| Pain Point | Scale |
|------------|-------|
| ~60 lakh names put on "doubtful voters" list in West Bengal alone | Millions affected |
| 27 lakh+ applications just to get names added back | Overwhelmed system |
| Booth realignment since 2003 — people can't find their polling station | Nationwide confusion |
| BLOs asking for different documents in different states | Trust breakdown |
| Multiple scattered portals — NVSP, ECI Electoral Search, Voter Portal, state CEO sites | Fragmented experience |
| Forms are confusing — Form 6, 7, 8, 8A — people don't know which to use | Complexity barrier |
| Language barriers — portals primarily in English/Hindi | Excludes millions |
| Maharashtra State Election Commission website went down during BMC elections | System failure |
| Hundreds of voter names missing from BMC rolls despite voting in recent elections | Data loss |
| Names showing in completely different wards online vs. actual booth | Data mismatch |

#### Maharashtra-Specific Issues
- Dual voter roll system (Assembly + Municipal) creates confusion — being on one doesn't mean you're on the other
- 29 Municipal Corporations + 232 Municipal Councils + 125 Nagar Panchayats — all separate rolls
- SIR Phase 3 starting April 2026 — imminent disruption
- Uddhav Thackeray publicly flagged widespread complaints of missing names across Mumbai
- Booth slips missing booth numbers in areas like Andheri, Borivali, Kalyan
- CEO Maharashtra helpline: 1800-208-2026

Sources:
- https://www.freepressjournal.in/mumbai/mumbai-bmc-elections-2026-maharashtra-state-election-commission-website-down-citizens-unable-to-check-name-in-voters-list-generate-polling-slips
- https://www.outlookindia.com/elections/hundreds-of-voter-names-missing-from-bmc-electoral-rolls
- https://www.india.com/news/india/west-bengal-voter-list-row-27-lakh-voters-rejected-doubtful-voters-list-election-commission-india-assembly-elections-2026-mamata-banerjee-politics-8371258/
- https://pucl.org/manage-writings/designed-to-exclude-the-ongoing-enumeration-phase-of-the-sir/

---

### The Solution: SIR Saathi (SIR Companion)

A single, mobile-first, multilingual platform that removes all friction from the SIR process.

#### Core Features

**1. Universal Voter Search**
- One search box across ECI electoral rolls
- Smart matching (handles spelling variations, transliteration issues)
- Shows exactly which booth, constituency, and ward you belong to

**2. AI-Powered Situation Guide ("What should I do?")**
- User answers 3-4 simple questions
- System tells them: which form, what documents, where to go, what deadline
- Covers: new registration, name correction, address change, deletion dispute, shifted constituency, NRI voting

**3. Smart Document Checklist Generator**
- Based on situation + state = exact documents needed
- Accounts for state-level BLO variations
- Shows alternatives ("If no Aadhaar, use X, Y, or Z")

**4. Form Pre-filler & Guide**
- Step-by-step walkthrough of Form 6/7/8/8A in simple language
- Pre-fills fields, generates print-ready PDF or NVSP submission link

**5. Status Tracker**
- Track application status from one place
- Push notifications on WhatsApp/SMS

**6. Polling Booth & BLO Locator**
- Map-based nearest polling booth, ERO office, voter help center
- BLO contact details

**7. Multilingual Support (Day 1)**
- Hindi, Bengali, Tamil, Telugu, Malayalam, Kannada, Marathi, Gujarati, Odia, Assamese, Urdu, Punjabi
- Voice input support

**8. AI Chatbot (in local languages)**
- Powered by Claude API
- Answers questions like "Mera naam voter list mein nahi hai, kya karoon?"
- Available via Web, WhatsApp, Telegram

#### What Makes This Different From Existing Portals

| Existing (ECI/NVSP) | SIR Saathi |
|----------------------|------------|
| Multiple portals, no single entry point | One platform, one search |
| English/Hindi only | 12+ Indian languages + voice |
| Assumes you know which form to use | Asks simple questions, tells you what to do |
| No guidance on documents | State-specific document checklists |
| Web-only, not mobile-optimized | PWA + WhatsApp + Telegram |
| No AI assistance | Conversational AI in local languages |
| No proactive notifications | SMS/WhatsApp alerts on deadlines & status |
| Assembly rolls only | Assembly + Municipal dual roll check (MH) |

#### Impact Potential
- 51+ crore voters covered under SIR 2026
- Targets the most vulnerable: rural, elderly, first-time voters, minorities
- Could be the difference between someone voting or being disenfranchised

#### Existing Government Portals (Fragmented)

| Portal | URL | Purpose |
|--------|-----|---------|
| NVSP | www.nvsp.in | National voter services |
| ECI Electoral Search | electoralsearch.eci.gov.in | Voter search by details/EPIC |
| ECI Voters Portal | voters.eci.gov.in | Electoral roll download |
| Voter Portal App | voterportal.eci.gov.in | Mobile voter services |
| CEO West Bengal | ceowestbengal.wb.gov.in | WB state portal |
| CEO Maharashtra | ceo.maharashtra.gov.in | MH state portal |
| CEO Election MH | ceoelection.maharashtra.gov.in | MH operational portal |
| MH Local Body Lists | localbodyvoterlist.maharashtra.gov.in | Municipal voter lists |
| BMC Election Data | electiondata.mcgm.gov.in | Mumbai municipal lists |

#### Required Documents for SIR Verification

**Identity Proof:** Aadhaar Card, PAN Card, Driving License, Passport, Class X Marksheet (with DOB), Birth Certificate

**Address Proof:** Aadhaar, Passport, Bank Passbook, Rent Agreement, Utility Bills

**For Specific Corrections:**
- Name change: Marriage certificate or gazette notification
- DOB correction: Birth certificate or school records

**Forms:**
- Form 6: New voter registration
- Form 7: Objection to inclusion (contest doubtful voter flag)
- Form 8: Correction of details
- Form 8A: Transposition of entry (moved within same constituency)

Processing timeline: 2-4 weeks for online submissions (2026)

Sources:
- https://www.nvsp.in/
- https://electoralsearch.eci.gov.in/
- https://voterportal.eci.gov.in/
- https://www.collegesimplified.in/post/documents-required-for-sir-voter-verification-in-india-complete-list-2026
- https://voterlist.co.in/what-is-sir-and-required-documents-for-sir-verification-2026/
- https://cleartax.in/s/voter-id

---

## Part B: Deep Technical Research

## Executive Summary

The Special Intensive Revision (SIR) 2026 affects 16.8 crore voters across West Bengal and Maharashtra alone. Millions are confused, unable to find their names, have incorrect details, or have been flagged as "doubtful voters." Existing government portals are fragmented (5+ websites), most data is locked in PDFs, and the 2002 base rolls are scanned images requiring OCR.

**Key findings:**

1. 2002 electoral rolls ARE available online for both states
2. ECI has an undocumented API enabling programmatic access
3. Maharashtra has dual voter roll systems (Assembly + Municipal)
4. ~330,000-450,000 PDFs need processing across both states
5. Open-source tools exist (in-rolls, PaddleOCR, Aksharamukha, IndicXlit)
6. Legal framework supports this - electoral rolls are public documents (RPA 1950)
7. Realistic budget: $500-1,000/month with cloud credits

---

## 1. Data Sources

### 1.1 West Bengal

#### Official Government Sources

| Source | URL | What's Available |
|--------|-----|-----------------|
| CEO West Bengal | ceowestbengal.wb.gov.in/SIR | SIR 2026 Final Roll, Draft Roll, Supplementary Lists |
| CEO WB 2002 Rolls | ceowestbengal.wb.gov.in/roll_dist | Complete 2002 base roll (scanned images) |
| CEO WB Additions/Deletions | ceowestbengal.wb.gov.in/asd_sir | SIR addition/supplementary/deletion lists |
| ECI Voters Portal | voters.eci.gov.in/download-eroll?stateCode=S25 | All roll types |
| WB State Archives | oldelectoralrolls.wb.gov.in | Historical rolls: 1952, 1957, 1962, 1967, 1971, 1994, 1995 |

#### Community Sources

| Source | URL | What's Available |
|--------|-----|-----------------|
| WB Voters Archive | wbvoters.netlify.app | 2002 rolls mirrored + Google Drive backups |
| VoterListIndia | voterlistindia.in/west-bengal/2002-voter-list/ | 2002 rolls by district/AC |
| Google Sites Archive | sites.google.com/view/oldelectoralrollswb/english | 1952-2002 rolls (2,060 PDFs) |
| OpenCity.in | data.opencity.in/dataset/west-bengal-and-kolkata-sir-electoral-rolls-2026 | CSV data - AC-wise Draft Rolls |

#### WB Scale

- Assembly Constituencies: 294
- Polling Stations: ~85,379
- SIR Draft Roll: 7,66,37,529 (~7.66 crore)
- SIR Final Roll: 7,08,16,630 (~7.08 crore)
- Names Deleted: ~91 lakh
- Under Adjudication: ~60 lakh (unprecedented new category)
- PDFs (2026): ~80,000-85,000
- PDFs (2002): ~50,000-70,000

#### WB SIR Three-Category System (Unprecedented)

1. **Approved** - confirmed valid voter
2. **Deleted** - removed from roll
3. **Under Adjudication** - being verified by Supreme Court-appointed judicial officers

### 1.2 Maharashtra

#### Official Government Sources

| Source | URL | What's Available |
|--------|-----|-----------------|
| CEO Maharashtra | ceo.maharashtra.gov.in | Landing page |
| CEO Election Maharashtra | ceoelection.maharashtra.gov.in | Operational site, current rolls |
| CEO MH 2002 Rolls | ceoelection.maharashtra.gov.in/2002/2002rolldata.aspx | Complete 2002 SIR base roll |
| ECI Voters Portal | voters.eci.gov.in/download-eroll?stateCode=S13 | All roll types |
| BMC Election Data | electiondata.mcgm.gov.in | Mumbai municipal voter lists |
| NMC Voter Lists | election.nagpurnmc.in | Nagpur municipal voter lists |
| Local Body Voter List | localbodyvoterlist.maharashtra.gov.in | ALL local body voter lists |
| State Election Commission | mahasecvoterlist.in | State EC voter list portal |

#### ECI Undocumented API

| Endpoint | Auth | Returns |
|----------|------|---------|
| GET gateway-voters.eci.gov.in/api/v1/common/states | None | All state codes |
| GET /common/districts/{stateCode} | None | Districts for a state |
| GET /common/constituencies?stateCode=S13 | None | All ACs |
| POST /printing-publish/get-publish-part-list | None | All PDFs for an AC |
| POST /elastic/search-by-epic-from-national-display | Captcha | Individual voter search |

#### Maharashtra DUAL Voter Roll System

| Roll Type | Managed By | Portal | Used For |
|-----------|-----------|--------|----------|
| Assembly/Parliament | ECI | voters.eci.gov.in | Lok Sabha & Vidhan Sabha |
| Municipal Corporation | State EC | localbodyvoterlist.maharashtra.gov.in | BMC, PMC, NMC etc. |

Being on one does NOT mean you're on the other.

#### MH Scale

- Assembly Constituencies: 288
- Polling Booths: ~100,186
- Total Voters: 9,70,25,119 (~9.7 crore)
- Municipal Corporations: 29 (separate rolls)
- Municipal Councils: 232 (separate rolls)
- Nagar Panchayats: 125 (separate rolls)
- BMC Voters: ~1.03 crore
- PDFs (Assembly): ~100,000
- PDFs (2002): ~96,000
- PDFs (Municipal): ~25,000+

---

## 2. Data Formats

### Modern Rolls (2024-2026) - Text-Searchable PDFs

- Digitally generated by ECI ERO-NET software
- Text layer present - can extract programmatically with pdfplumber
- ~30 entries per page in tabular format
- Fields: Serial No, Name, Father's/Husband's Name, Age, Gender, House No, EPIC Number, Photo
- Available in regional language + English

### 2002 Rolls - Scanned Image PDFs

- Scanned images of printed registers - NO text layer
- Requires OCR processing
- Quality variable - some clear, some degraded
- WB: Bengali script / MH: Devanagari (Marathi)
- ~25-50 pages per PDF, ~800-1500 voters per station

### OCR Accuracy

| Script | Clean Print | Degraded | Challenge |
|--------|------------|----------|-----------|
| Bengali (WB) | 70-85% | 50-70% | HIGH |
| Devanagari (MH) | 80-92% | 65-80% | MODERATE |

---

## 3. The 2002 Data Challenge

### Why 2002 Matters

The 2002 roll is the "Mother Roll" - last complete from-scratch enumeration. SIR 2026 compares against this base, flagging discrepancies.

### Problems with 2002 Comparison

- Anyone born after ~1984 was minor in 2002 - NOT in base roll
- Address formats, naming conventions, transliterations changed
- People moved, married, family details changed
- EPIC numbers not universal in 2002
- Digitization migration errors

### Legal Framework - In Our Favor

- RPA 1950 (Sections 22-23): Electoral rolls are public documents
- RTI Act: Data obtainable via RTI
- No explicit prohibition on republishing
- When ECI flags "doubtful," they must show basis (includes 2002 data)

### Practical Strategies

1. Direct download from CEO WB and CEO MH portals (available now)
2. RTI applications for specific records if incomplete
3. ECI grievance process (Form 7) forces disclosure of individual records
4. Intermediate revision rolls (2003-2025) reconstruct changes
5. Political party copies - TMC/CPI(M) in WB, Congress/NCP in MH

---

## 4. Search & Storage Architecture

### Recommended Stack

```
PDF Rolls --> Extraction (pdfplumber / PaddleOCR)
          --> Normalization (Aksharamukha + IndicXlit + Soundex)
          --> PostgreSQL (source of truth)
          --> OpenSearch (fuzzy multilingual search)
          --> Next.js PWA + Claude API chatbot
          --> Splink (cross-year linking / dedup)
```

### Why This Stack

| Component | Choice | Why |
|-----------|--------|-----|
| Search | OpenSearch | Bengali/Hindi analyzers, ICU plugin, phonetic filter, 100M+ scale, Apache 2.0 |
| Database | PostgreSQL | Source of truth, exact EPIC lookups, mature |
| OCR (primary) | PaddleOCR | Free, 109 languages, strong Indic, self-hosted |
| OCR (fallback) | Sarvam Vision | 22 Indian scripts, 93%+ accuracy |
| PDF extraction | pdfplumber | 96% table recognition |
| Transliteration | Aksharamukha + IndicXlit | 120 scripts + neural transliteration |
| Phonetic | LibIndic Soundex | Modified Soundex for 9 Indian languages |
| Record linkage | Splink | Probabilistic, 100M+ records |
| Embeddings | BGE-M3 / Vyakyarth | Cross-lingual matching |

### Multi-Layer Name Matching

Same person: Sample Name / Sample Naam / initials / bengali-script / devanagari-script

| Layer | Tool | What It Does |
|-------|------|-------------|
| 1 | Aksharamukha | Convert all names to canonical Devanagari |
| 2 | IndicXlit | Generate Roman transliterations |
| 3 | LibIndic Soundex | Map phonetically equivalent names |
| 4 | OpenSearch fuzzy | Edit-distance, n-gram, phonetic tokens |
| 5 | BGE-M3 vectors | Cross-script embedding similarity |

### Voter Record Schema

```yaml
voter_record:
  epic_number: string          # Primary key, stored from source data
  serial_number: integer
  name_original: string        # Original script
  name_original_script: enum   # bengali/devanagari/latin
  name_devanagari: string      # Aksharamukha-normalized
  name_roman: string           # IndicXlit transliteration
  name_phonetic_code: string   # IndicSoundex code
  name_embedding: float[768]   # Cross-script vector
  relation_type: enum          # father/husband/mother
  relation_name_original: string
  relation_name_roman: string
  relation_name_phonetic_code: string
  age: integer
  gender: enum                 # M/F/T
  house_number: string
  address_original: string
  address_roman: string
  state: string
  district: string
  ac_number: integer
  ac_name: string
  part_number: integer
  polling_station_name: string
  polling_station_address: string
  roll_year: integer           # 2002/2024/2026
  roll_type: enum              # draft/final/supplementary/sir_draft/sir_final
  sir_status: enum             # approved/deleted/under_adjudication (WB only)
  source_pdf: string
  extraction_method: enum      # text_extract/ocr_paddleocr/ocr_sarvam
  extraction_confidence: float
  canonical_id: uuid           # Links same person across years
  photo_hash: string           # Perceptual hash
  created_at: datetime
  updated_at: datetime
```

---

## 5. Cost Estimates

### One-Time OCR Processing

| Approach | Cost | Time | Quality |
|----------|------|------|---------|
| PaddleOCR self-hosted (10x A10G spot) | ~$300-500 | 1-3 days | Good |
| Google Cloud Vision | ~$8,300 | 2-4 days | Good |
| Tesseract self-hosted | ~$50-100 | 1-2 weeks | Moderate |

### Monthly Infrastructure

| Setup | Cost/Month |
|-------|-----------|
| Budget (with RI + credits) | $500-750 |
| Production | $1,000-1,600 |

Strategies: AWS Activate / Google for Nonprofits (up to $100K credits), OpenSearch (Apache 2.0), self-host OCR, data tiering.

---

## 6. Open-Source Tools

### Electoral Roll Processing

- in-rolls/electoral_rolls - Download scripts for all 36 state CEO sites
- in-rolls/parse_elex_rolls - Parse searchable PDFs to CSV (25+ fields)
- in-rolls/parse_unsearchable_rolls - OCR pipeline for image PDFs
- in-rolls/google_vision_ocr - Google Vision OCR pipeline
- gist.github.com/rmehta/9580863 - Maharashtra PDF parser

### Indic NLP

- Aksharamukha - 120-script transliteration
- IndicXlit (AI4Bharat) - Neural transliteration, 21 languages
- LibIndic Soundex - Phonetic matching, 9 languages
- indic_nlp_library - Tokenization, normalization
- Splink - Record linkage at 100M+ scale

### OCR

- PaddleOCR - 109 languages, strong Indic
- Surya OCR - 90+ languages, layout analysis
- EasyOCR - 80+ languages incl. Bengali, Hindi
- Indic-OCR Tesseract - Improved models for Indian scripts
- Sarvam Vision - 22 Indian scripts, best accuracy

---

## 7. Build Plan

| Phase | What | Timeline |
|-------|------|----------|
| 0 | Validate data access - download samples, test API, test OCR | Week 1 |
| 1 | MVP Search - parse 2026 rolls, OpenSearch index, mobile UI | Weeks 2-6 |
| 2 | 2002 Data - OCR pipeline, cross-year linking, comparison | Weeks 4-8 |
| 3 | AI Guide - chatbot, wizard, form pre-filler, RTI templates | Weeks 6-10 |
| 4 | Municipal Rolls - BMC/PMC/NMC, dual roll check | Weeks 8-12 |
