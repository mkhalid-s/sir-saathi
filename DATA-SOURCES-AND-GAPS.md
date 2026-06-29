# SIR Saathi — Data Sources, Gaps & Extraction Strategy

> Compiled: 2026-04-09
> Focus: Maharashtra (then expand)

## 1. ECI API — Fully Mapped (No Auth, No CAPTCHA)

Base: https://gateway-voters.eci.gov.in/api/v1/

| Endpoint | Method | Auth | Returns |
|----------|--------|------|---------|
| /common/states | GET | None | All 36 states/UTs with codes |
| /common/districts/{stateCode} | GET | None | Districts (MH=S13, 36 districts) |
| /common/acs/{stateDistrictCode} | GET | None | Assembly Constituencies |
| /printing-publish/get-publish-part-list | POST | None | Polling stations per AC |
| /printing-publish/get-publish-eroll-type?stateCd=S13&year=2024 | GET | None | Roll types available |
| /printing-publish/get-ac-languages | ? | None | Languages per AC |
| /printing-publish/generate-published-eroll | POST | **CAPTCHA** | PDF generation |
| /elastic/search-by-epic-from-national-display | POST | **CAPTCHA** | Voter search |
| /elastic/get-eroll-data-2003-by-epic-captcha | POST | **CAPTCHA** | 2002 base roll search |

### MH Roll Types (from API)
- 2024: General Election Vidhan Sabha 2024 (FC-EROLLGEN), Final Roll 2nd SSR (EROLLGEN), Draft Roll 2nd SSR
- 2026: Bye Election Final/Draft Roll (only ACs 201-Baramati, 223-Rahuri)

### Critical Finding
ECI has 2002 base roll data IN ELASTICSEARCH — endpoint: /elastic/get-eroll-data-2003-by-epic-captcha

## 2. Predictable PDF URL Sources (No CAPTCHA)

### BMC Mumbai Municipal Voter Lists — OPEN DIRECTORY
URL: https://electiondata.mcgm.gov.in/A4%20Booth%20wise%20Voter%20List%202026/
Pattern: BoothVoterList_A4_Ward_{WW}_Booth_{BB}.pdf
Coverage: 227 wards, multiple booths each (~9,000+ PDFs)
CAPTCHA: NONE — open directory
SSL: Government cert — may need --insecure flag or browser download

### CEO Maharashtra 2002 Rolls
URL: https://ceoelection.maharashtra.gov.in/2002/2002/PDFs/{District}/{AC_No}%20-%20{AC_Name}/{PartNo}-{PartName}.pdf
Confirmed: https://ceoelection.maharashtra.gov.in/2002/2002/PDFs/Yavatmal/160%20-%20Wani/192-Dhaba.pdf
Coverage: All MH districts, all ACs from 2002
CAPTCHA: Simpler/none on this older portal

### CEO Maharashtra Legislative Council Rolls
URL: https://ceoelection.maharashtra.gov.in/ConstituencyRollsFinal/{Division}/{District}/{Category}/{Language}/PART{NNN}_{LANG}.pdf
Confirmed: Pune/Satara/Graduates/English/PART220_EN.pdf
Coverage: Teachers/Graduates constituencies

### ECI Portal PDFs (with proper headers, URL guessing)
Pattern: https://voters.eci.gov.in/eroll/{year}/{state_lower}/{roll_type}/{ac}/{filename}.pdf
Example: 2026-EROLLGEN-S13-{AC}-FinalRoll-Revision1-ENG-{PART}-WI.pdf
ZIP: https://voters.eci.gov.in/eroll/{year}/{state_lower}/{roll_type}/{ac}-eroll.zip
Headers needed: User-Agent + Referer: https://voters.eci.gov.in/

## 3. Structured Data Sources (CSV/Open Data)

### OpenCity.in
- Maharashtra Assembly-wise Total Electors CSV (2024)
- Mumbai Constituencies Total Electors CSV
- District-wise Electors Count PDF
- URL: https://data.opencity.in/dataset/maharashtra-assembly-elections-2024
- 541 datasets scraped from ceoelection.maharashtra.gov.in

### Harvard Dataverse (in-rolls project)
- Parsed Indian Electoral Rolls as CSV (25+ fields)
- DOI: 10.7910/DVN/MUEGDT
- Access: Requires IRB form + privacy agreement
- Also on Google Cloud Storage (requester-pays)

### raphael-susewind/india-religion-politics (GitHub)
- mahaid: Maharashtra booth-level electoral data
- Includes demographic analysis by name
- License: ODbL 1.0 (open)
- URL: github.com/raphael-susewind/india-religion-politics/tree/master/mahaid

### datameet/india-election-data (GitHub)
- Constituency-level metadata for all India
- URL: github.com/datameet/india-election-data

## 4. Existing Tools (GitHub)

| Tool | Purpose | Language | URL |
|------|---------|----------|-----|
| in-rolls/electoral_rolls | Download PDFs from all 36 state CEOs | R/Python | github.com/in-rolls/electoral_rolls |
| in-rolls/parse_elex_rolls | Parse searchable PDFs → CSV | R | github.com/in-rolls/parse_searchable_rolls |
| rmehta gist 9580863 | MH-specific PDF extractor | Python | gist.github.com/rmehta/9580863 |
| shreekumar3d/voter-list | convert-ceo-mh.sh for MH | Bash | github.com/shreekumar3d/voter-list |
| shashwatismicro/electoralRoll | Selenium ECI portal automation | Python | github.com/shashwatismicro/electoralRoll |
| devarajphukan/Electoral_roll_parser | Electoral roll PDF parser | Python | github.com/devarajphukan/Electoral_roll_parser |

## 5. Mumbai Suburban — Live API Data

### All 26 ACs Confirmed
AC 152-177, covering: Borivali, Dhaisar, Magathane, Mulund, Vikhroli, Bhandup West,
Jogeshwari East, Dindoshi, Kandivali East, Charkop, Malad West, Goregaon, Varsova,
Andheri West (301 booths), Andheri East, Vile Parle, Chandivali, Ghatkopar West,
Ghatkopar East, Mankhurd Shivajinagar, Anushakti Nagar (262 booths, Trombay area),
Chembur (290 booths), Kurla SC, Kalina, Vandre East, Vandre West

### Trombay Area = Anushakti Nagar (AC 172) + Chembur (AC 173)
Old Trombay constituency was merged; area now split between these two ACs.
