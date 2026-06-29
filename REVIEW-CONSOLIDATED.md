# SIR Saathi — Consolidated Review & Final Decisions

> 6 independent review agents analyzed every aspect of the project.
> This document captures the consensus decisions and final tech stack.

---

## The Revised Tech Stack (Post-Review)

### What Changed and Why

| Component | BEFORE Reviews | AFTER Reviews | Why |
|---|---|---|---|
| **Frontend** | Next.js + React + Cloudflare Pages | **Astro + Preact islands** | ~30-40 KB JS (vs 120KB Next.js). Static site generation. Preact islands for interactive features (voice input, photo scan, live search). Future-proof for chatbot UI, complex features. |
| **CSS** | Tailwind | **Tailwind CSS** (via Astro integration, built-in) | Astro has first-class Tailwind support. No extra setup. |
| **Frontend hosting** | Cloudflare Pages (separate) | **Cloudflare Pages** (free, unlimited bandwidth, global CDN) | Static output from Astro deploys perfectly on Cloudflare Pages. API calls go to Oracle VM. |
| **Backend** | FastAPI | **FastAPI** (unchanged) | Unanimous: right choice, don't switch. |
| **Database** | PostgreSQL + Meilisearch | **PostgreSQL only** | Meilisearch eliminated (failed at 100M). pg_trgm with partitioning handles everything. |
| **Search** | pg_trgm + Meilisearch fallback | **pg_trgm only, require AC selection** | Global search without AC = impossible on 24GB. Require user to select AC first. |
| **Connection pooling** | Not planned | **PgBouncer** (mandatory) | 5MB RAM, prevents connection exhaustion under load. |
| **Partitioning** | LIST(ac_number) 288 partitions | **LIST(state_code) then RANGE(ac_number) in groups of 20-30** | AC numbers not unique across states. Grouped ranges avoid 1000+ partitions at scale. |
| **Phonetic matching** | LibIndic Soundex (package) | **Inline IndicSoundex algorithm** (~200 lines) + add Double Metaphone | Package is unmaintained/broken. Inline the logic. Add DMetaphone for better coverage. |
| **Transliteration** | Aksharamukha + IndicXlit | **IndicXlit only for MVP** | Aksharamukha only needed when adding non-Devanagari states. Store 2-3 transliteration variants per name. |
| **OCR** | PaddleOCR on ARM VM | **Do NOT run OCR on production VM** | PaddleOCR segfaults on ARM64. Use Google Cloud $300 trial or Surya as one-time batch job on separate machine. |
| **AI/LLM** | Ollama + GLM-OCR + Qwen2.5-VL | **Drop entirely for MVP** | 3-5 tokens/sec on ARM CPU = unusable. Not needed — 2024 rolls need OCR, not LLM. |
| **Name embeddings** | BGE-M3 vectors (768 dims) | **Drop entirely** | 768 dims x 97M rows = 290GB. Doesn't fit. Not needed for fuzzy text search. |
| **GIN index on father_name** | Planned (GIN) | **Keep, but use GiST instead of GIN** | Father/husband name is THE differentiator for same-name voters. GiST is 3-5x smaller than GIN (2-4 GB vs 6-12 GB). Essential for accurate results. |
| **Reverse proxy** | Nginx + Let's Encrypt | **Consider Caddy** (auto-HTTPS, simpler config) or keep Nginx | Caddy = 10 lines of config, built-in SSL. |
| **Anti-scraping** | Not planned | **Cloudflare Turnstile** (mandatory before launch) | Free, invisible CAPTCHA. Without it, database scraped in days. |
| **Rate limiting** | Not planned | **Nginx rate limiting + slowapi** | 5 searches/min/IP. Non-negotiable for PII data. |
| **Field redaction** | Not planned | **Hide house number, full EPIC on initial display** | Click-to-reveal for sensitive fields. Reduces PII exposure. |
| **Privacy/Legal** | Not planned | **Privacy policy + legal basis page + erasure mechanism** | DPDPA compliance. Must have before launch. |
| **Migrations** | Not planned | **Alembic from day 1** | Schema will evolve as we discover new PDF formats. |
| **Docker** | Considered | **No Docker. Bare metal + systemd** | ARM + Docker + ML = unnecessary pain. Systemd gives you everything needed. |
| **Monitoring** | UptimeRobot | **UptimeKuma on AMD Micro VM** (self-hosted) | Free, beautiful, runs on 1GB VM. |
| **Voice input** | Not planned | **Web Speech API** (mr-IN, hi-IN, en-IN) | Critical for low-literacy users. Mic button next to search. |
| **Photo search** | Not planned | **Tesseract.js WASM** for EPIC extraction from voter card photo | Most users have their card but can't type the number. |
| **WhatsApp sharing** | Not planned | **Deep link sharing** | Viral growth mechanism. Essential for India. |

