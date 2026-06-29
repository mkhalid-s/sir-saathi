# SIR Saathi - Technical Architecture (Maharashtra First)

> Compiled: 2026-04-09
> Target: Maharashtra (9.7 crore voters, 288 ACs, ~100K polling stations)
> Budget: $0 (Oracle Cloud Always Free + Cloudflare Free)
> Hardware: 4 ARM cores, 24GB RAM, 200GB SSD (Oracle Cloud Mumbai)

---

## 1. Infrastructure: Oracle Cloud Always Free (Mumbai Region)

### What We Get — Forever Free

| Resource | Specs | Our Use |
|----------|-------|---------|
| ARM Compute | 4 Ampere cores, 24GB RAM | Main server: PostgreSQL + Meilisearch + API |
| AMD Micro VMs | 2 VMs, 1GB RAM each | Worker for PDF processing / monitoring |
| Block Storage | 200GB total | PostgreSQL data (~70GB) + OS (~20GB) + temp (~50GB) |
| Object Storage | 10GB Standard + 10GB Archive | Sample PDFs, backups |
| Load Balancer | 1 instance, 10 Mbps | Frontend traffic |
| Outbound Transfer | 10 TB/month | More than enough |
| Autonomous DB | 2 instances, 20GB each | Optional Oracle DB backup |
| Email | 3,000/month | User notifications |
| Region | Mumbai (ap-mumbai-1) | Low latency for Indian users |

### Setup Steps

1. Sign up at https://www.oracle.com/cloud/free/ (credit card for verification only, never charged)
2. Select Home Region: **India South (Mumbai)**
3. Create ARM VM: VM.Standard.A1.Flex, 4 OCPUs, 24GB RAM, 150GB boot volume
4. Install: Ubuntu 22.04 + PostgreSQL + Meilisearch + Nginx + Python
5. **CRITICAL: Upgrade to Pay-As-You-Go** (still free, prevents idle instance reclamation)
6. Open ports: 80/443 in BOTH OCI Security Lists AND OS iptables

### Known Gotchas

| Issue | Solution |
|-------|----------|
| ARM instances "Out of Capacity" in Mumbai | Use retry script (OCI CLI in loop, try every 60 seconds) |
| Idle instance reclamation (<10% CPU for 7 days) | Upgrade to PAYG (free resources stay free) |
| Two firewall layers confuse newcomers | Must open ports in OCI Security List AND iptables/ufw |
| No SLA on free tier | Accept this for a civic project; set up monitoring |

### PostgreSQL Tuning (24GB RAM)

```
shared_buffers = 6GB
effective_cache_size = 18GB
maintenance_work_mem = 1GB
work_mem = 64MB
wal_buffers = 64MB
max_connections = 50
random_page_cost = 1.1
effective_io_concurrency = 200
```

---

## 2. PDF Download Pipeline

### Where the PDFs Come From

#### ECI Undocumented API (Primary — Current Rolls)

Base URL: `https://gateway-voters.eci.gov.in/api/v1/`

| Endpoint | Method | Auth | Returns |
|----------|--------|------|---------|
| `/common/states` | GET | None | All state codes (MH = S13) |
| `/common/districts/S13` | GET | None | Districts in Maharashtra |
| `/common/acs/S13{districtCode}` | GET | None | ACs for a district |
| `/printing-publish/get-publish-part-list` | POST | None | All PDF parts for an AC |

ZIP download pattern:
```
https://voters.eci.gov.in/eroll/2026/s13/sir-draftroll/{acNumber}-eroll.zip
```

Each ZIP contains all part PDFs for one Assembly Constituency.

**CAPTCHA Challenge:** ECI mandated CAPTCHA in 2018 to prevent scraping.
- Simple image-based text CAPTCHA (not reCAPTCHA)
- Options: Manual solving for small batches, or simple OCR on CAPTCHA image
- Rate limiting: Not documented but aggressive downloading may get IP blocked
- Strategy: Download slowly (1 ZIP every 30-60 seconds) with delays

