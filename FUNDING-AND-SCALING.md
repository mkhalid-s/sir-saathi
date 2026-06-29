# SIR Saathi - Funding, Investment & Scaling Strategy

> Compiled: 2026-04-09
> Status: Pre-build planning
> Assumption: individual open-source maintainer, no company/startup/NGO registered

---

## IMPORTANT: Maintainer Context

This plan assumes:
- **One individual maintainer** building for a public cause
- **No company, startup, or NGO** registered at the start
- **Limited upfront budget**, so the MVP should rely on free tiers and open-source tools

This changes the funding strategy significantly. Many grants (SISFS, Democracy at Work Fund, NED) require a registered entity. Cloud startup programs (AWS Activate $100K, Google for Startups $200K) need an incorporated company.

**But there is a clear path forward:**

1. **Phase 1 (NOW):** Build as an individual open-source project using free tiers + personal funds
2. **Phase 2 (With demo):** Get funded via individual-friendly programs (GitHub, Mozilla, Open Collective)
3. **Phase 3 (When ready):** Either register a Trust (cheapest NGO, needs just 2 people) OR partner with an existing NGO (ADR, DataMeet) who receives grants on your behalf

**The strategy: Build first, formalize later. A working demo unlocks everything.**

---

## Table of Contents

1. [Budget Reality Check](#1-budget-reality-check)
2. [Phase 0: Build for Free](#2-phase-0-build-for-free)
3. [Phase 1: What $1,000-$3,000 Gets You](#3-phase-1-what-1000-3000-gets-you)
4. [Funding for Solo Individual — No Company Needed](#4-funding-for-solo-individual--no-company-needed)
   - [Tier 1: Immediate (No Entity Required)](#tier-1-immediate-no-entity-required)
   - [Tier 2: With Working Demo (No Entity Required)](#tier-2-with-working-demo-no-entity-required)
   - [Tier 3: Crowdfunding (No Entity Required)](#tier-3-crowdfunding-no-entity-required)
   - [Tier 4: Free Cloud Credits (Individual)](#tier-4-free-cloud-credits-individual)
5. [The Entity Question — When and How to Formalize](#5-the-entity-question--when-and-how-to-formalize)
6. [Funding That Requires an Entity (For Later)](#6-funding-that-requires-an-entity-for-later)
7. [Strategic Partnerships](#7-strategic-partnerships)
8. [Scaling to All States](#8-scaling-to-all-states)
9. [Action Plan — Week by Week](#9-action-plan--week-by-week)
10. [Pitch Deck Outline](#10-pitch-deck-outline)
11. [Long-term Sustainability](#11-long-term-sustainability)
12. [Risk Mitigation](#12-risk-mitigation)

---

## 1. Budget Reality Check

### The Good News

SIR Saathi can be built and launched with ZERO personal investment because:

- The entire tech stack is open-source (no licensing costs)
- Cloud providers have generous always-free tiers (Oracle Cloud gives 4 ARM CPUs + 24GB RAM forever)
- Google Cloud gives $300 free credits (enough for OCR processing of initial data)
- Electoral roll data is free (public documents under Indian law)
- The social impact story unlocks donations via GitHub Sponsors, Open Collective, Milaap
- Open-source means community volunteers contribute code for free
- A domain isn't even needed initially — deploy on Vercel/Cloudflare with free subdomain

### The $0 MVP Stack (No Money Needed)

| Component | Free Service | What You Get | Limit |
|-----------|-------------|-------------|-------|
| Compute (backend) | **Oracle Cloud Always Free** | 4 ARM cores, 24GB RAM, 200GB storage | **Forever free** |
| Database | **Supabase Free** or PostgreSQL on Oracle VM | 500MB (Supabase) or unlimited (Oracle) | Permanent |
| Search | **Meilisearch on Oracle VM** | Full-text search | Self-hosted, no limit |
| Frontend | **Cloudflare Pages** | Unlimited bandwidth | Permanent |
| OCR Processing | **Google Cloud $300 trial** | ~200,000 pages of Cloud Vision OCR | 90-day trial |
| File Storage | **Cloudflare R2** | 10GB/month free | Permanent |
| Auth | **Supabase Auth** | 50,000 monthly active users | Permanent |
| Domain | **Not needed initially** | Use yourproject.pages.dev | Free |
| Code Hosting | **GitHub** | Unlimited | Permanent |
| CI/CD | **GitHub Actions** | 2,000 min/month | Permanent |
| Monitoring | **UptimeRobot free** | 50 monitors | Permanent |
| **TOTAL** | | **Full production-ready stack** | **$0/month** |

**Oracle Cloud Always Free is the game-changer:** You get 4 Ampere ARM cores + 24GB RAM + 200GB block storage PERMANENTLY FREE. That's more powerful than a $28/month Hetzner server. Enough to run PostgreSQL + Meilisearch + FastAPI backend for millions of voter records.

### What It Actually Costs

| Stage | Cost | What You Get |
|-------|------|-------------|
| MVP (2 districts) | **$0** | Proof of concept, working search for ~5-10 lakh voters |
| MVP (WB + MH full) | **$0** | 16.8 crore voters searchable (may need to upgrade to paid if Oracle free tier maxes out) |
| Scale (all India) | $500-1,000/mo | 97 crore voters — funded by grants/donations by this point |
| MVP (WB + MH full) | $500-800 | $1,500-2,000 | Working product for 16.8 crore voters |
| Scale (all India) | $500-1,000/mo | $1,500-2,500/mo | 97 crore voters covered |

An MVP can be built with a small budget if cloud credits and free tiers are used carefully.

---

## 2. Phase 0: Build for Free ($0)

Every component of the MVP has a free tier or open-source alternative:

### Infrastructure (Free Tiers)

| Component | Free Option | Limit | Enough for MVP? |
|-----------|------------|-------|-----------------|
| Code Hosting | GitHub (public repo) | Unlimited | Yes |
| Frontend Hosting | Vercel Free Tier | 100GB bandwidth/mo | Yes |
| Frontend Alt | Cloudflare Pages | Unlimited bandwidth | Yes |
| Database | Supabase Free Tier | 500MB PostgreSQL | Yes (for 2-3 districts) |
| Database Alt | Railway Free Tier | 1GB, 500 exec hours | Yes |
| Database Alt | Neon Free Tier | 512MB PostgreSQL | Yes |
| Search | Supabase full-text search | Included in free tier | Yes (for MVP) |
| Search Alt | Self-host Meilisearch | Requires VPS | Yes (with $5/mo VPS) |
| Object Storage | Cloudflare R2 | 10GB free | Yes |
| Object Storage Alt | Supabase Storage | 1GB free | Yes |
| CI/CD | GitHub Actions | 2,000 min/mo free | Yes |
| Monitoring | Uptime Kuma (self-hosted) | Free | Yes |
| Analytics | Plausible (self-hosted) or Umami | Free | Yes |
| SSL | Let's Encrypt | Free | Yes |

### Software Stack (All Free/Open-Source)

| Component | Tool | License | Cost |
|-----------|------|---------|------|
| Frontend | Next.js (React) | MIT | $0 |
| PWA Support | next-pwa | MIT | $0 |
| Backend/API | Next.js API Routes or FastAPI (Python) | MIT/BSD | $0 |
| Database | PostgreSQL | PostgreSQL License | $0 |
| Search Engine | OpenSearch or Meilisearch | Apache 2.0 / MIT | $0 |
| OCR | PaddleOCR | Apache 2.0 | $0 |
| PDF Extraction | pdfplumber | MIT | $0 |
| Transliteration | Aksharamukha | AGPL-3.0 | $0 |
| AI Transliteration | IndicXlit | MIT | $0 |
| Phonetic Matching | LibIndic Soundex | LGPL | $0 |
| NLP | indic_nlp_library | MIT | $0 |
| Record Linkage | Splink | MIT | $0 |
| i18n (Multilingual) | next-intl or react-i18next | MIT | $0 |

### AI/LLM (Free or Low-Cost Tiers)

| Service | Free Tier | For What |
|---------|----------|----------|
| Claude API (Anthropic) | Limited free credits / startup program | AI chatbot |
| Groq | Free tier (rate limited) | Fast inference fallback |
| Together AI | $5 free credits | Open-source model hosting |
| Ollama (self-hosted) | Free | Run open models locally |

---

## 3. The $0 Build Plan — Step by Step

### What You Set Up (All Free)

| Step | Service | Action | Time |
|------|---------|--------|------|
| 1 | GitHub | Create public repo `sir-saathi`, MIT license | 5 min |
| 2 | Oracle Cloud | Sign up for Always Free tier (needs credit card for verification, NOT charged) | 15 min |
| 3 | Oracle Cloud | Create ARM VM (4 cores, 24GB RAM) — install PostgreSQL + Meilisearch | 1 hour |
| 4 | Cloudflare | Sign up, create Pages project for frontend | 10 min |
| 5 | Google Cloud | Sign up for $300 free trial (for OCR later) | 10 min |
| 6 | Supabase | Sign up free tier (backup database + auth) | 5 min |
| 7 | GitHub Sponsors | Enable on your profile | 5 min |
| 8 | Open Collective | Create Collective, apply to Open Source Collective as fiscal host | 15 min |

**Total setup time: ~2 hours. Total cost: $0.**

### When Money Comes In (From Donations/Grants)

Once you start receiving donations through GitHub Sponsors / Open Collective / Milaap, here's the upgrade path:

| Monthly Income | What to Upgrade | Why |
|---------------|----------------|-----|
| $0/mo | Stay on free tiers | Everything works |
| $50/mo | Buy domain (sirsaathi.in ~$10/year) | Professional URL |
| $100/mo | Add Hetzner VPS as backup ($7/mo) | Redundancy |
| $200/mo | SMS notifications via MSG91 | User engagement |
| $500/mo | Managed database (Supabase Pro $25/mo) + Claude API for chatbot | Better reliability + AI features |
| $1,000+/mo | Full production stack | Scale to all India |

### If You Get ANY Personal Funds Later

Even $100-200 makes a difference:

| Amount | Best Use |
|--------|---------|
| $10 | Domain name (sirsaathi.in) |
| $50 | Domain + 3 months Hetzner VPS backup |
| $100 | Above + GPU spot instance for initial OCR batch |
| $200 | Above + Claude API credits for chatbot prototype |


### What Hetzner Gets You (Best Value for India-Proximate Hosting)

Hetzner's ARM servers (CAX line) offer exceptional value:

| Server | Specs | Monthly Cost |
|--------|-------|-------------|
| CAX11 | 2 vCPU, 4GB RAM, 40GB SSD | ~$4/mo |
| CAX21 | 4 vCPU, 8GB RAM, 80GB SSD | ~$7/mo |
| CAX31 | 8 vCPU, 16GB RAM, 160GB SSD | ~$14/mo |
| CAX41 | 16 vCPU, 32GB RAM, 320GB SSD | ~$28/mo |

A CAX31 ($14/mo) can comfortably run PostgreSQL + OpenSearch/Meilisearch + the API for the MVP scale.

---

## 4. Funding for Solo Individual — No Company Needed

**Everything in this section can be accessed by YOU, right now, as one person with no registered entity.**

### Tier 1: Immediate (No Entity Required)

#### GitHub Sponsors

- **URL:** https://github.com/sponsors
- **What:** Receive recurring monthly donations from anyone
- **Fee:** 0% (GitHub takes nothing)
- **Requirements:** Just a GitHub account with an active open-source project
- **How It Works:** Enable Sponsors on your profile, set tiers ($1, $5, $10, $25/mo), people donate directly
- **Realistic Income:** $50-$500/month once project has visibility
- **Action:** Enable as soon as repo is created

#### Open Collective via Open Source Collective (Fiscal Host)

- **URL:** https://opencollective.com/opensource
- **What:** Open Source Collective is a US 501(c)(6) nonprofit that acts as your "fiscal host" — they hold money on your behalf, handle taxes, issue receipts to donors
- **Fee:** ~10% of donations
- **Requirements:** An open-source project (no company needed)
- **Why This Is Key:** This gives you a legal entity to receive grants and donations WITHOUT registering a company. Open Source Collective is your fiscal sponsor.
- **How It Works:**
  1. Create a Collective on Open Collective for "SIR Saathi"
  2. Apply to Open Source Collective as fiscal host
  3. Once accepted, you can receive donations, submit expenses, everything is transparent
  4. Many grants can be paid through Open Source Collective
- **Realistic Income:** Depends on visibility; popular civic projects get $500-$5,000/month
- **Action:** Apply immediately after creating the GitHub repo

#### Liberapay

- **URL:** https://liberapay.com/
- **What:** Recurring donations platform for creators/developers
- **Fee:** 0% platform fee (payment processor fees only ~2-3%)
- **Requirements:** Individual, no entity needed
- **How:** Create account, link to project, share
- **Note:** Smaller community than GitHub Sponsors, but complementary

### Tier 2: With Working Demo (No Entity Required)

These require a working project/demo to apply — build first, then apply.

#### GitHub Accelerator — $20,000 Stipend

- **URL:** https://github.com/open-source/accelerator
- **What:** $20,000 cash stipend + 10 weeks of mentorship
- **Who:** Individual open-source maintainers
- **Requirements:** Active open-source project, able to commit to 10-week program
- **Why SIR Saathi Qualifies:** Open-source civic tech with massive impact
- **Application:** Annual cohort, watch for next call
- **Action:** Build MVP first, apply with working demo

#### Mozilla Democracy x AI Incubator — $50,000

- **URL:** https://opportunitydesk.org/2026/02/20/mozilla-foundation-incubator-democracy-x-ai-cohort-2026/
- **What:** $50,000 + 12 months of mentorship, cohort support, expert access
- **Who:** Researchers, technologists, nonprofits, advocates — INDIVIDUALS welcome
- **Focus:** AI + democracy intersection (SIR Saathi uses AI for voter data processing + chatbot = perfect fit)
- **Requirements:**
  - Must open-source code or provide roadmap to open-sourcing
  - Must be able to legally receive funds from US 501(c)(3) — Open Source Collective solves this!
  - Applications in English
- **2026 Deadline:** Was March 16, 2026 — may have passed for this cohort
- **Action:** Watch for next cohort announcement; apply with working demo
- **This is THE best fit for SIR Saathi — democracy + AI + open-source**

#### Mozilla Fellows Program — $100,000-$125,000

- **URL:** https://opportunitydesk.org/2025/12/25/mozilla-foundation-fellows-program-2026/
- **What:** $100,000-$125,000 total investment, up to 10 fellows selected
- **Who:** Individual visionary leaders building better technology futures
- **Requirements:** Track record of work in technology + social impact
- **Why You'd Qualify:** Building open-source AI-powered tool for voter empowerment at national scale
- **Action:** Watch for next application cycle; this is a stretch goal but worth pursuing

#### GitHub Secure Open Source Fund

- **URL:** https://github.com/open-source/github-secure-open-source-fund
- **What:** Funding for open-source maintainers focused on security
- **Who:** Individual maintainers
- **Requirements:** Valid open-source license, active project
- **Note:** Security focus — less direct fit, but voter data privacy/security angle works

### Tier 3: Crowdfunding (No Entity Required)

As an individual, you can run crowdfunding campaigns on these platforms:

#### Milaap — Best for Indian Social Causes

- **URL:** https://milaap.org/
- **Fee:** 0% platform fee
- **Who:** Any individual in India
- **Requirements:** Aadhaar/PAN, bank account — that's it
- **Why Best Choice:** India's largest crowdfunding platform, zero fee, built for social causes
- **Campaign Strategy:**
  - Title: "Help 97 Crore Indians Find Their Names on Voter Lists"
  - Include 2-minute video showing the problem (confused voters, crashed websites, missing names)
  - Show your demo/prototype
  - Set initial goal low (INR 50,000 = ~$600) for momentum
  - Stretch goals: INR 2 Lakh, 5 Lakh, 10 Lakh
- **Realistic Target:** INR 1-5 Lakh ($1,200-$6,000)
- **Action:** Launch after you have a working demo (even basic)

#### Ketto

- **URL:** https://www.ketto.org/
- **Fee:** 5-6%
- **Who:** Individuals
- **Larger platform but has fees

#### Buy Me a Coffee / Ko-fi

- **URL:** https://www.buymeacoffee.com/ / https://ko-fi.com/
- **Fee:** 0-5%
- **Good for:** Small recurring donations from international supporters
- **Action:** Add "Buy Me a Coffee" button to the project website

### Tier 4: Free Cloud Credits (Individual — No Company)

| Service | Free Tier | Requirements | What You Get |
|---------|----------|-------------|-------------|
| **Google Cloud Free Trial** | $300 credits + 90 days | Gmail account | Compute, Cloud Vision OCR, Storage |
| **Google Developer Program (Premium)** | $500/year cloud credits | Google developer profile | Annual credits |
| **AWS Free Tier** | 12 months of services | AWS account (personal) | EC2, RDS, S3, Lambda |
| **Oracle Cloud Free Tier** | 2 AMD VMs + 4 ARM VMs FOREVER | Oracle account | Always-free compute (generous!) |
| **Cloudflare** | Pages, Workers, R2 (10GB), D1 DB | Cloudflare account | Frontend hosting, edge compute, storage |
| **Vercel** | Free tier hosting | GitHub account | Next.js hosting |
| **Supabase** | 500MB PostgreSQL + auth + storage | GitHub account | Database + backend |
| **Railway** | $5 free/month | GitHub account | Easy app deployment |
| **Hetzner** | No free tier but cheapest VPS | Payment method | $4/mo for 2 vCPU, 4GB RAM |

**The Oracle Cloud Always Free Tier is huge:** 4 ARM Ampere A1 cores + 24GB RAM — enough to run PostgreSQL + Meilisearch + API for the MVP permanently for $0.

**Combined free strategy:**
- Oracle Cloud (always-free VMs) → PostgreSQL + Search + API backend
- Cloudflare Pages → Frontend hosting (unlimited bandwidth)
- Google Cloud $300 → OCR processing (Cloud Vision API)
- Supabase → Auth + user management
- Total: **$0/month** for MVP infrastructure

---

## 5. The Entity Question — When and How to Formalize

### You Don't Need an Entity to START

Build the tool, launch it, get users, prove impact. Entity comes later.

### When You'll Need an Entity

| Trigger | Why | What Entity |
|---------|-----|-------------|
| Applying for grants >$5,000 | Most grants require a legal entity | Trust or Section 8 Company |
| Receiving CSR funding | Companies need to donate to registered nonprofits | Section 8 Company with 80G |
| Government partnership | ECI/State ECs deal with registered organizations | Trust or Section 8 |
| Hiring people | Need to issue employment contracts | Any registered entity |
| Receiving international funds | FCRA registration required | Section 8 Company |

### Cheapest Path: Register a Trust (When Ready)

| Requirement | Details |
|-------------|---------|
| Minimum members | **Just 2 people** (you + one trusted friend/family) |
| Cost | INR 5,000-15,000 (~$60-$180) |
| Time | 2-4 weeks |
| Documents | Trust deed, IDs of trustees, address proof |
| Registered under | State Trust Act (varies by state) |
| Annual compliance | Minimal — file trust returns |
| Can receive donations? | Yes |
| Can apply for grants? | Yes |
| Tax exemption (12A)? | Can apply separately |
| Donor tax benefit (80G)? | Can apply separately |

**This is the simplest path** — find one trustworthy person, register a Trust for INR 5,000-15,000, and you unlock all grant eligibility.

### Alternative: Use an Existing NGO as Fiscal Sponsor

Instead of registering your own entity, partner with an existing NGO:

| Organization | Why They'd Partner | What You Get |
|-------------|-------------------|-------------|
| **ADR** | Aligned mission (voter empowerment) | Their legal entity receives grants; they channel funds to the project |
| **DataMeet** | Open data community | Community fiscal sponsorship |
| **Any local NGO** working on voter rights | Ground-level access | Legal entity + field volunteers |

**How fiscal sponsorship works:**
1. You find a grant that requires an NGO
2. Partner NGO applies for the grant (or you apply naming them as fiscal sponsor)
3. Grant money goes to the NGO's account
4. NGO disburses funds to you as project expenses
5. NGO takes 5-15% as administrative fee

**Open Source Collective (international) does this too** — they're a US 501(c)(6) that can receive funds on behalf of open-source projects globally.

### Entity Comparison Table

| Type | Min People | Cost (INR) | Time | Best For |
|------|-----------|-----------|------|----------|
| No entity (individual + OSC) | 1 | 0 | Immediate | Starting out, international donations |
| Trust | 2 | 5,000-15,000 | 2-4 weeks | Indian grants, simplicity |
| Society | 7 | 5,000-20,000 | 4-8 weeks | Community-driven projects |
| Section 8 Company | 2 directors + 2 members | 15,000-50,000 | 2-3 months | Large grants, CSR, FCRA |

**Recommendation:** Start with Open Source Collective (international fiscal host, $0, immediate). Register a Trust when you need Indian grants (after demo is ready, costs INR 5K-15K).

---

## 6. Funding That Requires an Entity (For Later)

These become available once you register a Trust or partner with an NGO:

### Government Grants (Need DPIIT-recognized Startup OR NGO)

#### Startup India Seed Fund Scheme (SISFS)
- **Amount:** Up to INR 20 Lakhs (~$24,000) as grant
- **Requires:** DPIIT-recognized startup (Private Ltd or LLP), incorporated <2 years
- **If you go startup route:** Register a Private Limited company (~INR 10,000-20,000) + get DPIIT recognition
- **Priority sectors:** Social impact explicitly listed

#### MeitY Grants
- **Amount:** Varies (up to INR 7 crore for TIDE 2.0)
- **Requires:** Registered entity
- **Relevant programs:** Digital India, TIDE 2.0

### International Democracy Grants (Need NGO or Fiscal Sponsor)

#### Democracy at Work Fund
- **Amount:** $10,000-$80,000 for 18 months
- **Requires:** Registered organization (Trust/Society/Section 8 qualifies, OR Open Source Collective as fiscal host — verify)
- **Focus:** Frontline democracy organizations in Asia

#### National Endowment for Democracy (NED)
- **Amount:** 2,000+ grants/year globally
- **Requires:** NGO/nonprofit
- **Focus:** Civic education, democratic reforms

#### Open Society Foundations
- **Amount:** $10K-$500K+
- **Requires:** Registered entity
- **Focus:** Democratic governance, digital rights

#### Omidyar Network India
- **Amount:** $100K+ (equity or grant)
- **Requires:** Registered entity
- **Focus:** Civic tech, digital identity — very strong fit

### Cloud Credits (Need Startup Registration)

#### AWS Activate — $5,000 to $100,000
- **Requires:** DPIIT-recognized startup
- **The $5K tier:** Just needs Startup India registration
- **The $100K tier:** Needs accelerator affiliation

#### Google for Startups Cloud — $100,000-$350,000
- **Requires:** Incorporated entity (Pvt Ltd or LLP)

#### Microsoft for Startups — $150,000
- **Requires:** Registered startup (<7 years, <$1M revenue)

### CSR Funding (Need Section 8 Company with 80G)
- **Amount:** Potentially INR 5-50 Lakhs+ per donor
- **Requires:** Section 8 Company with 12A + 80G tax exemption
- **Target donors:** Infosys Foundation, Wipro, TCS, Azim Premji Foundation
- **Timeline:** Realistically 6-12 months to set up and attract

---

## 7. Strategic Partnerships

- **URL:** https://aws.amazon.com/startups/credits
- **Amount:** $5,000 to $100,000 in AWS credits
- **Eligibility:**
  - Must be a startup (less than 10 years old)
  - DPIIT-recognized startups via Startup India get automatic $5,000
  - Startups affiliated with qualifying accelerators/incubators get up to $100,000
- **How to Apply:**
  1. Register on Startup India (https://www.startupindia.gov.in/) — free
  2. Get DPIIT recognition (takes 1-2 weeks)
  3. Apply for AWS Activate via the AWS portal
  4. For $100K tier: join a qualifying accelerator (many are free to join)
- **What It Covers:** EC2, RDS (PostgreSQL), OpenSearch Service, S3, Lambda, SageMaker (for ML/OCR)
- **Timeline:** 2-4 weeks from application to credits

#### Google for Startups Cloud Program

- **URL:** https://cloud.google.com/startup
- **Amount:**
  - Start tier: $100,000 in Google Cloud credits over 2 years
  - Scale tier: $200,000 over 2 years
  - AI-focused startups: up to $350,000
- **Eligibility:**
  - Must be incorporated (Pvt Ltd, LLP, or Section 8 company)
  - Must not have previously received Google Cloud credits
  - Seed to Series A stage
- **How to Apply:** Direct application on Google Cloud for Startups portal
- **What It Covers:** Compute Engine, Cloud SQL, Cloud Vision API (OCR), Cloud Functions, BigQuery, Vertex AI
- **Why Apply:** Google Cloud Vision API is one of the best OCR options for Indian languages — $100K in credits = millions of pages of free OCR
- **Timeline:** 2-6 weeks

#### Microsoft for Startups (Founders Hub)

- **URL:** https://www.microsoft.com/en-us/startups
- **Amount:** Up to $150,000 in Azure credits
- **Eligibility:** Startups less than 7 years old, revenue under $1M
- **What It Covers:** Azure VMs, Azure AI (OCR), Cosmos DB, Azure Search
- **Timeline:** 1-2 weeks (fastest approval)

#### AWS Nonprofit Credit Program

- **URL:** https://aws.amazon.com/government-education/nonprofits/nonprofit-credit-program/
- **Eligibility:** Must be a registered nonprofit (Section 8 company in India)
- **How:** Apply through TechSoup India (https://www.techsoup.org/india)
- **Amount:** Varies, typically $1,000-$5,000
- **Note:** If you register as Section 8 company (nonprofit), this is an easy path

#### Anthropic (Claude API Credits)

- **How:** Apply to Anthropic's startup program or social impact program
- **What It Covers:** Claude API usage for the chatbot feature
- **Why:** Our chatbot is powered by Claude — Anthropic has interest in social impact use cases
- **Action:** Email partnerships@anthropic.com describing the project

### Tier 2: Government Grants

#### Startup India Seed Fund Scheme (SISFS)

- **URL:** https://seedfund.startupindia.gov.in/
- **Amount:** Up to **INR 20 Lakhs (~$24,000 USD)** as grant (non-equity)
  - Up to INR 50 Lakhs as debt/convertible debenture
- **Eligibility:**
  - DPIIT-recognized startup
  - Incorporated not more than 2 years ago at time of application
  - Using technology in core product/service
  - Not received more than INR 10 Lakhs from other government schemes
  - Indian promoters hold minimum 51% shareholding
- **Process:**
  1. Get DPIIT recognition on Startup India portal
  2. Apply to up to 3 incubators from SISFS approved list
  3. Incubator evaluates within 45 days
  4. If selected, funds disbursed through incubator
- **Priority Sectors:** Social impact is explicitly listed as a priority
- **Why SIR Saathi Qualifies:**
  - Technology-driven solution
  - Massive social impact (97 crore voters)
  - Innovative (no existing tool does this)
  - Scalable across India
- **Timeline:** 2-3 months from application to funding
- **Action Items:**
  1. Register as Private Limited company or LLP (costs ~INR 5,000-10,000)
  2. Get DPIIT recognition
  3. Identify 3 SISFS-approved incubators
  4. Prepare pitch deck and financial projections

#### MeitY (Ministry of Electronics & IT) Grants

- **URL:** https://www.meity.gov.in/
- **Programs:**
  - Digital India programme — supports GovTech initiatives
  - TIDE 2.0 (Technology Incubation and Development of Entrepreneurs)
  - Grants up to INR 7 crore for tech entrepreneurship
- **Why Relevant:** SIR Saathi directly supports Digital India's mission of citizen services

#### State Government Innovation Funds

- **West Bengal:** WBIIDC (WB Industrial Infrastructure Development Corporation) startup support
- **Maharashtra:** Maharashtra Startup Week, Maharashtra Innovation Society
- **Action:** Apply to state-specific innovation programs in both states

### Tier 3: International Democracy & Civic Tech Grants

#### Democracy at Work Fund 2025/2026

- **URL:** https://www.ngobox.org/full_grant_announcement_Applications-Invited-for-the-Democracy-at-Work-Fund-2025-2026-Call--_13042
- **Amount:** $10,000 to $80,000 for up to 18 months
- **Focus:** Frontline democracy organizations in Asia, Africa, South America
- **Why SIR Saathi Qualifies:**
  - Directly empowers voters in a functioning democracy
  - Addresses systemic voter exclusion
  - Technology-driven, scalable approach
- **How to Apply:** Direct application; pools funding from multiple democracy funders
- **Timeline:** Rolling applications; projects start from February 2026 (current cycle)

#### National Endowment for Democracy (NED)

- **URL:** https://www.ned.org/apply-for-grant/
- **Amount:** Varies; NED provides 2,000+ grants annually globally
- **Focus:** Civic education, democratic participation, election integrity
- **Eligibility:** NGOs/nonprofits working on democratic reforms
- **Why SIR Saathi Qualifies:**
  - Voter empowerment and election integrity
  - Addresses voter suppression/disenfranchisement concerns
  - Transparent, open-source approach
- **Note:** Would need to register as NGO/Section 8 company

#### Civic Innovation Fund (European, but open)

- **URL:** https://thecivics.eu/projects/civic-innovation-fund/
- **Amount:** EUR 10,000-12,000 for 12 months
- **Focus:** Civic education apps, democratic innovation
- **Timeline:** Annual call for proposals

#### Open Society Foundations

- **URL:** https://www.opensocietyfoundations.org/grants
- **Focus:** Democratic governance, digital rights, civic engagement
- **Amount:** Varies widely ($10K-$500K+)
- **Relevance:** Very strong alignment with voter rights and democratic participation

#### Ford Foundation

- **URL:** https://www.fordfoundation.org/
- **Focus:** Civic engagement, technology and society
- **Note:** Larger grants, typically for established organizations; consider for later stage

#### Omidyar Network India

- **URL:** https://www.omidyarnetwork.in/
- **Focus:** Digital identity, governance, civic tech
- **Relevance:** Very strong — they specifically fund civic tech in India
- **Amount:** Equity investment or grants, typically $100K+

#### Luminate (Omidyar Group)

- **URL:** https://luminategroup.com/
- **Focus:** Civic empowerment, data & digital rights
- **Relevance:** Directly aligned with SIR Saathi's mission

### Tier 4: Crowdfunding

#### Milaap (Recommended First)

- **URL:** https://milaap.org/
- **Platform Fee:** 0% (they charge no platform fee)
- **Reach:** India's largest crowdfunding platform
- **Best For:** Social cause campaigns, grassroots projects
- **How to Maximize:**
  - Create a compelling 2-minute video showing the problem (people unable to find names, confusion at BLO offices)
  - Set initial goal low ($500-1,000) for momentum
  - Share on social media, WhatsApp groups, Twitter/X
  - Get endorsements from ADR, civic activists
- **Target:** INR 5-10 Lakhs ($6,000-$12,000)
- **The Pitch:** "6 crore Indians are at risk of losing their right to vote. We're building a free tool to help them. Support democracy."

#### Ketto

- **URL:** https://www.ketto.org/
- **Platform Fee:** 5-6%
- **Reach:** 2 lakh+ campaigns hosted, large Indian user base
- **Best For:** Broader social impact, healthcare, education — but civic causes work too

#### GitHub Sponsors

- **URL:** https://github.com/sponsors
- **Platform Fee:** 0%
- **Best For:** Ongoing open-source project funding
- **How:** Enable GitHub Sponsors on the sir-saathi repo
- **Target:** $100-500/month from developer community

#### Open Collective

- **URL:** https://opencollective.com/
- **Platform Fee:** 5-10%
- **Best For:** Transparent, accountable open-source funding
- **How:** Create a Collective for SIR Saathi, share expenses publicly
- **Why:** Transparency builds donor trust — they see exactly where money goes

### Tier 5: Strategic Partnerships

#### Association for Democratic Reforms (ADR)

- **Website:** https://adrindia.org/
- **What They Do:** Run MyNeta.info (election candidate data), won NASSCOM ICT Innovation Award
- **What They Bring:**
  - Brand credibility — 25+ years in democratic reform
  - Technical infrastructure and data experience
  - Media relationships (their reports get national coverage)
  - Potential co-grant applications (stronger together)
- **How to Approach:**
  - Email: info@adrindia.org
  - LinkedIn: ADR India & MyNeta
  - Show a working demo (even for 1 district)
  - Propose collaboration, not competition
- **Pitch:** "We've built what MyNeta does for candidates, but for voters. Let's partner to cover both sides of the election."

#### DataMeet

- **Website:** https://datameet.org/
- **GitHub:** https://github.com/datameet
- **What They Bring:**
  - India's largest open data community
  - Technical volunteers (data engineers, mappers)
  - Community events and hackathons
  - Experience with election data (india-election-data repo)
- **How to Approach:**
  - Join their mailing list / Telegram group
  - Present at their meetup/hackathon
  - Invite them as contributors to the repo

#### AI4Bharat (IIT Madras)

- **Website:** https://ai4bharat.iitm.ac.in/
- **What They Built:** IndicXlit, IndicNLP, IndicTrans — the exact NLP tools we need
- **What They Bring:**
  - Research partnership (academic credibility)
  - Custom model fine-tuning for electoral roll data
  - Student volunteers
  - Potential research funding through IIT channels
- **How to Approach:**
  - Email the lab directly
  - Propose a research collaboration: "Indian language OCR accuracy on electoral roll data"
  - Offer attribution and co-authorship on papers

#### Civic Data Lab

- **Website:** https://civicdatalab.in/
- **What They Bring:**
  - Data pipeline expertise
  - Government partnership experience
  - Open data advocacy
- **How to Approach:** Direct outreach with project proposal

#### Election Commission of India (ECI)

- **Website:** https://www.eci.gov.in/
- **ICT Apps Portal:** https://www.eci.gov.in/ict-app
- **Why Approach:**
  - If ECI adopts or endorses SIR Saathi, we get instant national reach
  - ECI already has an ICT apps ecosystem
  - They may provide data access or API support
- **How to Approach:**
  - Build first, approach later (with working product)
  - File RTI to understand their ICT partnership process
  - Connect through ADR or other intermediary
- **Risk:** ECI may see this as competition or political — tread carefully, stay non-partisan
- **Timing:** Approach after elections, not during

#### TechSoup India

- **Website:** https://www.techsoup.org/
- **What They Bring:**
  - Discounted/donated tech products for nonprofits
  - AWS nonprofit credits distribution
  - Microsoft 365 nonprofit licenses
  - Software donations
- **Requirement:** Must be registered as nonprofit (Section 8 company)

### Tier 6: Long-term Sustainability

#### Revenue Streams (Keeping the Tool FREE for Citizens)

| Model | Description | Estimated Revenue | Timeline |
|-------|-------------|-------------------|----------|
| **Grants (recurring)** | Annual applications to democracy/civic tech grants | $10K-$80K/year | Ongoing |
| **CSR Funding** | Indian companies with >5 crore profit must spend 2% on CSR; voter empowerment qualifies under "promoting education" and "rural development" | $10K-$100K/year | After 1 year |
| **Government Adoption** | State Election Commissions or ECI adopt and fund the tool | Infrastructure + team covered | After 2 years |
| **API Licensing** | Other civic tech orgs, media companies, researchers use parsed voter data API | $5K-$20K/year | After 6 months |
| **Donations** | Ongoing Milaap/GitHub Sponsors from grateful citizens | $1K-$5K/year | Ongoing |
| **Consulting** | Help other countries build similar tools (Bangladesh, Pakistan, Nigeria, Indonesia) | $10K-$50K/project | After 2 years |
| **Training & Workshops** | Train BLOs, NGOs, civic workers on using the tool | $2K-$10K/year | After 1 year |

#### CSR Funding — Detailed

Under India's Companies Act 2013, Section 135, companies with net worth >= INR 500 crore, or turnover >= INR 1000 crore, or net profit >= INR 5 crore must spend 2% of average net profit on CSR activities.

Eligible CSR activities that SIR Saathi falls under:
- Clause (ii): Promoting education, including special education
- Clause (v): Rural development projects
- Clause (ix): Contributions to technology incubators in academic institutions
- Clause (x): Rural development

**Target CSR Donors:**
- Infosys Foundation (Infosys' CSR arm)
- Wipro Foundation
- TCS Foundation
- Reliance Foundation
- Azim Premji Foundation
- Tata Trusts

**How to Approach:**
- Register as Section 8 company (nonprofit)
- Get 80G tax exemption certificate (allows donors to claim tax benefit)
- Apply to CSR portals of target companies
- Show measurable impact (# of voters helped, # of corrections facilitated)

---

## 5. Scaling to All States

### India's Electoral Scale

| Metric | Number |
|--------|--------|
| States | 28 |
| Union Territories | 8 |
| Total Assembly Constituencies | ~4,120 |
| Total Lok Sabha Constituencies | 543 |
| Total Registered Voters (2024) | ~97 crore (~970 million) |
| Total Polling Stations | ~10.5 lakh (~1.05 million) |
| Official Languages | 22 (+ English) |

### State-by-State Data

| # | State/UT | ACs | Approx Voters (Cr) | Script | Language |
|---|----------|-----|---------------------|--------|----------|
| 1 | Uttar Pradesh | 403 | 15.0 | Devanagari | Hindi |
| 2 | Maharashtra | 288 | 9.7 | Devanagari | Marathi |
| 3 | West Bengal | 294 | 7.1 | Bengali | Bengali |
| 4 | Tamil Nadu | 234 | 6.3 | Tamil | Tamil |
| 5 | Bihar | 243 | 7.3 | Devanagari | Hindi |
| 6 | Madhya Pradesh | 230 | 5.3 | Devanagari | Hindi |
| 7 | Karnataka | 224 | 5.3 | Kannada | Kannada |
| 8 | Rajasthan | 200 | 5.1 | Devanagari | Hindi |
| 9 | Gujarat | 182 | 4.9 | Gujarati | Gujarati |
| 10 | Andhra Pradesh | 175 | 4.1 | Telugu | Telugu |
| 11 | Kerala | 140 | 2.7 | Malayalam | Malayalam |
| 12 | Odisha | 147 | 3.3 | Odia | Odia |
| 13 | Telangana | 119 | 3.2 | Telugu | Telugu |
| 14 | Assam | 126 | 2.4 | Assamese/Bengali | Assamese |
| 15 | Jharkhand | 81 | 2.3 | Devanagari | Hindi |
| 16 | Punjab | 117 | 2.1 | Gurmukhi | Punjabi |
| 17 | Chhattisgarh | 90 | 2.0 | Devanagari | Hindi |
| 18 | Haryana | 90 | 1.9 | Devanagari | Hindi |
| 19 | Delhi | 70 | 1.5 | Devanagari | Hindi |
| 20 | Uttarakhand | 70 | 0.8 | Devanagari | Hindi |
| 21 | Himachal Pradesh | 68 | 0.5 | Devanagari | Hindi |
| 22 | Tripura | 60 | 0.3 | Bengali | Bengali |
| 23 | Meghalaya | 60 | 0.2 | Latin | English/Khasi |
| 24 | Manipur | 60 | 0.2 | Bengali/Meitei | Manipuri |
| 25 | Nagaland | 60 | 0.1 | Latin | English |
| 26 | Goa | 40 | 0.1 | Devanagari | Konkani |
| 27 | Arunachal Pradesh | 60 | 0.1 | Latin | English |
| 28 | Mizoram | 40 | 0.08 | Latin | Mizo |
| 29 | Sikkim | 32 | 0.04 | Devanagari | Nepali |
| 30 | Puducherry | 30 | 0.1 | Tamil | Tamil |
| 31 | J&K | 90 | 0.7 | Arabic/Devanagari | Urdu/Hindi |
| 32 | Others (UTs) | ~30 | 0.1 | Various | Various |

### Architecture Designed for Scale

The system is **state-agnostic by design**. Each state is a configuration:

```yaml
# Example: Adding a new state
states:
  west_bengal:
    eci_code: "S25"
    ceo_portal: "ceowestbengal.wb.gov.in"
    languages: ["bengali", "english"]
    scripts: ["bengali", "latin"]
    ocr_model: "paddleocr_bengali"
    has_municipal_rolls: false
    has_2002_roll: true
    roll_2002_url: "ceowestbengal.wb.gov.in/roll_dist"
    pdf_parser: "wb_parser_v1"
    sir_categories: ["approved", "deleted", "under_adjudication"]

  maharashtra:
    eci_code: "S13"
    ceo_portal: "ceo.maharashtra.gov.in"
    languages: ["marathi", "english"]
    scripts: ["devanagari", "latin"]
    ocr_model: "paddleocr_devanagari"
    has_municipal_rolls: true
    municipal_portal: "localbodyvoterlist.maharashtra.gov.in"
    municipal_corporations: 29
    has_2002_roll: true
    roll_2002_url: "ceoelection.maharashtra.gov.in/2002/2002rolldata.aspx"
    pdf_parser: "mh_parser_v1"

  # Adding a new state = adding this config + writing a PDF parser
  tamil_nadu:
    eci_code: "S22"
    ceo_portal: "elections.tn.gov.in"
    languages: ["tamil", "english"]
    scripts: ["tamil", "latin"]
    ocr_model: "paddleocr_tamil"
    has_municipal_rolls: true
    has_2002_roll: true  # TBD - needs verification
    pdf_parser: "tn_parser_v1"
```

**Adding a new state requires:**
1. A state config (5 minutes)
2. A PDF parser (if the format differs from existing states) (2-8 hours)
3. OCR model configuration (if new script) (1 hour)
4. Downloading and processing PDFs (automated, 1-3 days)

### Scaling Roadmap

| Phase | Timeline | States | New Voters | Cumulative | New Languages |
|-------|----------|--------|-----------|------------|---------------|
| **MVP** | Months 1-3 | West Bengal, Maharashtra | 16.8 Cr | 16.8 Cr | Bengali, Marathi, Hindi, English |
| **Wave 2** | Months 4-6 | Tamil Nadu, Kerala, Assam, UP | ~25.4 Cr | 42.2 Cr | Tamil, Malayalam, Assamese |
| **Wave 3** | Months 7-9 | Gujarat, Rajasthan, MP, Karnataka, Bihar | ~27.9 Cr | 70.1 Cr | Gujarati, Kannada |
| **Wave 4** | Months 10-12 | AP, Telangana, Odisha, Punjab, Haryana, Delhi, Jharkhand, Chhattisgarh | ~21.1 Cr | 91.2 Cr | Telugu, Odia, Punjabi, Urdu |
| **Wave 5** | Months 13-15 | All remaining states + UTs | ~5.8 Cr | 97.0 Cr | Remaining |

### Why This Scaling Order?

| Wave | Reasoning |
|------|-----------|
| MVP (WB + MH) | Most acute SIR problems RIGHT NOW; elections imminent in WB; SIR Phase 3 starting in MH |
| Wave 2 | 2026 Assembly elections in TN, Kerala, Assam; UP is largest state by voters |
| Wave 3 | Large Hindi-belt states (same Devanagari parser); Karnataka has upcoming elections |
| Wave 4 | Cover 90%+ of India's voters; Telugu/Odia scripts add broad coverage |
| Wave 5 | Long tail — smaller states, NE India (mostly English/Latin script = easier) |

### Script/OCR Reuse Across States

A key insight: **many states share scripts**, so OCR models and parsers can be reused:

| Script | States Using It | Voters (Cr) | One Model Covers |
|--------|----------------|-------------|------------------|
| Devanagari | UP, MH, MP, RJ, CG, JH, UK, HP, Goa, Delhi, Haryana, Bihar | ~50+ Cr | ~52% of India |
| Bengali | WB, Tripura, parts of Assam | ~7.5 Cr | ~8% |
| Tamil | TN, Puducherry | ~6.4 Cr | ~7% |
| Telugu | AP, Telangana | ~7.3 Cr | ~8% |
| Kannada | Karnataka | ~5.3 Cr | ~5% |
| Malayalam | Kerala | ~2.7 Cr | ~3% |
| Gujarati | Gujarat | ~4.9 Cr | ~5% |
| Odia | Odisha | ~3.3 Cr | ~3% |
| Gurmukhi | Punjab | ~2.1 Cr | ~2% |
| Latin/English | NE states, some UTs | ~1.0 Cr | ~1% |

**With just 3 OCR models (Devanagari + Bengali + Latin), we cover ~61% of India's voters.**
**With 6 models (+ Tamil + Telugu + Kannada), we cover ~82%.**

### Infrastructure Scaling

| Scale | Voters | PostgreSQL | OpenSearch | Monthly Cost |
|-------|--------|-----------|-----------|-------------|
| MVP (2 states) | 16.8 Cr | 1x 16GB | 3x 8GB | $500-750 |
| Wave 2 (6 states) | 42.2 Cr | 1x 32GB | 3x 16GB | $800-1,200 |
| Wave 3 (11 states) | 70.1 Cr | 1x 64GB + replica | 5x 16GB | $1,200-1,800 |
| Full India | 97.0 Cr | Citus cluster | 7x 32GB | $2,000-3,000 |

With cloud credits ($100K-$350K), the first 2+ years of infrastructure are essentially free.

---

## 6. Action Plan — Week by Week

### Week 1: Foundation

| Day | Action | Owner | Cost | Notes |
|-----|--------|-------|------|-------|
| Mon | Register domain (sirsaathi.in) | You | $10 | Hostinger or BigRock for .in domains |
| Mon | Create GitHub repo (public, MIT license) | You | $0 | Include README with vision + architecture |
| Mon | Start Startup India registration | You | $0 | https://www.startupindia.gov.in/ |
| Tue | Apply for AWS Activate | You | $0 | Use Startup India registration as reference |
| Tue | Apply for Google for Startups Cloud | You | $0 | Parallel application |
| Wed | Download 5 sample PDFs (WB 2002, WB 2026, MH 2002, MH 2026, BMC) | You | $0 | Validate data access |
| Wed | Test ECI undocumented API | You | $0 | Verify endpoints work |
| Thu | Run PaddleOCR on WB 2002 Bengali PDF | You | $0 | Measure actual accuracy |
| Thu | Parse WB 2026 text-searchable PDF with pdfplumber | You | $0 | Validate extraction pipeline |
| Fri | Email ADR (info@adrindia.org) proposing partnership | You | $0 | Include project description |
| Fri | Post on DataMeet mailing list introducing the project | You | $0 | Invite contributors |
| Sat-Sun | Build landing page with problem statement + signup form | You | $0 | Collect emails from interested users/volunteers |

### Week 2: MVP Scaffold

| Action | Notes |
|--------|-------|
| Set up Next.js project with i18n (Bengali, Marathi, Hindi, English) | PWA-ready |
| Set up PostgreSQL schema (voter_record table) | Based on schema in RESEARCH.md |
| Build PDF download pipeline (ECI API + CEO scraping) | Start with 1 WB district |
| Build text-searchable PDF parser for WB 2026 rolls | Using pdfplumber |
| Ingest first district's data into PostgreSQL | Validate end-to-end |

### Week 3: Search & UI

| Action | Notes |
|--------|-------|
| Implement search (PostgreSQL full-text search for MVP) | Upgrade to OpenSearch later |
| Build search UI (mobile-first) | Name, EPIC, father's name, address |
| Add transliteration (Aksharamukha) | Bengali <-> Devanagari <-> Latin |
| Test with real users (friends, family in WB/MH) | Get feedback |

### Week 4: Expand & Fund

| Action | Notes |
|--------|-------|
| Apply for SISFS (Startup India Seed Fund) | Identify 3 incubators |
| Launch Milaap crowdfunding campaign | With demo video |
| Scale to all WB districts (automated pipeline) | ~294 ACs |
| Start MH 2026 roll ingestion | Same parser, different state config |
| Apply for Democracy at Work Fund | $10K-$80K |

### Month 2: Complete MVP

| Action | Notes |
|--------|-------|
| Complete WB + MH data ingestion (2026 rolls) | All districts |
| Start 2002 OCR pipeline (WB Bengali) | PaddleOCR |
| Build "What should I do?" wizard | Situation-based guidance |
| Add document checklist generator | State-specific |
| Launch publicly on Product Hunt / HackerNews | For visibility |

### Month 3: AI & Outreach

| Action | Notes |
|--------|-------|
| Integrate Claude API chatbot | Hindi, Bengali, Marathi, English |
| Build Form 7 (objection) template generator | For doubtful voters |
| Build RTI application template generator | For historical records |
| Media outreach (The Wire, Scroll.in, NDTV) | Pitch the story |
| Approach ECI after elections conclude | Show impact data |

---

## 7. Pitch Deck Outline

For grant applications, investor meetings, and crowdfunding campaigns:

### Slide 1: The Problem
- 97 crore Indians are registered voters
- SIR 2026 is the largest voter verification in 24 years
- 91 lakh names deleted in West Bengal alone
- 60 lakh voters "under adjudication" — can't vote until cleared
- Government portals are fragmented (5+ websites), confusing, and crash under load

### Slide 2: The Human Impact
- A farmer in Murshidabad who voted for 20 years finds his name deleted
- A woman in Mumbai discovers she's on the Assembly roll but not the BMC roll
- A first-time voter can't find which form to fill for which correction
- An elderly person can't navigate English-only portals
- Stories of real people losing their democratic voice

### Slide 3: The Solution — SIR Saathi
- One platform to search, verify, correct, and track voter registration
- Works in 12+ Indian languages including voice
- AI chatbot explains everything in plain language
- Free for all citizens, forever

### Slide 4: How It Works
- Demo screenshot / video of the search interface
- Show: search by name → find record → check status → get guidance → generate forms

### Slide 5: The Data
- 2002 + 2026 electoral rolls (publicly available, legally accessible)
- 330,000+ PDFs processed with OCR and NLP
- 16.8 crore voter records indexed (WB + MH)
- Scalable to 97 crore (all India)

### Slide 6: Technology
- Open-source stack: Next.js, PostgreSQL, OpenSearch, PaddleOCR
- 5-layer name matching (script normalization, AI transliteration, phonetic, fuzzy, vector)
- Built on existing open-source work (in-rolls, Aksharamukha, IndicXlit)

### Slide 7: Traction (update as you grow)
- X users in first week
- X voter records indexed
- X corrections facilitated
- X volunteers contributing

### Slide 8: Scaling Plan
- Wave 1: WB + MH (16.8 Cr voters) — NOW
- Wave 2: TN, KL, Assam, UP (+25 Cr) — Month 4
- Wave 3-5: All India (97 Cr) — Month 12
- International: Bangladesh, Pakistan, Nigeria — Year 2+

### Slide 9: Team
- Your background and motivation
- Open-source contributors
- Advisory partners (ADR, DataMeet, AI4Bharat — as onboarded)

### Slide 10: The Ask
- For grants: $X for Y months to achieve Z
- For crowdfunding: "Help us help 97 crore Indians exercise their right to vote"
- For partnerships: "Join us as [technical partner / data partner / outreach partner]"

---

## 8. Risk Mitigation

### Technical Risks

| Risk | Mitigation |
|------|-----------|
| OCR accuracy too low for 2002 rolls | Use multi-engine approach (PaddleOCR + Google Vision fallback); implement confidence scoring; flag low-confidence records for manual review |
| ECI undocumented API gets blocked | Have backup scraping pipeline; download and cache all PDFs locally; the data is public, so we can always access it |
| Scale overwhelms free tier infrastructure | Cloud credits cover 2+ years; grants kick in before credits expire |
| Name matching produces false positives | Use multi-layer matching with confidence scores; always show top-N results, not just top-1; let users confirm their identity |

### Legal Risks

| Risk | Mitigation |
|------|-----------|
| ECI objects to our use of data | Electoral rolls are public under RPA 1950 Sections 22-23; we have strong legal standing; stay transparent about methodology |
| Digital Personal Data Protection Act (DPDPA) 2023 | Electoral rolls are public documents, likely exempt; don't store Aadhaar or other sensitive PII; consult a lawyer before launch |
| Accused of political bias | Remain strictly non-partisan; open-source everything; don't accept funding from political parties; equal coverage across all states |
| Copyright claims on PDF processing | Electoral rolls are government documents; no copyright applies to factual data |

### Operational Risks

| Risk | Mitigation |
|------|-----------|
| Running out of money | Multiple funding sources (don't depend on one); keep costs minimal with free tiers and credits; open-source means community contributes labor |
| Key person dependency (just you) | Open-source from day 1; document everything; build a contributor community early; partner with organizations |
| Data becomes stale | Automated pipeline refreshes data when new rolls are published; monitor CEO websites for updates; supplementary lists auto-ingested |
| Government changes policy | Stay non-political; position as "helping the government's mission" not "opposing the government" |

### Political Risks

| Risk | Mitigation |
|------|-----------|
| SIR is politically charged (BJP vs TMC in WB, etc.) | Tool serves ALL voters regardless of party; don't take sides; open-source + transparent methodology deflects accusations |
| Accused of helping "illegal voters" | The tool helps people prove their legitimacy; we don't add/remove anyone from rolls; we help people navigate the official process |
| Government tries to shut down the tool | Multiple mirrors; open-source means anyone can fork and host; international hosting as backup; legal team via ADR |

---

## Sources & Links

### Funding
- [Startup India](https://www.startupindia.gov.in/)
- [SISFS Portal](https://seedfund.startupindia.gov.in/)
- [AWS Activate](https://aws.amazon.com/startups/credits)
- [AWS Nonprofit Credits](https://aws.amazon.com/government-education/nonprofits/nonprofit-credit-program/)
- [Google for Startups Cloud](https://cloud.google.com/startup)
- [Microsoft for Startups](https://www.microsoft.com/en-us/startups)
- [Democracy at Work Fund](https://www.ngobox.org/full_grant_announcement_Applications-Invited-for-the-Democracy-at-Work-Fund-2025-2026-Call--_13042)
- [NED Grants](https://www.ned.org/apply-for-grant/)
- [Civic Innovation Fund](https://thecivics.eu/projects/civic-innovation-fund/)
- [Open Society Foundations](https://www.opensocietyfoundations.org/grants)
- [Omidyar Network India](https://www.omidyarnetwork.in/)
- [Luminate](https://luminategroup.com/)
- [Cloud Credits Guide for Indian Startups](https://www.startupbricks.in/blog/cloud-credits-for-startups)
- [Milaap](https://milaap.org/)
- [Ketto](https://www.ketto.org/)
- [GitHub Sponsors](https://github.com/sponsors)
- [Open Collective](https://opencollective.com/)
- [TechSoup India](https://www.techsoup.org/)

### Partners
- [ADR - Association for Democratic Reforms](https://adrindia.org/)
- [MyNeta.info](https://myneta.info/)
- [DataMeet](https://datameet.org/)
- [AI4Bharat](https://ai4bharat.iitm.ac.in/)
- [Civic Data Lab](https://civicdatalab.in/)
- [Civic Tech Field Guide](https://civictech.guide/)
- [ECI ICT Apps](https://www.eci.gov.in/ict-app)

### Government Schemes
- [SISFS About](https://seedfund.startupindia.gov.in/about)
- [SISFS How to Apply](https://www.cashfree.com/blog/startup-india-seed-fund-scheme-sisfs-eligibility-how-to-apply/)
- [50+ Government Schemes for Startups](https://e-startupindia.com/learn/50-government-schemes-and-subsidies-for-startups-in-india-2025/)
- [Top Government Grants for Startups](https://hexstaruniverse.com/top-20-government-grants-for-startups-in-india/)

### CSR
- [Companies Act 2013 Section 135](https://www.mca.gov.in/Ministry/pdf/CompaniesAct2013.pdf)
- [CSR Rules](https://www.mca.gov.in/Ministry/pdf/CompaniesActNotification2_2014.pdf)
- [Infosys Foundation](https://www.infosys.com/infosys-foundation.html)
- [Wipro Foundation](https://www.wipro.com/content/wiprocorporate/en/corporate-responsibility/)
- [Azim Premji Foundation](https://azimpremjifoundation.org/)