---

## The Final Stack (Minimal, Every Piece Justified)

```
┌──────────────────────────────────────────────────────┐
│                  CLOUDFLARE (Free)                    │
│   DNS + CDN + DDoS + Turnstile + API response cache  │
│                                                      │
│  ┌────────────────────┐  ┌────────────────────────┐  │
│  │ Cloudflare Pages   │  │  Cloudflare Proxy      │  │
│  │ (Frontend)         │  │  (API CDN + caching)   │  │
│  │ Astro static HTML  │  │  Cache-Control headers │  │
│  │ + Preact islands   │  │  → Oracle VM backend   │  │
│  │ ~30-40KB JS        │  │                        │  │
│  │ Global edge CDN    │  │                        │  │
│  └────────────────────┘  └───────────┬────────────┘  │
└──────────────────────────────────────┼───────────────┘
                                       │
┌──────────────────────────────────────▼───────────────┐
│           ORACLE CLOUD ARM VM (Free)                  │
│           4 cores · 24GB RAM · 200GB SSD · Mumbai     │
│                                                       │
│  ┌─────────────────────────────────────────────────┐  │
│  │  Caddy (or Nginx)                               │  │
│  │  Auto-HTTPS · Reverse Proxy · Rate Limiting     │  │
│  └───────────────┬─────────────────────────────────┘  │
│                  │                                     │
│  ┌───────────────▼─────────────────────────────────┐  │
│  │  FastAPI (JSON API only)                        │  │
│  │  uvicorn --workers 2                             │  │
│  │                                                  │  │
│  │  GET /api/search?name=...&ac=...                 │  │
│  │  GET /api/compare?epic=...                       │  │
│  │  GET /api/districts                              │  │
│  │  GET /api/acs?district=...                       │  │
│  │  GET /api/polling-stations?ac=...                │  │
│  │  GET /api/guidance?situation=...                  │  │
│  └─────────┬──────────────────┬────────────────────┘  │
│            │                  │                        │
│  ┌─────────▼──────┐  ┌───────▼────────────────────┐  │
│  │  PgBouncer     │  │  Search Logic (Python)     │  │
│  │  Connection    │  │  Phase 1: SQL (indexed)    │  │
│  │  Pooling       │  │  Phase 2: Python (ranking) │  │
│  └─────────┬──────┘  └────────────────────────────┘  │
│            │                                          │
│  ┌─────────▼──────────────────────────────────────┐  │
│  │  PostgreSQL 16                                  │  │
│  │  pg_trgm · Partitioned by state+AC range        │  │
│  │  shared_buffers=6GB · Alembic migrations        │  │
│  │  ~60-70GB data + ~15GB indexes                  │  │
│  └─────────────────────────────────────────────────┘  │
│                                                       │
│  RAM Budget:                                          │
│  PostgreSQL: 8GB | FastAPI: 1GB | PgBouncer: 5MB     │
│  Caddy: 50MB | OS+cache: 15GB                        │
│  Total: ~24GB (fits perfectly, no frontend overhead)  │
└───────────────────────────────────────────────────────┘

┌───────────────────────────────────┐
│  AMD Micro VM #1 (Free, 1GB)     │
│  UptimeKuma monitoring            │
│  Backup receiver (WAL archives)   │
└───────────────────────────────────┘

┌───────────────────────────────────┐
│  OCR (Separate, NOT on prod VM)   │
│  Google Cloud $300 trial          │
│  OR Surya on temp x86 instance    │
│  One-time batch for 2002 rolls    │
└───────────────────────────────────┘
```

---

## What We Build vs What We Drop

### MVP (Ship This)

| Feature | How | Status |
|---|---|---|
| Search by name within AC | pg_trgm + phonetic + token matching | Build |
| Search by EPIC | B-tree exact lookup | Build |
| Cross-year comparison (2002 vs 2024) | AC mapping table + age-based matching | Build |
| "What should I do?" guidance | Static content, situation-based | Build |
| Polling station finder | Already have 100K stations from API | Build |
| Marathi + Hindi + English | gettext + Jinja2 | Build |
| Voice input | Web Speech API | Build |
| Voter card photo scan | Tesseract.js WASM (EPIC extraction) | Build |
| WhatsApp sharing | Deep link | Build |
| Print voter slip | @media print CSS + QR | Build |
| Cloudflare Turnstile | Anti-scraping CAPTCHA | Build |
| Privacy policy + legal page | Static content | Build |

### Phase 2 (After Launch)

| Feature | When |
|---|---|
| AI chatbot | When funded (cloud API) |
| Form pre-filler | Month 2 |
| RTI template generator | Month 2 |
| 2026 SIR roll ingestion | When published for MH |
| West Bengal expansion | Month 3 |
| All India | Month 6+ |

### Permanently Dropped