#### CEO Maharashtra (2002 Rolls)

URL: `ceoelection.maharashtra.gov.in/2002/2002rolldata.aspx`
- ASP.NET WebForms app (District → AC → Part dropdowns)
- Simpler/no CAPTCHA protection on this older portal
- Can be scripted with Selenium or requests + form POST

#### Existing Download Tools

| Tool | URL | Notes |
|------|-----|-------|
| in-rolls/electoral_rolls | github.com/in-rolls/electoral_rolls | Download scripts for 36 state CEOs |
| shashwatismicro/electoralRoll | github.com/shashwatismicro/electoralRoll | Selenium automation with CAPTCHA handling |
| shreekumar3d/voter-list | github.com/shreekumar3d/voter-list | Has `convert-ceo-mh.sh` for Maharashtra |

### PDF Storage Strategy: Extract and Discard

| Metric | Value |
|--------|-------|
| Total PDFs (Maharashtra) | ~100,000 |
| Average PDF size | ~5 MB |
| Total raw PDF size | ~500 GB |
| Oracle VM storage | 200 GB |
| **Conclusion** | Cannot store all PDFs — extract data, discard PDF |

**Pipeline:**
1. Download ZIP for one AC (~30-50 MB)
2. Unzip to temp directory
3. Parse each PDF → extract voter records
4. Bulk INSERT into PostgreSQL
5. Delete PDF and ZIP
6. Move to next AC

Only ~50-100 MB of temp space needed at any time.

### Extracted Data Storage

| Metric | Value |
|--------|-------|
| Total voter records | ~9.7 crore (97 million) |
| Estimated row size | ~600-700 bytes |
| Total data + indexes | ~60-70 GB |
| Available block storage | 200 GB |
| **Fits?** | YES (with ~100 GB to spare) |

---

## 3. PDF Parsing Pipeline

### Detect: Searchable vs Scanned

```python
import pdfplumber

def is_searchable(pdf_path):
    """Check if PDF has extractable text."""
    with pdfplumber.open(pdf_path) as pdf:
        # Check first 3 non-empty pages
        for page in pdf.pages[:5]:
            text = page.extract_text()
            if text and len(text.strip()) > 100:
                return True
    return False
```

### For Searchable PDFs (Current 2026 Rolls)

Use pdfplumber — fast, accurate, no OCR needed.

```python
import pdfplumber
import re

def extract_voters_from_pdf(pdf_path, ac_no, part_no):
    """Extract voter records from a searchable Maharashtra electoral roll PDF."""
    voters = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            # Parse voter blocks using regex (pattern varies — must calibrate to actual format)
            # Each voter entry typically has: Serial No, Photo, Name, Relation, House No, Age, Sex, EPIC
            blocks = re.split(r'(?=\d+\s+[A-Z]{3}\d{7})', text)
            for block in blocks:
                voter = parse_voter_block(block)
                if voter:
                    voter['ac_no'] = ac_no
                    voter['part_no'] = part_no
                    voter['source_pdf'] = pdf_path
                    voters.append(voter)
    return voters
```

**Speed:** 1-3 seconds per PDF, ~350 PDFs per AC = 6-18 min per AC, ~10-20 hours total with 4 workers.

### For Scanned PDFs (2002 Rolls)

Need OCR — much slower.

| OCR Option | Cost | Speed | Accuracy for Devanagari |
|------------|------|-------|------------------------|
| PaddleOCR (self-hosted) | $0 | ~30-60 sec/page | Good (~90%) |
| Google Cloud Vision ($300 free trial) | $300 credit = ~200K pages free | Fast | Good (~92%) |
| Tesseract + mar model | $0 | ~60-120 sec/page | Moderate (~85%) |
| Sarvam Vision | Free tier 100 pages/mo | Fast | Best (~93%) |

**Recommendation:** Use Google Cloud $300 free trial for 2002 OCR (~200K pages = ~5,000 PDFs = several districts).

