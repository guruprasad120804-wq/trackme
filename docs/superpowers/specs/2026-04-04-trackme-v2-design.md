# TrackMe v2 — Design Specification

## 1. Product Vision

TrackMe is a next-generation portfolio tracking and financial intelligence platform for Indian investors. It replaces and dramatically improves upon Mprofit by providing:

- **Multi-asset tracking** across all brokers (stocks, mutual funds, ETFs, bonds, gold, NPS, PPF, FDs, crypto)
- **AI-powered conversational assistant** for portfolio analysis
- **Real-time alerts** via push, email, and WhatsApp
- **Automated data ingestion** from broker APIs, CAS PDFs, email scanning, and manual entry
- **Premium fintech UI** with dark navy + amber design language

### How TrackMe Beats Mprofit

| Dimension | Mprofit | TrackMe |
|---|---|---|
| Asset types | Stocks, MF, bonds | 10+ asset types including crypto, NPS, PPF |
| Broker integration | Manual CSV import | Direct API + CAS PDF + email scan + manual |
| UI/UX | Dated desktop app | Modern web + mobile, premium dark theme |
| AI | None | Claude-powered portfolio assistant |
| Alerts | Basic | Multi-channel (push, email, WhatsApp) with rule engine |
| WhatsApp | None | Full bot for queries, alerts, portfolio checks |
| Auth | Password-based | Google OAuth with multi-device sync |
| Pricing | One-time license | Freemium SaaS with tiered subscriptions |
| Mobile | No | Mobile-first responsive web, React Native planned |
| Real-time | Manual refresh | WebSocket + scheduled background updates |

---

## 2. System Architecture

### Tech Stack

- **Backend:** FastAPI (Python 3.12), SQLAlchemy 2.0 async, PostgreSQL 16, Redis 7, Celery 5
- **Frontend:** Next.js 15, TypeScript, Tailwind CSS, shadcn/ui, Recharts, Framer Motion
- **AI:** Anthropic Claude API (Sonnet 4 for chat, portfolio RAG)
- **WhatsApp:** Meta WhatsApp Business Cloud API
- **Payments:** Razorpay (India)
- **Auth:** Google OAuth 2.0 → JWT (access + refresh tokens)
- **Deployment:** Docker Compose (dev), Kubernetes (prod)

### Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                        CLIENTS                                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐   │
│  │ Next.js  │  │  Mobile  │  │ WhatsApp │  │ Email/Gmail   │   │
│  │  Web App │  │  (RN)    │  │  Bot     │  │  Webhook      │   │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘  └──────┬────────┘   │
└────────┼─────────────┼─────────────┼───────────────┼────────────┘
         │             │             │               │
         ▼             ▼             ▼               ▼