| What | Why |
|---|---|
| Meilisearch | Failed at 100M records |
| Vector search / embeddings | 290GB, doesn't fit, not needed |
| Ollama / local LLMs | Too slow on ARM CPU |
| Docker | ARM + Docker + ML = pain |
| Next.js / React | Astro + Preact is lighter, faster, future-proof |
| PaddleOCR on production VM | Segfaults on ARM64 |
| LibIndic Soundex package | Unmaintained; inline the 200 lines |

---

## Critical Missing Pieces (Must Add)

### 1. AC Delimitation Mapping Table
Old Trombay (046) → New Anushakti Nagar (172) + Chembur (173).
Without this, cross-year comparison CANNOT WORK.
Source: 2008 Delimitation Commission order (public).

### 2. Data Validation Layer
Every record gets a quality_score. Invalid records flagged, not silently inserted.
- EPIC format validation
- Age range check (18-120)
- Non-empty name
- Gender validation

### 3. Multiple Transliteration Variants
Store 2-3 IndicXlit outputs per name. Top-1 accuracy is only 75-80%.
Top-5 accuracy is 90-95%.

### 4. Multiple Phonetic Codes
IndicSoundex (inlined) + Double Metaphone + per-token phonetic codes.
Catches name order swaps and cross-language phonetic equivalences.

### 5. Two-Phase Search (SQL + Python)
- Phase 1 (SQL): Get 200 candidates via index (pg_trgm + phonetic)
- Phase 2 (Python): Token matching, abbreviation expansion, weighted scoring, re-rank to top 20

### 6. Field Redaction
Show name + AC + part + serial on initial display.
Require click-to-reveal for: house number, age, full EPIC, polling station address.

---

## Revised Build Order

| Day | What | Details |
|---|---|---|
| **Day 1** | Parse 2002 Trombay PDF | pdfplumber + regex → structured JSON. Validate against what we saw in the PDF. |
| **Day 1** | Set up PostgreSQL | Schema with partitioning, pg_trgm, Alembic. Load 739 voters. |
| **Day 1** | Build enrichment pipeline | IndicXlit transliteration + inlined IndicSoundex + token generation. |
| **Day 2** | Build search API | FastAPI JSON API. Two-phase search (SQL candidates → Python ranking). |
| **Day 2** | Build frontend | Astro + Preact. Search page, results page. i18n (mr, en). Cloudflare Pages deploy. |
| **Day 2** | Add Cloudflare Turnstile + rate limiting | Before any public access. |
| **Day 3** | Deploy to Oracle VM | Caddy + systemd + PgBouncer. Cloudflare DNS. |
| **Day 3** | Add guidance pages + privacy policy | Static content. |
| **Day 3** | Test on mobile | Real phone, Jio 4G, verify < 3 second load. |
| **Day 4-5** | Download more 2002 PDFs (Trombay area) | Expand from 1 part to all parts for AC 046. |
| **Day 4-5** | Build AC mapping table for Mumbai Suburban | Manual from delimitation order. |
| **Day 6-7** | OCR 2024 PDF (batch, NOT on prod VM) | Surya or Google Cloud. Load 2024 data. Enable cross-year comparison. |

---

## Review Agent Consensus Summary

| Topic | Verdict | Confidence |
|---|---|---|
| FastAPI + PostgreSQL | **KEEP** | 6/6 unanimous |
| pg_trgm with partitioning | **CORRECT approach** | 6/6 unanimous |
| Next.js | **DROP** — use Astro + Preact (future-proof, interactive islands, 30-40KB) | 5/6 (all agreed Next.js is overkill; Astro chosen for extensibility) |
| Meilisearch | **DROP entirely** | 6/6 unanimous |
| Vector search / embeddings | **DROP entirely** | 6/6 unanimous |
| Ollama / local LLMs | **DROP for MVP** | 5/6 (Data Eng said "useful for unknown formats" but agreed not for MVP) |
| PaddleOCR on ARM | **DO NOT run on prod VM** | 4/6 (confirmed ARM segfault issues) |
| Docker | **NO — bare metal + systemd** | 4/6 (DevOps + Tech Stack strongly against Docker on ARM) |
| Cloudflare Turnstile | **MANDATORY before launch** | Security review: non-negotiable |
| AC mapping table | **CRITICAL missing piece** | Architecture + Data Eng both flagged |
| Data validation | **CRITICAL missing piece** | Data Eng: "never silently insert bad data" |
| PgBouncer | **ADD** | DevOps + Tech Stack both recommend |
| Alembic | **ADD from day 1** | Architecture + Tech Stack both recommend |
| Voice input | **ADD** | Frontend/UX: critical for target users |
| WhatsApp sharing | **ADD** | Frontend/UX: viral growth essential for India |
| Privacy policy | **MANDATORY before launch** | Security/Legal: DPDPA requirement |
