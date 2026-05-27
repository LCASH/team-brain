---
title: "BoostBet Racing Adapter"
aliases: [boostbet-adapter, boostbet-api, boostbet-race-card, boostbet-onboarding]
tags: [superwin, racing, scraping, api, bookie-onboarding, architecture]
sources:
  - "daily/lcash/2026-05-26.md"
created: 2026-05-26
updated: 2026-05-26
---

# BoostBet Racing Adapter

On 2026-05-26, lcash onboarded BoostBet (boostbet.com.au) as a new racing sportsbook adapter in the SuperWin value-betting scanner. The initial adapter used the `next-to-jump` endpoint but was capped at 90 races (rolling window). A same-day upgrade to two key endpoints — `GET /v1/racing/race-card/today/A` (full day card, 447 specs) and `POST /v1/racing/event-races-by-ids` (batch fetch by ID, 20-ID limit per request) — expanded coverage to 440 races (today + tomorrow), achieving 100% TAB overlap (195/195) plus 30 extra NZ/tomorrow races. No auth, no proxy, no browser needed.

## Key Points

- **Two critical endpoints**: `race-card/today/A` + `tomorrow/A` for discovery (full day card), `event-races-by-ids` POST for batch fetching (20-ID limit per request, chunked with asyncio.gather)
- **440 races total** (today + tomorrow), 195/195 TAB overlap (100%), plus 30 extra NZ/tomorrow races — more coverage than TAB when including tomorrow's card
- **No auth, no proxy, no browser** — pure HTTP REST, same simplicity class as Betr/BlueBet
- **`next-to-jump` is inadequate** — capped at 90 races in a rolling ~6-8hr window; only 54 AU/NZ races vs TAB's 197
- **Tiered cadence**: hot ≤60min → 3s, warm ≤4h → 9s, cold → 45s polling intervals
- **Batch POST has hard 20-ID limit** — exceeding silently truncates; 213 races requires ~11 parallel requests
- **Promo/boost product exists** (`/v1/benefits/dividend-boosts`) — auth-gated, needs Phase 2 investigation
- **Next.js SSR + CloudFront + Cloudflare** infrastructure — static recon found zero WS references across 25 JS bundles

## Details

### Discovery Architecture

The adapter went through two phases in a single day. Phase 1 used the `next-to-jump` endpoint, which returns a rolling window of upcoming races across all venues. This proved inadequate: the window caps at approximately 90 races spanning ~6-8 hours, producing only 54 AU/NZ races versus TAB's 197. For full-day edge scanning coverage, the adapter needs visibility into all races for the current day plus early next-day markets.

Phase 2 discovered two superior endpoints via browser network capture:

**`GET /v1/racing/race-card/today/A`** — returns the complete Australian racing day card with 447 race specifications. Combined with the `tomorrow/A` variant, this provides full coverage of both today's and tomorrow's early card. The `A` suffix appears to indicate the Australian jurisdiction filter.

**`POST /v1/racing/event-races-by-ids`** — accepts an array of race IDs and returns full race data including runners, odds, and metadata. The endpoint has a hard 20-ID batch limit; exceeding this silently truncates the response (same pattern as BoostBet's — no error, just missing data). The adapter chunks requests into groups of 20 and fires them in parallel via `asyncio.gather`, completing ~213 races in approximately 11 parallel requests.

### Coverage Comparison

| Source | Races | Assessment |
|--------|-------|------------|
| next-to-jump (Phase 1) | 54 AU/NZ | Inadequate — rolling window misses ~75% of day |
| race-card today+tomorrow (Phase 2) | 440 | Full day + tomorrow early card |
| TAB (reference) | 197 | Benchmark soft book |
| Overlap with TAB | 195/195 (100%) | Perfect coverage parity |

BoostBet actually covers MORE races than TAB when including tomorrow's card — particularly harness racing (44 BoostBet vs 15 TAB), which is the scanner's most profitable segment.

### Implementation Details

The Race constructor must use canonical model field names, not flat-model names — a subtle distinction that caused early smoke test failures. Cumulative `race_count` tracking is essential: per-cycle count (9 races per fetch cycle) is misleading versus the true coverage (440 total across all tiers).

The adapter follows the same registration pattern as other bookies: Supabase row in `bookies` table with `poll_interval`, `discovery_interval`, `is_canonical`, and `needs_browser` fields, plus `edges` table entries for `bb-normal` (value mode) and `racing-run-2nd-3rd-boostbet` (refund-as-bonus mode).

### Recon Findings

Static recon of boostbet.com.au scanned 25 JS bundles and probed common WS/API endpoints — zero `wss://` references found. The site uses Next.js SSR with CloudFront CDN and Cloudflare protection (not Akamai, despite initial JS lib match). The REST API is fully private: `/api`, `/api/v1/*`, `/api/racing`, `/api/markets` all return 404 for unauthenticated requests. Data is served via Next.js SSR fetch to internal paths, but the racing card endpoints were discovered to be publicly accessible.

Live browser recon via AdsPower (profile `k19yb91n`) with Playwright CDP WebSocket monitoring confirmed no lazy-loaded WS connections — BoostBet is pure HTTP for racing odds delivery.

## Related Concepts

- [[concepts/betr-bluebet-api-integration]] - Same integration simplicity class: no auth, plain HTTP, no browser needed
- [[concepts/tab-scraper-threshold-markets]] - TAB is the coverage benchmark that BoostBet achieves 100% overlap with
- [[concepts/superwin-racing-profitability-dimensions]] - Harness racing is the scanner's most profitable segment; BoostBet's extra harness coverage (44 vs 15 TAB) adds value
- [[concepts/scanner-warmup-false-ev-guard]] - Warmup guard applies to BoostBet ramp-up alongside other bookies

## Sources

- [[daily/lcash/2026-05-26.md]] - Phase 1: next-to-jump capped at 90 races, only 54 AU/NZ vs TAB 197. Phase 2: race-card/today/A + tomorrow/A for discovery, event-races-by-ids POST for batch fetch (20-ID limit, asyncio.gather parallelism); 440 total races, 195/195 TAB overlap; tiered cadence hot≤60m→3s, warm≤4h→9s, cold→45s; no auth/proxy/browser; Next.js+CloudFront+Cloudflare infra; boost product auth-gated; commits 1a25db2 (Phase 1), 3c29314 (day-card upgrade) (Sessions 10:43, 11:45)
