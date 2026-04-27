---
title: "TabTouch Kambi White-Label Sports Platform"
aliases: [kambi-api, tabtouch-kambi, kambi-white-label, tabtouch-sports-api, kambi-betoffer]
tags: [superwin, tabtouch, kambi, scraping, reverse-engineering, value-betting, sports-betting]
sources:
  - "daily/lcash/2026-04-26.md"
  - "daily/lcash/2026-04-27.md"
created: 2026-04-26
updated: 2026-04-27
---

# TabTouch Kambi White-Label Sports Platform

On 2026-04-26, lcash discovered that TabTouch's sports betting section is powered by **Kambi** — a white-label sportsbook platform completely separate from TabTouch's racing product (which uses AWS IoT MQTT). The Kambi REST API at `ap.offering-api.kambicdn.com` is fully public with no authentication, cookies, or TLS fingerprinting required. It provides full player names (eliminating the name normalization problem seen with TAB.com.au), stable `participantId` values across markets, and delivers 242 player prop markets from a single NBA game endpoint. A Kambi push service via Socket.IO provides real-time odds updates (763 messages in 120 seconds during testing).

## Key Points

- **TabTouch sports = Kambi white-label** — the API is at `ap.offering-api.kambicdn.com`, completely separate from the racing MQTT platform at `tabtouch.com.au`
- Kambi REST API requires **no auth, no cookies, no TLS fingerprinting** — dramatically simpler than TAB.com.au (which needs `curl_cffi` for Akamai) or bet365 (which needs headed Chrome + CDP)
- **Full player names** ("Anthony Edwards" not "A Edwards") — eliminates the abbreviation-to-full-name resolution problem documented in [[concepts/tab-scraper-threshold-markets]]
- **Stable `participantId`** values across all markets for the same player — makes cross-market correlation trivial (unlike bet365's coupon-PM ID mismatch)
- **betOffer types**: type 2 = over/under (line-based player props), type 1 = 1x2/moneyline; player props use `criterion.id` to identify stat category (points, rebounds, assists, etc.)
- 426 betOffers captured from a single NBA game endpoint, including 242 player prop markets — comparable to bet365's batch API coverage
- Kambi push uses **Socket.IO** at `push-ap.offering-api.kambicdn.com` — 763 real-time odds updates in 120 seconds
- TabTouch runs **two completely independent streaming systems**: AWS IoT MQTT (racing/tote) and Kambi Socket.IO (sports odds)

## Details

### Discovery

On 2026-04-26, lcash navigated an AdsPower browser to TabTouch's basketball page and captured network traffic. The API calls were not going to `tabtouch.com.au` endpoints (used for racing) but to `ap.offering-api.kambicdn.com` — a CDN-hosted API belonging to Kambi, a B2B sportsbook platform provider that powers multiple betting operators worldwide. TabTouch is a Kambi client for their sports betting product while maintaining their own proprietary racing platform.

This is architecturally significant: TabTouch is not one platform but two completely independent ones stitched together under a single brand. The racing product (documented in [[concepts/tabtouch-domain-migration-mqtt]]) uses SSR HTML + Knockout.js + AWS IoT MQTT with Cognito authentication. The sports product uses Kambi's standardized REST API and Socket.IO push service. Different tech stacks, different data formats, different authentication models (Cognito for racing, none for sports), and different CDN infrastructure.

### API Architecture

The Kambi REST API follows a clean, well-documented structure:

**Discovery**: The offering endpoint returns all available events for a sport with inline betOffers. A single request to the NBA competition endpoint returns the full slate of games with all markets — no pagination, no per-game fetching required. Testing returned 426 betOffers from a single game, with 242 being player prop markets.

**betOffer Structure**: Each betOffer has a `type` field: type 2 for over/under (line-based, used for all player props), type 1 for 1x2/moneyline (used for game outcomes). Player props use a `criterion.id` field to identify the stat category — a partial mapping was documented during the session (covering points, rebounds, assists, threes, blocks, steals, turnovers). Each betOffer contains `outcomes` with decimal odds and line values.

**Player Identity**: Kambi uses full, properly formatted player names ("Anthony Edwards", "Victor Wembanyama") with stable `participantId` values that are consistent across all betOffers for the same player. This eliminates two problems that required complex workarounds in other scrapers: the name abbreviation resolution needed for TAB.com.au (see [[concepts/tab-scraper-threshold-markets]]) and the participant ID mismatch between coupon and PM data in bet365 (see [[concepts/bet365-coupon-pm-id-mismatch]]).

### Real-Time Push Service

Kambi provides real-time odds updates via Socket.IO at `push-ap.offering-api.kambicdn.com`. During a 120-second capture window, 763 push messages were received containing live odds and line updates. This is significantly denser than TabTouch's racing MQTT stream (721 updates in 8.5 minutes) and provides sub-second odds freshness for sports markets.

The push service operates independently of the racing MQTT stream — TabTouch runs two WebSocket-based real-time systems simultaneously:

| System | Protocol | Purpose | Auth |
|--------|----------|---------|------|
| AWS IoT MQTT | MQTT over WebSocket | Racing/tote odds | Cognito anonymous |
| Kambi Push | Socket.IO | Sports odds | None observed |

### Comparison to Other Soft Book Scrapers

| Dimension | Kambi (TabTouch Sports) | TAB.com.au | bet365 |
|-----------|----------------------|------------|--------|
| Auth required | None | Akamai (curl_cffi) | Headed Chrome + CDP |
| Player names | Full | Abbreviated ("A Edwards") | Full (BB wizard) |
| Player IDs | Stable across markets | N/A | Coupon ≠ PM IDs |
| Prop coverage | 242/game (NBA) | ~326/game (near-tipoff) | 332/game (dual endpoint) |
| Real-time | Socket.IO push | N/A (REST polling) | WS (racing only), HTTP poll (props) |
| Implementation effort | Low (public REST) | Medium (Akamai bypass) | High (browser automation) |

Kambi is the simplest soft book integration yet discovered — no browser automation, no anti-bot bypass, no authentication of any kind. The REST API is designed for consumption by Kambi's own white-label clients and is publicly accessible.

### Implementation Plan

A Kambi scraper adapter for the value betting scanner should:

1. **REST poller** — poll the NBA/MLB competition endpoints on the Kambi API at ~60s intervals, parse betOffers into the scanner's market format
2. **Criterion mapping** — map Kambi `criterion.id` values to the scanner's internal prop type identifiers (points, rebounds, assists, etc.)
3. **Book ID assignment** — assign a new book_id for TabTouch Kambi (distinct from TAB.com.au's 908)
4. **Optional: Socket.IO streaming** — for sub-second updates, implement a Socket.IO client to receive push messages (Phase 2, after REST polling proves stable)

MLB data should be captured from the Kambi baseball endpoint to confirm player prop structure matches the NBA format — if Kambi uses the same betOffer schema across sports (likely, as it's a standardized platform), the scraper adapter is sport-agnostic.

### Production Deployment (2026-04-27)

On 2026-04-27, the Kambi scraper was built and deployed as book_id **909** (TabTouch Kambi), integrated directly into `direct_scraper_worker.py` alongside TAB polling at 60-second REST intervals. Key deployment findings:

- **Book ID 909** was already present in `SOFT_BOOK_IDS` and `BOOK_NAMES` — no additional configuration needed
- **MLB confirmed**: 182 betOffers per game with 11 player prop types (Home Runs, Hits, Runs, Bases, RBIs, Doubles, Strikeouts, Stolen Bases, Outs, and more) — proper Over/Under lines, not just thresholds like TAB
- **Key structural difference from TAB**: Kambi returns **1 outcome per betOffer** (Over OR Under separately), while TAB returns 2 outcomes per market. The scraper parses each betOffer independently rather than pairing them
- **Integer encoding**: Odds are `odds_value / 1000` (e.g., 1850 → 1.85 decimal), lines are `line / 1000` (e.g., 5500 → 5.5)
- **106 unique criterion labels** for NBA — mapped to the scanner's internal prop type identifiers
- **Operator codes**: `rwwawa` = TabTouch/RWWA; Kambi powers multiple AU bookies with the same API structure, just different operator codes
- **`participantId`** confirmed stable across all markets for the same player — useful for cross-market player matching
- **WebSocket upgrade deferred**: REST polling at 60s is sufficient for initial deployment; Socket.IO consumer for sub-second updates is Phase 2

### AdsPower Session Management Gotcha

During the Kambi discovery session, AdsPower browser session management exhibited finicky behavior: profile WebSocket endpoints went stale when the browser restarted, and the browser opened to a cached page (Twitter from a prior login pipeline session) instead of the requested URL. This is an operational nuance of using AdsPower for network traffic capture — the profile state persists across sessions and may need manual navigation to the target page before traffic analysis.

## Related Concepts

- [[concepts/tabtouch-domain-migration-mqtt]] - TabTouch's racing platform (MQTT) is completely separate from the Kambi sports platform; the two systems share a brand but no technology
- [[concepts/tab-scraper-threshold-markets]] - TAB.com.au (book_id 908) uses abbreviated player names requiring self-contained resolution; Kambi eliminates this problem with full names
- [[concepts/bet365-coupon-pm-id-mismatch]] - bet365's participant ID mismatch between data sources required barrier-number fallback joins; Kambi's stable participantId avoids this entirely
- [[connections/anti-scraping-driven-architecture]] - bet365's six-layer defense stack forces browser automation; Kambi has zero anti-scraping, requiring only standard HTTP requests
- [[concepts/opticodds-sse-streaming-scaling]] - Kambi Socket.IO provides an alternative real-time data path independent of OpticOdds SSE; could serve as a redundant odds source

## Sources

- [[daily/lcash/2026-04-26.md]] - AdsPower browser traffic capture revealed TabTouch sports = Kambi white-label; API at `ap.offering-api.kambicdn.com` requires no auth; 426 betOffers including 242 player props from single NBA game; full player names and stable participantIds; Kambi push via Socket.IO (763 messages/120s); two independent streaming systems (MQTT racing + Socket.IO sports); betOffer types: type 2 = over/under, type 1 = moneyline; criterion.id maps to stat categories; AdsPower session management gotcha (Session 22:10)
- [[daily/lcash/2026-04-27.md]] - Production deployment: book_id 909, REST polling at 60s in direct_scraper_worker.py; MLB confirmed 182 betOffers / 11 prop types with proper O/U lines; 1 outcome per betOffer (vs TAB's 2); integer encoding odds/1000, line/1000; 106 unique NBA criterion labels; operator code `rwwawa` = TabTouch/RWWA; participantId stable across markets confirmed; WebSocket deferred to Phase 2 (Session 07:38)
