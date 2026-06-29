# ECI API Discovery — Live Research Results (2026-04-09)

## Working Endpoints (No Auth, No CAPTCHA)

### 1. States
GET https://gateway-voters.eci.gov.in/api/v1/common/states/
→ Returns all 36 states/UTs with codes (Maharashtra = S13)

### 2. Districts
GET https://gateway-voters.eci.gov.in/api/v1/common/districts/S13
→ Returns all 36 MH districts with codes (Mumbai Suburban = S1322)

### 3. Assembly Constituencies
GET https://gateway-voters.eci.gov.in/api/v1/common/acs/S1322
→ Returns all 26 ACs in Mumbai Suburban (Andheri West=165, Anushakti Nagar=172, Chembur=173, etc.)

### 4. Polling Stations (Parts)
POST https://gateway-voters.eci.gov.in/api/v1/printing-publish/get-publish-part-list
Body: {"stateCd":"S13","acNumber":172}
→ Returns all 262 polling stations for Anushakti Nagar (Trombay area)

### 5. Roll Types
GET https://gateway-voters.eci.gov.in/api/v1/printing-publish/get-publish-eroll-type?stateCd=S13&year=2024
→ Returns available roll types:
   - "General Election Vidhan Sabha 2024" (FC-EROLLGEN, FinalRoll)
   - "Final Roll - 2nd SSR - 2024" (EROLLGEN, FinalRoll)
   - "Draft Roll - 2nd SSR - 2024" (EROLLGEN, DraftRoll)

GET ...?stateCd=S13&year=2026
→ Returns:
   - "Bye Election Final Roll 2026" (BY-EROLLGEN, only for AC 201-Baramati, 223-Rahuri)
   - "Bye Election Draft Roll 2026"

## CAPTCHA-Protected Endpoints

### 6. Generate PDF (REQUIRES CAPTCHA)
POST https://gateway-voters.eci.gov.in/api/v1/printing-publish/generate-published-eroll
Required fields: stateCd, acNumber, partNumber, langCd, captcha, captchaId
→ Presumably returns PDF file or download URL

### 7. Voter Search (REQUIRES CAPTCHA)
POST https://gateway-voters.eci.gov.in/api/v1/elastic/search-by-epic-from-national-display
Required: epicNumber, stateCd, captchaData, captchaId, securityKey("na")

## All Discovered API Endpoints (from JS bundle)

- /api/v1/printing-publish/generate-published-eroll (CAPTCHA)
- /api/v1/printing-publish/generate-published-geroll (CAPTCHA)
- /api/v1/printing-publish/generate-published-pdfs (CAPTCHA)
- /api/v1/printing-publish/generate-bye-election-draftroll
- /api/v1/printing-publish/generate-published-supplement
- /api/v1/printing-publish/get-ac-languages
- /api/v1/printing-publish/get-part-list
- /api/v1/printing-publish/get-publish-eroll-type (no auth)
- /api/v1/printing-publish/get-publish-part-list (no auth)
- /api/v1/printing-publish/get-publish-roll
- /api/v1/printing-publish/download-statutory-report
- /api/v1/document-adhoc/downloadPresignedFile?bucketName=objectstorage&fileName=
- /api/v1/document/downloadFile?bucketName=objectstorage&fileName=
- /api/v1/elastic/get-eroll-data-2003-by-epic-captcha (2002 base roll!)
- /api/v1/elastic-sir-citizen/get-eroll-data-2003
- /api/v1/elastic-sir-citizen/get-eroll-data-2003-by-epic-captcha

## Direct PDF URL Pattern (from reverse engineering article)
Individual: https://voters.eci.gov.in/eroll/{year}/{state_lower}/{roll_type}/{ac}/{filename}.pdf
ZIP: https://voters.eci.gov.in/eroll/{year}/{state_lower}/{roll_type}/{ac}-eroll.zip
Requires headers: User-Agent + Referer: https://voters.eci.gov.in/

## Alternative PDF Sources (No CAPTCHA)

### BMC Mumbai Municipal Voter Lists
Open directory: https://electiondata.mcgm.gov.in/A4%20Booth%20wise%20Voter%20List%202026/
Pattern: BoothVoterList_A4_Ward_{WW}_Booth_{BB}.pdf
(SSL certificate issue from cloud environments - works from browser)

### CEO Maharashtra 2002 Rolls
https://ceoelection.maharashtra.gov.in/2002/2002/PDFs/{District}/{AC_No}%20-%20{AC_Name}/{PartNo}-{PartName}.pdf
(SSL certificate issue from cloud environments - works from browser)

### CEO Maharashtra Legislative Council Rolls
https://ceoelection.maharashtra.gov.in/ConstituencyRollsFinal/{Division}/{District}/{Category}/{Language}/PART{NNN}_{LANG}.pdf

## Mumbai Suburban — Full AC Map (26 ACs)

| AC | Name | Hindi | Booths |
|----|------|-------|--------|
| 152 | Borivali | बोरीवली | - |
| 153 | Dhaisar | दहिसर | - |
| 154 | Magathane | मागाठाणे | - |
| 155 | Mulund | मुलुंड | - |
| 156 | Vikhroli | विक्रोळी | - |
| 157 | Bhandup West | भाडुंप पश्चिम | - |
| 158 | Jogeshwari East | जोगेश्वरी पूर्व | - |
| 159 | Dindoshi | दिंडोशी | - |
| 160 | Kandivali East | कांदिवली पूर्व | - |
| 161 | Charkop | चारकोप | - |
| 162 | Malad West | मालाड पश्चिम | - |
| 163 | Goregaon | गोरेगांव | - |
| 164 | Varsova | वर्सोवा | - |
| 165 | Andheri West | अंधेरी पश्चिम | 301 |
| 166 | Andheri East | अंधेरी पूर्व | - |
| 167 | Vile Parle | विलेपार्ले | - |
| 168 | Chandivali | चांदिवली | - |
| 169 | Ghatkopar West | घाटकोपर पश्चिम | - |
| 170 | Ghatkopar East | घाटकोपर पूर्व | - |
| 171 | Mankhurd Shivajinagar | मानखुर्द शिवाजीनगर | - |
| 172 | Anushakti Nagar | अणुशक्ती नगर | 262 |
| 173 | Chembur | चेंबूर | 290 |
| 174 | Kurla (SC) | कुर्ला (अ.जा.) | - |
| 175 | Kalina | कलीना | - |
| 176 | Vandre East | वांद्रे पूर्व | - |
| 177 | Vandre West | वांद्रे पश्चिम | - |

## Critical 2002 Data Endpoint!
/api/v1/elastic/get-eroll-data-2003-by-epic-captcha
→ ECI has the 2002 base roll data IN ELASTICSEARCH, searchable by EPIC!