### Existing Maharashtra-Specific Parsers

| Parser | Language | URL |
|--------|----------|-----|
| rmehta's MH extractor | Python | gist.github.com/rmehta/9580863 |
| shreekumar3d convert-ceo-mh.sh | Bash | github.com/shreekumar3d/voter-list |
| in-rolls parse_elex_rolls | R | github.com/in-rolls/parse_searchable_rolls |

**CRITICAL FIRST STEP:** Download 5-10 sample PDFs manually and examine the actual text structure before writing the parser. Formats vary between years and states.

---

## 4. Search Architecture

### Why We Don't Need Vector Search / Elasticsearch / OpenSearch

| What Uber Needed | What We Need |
|------------------|-------------|
| Semantic search (meaning-based) | Fuzzy text search (name matching) |
| 1.5 billion high-dimensional vectors | 10 crore text records |
| Understanding user intent | Finding exact person by name/ID |
| GPU-powered ANN retrieval | String similarity + phonetic matching |
| Multi-datacenter deployment | Single free VM |

**Our search problem is solved by: pre-filtering + fuzzy text + phonetic matching. No vectors needed.**

### The Pre-Filtering Approach (Key Insight)

```
Full Maharashtra: 9,70,25,119 voters → 2-5 second search
  ↓ User selects District
District (e.g., Pune): ~30-50 lakh → 200-500ms search
  ↓ User selects AC
Assembly Constituency: ~3.4 lakh → < 50ms search
  ↓ User knows booth
Polling Station: ~970 → < 5ms search
```

By making the user narrow down their location FIRST, we reduce the search space by 100-1000x before doing any fuzzy matching. This is exactly how electoralsearch.eci.gov.in works.

### Search Stack Decision