┌──────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                               │
│  ┌─────────┐  ┌──────────┐  ┌────────┐  ┌──────────────────┐   │
│  │  Auth   │  │ Dashboard│  │ Alert  │  │  AI Assistant    │   │
│  │  API    │  │ Portfolio│  │ Engine │  │  (Claude RAG)    │   │
│  │  (JWT)  │  │ Txns API │  │  API   │  │                  │   │
│  └─────────┘  └──────────┘  └────────┘  └──────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              Subscription & Feature Gating              │    │
│  └─────────────────────────────────────────────────────────┘    │
└────────────────────────────┬─────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐
│  PostgreSQL  │   │    Redis     │   │      Celery          │
│  (Data)      │   │ (Cache/Queue)│   │  ┌────────────────┐  │
│              │   │              │   │  │ NAV Updater    │  │
│  - Users     │   │  - Sessions  │   │  │ Email Scanner  │  │
│  - Holdings  │   │  - Cache     │   │  │ Alert Checker  │  │
│  - Txns      │   │  - Task Q    │   │  │ Price Updater  │  │
│  - Alerts    │   │              │   │  │ CAS Importer   │  │
│  - Chat      │   │              │   │  └────────────────┘  │
└──────────────┘   └──────────────┘   └──────────────────────┘
```

### Key Design Decisions

1. **Async everywhere:** FastAPI + asyncpg + async SQLAlchemy for non-blocking I/O
2. **Celery for background work:** NAV updates, email scanning, alert evaluation, CAS parsing — all async
3. **Universal Asset model:** Single `assets` table + type discriminator, NOT separate tables per asset type
4. **Holdings-based architecture:** Positions tracked as Holdings linked to Assets, not embedded in Folios
5. **Feature gating via middleware:** Subscription plan limits enforced at the API dependency level

---

## 3. Database Schema

### Core Tables (14 tables)

**Users & Auth:**
- `users` — Google OAuth users (email, name, avatar, google_id)
- `subscriptions` — Plan (free/pro/premium), status, Razorpay IDs, usage counters

**Portfolio:**
- `portfolios` — User's named portfolios (default "My Portfolio")
- `assets` — Universal asset master (type: stock/mf/etf/bond/gold/fd/nps/ppf/crypto/other)
- `holdings` — User's position in an asset within a portfolio (qty, avg cost, current value, XIRR)
- `transactions` — All buy/sell/dividend/SIP/switch transactions with dedup constraints

**Broker Integration:**
- `brokers` — Master list of supported brokers
- `broker_connections` — User's linked broker accounts (encrypted credentials)

**Market Data:**
- `current_prices` — Latest price per asset (updated real-time for stocks, daily for MFs)
- `price_history` — OHLCV daily history

**Mutual Fund Specific:**
- `fund_houses`, `schemes`, `folios`, `nav_history`

**Alerts:**
- `alerts` — Rule definitions (condition, threshold, channels, recurring flag)
- `alert_history` — Trigger log with notification status

**AI Chat:**
- `chat_conversations`, `chat_messages`

**Data Import:**
- `import_logs`, `email_configs` (encrypted), `processed_emails`

**WhatsApp:**
- `whatsapp_configs` — Phone verification and active status

---

## 4. Data Integration Design

### Layer 1: Broker APIs (Direct Integration)
Standardized broker adapter pattern:
```
BrokerAdapter (abstract)
├── ZerodhaAdapter (Kite Connect API)
├── GrowwAdapter
├── UpstoxAdapter
├── AngelOneAdapter
└── ... (pluggable)
```
Each adapter implements: `authenticate()`, `get_holdings()`, `get_transactions()`, `sync()`.

### Layer 2: CAS PDF Import
- Uses `casparser` library for CAMS/KFintech formats
- Parses investor, folio, scheme, and transaction data
- Deduplication via unique constraints on transactions
- Background processing via Celery

### Layer 3: Email Scanning
- Gmail OAuth integration
- Searches for CAS PDFs from known senders (CAMS, KFintech)
- Auto-downloads, parses, and imports
- Tracks processed emails to avoid duplicates
- Runs every 6 hours via Celery Beat

### Layer 4: Manual Entry
- Smart asset resolution (search by name, symbol, ISIN)
- Auto-fill suggestions from existing assets
- Holding position auto-updated on transaction entry

---

## 5. API Design

### Auth
- `POST /api/v1/auth/google` — Exchange Google auth code for JWT tokens
- `POST /api/v1/auth/refresh` — Refresh access token
- `GET /api/v1/auth/me` — Get current user profile

### Dashboard
- `GET /api/v1/dashboard/summary` — Total invested, value, gain, day change, XIRR, allocation breakdown
- `GET /api/v1/dashboard/holdings` — All holdings with sorting/filtering
- `GET /api/v1/dashboard/top-movers` — Today's biggest movers in portfolio

### Portfolio
- `GET /api/v1/portfolio/` — List user's portfolios
- `POST /api/v1/portfolio/` — Create new portfolio
- `GET /api/v1/portfolio/{id}/holdings` — Holdings in a specific portfolio

### Transactions
- `GET /api/v1/transactions/` — Paginated, filtered transaction list

### Alerts
- `GET /api/v1/alerts/` — List alerts
- `POST /api/v1/alerts/` — Create alert
- `PATCH /api/v1/alerts/{id}/toggle` — Enable/disable
- `DELETE /api/v1/alerts/{id}` — Delete
- `GET /api/v1/alerts/history` — Trigger history

### AI Chat
- `POST /api/v1/chat/` — Send message, get AI response
- `GET /api/v1/chat/conversations` — List conversations
- `GET /api/v1/chat/conversations/{id}/messages` — Get messages
- `DELETE /api/v1/chat/conversations/{id}` — Delete conversation

### Subscription
- `GET /api/v1/subscription/` — Current plan and limits
- `GET /api/v1/subscription/plans` — Available plans with pricing
- `POST /api/v1/subscription/checkout` — Create Razorpay order
- `POST /api/v1/subscription/verify` — Verify payment, activate plan

### Import
- `POST /api/v1/import/cas-upload` — Upload CAS PDF
- `POST /api/v1/import/manual` — Manual transaction entry
- `GET /api/v1/import/history` — Import history
- `POST /api/v1/import/email/scan-now` — Trigger email scan

---

## 6. UI/UX Structure

### Design Language
- **Background:** Dark Navy (#0A1628)
- **Card/Surface:** (#111D35), (#1A2742)
- **Accent:** Warm Amber (#F5A623)
- **Success:** Emerald (#10B981)
- **Danger:** Red (#EF4444)
- **Text:** White (#F1F5F9), Muted (#94A3B8)
- **Borders:** Subtle navy (#1E3A5F)

### Screens (8 pages built)

1. **Login** — Split layout: left branding + right Google OAuth button
2. **Dashboard** — 4 stat cards + performance area chart + allocation pie + holdings list + top movers
3. **Portfolio** — Portfolio cards + filterable holdings table (9 columns)
4. **Transactions** — Paginated table with search, type badges, export button
5. **Alerts** — Active alerts list with toggle/delete + alert history tab
6. **AI Chat** — Conversation sidebar + chat area with suggestions + streaming responses
7. **Settings** — Tabbed layout: Profile, Import Data, Email Scanning, WhatsApp, Subscription
8. **Settings/Subscription** — Current plan card + upgrade plan cards with feature lists

---

## 7. AI Chat Design

The AI assistant uses Claude Sonnet 4 with portfolio-aware RAG:

1. On each message, the system builds a **portfolio context snapshot** (all holdings, values, gains)
2. This snapshot is injected into the system prompt
3. Conversation history (last 20 messages) provides continuity
4. The AI can answer: portfolio questions, investment summaries, risk analysis, financial concepts
5. Hard guardrail: NO specific buy/sell recommendations (compliance)

### System Prompt Structure
```
[System role and rules]
[User's portfolio snapshot: total invested, current value, gain, all holdings with details]
[Conversation history]
[User's message]
```

---

## 8. WhatsApp Bot Architecture

```
User (WhatsApp) → Meta Cloud API → Webhook (FastAPI) → Bot Handler → Response
                                                            │
                                                    ┌───────┴───────┐
                                                    │ Command Router │
                                                    ├── /portfolio   │
                                                    ├── /holdings    │
                                                    ├── /alerts      │
                                                    ├── /value       │
                                                    ├── /help        │
                                                    └── [AI fallback]│
                                                    └────────────────┘
```

- Webhook verification via GET challenge
- Signature verification on POST (HMAC SHA256)
- Commands for quick data; free-text routed to AI assistant
- User linked via verified phone number in `whatsapp_configs`

---

## 9. Subscription Model

| Feature | Free | Pro (₹299/mo) | Premium (₹599/mo) |
|---|---|---|---|
| Portfolios | 1 | 5 | Unlimited |
| Broker connections | 1 | 5 | Unlimited |
| Alerts | 3 | 25 | Unlimited |
| AI queries/day | 5 | 50 | Unlimited |
| WhatsApp bot | No | Yes | Yes |
| Email scanning | No | Yes | Yes |
| Excel export | No | Yes | Yes |
| Advanced analytics | No | Yes | Yes |
| Priority support | No | No | Yes |
| API access | No | No | Yes |

Yearly pricing: Pro ₹2,999 (save 16%), Premium ₹5,999 (save 17%).

Feature gating enforced via `require_feature()` FastAPI dependency.

---

## 10. Scaling Strategy

### Phase 1 (0-10K users): Current Architecture
- Single PostgreSQL + Redis
- 2-4 Celery workers
- Docker Compose deployment

### Phase 2 (10K-100K users):
- PostgreSQL read replicas
- Redis Cluster
- Celery autoscaling
- CDN for frontend (Vercel/Cloudflare)
- Connection pooling (PgBouncer)

### Phase 3 (100K-1M users):
- Kubernetes with horizontal pod autoscaling
- Database sharding by user_id
- Dedicated market data service (WebSocket feeds)
- Dedicated AI service with response caching
- Event-driven architecture (Kafka/Redis Streams)
- Rate limiting per plan tier

### Phase 4 (1M+ users):
- Multi-region deployment
- TimescaleDB for time-series price data
- Dedicated alerting microservice
- ML pipeline for personalized insights
- gRPC between internal services

---

## 11. Risks & Mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| Broker API changes/breakage | Data sync fails | Adapter pattern isolates changes; fallback to CAS/manual |
| Financial data accuracy | User trust | Reconciliation checks; dedup constraints; audit logs |
| Security breach | Critical | Fernet encryption at rest; JWT with short expiry; no PII in logs |
| AI hallucinations | Compliance risk | Hard guardrails in prompt; disclaimer in UI; no buy/sell advice |
| Razorpay downtime | Revenue loss | Graceful degradation; webhook retry; manual activation path |
| WhatsApp API rate limits | Bot degradation | Queue outbound messages; respect rate limits |
| Celery task failures | Stale data | Dead letter queue; retry policies; monitoring alerts |
| CAS format changes | Import breaks | casparser maintained upstream; fallback to AI parsing |
| Scale beyond single DB | Performance | Planned migration path to sharded architecture |