| Engine | Can handle 100M on 24GB? | Devanagari support | Fuzzy search | Our verdict |
|--------|-------------------------|-------------------|-------------|-------------|
| **PostgreSQL + pg_trgm** | YES (with partitioning) | YES | YES (trigram similarity) | PRIMARY — structured queries + fuzzy search within AC |
| **Meilisearch** | **NO — FAILED at 116M records** (couldn't index in 2 days on 128GB RAM) | Basic | YES | **ELIMINATED** |
| OpenSearch | YES but needs 16GB+ RAM | YES (analyzers) | YES | OVERKILL — too heavy for our VM |
| Typesense | Possible but untested at 100M | Limited | YES | NOT ENOUGH Indian language support |
| Vector (FAISS/Qdrant) | YES but wrong problem | N/A | N/A | NOT NEEDED — our problem isn't semantic |

### Primary: PostgreSQL + pg_trgm (For Filtered Searches)

```sql
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- The voters table (partitioned by AC)
CREATE TABLE voters (
    id BIGSERIAL,
    epic_number VARCHAR(20),

    -- Original data
    name_original TEXT NOT NULL,
    father_name_original TEXT,
    age SMALLINT,
    gender CHAR(1),
    house_number TEXT,
    address_original TEXT,

    -- Pre-computed search fields (generated at ingest time)
    name_roman TEXT,           -- "Mohammad Ali" (transliterated from Devanagari)
    name_phonetic VARCHAR(20), -- "M530" (LibIndic Soundex)
    name_normalized TEXT,      -- lowercase, normalized
    father_name_roman TEXT,
    father_name_phonetic VARCHAR(20),

    -- Location
    state_code VARCHAR(5),
    district VARCHAR(50),
    ac_number SMALLINT NOT NULL,
    ac_name VARCHAR(100),
    part_number SMALLINT,
    polling_station TEXT,

    -- Metadata
    roll_year SMALLINT,
    roll_type VARCHAR(20),
    source_pdf TEXT,

    PRIMARY KEY (id, ac_number)
) PARTITION BY LIST (ac_number);

-- Create 288 partitions (one per AC)
-- Auto-generate with: DO $$ BEGIN FOR i IN 1..288 LOOP EXECUTE format('CREATE TABLE voters_ac_%s PARTITION OF voters FOR VALUES IN (%s)', i, i); END LOOP; END $$;

-- Indexes for each search pattern
CREATE INDEX idx_epic ON voters (epic_number);                           -- Exact EPIC lookup: < 1ms
CREATE INDEX idx_name_trgm ON voters USING gin (name_roman gin_trgm_ops);  -- Fuzzy name: < 50ms per AC
CREATE INDEX idx_phonetic ON voters (name_phonetic);                     -- Phonetic match: < 10ms
CREATE INDEX idx_father_trgm ON voters USING gin (father_name_roman gin_trgm_ops);
CREATE INDEX idx_district ON voters (district);
```

### Search Queries

```sql
-- Search 1: By EPIC number (instant, any scope)
SELECT * FROM voters WHERE epic_number = 'MH1234567';
-- < 1ms, uses B-tree index

-- Search 2: By name within AC (most common)
SELECT *, similarity(name_roman, 'mohammad ali') AS score
FROM voters
WHERE ac_number = 185
  AND name_roman % 'mohammad ali'  -- pg_trgm fuzzy match (default threshold 0.3)
ORDER BY score DESC
LIMIT 20;
-- < 50ms on ~3.4 lakh records

-- Search 3: By name + father's name within district
SELECT *, similarity(name_roman, 'mohammad ali') AS name_score
FROM voters
WHERE district = 'Pune'
  AND name_roman % 'mohammad ali'
  AND father_name_roman % 'akbar ali'
ORDER BY name_score DESC
LIMIT 20;
-- < 200ms on ~30-50 lakh records

-- Search 4: By phonetic code (catches transliteration variations)
SELECT * FROM voters
WHERE ac_number = 185
  AND name_phonetic = 'M530'  -- IndicSoundex code for "Mohammad"
LIMIT 50;
-- < 10ms

-- Search 5: Combined fuzzy + phonetic (best results)
SELECT *,
  GREATEST(
    similarity(name_roman, 'mohammad ali'),
    CASE WHEN name_phonetic = 'M530' THEN 0.7 ELSE 0 END
  ) AS combined_score
FROM voters
WHERE ac_number = 185
  AND (name_roman % 'mohammad ali' OR name_phonetic = 'M530')
ORDER BY combined_score DESC
LIMIT 20;
```

### Secondary: Meilisearch (For Global Search — "I Don't Know My AC")

For users who don't know their district/AC, we need to search ALL 9.7 crore records. PostgreSQL pg_trgm is too slow for this without pre-filtering.

**Meilisearch approach:** Index a lightweight version of each voter (name + EPIC + AC + district only) in Meilisearch. Keep it under ~6GB RAM.

```python
# Index voters into Meilisearch (lightweight fields only)
import meilisearch

client = meilisearch.Client('http://127.0.0.1:7700', 'MASTER_KEY')
index = client.index('voters_mh')

# Configure
index.update_settings({
    'searchableAttributes': ['name_roman', 'name_original', 'father_name_roman', 'epic_number'],
    'filterableAttributes': ['district', 'ac_number', 'gender', 'roll_year'],
    'sortableAttributes': ['ac_number'],
    'typoTolerance': {
        'enabled': True,
        'minWordSizeForTypos': {'oneTypo': 3, 'twoTypos': 6}
    }
})

# Add documents in batches of 50,000
batch = []
for voter in all_voters:
    batch.append({
        'id': voter['id'],
        'name_roman': voter['name_roman'],
        'name_original': voter['name_original'],
        'father_name_roman': voter['father_name_roman'],
        'epic_number': voter['epic_number'],
        'district': voter['district'],
        'ac_number': voter['ac_number'],
        'ac_name': voter['ac_name'],
        'age': voter['age'],
        'gender': voter['gender'],
    })
    if len(batch) >= 50000:
        index.add_documents(batch)
        batch = []
```

**Meilisearch at 100M records:** This is at the edge of Meilisearch's practical limits. If it struggles, we can:
1. Create per-district indexes (36 indexes, ~2.7M records each — well within Meilisearch's comfort zone)
2. Route user's search to the appropriate district index
3. For "I don't know anything" searches, query all 36 in parallel and merge results

### Memory Budget

| Component | RAM Usage | Notes |
|-----------|----------|-------|
| OS + Nginx | ~500 MB | Minimal |
| PostgreSQL | ~8-10 GB | shared_buffers (6GB) + active queries |
| Meilisearch | ~4-8 GB | Depends on index size; per-district approach uses less |
| FastAPI/Node | ~200-500 MB | Application server |
| Python workers | ~500 MB - 1 GB | PDF processing (when running) |
| **Total** | **~14-20 GB** | Fits in 24 GB with headroom |

---

## 5. Name Matching Pipeline (At Ingest Time)

### Pre-Compute Everything at Ingest (Zero Query-Time Cost)

For each voter record, before storing in PostgreSQL:

```python
from aksharamukha import transliterate
from indicxlit import Transliterator  # AI4Bharat
from soundex import Soundex           # LibIndic

# Initialize once
xlit = Transliterator(source='mr', target='en')  # Marathi to English
soundex_engine = Soundex()

def enrich_voter(voter):
    """Add search fields to a voter record before DB insertion."""

    name = voter['name_original']  # e.g., "मोहम्मद अली"

    # 1. Transliterate to Roman (Devanagari → English)
    voter['name_roman'] = xlit.transliterate(name)  # "Mohammad Ali"

    # 2. Generate phonetic code
    voter['name_phonetic'] = soundex_engine.soundex(voter['name_roman'])  # "M530"

    # 3. Normalize (lowercase, strip whitespace)
    voter['name_normalized'] = voter['name_roman'].lower().strip()

    # 4. Same for father's name
    if voter.get('father_name_original'):
        voter['father_name_roman'] = xlit.transliterate(voter['father_name_original'])
        voter['father_name_phonetic'] = soundex_engine.soundex(voter['father_name_roman'])

    return voter
```

This means at query time, we only do string comparison — no transliteration, no AI models, no embeddings. Fast.

---

## 6. Complete Architecture Diagram

```
                    ┌──────────────────────────┐
                    │     Cloudflare Pages      │
                    │   (Next.js PWA Frontend)  │
                    │   Free · Unlimited BW     │
                    └────────────┬─────────────┘
                                 │ HTTPS
                    ┌────────────▼─────────────┐
                    │        Cloudflare         │
                    │     (DNS + CDN + DDoS)    │
                    │         Free Tier         │
                    └────────────┬─────────────┘
                                 │
              ┌──────────────────▼──────────────────┐
              │    Oracle Cloud Always Free VM       │
              │    Mumbai Region · 4 ARM · 24GB RAM  │
              │                                      │
              │  ┌──────────────────────────────┐   │
              │  │         Nginx                │   │
              │  │   Reverse Proxy + SSL        │   │
              │  │   (Let's Encrypt)            │   │
              │  └──────────┬───────────────────┘   │
              │             │                        │
              │  ┌──────────▼───────────────────┐   │
              │  │     FastAPI / Next.js API     │   │
              │  │     Application Server        │   │
              │  └──┬───────────────────┬───────┘   │
              │     │                   │            │
              │  ┌──▼──────────┐  ┌────▼────────┐  │
              │  │ PostgreSQL  │  │ Meilisearch │  │
              │  │ 9.7 Cr rows │  │ Global      │  │
              │  │ Partitioned │  │ Search      │  │
              │  │ by AC (288) │  │ (fallback)  │  │
              │  │ pg_trgm     │  │             │  │
              │  │ ~8-10GB RAM │  │ ~4-8GB RAM  │  │
              │  └─────────────┘  └─────────────┘  │
              │                                      │
              │  Storage: 150GB Block Volume          │
              │  ├── OS + Apps: ~20 GB               │
              │  ├── PostgreSQL data: ~70 GB          │
              │  ├── Meilisearch index: ~30 GB        │
              │  └── Temp/working: ~30 GB             │
              └──────────────────────────────────────┘

        ┌────────────────────────────────────────┐
        │   Oracle Cloud AMD Micro VM #1         │
        │   1 CPU · 1GB RAM                      │
        │   PDF Processing Worker                │
        │   (downloads, parses, inserts)          │
        └────────────────────────────────────────┘

        ┌────────────────────────────────────────┐
        │   Oracle Cloud AMD Micro VM #2         │
        │   1 CPU · 1GB RAM                      │
        │   Monitoring (UptimeKuma) + Cron jobs  │
        └────────────────────────────────────────┘
```

---

## 7. Processing Timeline

### Phase 0: Validate (Day 1-3)

| Task | Time | What |
|------|------|------|
| Sign up Oracle Cloud | 15 min | Mumbai region, get VM |
| Download 5 sample MH PDFs manually | 30 min | Test format |
| Examine PDF structure | 2 hours | Searchable? English? Marathi? Layout? |
| Write parser for sample PDFs | 4-8 hours | Calibrate regex to actual format |
| Test pg_trgm search on sample data | 2 hours | Verify < 50ms on sample |

### Phase 1: Maharashtra Data Ingestion (Week 1-2)

| Task | Time | What |
|------|------|------|
| Set up PostgreSQL + schema + partitions | 2 hours | On Oracle VM |
| Build download pipeline (with CAPTCHA handling) | 4-8 hours | Python script |
| Process all 288 ACs (2026 searchable PDFs) | 10-20 hours | 4 parallel workers |
| Build transliteration pipeline | 4 hours | Aksharamukha + IndicXlit + Soundex |
| Enrich all records with search fields | 4-8 hours | Batch update |
| Create indexes | 2-4 hours | pg_trgm GIN indexes on 97M rows |
| Test "I don't know my AC" search with pg_trgm on full dataset | 2-4 hours | Measure if < 2 seconds on all MH |
| **Total** | **~30-55 hours of compute** | **~1 week calendar time** |

### Phase 2: Frontend + Search API (Week 2-3)

| Task | Time |
|------|------|
| Next.js PWA with i18n (Marathi, Hindi, English) | 2-3 days |
| Search API (EPIC lookup, name search, filtered search) | 1-2 days |
| Deploy on Cloudflare Pages + Oracle VM | 2-4 hours |
| Test with real users | Ongoing |

---

## 8. Search Performance Benchmarks (Expected)

| Search Type | Scope | Records Searched | Expected Latency |
|------------|-------|-----------------|------------------|
| EPIC number lookup | All MH | 9.7 Cr (B-tree) | **< 1 ms** |
| Name within AC | 1 AC | ~3.4 lakh | **< 50 ms** |
| Name within District | 1 District | ~30 lakh | **< 200 ms** |
| Name + Father within AC | 1 AC | ~3.4 lakh | **< 50 ms** |
| Phonetic code within AC | 1 AC | ~3.4 lakh | **< 10 ms** |
| Global name search (Meilisearch) | All MH | 9.7 Cr | **< 500 ms** |
| Global name search (per-district Meilisearch) | 1 District | ~30 lakh | **< 100 ms** |

---

## 9. When to Upgrade (Funded Phase)

| Trigger | What to Add | Cost |
|---------|------------|------|
| >1000 concurrent users | Second Oracle VM as read replica | $0 (use second free account) |
| Adding West Bengal | More storage needed | $5-10/mo (Hetzner backup) |
| Adding 5+ states | Meilisearch struggles at 50Cr+ | Upgrade to OpenSearch ($50/mo) |
| All India (97 Cr) | Need dedicated search cluster | $200-500/mo (grant-funded) |
| 2002 OCR processing | GPU compute for batch OCR | Google Cloud $300 free trial |

---

## 10. Key Decisions Summary

| Question | Decision | Why |
|----------|----------|-----|
| Vector search? | **NO** | Our problem is fuzzy text, not semantic similarity |
| Elasticsearch/OpenSearch? | **NO (for now)** | Too heavy for 24GB; PostgreSQL + Meilisearch is enough |
| Store PDFs? | **NO** | Extract data, discard PDFs. Data fits; PDFs don't. |
| Which search engine? | **PostgreSQL pg_trgm ONLY** | Meilisearch FAILED at 100M; pg_trgm with partitioning handles all cases; ECI uses Elasticsearch but we can't afford it on free tier |
| Partition how? | **By AC number (288 partitions)** | Matches user's search pattern (select district → AC → search) |
| Pre-compute or query-time? | **Pre-compute transliterations at ingest** | Zero overhead at search time |
| Which OCR? | **PaddleOCR (free) + Google Vision ($300 free trial)** | For 2002 scanned rolls only; 2026 rolls are text-searchable |
| Frontend hosting? | **Cloudflare Pages** | Free, unlimited bandwidth, global CDN |

---

## Sources

### Uber's Billion-Scale Search
- [Uber: Powering Billion-Scale Vector Search with OpenSearch](https://www.uber.com/blog/powering-billion-scale-vector-search-with-opensearch/)
- [Uber Billion Scale Vector Search Whitepaper](https://www.scribd.com/document/984346674/Uber-Billion-Scale-Vector-Search-Whitepaper-Detailed)

### Search Technologies
- [DiskANN: Billion-point Nearest Neighbor on Single Node (Microsoft)](https://suhasjs.github.io/files/diskann_neurips19.pdf)
- [Microsoft DiskANN GitHub](https://github.com/microsoft/DiskANN)
- [FAISS: Facebook AI Similarity Search](https://github.com/facebookresearch/faiss)
- [pgvector: Vector search for PostgreSQL](https://github.com/pgvector/pgvector)
- [Scaling Vector Search to 1B on PostgreSQL (VectorChord)](https://blog.vectorchord.ai/scaling-vector-search-to-1-billion-on-postgresql)
- [PostgreSQL pg_trgm documentation](https://www.postgresql.org/docs/current/pgtrgm.html)
- [Meilisearch Multi-tenancy Guide](https://www.meilisearch.com/blog/multi-tenancy-guide)
- [Meilisearch RAM and Performance](https://www.meilisearch.com/docs/learn/indexing/ram_multithreading_performance)

### PDF Processing
- [Reverse Engineering India's Electoral Roll System (Medium)](https://medium.com/@blacklovertech/reverse-engineering-indias-electoral-roll-system)
- [rmehta's Maharashtra Electoral Roll Extractor](https://gist.github.com/rmehta/9580863)
- [shreekumar3d/voter-list (convert-ceo-mh.sh)](https://github.com/shreekumar3d/voter-list)
- [in-rolls/electoral_rolls](https://github.com/in-rolls/electoral_rolls)
- [in-rolls/parse_searchable_rolls](https://github.com/in-rolls/parse_searchable_rolls)
- [shashwatismicro/electoralRoll (CAPTCHA handling)](https://github.com/shashwatismicro/electoralRoll)
- [OpenCity.in Maharashtra Voter Rolls CSV](https://data.opencity.in/dataset/maharashtra-assembly-elections-2024)

### Infrastructure
- [Oracle Cloud Always Free](https://www.oracle.com/cloud/free/)
- [Oracle Cloud Free Tier FAQ](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)
- [Cloudflare Pages](https://pages.cloudflare.com/)
- [Let's Encrypt](https://letsencrypt.org/)

### NLP/Transliteration
- [Aksharamukha (120-script transliteration)](https://github.com/virtualvinodh/aksharamukha)
- [AI4Bharat IndicXlit](https://github.com/AI4Bharat/IndicXlit)
- [LibIndic Soundex](https://github.com/libindic/soundex)
- [indic_nlp_library](https://github.com/anoopkunchukuttan/indic_nlp_library)
